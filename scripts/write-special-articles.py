#!/usr/bin/env python3
"""Create 300-600 word unpublished Italian article drafts from retrieved evidence.
This script never writes site HTML or approval JSON.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
KEY=os.environ.get("GEMINI_API_KEY","").strip()
MODEL=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite")
SOURCE=ROOT/"special-source-evidence.json"
OUT=ROOT/"special-full-articles-review.json"
def generate(prompt):
    endpoint="https://generativelanguage.googleapis.com/v1beta/models/"+MODEL+":generateContent"
    payload={"contents":[{"parts":[{"text":prompt}]}],
             "generationConfig":{"responseMimeType":"application/json","maxOutputTokens":4600,"temperature":0.15}}
    req=urllib.request.Request(endpoint,data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json","x-goog-api-key":KEY},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=80) as response:data=json.load(response)
    except urllib.error.HTTPError as exc:
        print("Gemini unavailable for full article draft:",exc.code,"no article published")
        return None
    text="".join(p.get("text","") for c in data.get("candidates",[])
                 for p in c.get("content",{}).get("parts",[]))
    try:return json.loads(text)
    except (TypeError,ValueError):return None
def main():
    if not KEY:
        print("Missing API key; no article drafts generated")
        return
    items=json.loads(SOURCE.read_text(encoding="utf-8")).get("items",[])
    output=[]
    for item in items[:6]:
        # Google News RSS redirects and page titles are NOT sufficient evidence.
        sources=[x["data"] for x in item.get("sources",[]) if x.get("result")=="retrieved"
                 and len(x.get("data",{}).get("excerpts",[]))>=3]
        if not sources:
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"insufficient_primary_material","approved":False})
            continue
        # Supply short excerpts for understanding, never for copying.
        evidence=[{"url":x["url"],"publication_meta":x.get("metadata",{}),
                   "research_extracts":x["excerpts"][:9]} for x in sources[:2]]
        prompt="""Sei un redattore italiano di ZazoomTek. Prepara UNA BOZZA NON PUBBLICABILE da 300-600 parole, usando ESCLUSIVAMENTE le informazioni che trovi nei materiali riportati. Sono estratti parziali di pagine web e NON implicano verifica indipendente. Evita ogni fatto non dimostrato, qualifica le incertezze, niente informazioni inventate, citazioni attribuite, accuse o contenuti coperti da copyright copiati letteralmente. Non affermare di aver compiuto un'inchiesta autonoma, un test o una verifica definitiva. Scrivi in modo originale e giornalistico, con paragrafi corposi e sottotitoli pertinenti. Se il materiale non è sufficiente a scrivere almeno 300 parole reali e informative, restituisci {"status":"insufficient_evidence"}. NON ALLUNGARE per arrivare a 300 con ripetizioni. Restituisci JSON: {"status":"draft","title":"...","summary":"...","paragraphs":["..."],"evidence_limits":["..."]}. NON includere HTML. Tema: """+str(item.get("title",""))+"\nEstratti per la ricerca:\n"+json.dumps(evidence,ensure_ascii=False)[:13500]
        raw=generate(prompt)
        if not isinstance(raw,dict) or raw.get("status")!="draft":
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"insufficient_evidence_or_model_error","approved":False})
            continue
        title=raw.get("title","");summary=raw.get("summary","");paragraphs=raw.get("paragraphs",[])
        if not isinstance(title,str) or not isinstance(summary,str) or not isinstance(paragraphs,list) or not all(isinstance(p,str) for p in paragraphs):
            continue
        count=len((" ".join([title,summary]+paragraphs)).split())
        if not 300<=count<=600:
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"invalid_word_count","words":count,"approved":False})
            continue
        output.append({"section":item["section"],"status":"needs_human_fact_check",
            "title":title,"summary":summary,"paragraphs":paragraphs,"words":count,
            "source_urls":[x["url"] for x in sources],"evidence_limits":raw.get("evidence_limits",[]),
            "approved":False,"publication_allowed":False})
    OUT.write_text(json.dumps({"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "published":False,"articles":output},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Full drafts reviewed:",len(output),"published: 0")
if __name__=="__main__":main()
