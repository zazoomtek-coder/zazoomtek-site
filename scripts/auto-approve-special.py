#!/usr/bin/env python3
"""Strict unattended source-grounded approval. No approvals from titles or RSS alone."""
import datetime as dt
from difflib import SequenceMatcher
import hashlib,json,os,re,unicodedata,urllib.parse,urllib.request,urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
KEY=os.environ.get("GEMINI_API_KEY","").strip()
MODEL=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite")
def norm(s):return re.sub(r"\s+"," ",str(s)).casefold().strip()
def slug(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",s).strip("-")[:85].strip("-")
def domain(url):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:return ""
    h=p.hostname.lower().removeprefix("www.")
    return "" if h in ("news.google.com","google.com","localhost") else h
def primary(h):
    return h.endswith((".gov",".gov.uk",".gov.au",".europa.eu")) or h in ("ico.org.uk","edpb.europa.eu")
def material(x):
    docs=[];seen=set()
    for row in x.get("sources",[])[:3]:
        if row.get("result")!="retrieved":continue
        d=row.get("data") or {};host=domain(d.get("url",""))
        excerpt=" ".join(d.get("excerpts",[]))
        if not host or host in seen or len(excerpt.split())<175:continue
        docs.append({"url":d["url"],"text":excerpt,"excerpts":d.get("excerpts",[])[:10],"metadata":d.get("metadata",{})})
        seen.add(host)
    # A long, retrieved original report can be checked fact-by-fact without
    # manufacturing a second source. Source URLs, body and metadata are required.
    # For an ordinary newsroom story, always attribute reporting in the article.
    authoritative=any(primary(domain(d["url"])) for d in docs)
    independent=len(seen)>=2
    documented_single=(len(docs)==1 and
        len(docs[0]["text"].split())>=240 and
        len(docs[0]["excerpts"])>=3 and
        bool((docs[0]["metadata"].get("og:title") or
              docs[0]["metadata"].get("description"))))
    return docs if authoritative or independent or documented_single else []
def duplicate(article,existing):
    x=norm(article["title"])
    urls=set(article.get("source_urls",[]))
    for a in existing:
        if a.get("section")!=article["section"]:continue
        if SequenceMatcher(None,x,norm(a.get("title",""))).ratio()>=.73:return True
        if urls.intersection(set(a.get("sources",[]))):return True
    return False
def review(article,docs):
    if not KEY:raise RuntimeError("GEMINI_API_KEY missing")
    prompt=("""Sei un verificatore indipendente di ZazoomTek. Esamina ogni paragrafo della
bozza confrontandolo con le fonti originali allegate. Non usare informazioni esterne,
non inventare citazioni. Rifiuta se esiste anche UNA affermazione non documentata,
una data dubbia, un'accusa non attribuita, un titolo sensazionalistico o due fonti che
descrivono eventi differenti. Rifiuta testi troppo simili al copyright delle fonti.
Una singola fonte giornalistica originale approfondita è ammissibile se ogni
affermazione è supportata dall'articolo e attribuita correttamente, senza presentare
il racconto della fonte come indagine autonoma di ZazoomTek.
Per ogni paragrafo fornisci una CITAZIONE LETTERALE di 28-160 caratteri presa
dagli estratti a sostegno dei fatti del paragrafo; queste citazioni NON saranno
pubblicate. Rispondi SOLO JSON:
{"publish":true/false,"headline_supported":true/false,"summary_supported":true/false,"unsupported_indices":[0],"supported":[{"index":0,"quote":"citazione letterale presente negli estratti"}],"reason":"..."}
SEZIONE: """+article["section"]+"\nARTICOLO: "+json.dumps(
        {k:article[k] for k in ("title","summary","paragraphs")},ensure_ascii=False)+
        "\nFONTI: "+json.dumps([{"url":d["url"],"metadata":d["metadata"],"excerpts":d["excerpts"]}
                             for d in docs],ensure_ascii=False)[:15000])
    request=urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent",
        method="POST",headers={"Content-Type":"application/json","x-goog-api-key":KEY},
        data=json.dumps({"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"responseMimeType":"application/json","temperature":0,
                                "maxOutputTokens":1850}}).encode("utf-8"))
    with urllib.request.urlopen(request,timeout=75) as res:out=json.load(res)
    answer="".join(part.get("text","") for c in out.get("candidates",[])
                   for part in c.get("content",{}).get("parts",[]))
    return json.loads(answer)
def verified(article,docs,audit):
    text=article.get("paragraphs")
    if not isinstance(text,list) or not 3<=len(text)<=8 or any(
        not isinstance(p,str) or len(p.strip())<100 for p in text):return False
    if not isinstance(article.get("title"),str) or not 25<=len(article["title"])<=170:return False
    if not isinstance(article.get("summary"),str) or not 65<=len(article["summary"])<=420:return False
    if not 300<=len(" ".join([article["title"],article["summary"]]+text).split())<=600:return False
    if article.get("status")!="needs_human_fact_check":return False
    if not isinstance(audit,dict) or audit.get("publish") is not True or audit.get("unsupported_indices"):return False
    if audit.get("headline_supported") is not True or audit.get("summary_supported") is not True:return False
    grounded=set();quotes=set()
    corpus=[norm(d["text"]) for d in docs]
    for row in audit.get("supported",[]):
        if not isinstance(row,dict):continue
        i=row.get("index");q=norm(row.get("quote",""))
        if type(i) is int and 0<=i<len(text) and 28<=len(q)<=180 and any(q in c for c in corpus):
            grounded.add(i);quotes.add(q)
    return grounded==set(range(len(text))) and len(quotes)>=3
