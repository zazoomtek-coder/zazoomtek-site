#!/usr/bin/env python3
"""Create 400-750 body-word unpublished Italian article drafts from retrieved evidence.
This script never writes site HTML or approval JSON.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from special_gemini_client import call_json, GeminiRequestError

ROOT=Path(__file__).resolve().parent.parent
KEY=os.environ.get("GEMINI_API_KEY","").strip()
MODEL=os.environ.get("GEMINI_MODEL","gemini-3.5-flash-lite")
SOURCE=ROOT/"special-source-evidence.json"
OUT=ROOT/"special-full-articles-review.json"
def generate(prompt):
    try:
        draft,used=call_json(prompt,KEY,MODEL,
            {"responseMimeType":"application/json","maxOutputTokens":7000,"temperature":0.15},timeout=80)
        return draft
    except GeminiRequestError as exc:
        print("Article drafting unavailable:",str(exc))
        return None

def main():
    global MODEL
    selected=json.loads((ROOT/"special-drafts-review.json").read_text(encoding="utf-8")).get("gemini_model","")
    if isinstance(selected,str) and re.fullmatch(r"gemini-[a-z0-9.\-]+",selected): MODEL=selected
    if not KEY:
        print("Missing API key; no article drafts generated")
        return
    items=json.loads(SOURCE.read_text(encoding="utf-8")).get("items",[])
    output=[]
    for item in items[:12]:
        # Google News RSS redirects and page titles are NOT sufficient evidence.
        # Newsrooms are legitimate sources too. A substantive original article
        # or official statement can be enough to draft; only publication requires
        # a final check. Aggregators are already excluded by source retrieval.
        sources=[x["data"] for x in item.get("sources",[]) if x.get("result")=="retrieved"
                 and len(" ".join(x.get("data",{}).get("excerpts",[])).split())>=110]
        if not sources:
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"insufficient_primary_material","approved":False})
            continue
        # Supply short excerpts for understanding, never for copying.
        evidence=[{"url":x["url"],"publication_meta":x.get("metadata",{}),
                   "research_extracts":x["excerpts"][:18]} for x in sources[:2]]
        prompt="""Sei un redattore italiano di ZazoomTek. Sono fonti utilizzabili sia testate giornalistiche credibili, sia fonti ufficiali e documenti pubblici: attribuisci ogni informazione sostanziale alla sua provenienza, senza appropriarti di esclusive altrui. Evita toni accusatori quando mancano conferme e distingui ipotesi da decisioni definitive. Prepara UNA BOZZA NON PUBBLICABILE con un corpo di 300-550 parole originali, usando ESCLUSIVAMENTE le informazioni che trovi nei materiali riportati. Sono estratti parziali di pagine web e NON implicano verifica indipendente. Evita ogni fatto non dimostrato, qualifica le incertezze, niente informazioni inventate, citazioni attribuite, accuse o contenuti coperti da copyright copiati letteralmente. Non affermare di aver compiuto un'inchiesta autonoma, un test o una verifica definitiva. Scrivi in modo originale e giornalistico, con paragrafi corposi e sottotitoli pertinenti. Approfondisci solo i fatti realmente presenti: contesto, istituzioni e soggetti coinvolti, provvedimenti, stato della decisione, eventuali conseguenze confermate e ciò che resta incerto. Struttura 3-6 paragrafi originali da 300-550 parole complessive, SENZA ripetizioni. Se il materiale non è sufficiente a scrivere almeno 300 parole reali e informative nel corpo, restituisci {"status":"insufficient_evidence"}. Non inventare informazioni per arrivare al minimo; elimina ogni frase generica, conclusione dedotta o dettagli non presenti nell'evidenza. Una frase supportata in modo parziale va riscritta o rimossa. Restituisci JSON: {"status":"draft","title":"...","summary":"...","paragraphs":["..."],"evidence_limits":["..."]}. NON includere HTML. Tema: """+str(item.get("title",""))+"\nEstratti per la ricerca:\n"+json.dumps(evidence,ensure_ascii=False)[:22000]
        raw=generate(prompt)
        if not isinstance(raw,dict) or raw.get("status")!="draft":
            reason=raw.get("status","invalid_generation") if isinstance(raw,dict) else "invalid_generation"
            print("No complete draft:",item.get("title","")[:95],"; reason:",reason)
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":reason,"approved":False})
            continue
        title=raw.get("title","");summary=raw.get("summary","");paragraphs=raw.get("paragraphs",[])
        if not isinstance(title,str) or not isinstance(summary,str) or not isinstance(paragraphs,list) or not all(isinstance(p,str) for p in paragraphs):
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"invalid_structure","approved":False})
            continue
        count=len(" ".join(paragraphs).split())
        if not 300<=count<=750:
            output.append({"section":item.get("section"),"topic":item.get("title"),
                "status":"invalid_word_count","words":count,"approved":False})
            print("Draft rejected for word count:",item.get("title","")[:80],count)
            continue
        output.append({"section":item["section"],"topic":item.get("title"),"status":"needs_human_fact_check",
            "title":title,"summary":summary,"paragraphs":paragraphs,"words":count,
            "source_urls":[x["url"] for x in sources],
            "featured_priority":item.get("featured_priority",0),
            "evidence_limits":raw.get("evidence_limits",[]),
            "approved":False,"publication_allowed":False})
    OUT.write_text(json.dumps({"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "published":False,"articles":output},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Full drafts reviewed:",len(output),"published: 0")
if __name__=="__main__":main()
