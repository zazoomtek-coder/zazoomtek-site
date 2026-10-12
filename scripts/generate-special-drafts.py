#!/usr/bin/env python3
"""Gemini editorial *drafts*, never automatically publish.
Requires GEMINI_API_KEY in environment. Uses only public candidate headlines;
those headlines do not verify the underlying events.
"""
import datetime as dt
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
KEY=os.environ.get("GEMINI_API_KEY","").strip()
MODEL=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite")
OUT=ROOT/"special-drafts-review.json"
# Prefer direct, accountable reporting from institutions and established
# newsrooms, but retain other verifiable reporting when it is available.
TRUSTED=("reuters","associated press","ap news","ansa","il sole 24 ore",
         "bbc","politico","euronews","financial times","bloomberg",
         "agcm","european commission","commissione europea","europarl",
         "eurogamer","gamesindustry","the verge","wired","corriere")
GENERIC=set("the a and for in on to of with from news technology tech gaming "
            "ai artificial intelligence government legge laws law europe european "
            "video games game videogiochi videogame digitale digital world "
            "new nuovo nuovi news italian italy italia privacy regulation "
            "regole rules economy economia policy".split())
def clean_title(title):
    s=str(title).rsplit(" - ",1)[0]
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+"," ",s).strip()
def event_match(a,b):
    """Conservative same-event headline match; shared broad topics don't count."""
    aa,bb=clean_title(a),clean_title(b)
    left,right=set(aa.split()),set(bb.split())
    joint=left&right
    distinctive={t for t in joint if len(t)>3 and t not in GENERIC}
    if len(joint)<4 or len(distinctive)<2:return False
    overlap=len(joint)/max(1,min(len(left),len(right)))
    jaccard=len(joint)/max(1,len(left|right))
    return overlap>=.65 and jaccard>=.42 and SequenceMatcher(None,aa,bb).ratio()>=.62
def outlet_key(outlet):
    return re.sub(r"[^a-z0-9]+","",clean_title(outlet))
def outlet_priority(outlet):
    t=str(outlet).casefold()
    return 1 if any(k in t for k in TRUSTED) else 0