def main():
    saved=ROOT/"approved-special-articles.json"
    existing=json.loads(saved.read_text(encoding="utf-8"))
    old=existing["articles"]
    drafts=json.loads((ROOT/"special-full-articles-review.json").read_text(encoding="utf-8")).get("articles",[])
    evidence=json.loads((ROOT/"special-source-evidence.json").read_text(encoding="utf-8")).get("items",[])
    selected=json.loads((ROOT/"special-drafts-review.json").read_text(encoding="utf-8")).get("gemini_model","")
    global MODEL
    if isinstance(selected,str) and re.fullmatch(r"gemini-[a-z0-9.\-]+",selected):MODEL=selected
    by_subject={(x.get("section"),x.get("title")):x for x in evidence}
    created=[];log=[];counts={"tech":0,"gaming":0};now=dt.datetime.now(dt.timezone.utc)
    for x in drafts:
        if not isinstance(x,dict):continue
        sec=x.get("section")
        if sec not in counts or counts[sec]>=({"tech":2,"gaming":1}[sec]):continue
        why=""
        source_record=by_subject.get((sec,x.get("topic")))
        if source_record is None and isinstance(x.get("source_urls"),list):
            # Recover topic linkage if an older draft omitted its source title.
            matching=[v for v in evidence
              if v.get("section")==sec and any(
                row.get("data",{}).get("url") in x["source_urls"]
                for row in v.get("sources",[]) if isinstance(row,dict))]
            if len(matching)==1:source_record=matching[0]
        docs=material(source_record or {})
        if not docs:why="Insufficient original reporting or primary-source evidence"
        elif duplicate(x,old+created):why="Topic or original source already published"
        elif sec=="gaming" and not re.search(r"(?i)videogioc|videoludic|gaming|giocator|game|playstation|xbox|nintendo|steam|diablo|call.of.duty",(x.get("topic") or "")+" "+x.get("title","")):why="Not a gaming policy topic"
        elif x.get("status")!="needs_human_fact_check":why="Not a complete draft"
        else:
            try:assessment=review(x,docs)
            except (ValueError,KeyError,urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as e:
                why="Verification request failed: "+type(e).__name__
            else:
                if not verified(x,docs,assessment):why="Factual paragraph verification failed"
        if why:
            log.append({"topic":x.get("topic",""),"section":sec,"status":"rejected","reason":why})
            continue
        sl=slug(x["title"])
        if len(sl)<12:continue
        srcs=[d["url"] for d in docs]
        new={
            "section":sec,"slug":sl,"title":x["title"].strip(),
            "summary":x["summary"].strip(),"paragraphs":[p.strip() for p in x["paragraphs"]],
            "date":now.date().isoformat(),"sources":srcs,
            "editor_approved":False,"auto_approved":True,
            "approval_method":"strict_source_evidence",
            "evidence_review":{"paragraphs_supported":True,"source_count":len(srcs),
               "official_source":any(primary(domain(u)) for u in srcs),
               "verified_at":now.isoformat()},
            "source_fingerprints":[hashlib.sha256(u.encode()).hexdigest()[:16] for u in srcs],
            "featured":True,"cover_mode":"auto"
        }
        created.append(new);counts[sec]+=1
        log.append({"topic":x["title"],"section":sec,"status":"source_verified_auto_approved"})
    (ROOT/"special-auto-report.json").write_text(json.dumps({
        "generated_utc":now.isoformat(),"approved_count":len(created),"review":log
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if created:
        existing["articles"]=old+created
        saved.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Verified automatic approvals:",len(created),"; rejected:",sum(r["status"]=="rejected" for r in log))
def self_test():
    assert primary("digital-strategy.ec.europa.eu")
    assert not primary("example.com")
    assert slug("PlayStation 2: TV 4K!")=="playstation-2-tv-4k"
    detailed={
       "sources":[{"result":"retrieved","data":{
           "url":"https://example.org/technology-research",
           "excerpts":["A detailed original public report explains the documented technology decision. "*8]*5,
           "metadata":{"og:title":"Detailed original report about technology"}}}]
    }
    assert len(material(detailed))==1, "Documented single-source reporting should be reviewed"
    assert material({"sources":[{"result":"retrieved","data":{
           "url":"https://example.org/brief-note",
           "excerpts":["Short, unsupported promotional blurb."],
           "metadata":{"og:title":"Promotional note"}}}]})==[]
    assert not verified({"status":"needs_human_fact_check","title":"Title of test source article",
                         "summary":"A summary that contains enough information for an ordinary editorial website article.",
                         "paragraphs":["Invented facts do not belong in the site. "*5]*4},
                        [],{"publish":True,"supported":[]})
    print("Verified editorial auto-approval self-test passed")
if __name__=="__main__":
    import sys
    self_test() if "--self-test" in sys.argv else main()
