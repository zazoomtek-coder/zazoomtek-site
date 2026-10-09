#!/usr/bin/env python3
"""Gemini editorial *drafts*, never automatically publish.
Requires GEMINI_API_KEY in environment. Uses only public candidate headlines;
those headlines do not verify the underlying events.
"""
import datetime as dt
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
KEY=os.environ.get("GEMINI_API_KEY","").strip()
MODEL=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite")
OUT=ROOT/"special-drafts-review.json"
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
        if dt.timedelta(0)<=now-published<=dt.timedelta(hours=48):
            leads.append({"section":x["section"],"title":x["title"],"outlet":x["source"],"url":x["source_url"],"time":x["published_utc"]})
    leads=leads[:65]
    if not leads:
        print("No timely leads; no AI request.")
        return
    prompt="""Sei il filtro editoriale di ZazoomTek. Input: SOLO TITOLI RSS NON VERIFICATI, non testi degli articoli. Devi scegliere fino a quattro temi per TECH IMPACT e fino a due per GAMING INSIDE. Non devi inventare fatti.
TECH IMPACT: tecnologia con conseguenze concrete e documentabili su politica, istituzioni, cybersecurity, IA, privacy, innovazione e società.
GAMING INSIDE: SOLO temi direttamente collegati a videogiochi, editori/studi di videogiochi, piattaforme gaming, diritti dei videogiocatori, legislazione gaming, server dei videogiochi, censura e controversie nell'industria gaming. Escludi in modo rigoroso notizie genericamente su Meta, copyright o IA se non riguardano esplicitamente videogiochi.
Scarta argomenti che paiono titoli sensazionalistici, accuse non comprovate, articoli di opinione non documentati o duplicati sullo stesso evento. Se non ci sono due notizie pertinenti al gaming, selezionane meno, mai riempire.
Rispondi SOLO con JSON: {"drafts":[{"section":"tech oppure gaming","title":"titolo originale italiano","summary":"breve ipotesi di notizia, 80-130 parole, senza trattare titolo come fatto verificato","source_urls":["URL preso dall'input"],"verification_needed":["controllo concreto prima della pubblicazione"],"editorial_status":"needs_human_review"}]}. Questi sono spunti di ricerca, NON articoli pronti. Non inventare citazioni, prove, date, dichiarazioni o scoperte. Input:\\n"""+json.dumps(leads,ensure_ascii=False)
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
    payload={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json","maxOutputTokens":2800,"temperature":0.2}}
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
        import re
        message=re.sub(r"AIza[A-Za-z0-9_-]+","[REDACTED_KEY]",message)
        message=re.sub(r"projects/[0-9]+","projects/[REDACTED]",message)
        print("Gemini HTTP error:",exc.code,"status:",status,"message:",message[:380])
        print("No article was published. Check model access and billing tier in Google AI Studio.")
        raise SystemExit(1)
    response_text="".join(p.get("text","") for c in data.get("candidates",[]) for p in c.get("content",{}).get("parts",[]))
    parsed=json.loads(response_text)
    allowed={x["url"] for x in leads}
    verified=[]
    for x in parsed.get("drafts",[]):
        if not isinstance(x,dict) or x.get("section") not in ("tech","gaming"):continue
        urls=x.get("source_urls",[])
        if not isinstance(urls,list) or not urls or any(u not in allowed for u in urls):continue
        if not isinstance(x.get("title"),str) or not isinstance(x.get("summary"),str):continue
        verified.append({"section":x["section"],"title":x["title"][:180],"summary":x["summary"][:1500],"source_urls":urls,"verification_needed":x.get("verification_needed",[]),"editorial_status":"needs_human_review"})
    report={"generated_utc":now.isoformat(),"published":False,"note":"Research drafts only; titles from RSS are not factual verification.","drafts":verified[:6]}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Gemini drafts created for human review:",len(verified[:6]),"; published: 0")
if __name__=="__main__":main()