def main():
    if not KEY:
        print("No API key: skipping Gemini draft generation.")
        return
    candidates=json.loads((ROOT/"special-candidates.json").read_text(encoding="utf-8")).get("items",[])
    now=dt.datetime.now(dt.timezone.utc)
    leads=[]
    for x in candidates:
        if x.get("section") not in ("tech","gaming") or not x.get("source_url","").startswith("https://"):
            continue
        try:published=dt.datetime.fromisoformat(x["published_utc"])
        except (KeyError,ValueError):continue
        if dt.timedelta(0)<=now-published<=dt.timedelta(hours=72):
            leads.append({"section":x["section"],"title":x["title"],"outlet":x["source"],"url":x["source_url"],"time":x["published_utc"],
                          "featured_priority":x.get("featured_priority",0)})
    # Match the *same event* across independent publishers, never a generic
    # subject such as AI regulation. Preserve ordinary recent articles too.
    for x in leads:
        related=[o for o in leads
                 if o["section"]==x["section"] and o["url"]!=x["url"]
                 and outlet_key(o["outlet"])!=outlet_key(x["outlet"])
                 and event_match(x["title"],o["title"])]
        unique={}
        for other in related:
            unique.setdefault(outlet_key(other["outlet"]),other)
        x["related"]=list(unique.values())[:3]
        x["independent_outlets"]=len(unique)+1
    # Virality proxy: top homepage placement, then multiple publishers, recency.
    # These signals estimate interest; never claim actual visits or shares.
    leads.sort(key=lambda x:(x.get("featured_priority",0)>0,
                              x.get("featured_priority",0),
                              x["independent_outlets"]>=2,
                              x["independent_outlets"], outlet_priority(x["outlet"]),
                              x["time"]),reverse=True)
    selected=[x for x in leads if x["section"]=="tech"][:38]+[
             x for x in leads if x["section"]=="gaming"][:27]
    leads=selected
    if not leads:
        print("No timely leads; no AI request.")
        return
    # Only hints for research: both titles and bodies still need verification.
    for x in leads:
        x["possible_corrob"]=[{"title":v["title"],"outlet":v["outlet"],"url":v["url"]}
                              for v in x.pop("related",[])[:3]]
    print("Research leads:",len(leads),
          "; same-event corroboration candidates:",sum(x["independent_outlets"]>=2 for x in leads))
    prompt="""Sei un ricercatore editoriale di ZazoomTek. Disponi di SOLI TITOLI RSS: queste informazioni NON BASTANO a verificare gli articoli. Seleziona fino a 6 proposte TECH IMPACT e fino a 6 GAMING INSIDE per scansione (solo se supportate da fonti), preferendo notizie forti, in primo piano nelle homepage, freschissime e con alto potenziale virale. Il campo featured_priority indica prominenza, NON il numero reale di lettori o condivisioni. Non inventare metriche e non riempire la quota con casi privi di fatti verificabili. Privilegia Reuters, ANSA, AP, istituzioni e testate autorevoli italiane/internazionali. I temi includono politica nazionale ed estera, norme, economia e tutela dei consumatori purché il nesso con tecnologia o videogiochi sia concreto. I campi possible_corrob sono IPOTESI di corrispondenza tra titoli: includi due URL solo quando si riferiscono alla STESSA notizia e a testate diverse; altrimenti scegli anche una notizia singola solida per le pagine, ma non definirla tendenza.
TECH IMPACT: politica e tecnologia, cybersicurezza pubblica, sicurezza digitale, diritti, innovazioni con implicazioni documentabili; escludi ordinaria pubblicità e lanci banali.
GAMING INSIDE: esclusivamente politica e leggi dei VIDEOGIOCHI, proprietà di giochi digitali, chiusura server, consumatori, censura, tutela minori, crisi e acquisizioni di studi videoludici. Un evento su Meta, Hollywood, IA o copyright SENZA un rapporto esplicito con i videogiochi NON è pertinente.
Requisiti: niente affermazioni definitive tratte da titoli; non inventare fonti, cifre, nomi, dichiarazioni, test, accuse o contenuti. Per ciascun tema proponi UN PIANO PER ARTICOLO CON 300-750 PAROLE NEL CORPO DEL TESTO, NON un articolo pronto: titolo italiano originale, summary neutrale di 30-50 parole (non oltre 380 caratteri), 3-5 sezioni di ricerca, controllo delle fonti primarie e verifica di data/esito/circostanze, attenzione legale. Ogni eventuale articolo con almeno 300 parole originali nel corpo dovrà essere scritto SOLO DOPO verifica documentale separata.
Emetti esclusivamente JSON: {"drafts":[{"section":"tech oppure gaming","title":"titolo originale italiano","summary":"breve descrizione prudente della pista di ricerca, non del fatto confermato","source_urls":["URL presente nell'input"],"verification_needed":["verifica puntuale da effettuare"],"outline":["aspetto da approfondire"],"target_words":550,"editorial_status":"needs_human_review"}]}. Inserisci solo URL forniti nell'input, non riempire posti mancanti. Input:\\n"""+json.dumps(leads,ensure_ascii=False)
    # Query available models for this key instead of assuming a model exists.
    list_req=urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100",
        headers={"x-goog-api-key":KEY})
    try:
        with urllib.request.urlopen(list_req,timeout=25) as response:
            catalog=json.load(response).get("models",[])
    except urllib.error.HTTPError as exc:
        print("Gemini model discovery HTTP error:",exc.code,"(key hidden)")
        raise SystemExit(1)
    available={m.get("name","").removeprefix("models/") for m in catalog
               if "generateContent" in m.get("supportedGenerationMethods",[])}
    preferred=[MODEL,"gemini-3.5-flash-lite","gemini-3.5-flash"]
    selected=next((name for name in preferred if name in available),None)
    if not selected:
        # Never guess a paid-only model or silently enable billing.
        print("No configured Gemini text model available. Supported names:",", ".join(sorted(available)[:15]))
        raise SystemExit(1)
    print("Gemini model selected:",selected)
    endpoint="https://generativelanguage.googleapis.com/v1beta/models/"+selected+":generateContent"
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json","maxOutputTokens":10000,"temperature":0.2}}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode("utf-8"),headers={"Content-Type":"application/json","x-goog-api-key":KEY},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=65) as response:
            data=json.load(response)
    except urllib.error.HTTPError as exc:
        # Google error text may contain project-specific information; display only
        # the public API's safe structured status and a short redacted message.
        raw=exc.read(3000).decode("utf-8","replace")
        try:
            err=json.loads(raw).get("error",{})
            status=str(err.get("status","unknown"))[:60]
            message=str(err.get("message","unknown"))
        except (ValueError,AttributeError,TypeError):
            status="unknown"
            message="No structured API error returned"
        message=re.sub(r"AIza[A-Za-z0-9_-]+","[REDACTED_KEY]",message)
        message=re.sub(r"projects/[0-9]+","projects/[REDACTED]",message)
        print("Gemini HTTP error:",exc.code,"status:",status,"message:",message[:380])
        print("No article was published. Check model access and billing tier in Google AI Studio.")
        raise SystemExit(1)
    response_text="".join(p.get("text","") for c in data.get("candidates",[]) for p in c.get("content",{}).get("parts",[]))
    try:
        parsed=json.loads(response_text)
    except (ValueError,TypeError):
        print("Gemini returned incomplete research JSON; no unsafe publication. Characters:",len(response_text))
        parsed={"drafts":[]}
    by_url={x["url"]:x for x in leads}
    for lead in leads:
        for source in lead.get("possible_corrob",[]):
            by_url.setdefault(source["url"],source)
    allowed=set(by_url)
    verified=[]
    for x in parsed.get("drafts",[]):
        if not isinstance(x,dict) or x.get("section") not in ("tech","gaming"):continue
        urls=x.get("source_urls",[])
        if not isinstance(urls,list) or not urls or any(u not in allowed for u in urls):continue
        if not isinstance(x.get("title"),str) or not isinstance(x.get("summary"),str):continue
        if x["section"]=="gaming" and not any(w in ("gaming","game","games","videogame","videogiochi","videogioco","xbox","playstation","nintendo","steam","videoludic","giocatori") for w in re.findall(r"[a-zA-Z]+",(x["title"]+" "+" ".join(by_url[u]["title"] for u in urls)).lower())):continue
        # Add only conservatively matched independent reporting from input.
        # The subsequent full-source check rejects mismatched events.
        corroborating=[]
        for u in urls:
            lead=by_url.get(u,{})
            for other in lead.get("possible_corrob",[]):
                if other["url"] not in urls+corroborating:
                    corroborating.append(other["url"])
        urls=(urls+corroborating)[:3]
        verified.append({"section":x["section"],"title":x["title"][:180],"summary":x["summary"][:1500],"source_urls":urls,"verification_needed":x.get("verification_needed",[]),"outline":x.get("outline",[])[:6] if isinstance(x.get("outline"),list) else [],"target_words":450,"featured_priority":max((by_url[u].get("featured_priority",0) for u in urls),default=0),
                         "editorial_status":"needs_human_review"})
    report={"generated_utc":now.isoformat(),"published":False,"gemini_model":selected,"note":"Research drafts only; titles from RSS are not factual verification.","drafts":verified[:12]}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Gemini research proposals:",len(verified[:12]),"; publication occurs only after full-text verification")
if __name__=="__main__":main()
