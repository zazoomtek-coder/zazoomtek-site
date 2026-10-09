#!/usr/bin/env python3
"""Discover original reporting leads; never auto-publish unverified news.
Runs separately from the YouTube Community importer."""
import datetime as dt
import email.utils
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"special-candidates.json"
QUERIES={
 "tech":[
  'cybersecurity government breach privacy technology',
  'European Union digital laws tech antitrust privacy',
  'AI regulation technology impact',
  'technology patent innovation semiconductors',
  'big tech layoffs acquisition antitrust policy',
  'smartphone security vulnerability major software',
 ],
 "gaming":[
  'videogame industry legislation political regulation rights',
  'stop killing games digital ownership servers consumer law',
  'videogame censorship child protection gaming policy',
  'games industry studios closures layoffs acquisitions',
  'video games artificial intelligence copyright lawsuit',
  'gaming platforms refunds consumer rights antitrust',
 ]
}
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"ZazoomTekEditorialResearch/1.0 (+https://zazoomtek.it/contatti.html)","Accept":"application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req,timeout=18) as response:
        if int(response.headers.get("Content-Length","0"))>1_800_000:
            raise ValueError("feed too large")
        return response.read(1_800_001)
def clean(s):
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",s or "")).strip()
def discover():
    now=dt.datetime.now(dt.timezone.utc)
    existing={}
    if OUT.exists():
        try:
            for x in json.loads(OUT.read_text(encoding="utf-8")).get("items",[]):
                if isinstance(x,dict) and x.get("id"):existing[x["id"]]=x
        except (ValueError,OSError):pass
    fresh={}
    errors=[]
    for section,queries in QUERIES.items():
        for query in queries:
            # Google News is used for discovery only, NOT as factual proof.
            url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query+" when:2d","hl":"en-US","gl":"US","ceid":"US:en"})
            try:
                root=ET.fromstring(fetch(url))
                for item in root.findall(".//channel/item")[:12]:
                    title=clean(item.findtext("title"))
                    link=clean(item.findtext("link"))
                    source=item.find("source")
                    outlet=clean(source.text if source is not None else "")
                    pub=clean(item.findtext("pubDate"))
                    try:date=email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
                    except (TypeError,ValueError):continue
                    if not title or not link.startswith("https://") or not outlet:continue
                    if not (dt.timedelta(0)<=now-date<=dt.timedelta(hours=55)):continue
                    ident=hashlib.sha256((section+"|"+link).encode()).hexdigest()[:20]
                    fresh[ident]={"id":ident,"section":section,"title":title[:220],"source":outlet[:100],"source_url":link,"published_utc":date.isoformat(),"status":"research_only"}
            except Exception as exc:
                errors.append({"query":query,"error":str(exc)[:160]})
    # Preserve up to seven days of previously discovered leads and their status.
    for key,item in existing.items():
        try:age=now-dt.datetime.fromisoformat(item["published_utc"])
        except (ValueError,KeyError,TypeError):continue
        if age<=dt.timedelta(days=7) and key not in fresh:fresh[key]=item
    ordered=sorted(fresh.values(),key=lambda x:x["published_utc"],reverse=True)[:240]
    payload={"generated_utc":now.isoformat(),"publication_enabled":False,
             "disclaimer":"Discovery only: every story requires independent verification, original writing, rights review and approval before publication.",
             "items":ordered,"errors":errors}
    output=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=output:OUT.write_text(output,encoding="utf-8")
    print("Leads:",len(ordered),"feed errors:",len(errors),"published: 0")
if __name__=="__main__":discover()
