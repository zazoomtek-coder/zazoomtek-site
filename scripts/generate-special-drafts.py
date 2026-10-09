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
MODEL=os.environ.get("GEMINI_MODEL","gemini-2.5-flash-lite")
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
    prompt="""Sei un assistente editoriale di ZazoomTek. Questa è una lista di TITOLI RSS NON VERIFICATI. Seleziona fino a 4 temi Tech Impact (politica, cybersecurity, impatto sociale) e fino a 2 Gaming Inside (leggi, diritti, industria, casi particolari), usando SOLO i titoli forniti, senza inventare fatti o dire di aver verificato. Produci un JSON con campo 'drafts' lista; ogni elemento deve avere section, title, summary (80-130 parole in italiano, tono condizionale quando il fatto non è confermato), source_urls (URL tra quelli forniti), verification_needed (lista di ciò che deve essere confermato prima di pubblicare), editorial_status fisso 'needs_human_review'. NON creare articoli pubblicabili; NON inventare citazioni, immagini, dati, date, istituzioni, decisioni definitive, test o dichiarazioni. Se insufficiente, meno bozze. Input:\n"""+json.dumps(leads,ensure_ascii=False)
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
    preferred=[MODEL,"gemini-2.5-flash-lite","gemini-2.5-flash","gemini-2.0-flash-lite","gemini-2.0-flash","gemini-1.5-flash"]
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
        print("Gemini HTTP error:",exc.code,"(details and key hidden)")
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
