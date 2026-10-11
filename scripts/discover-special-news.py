#!/usr/bin/env python3
"""Discover original reporting leads; never auto-publish unverified news.
Runs separately from the YouTube Community importer."""
import concurrent.futures
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
  'attacco hacker ministero istituzioni sicurezza informatica',
  'cyberattack critical infrastructure government Asia Europe',
  'Japan South Korea semiconductor digital policy AI regulation',
  # Italy, Europe and the wider world: authoritative reporting and policy.
  'site:ansa.it intelligenza artificiale legge parlamento digitale',
  'site:ilsole24ore.com digitale tecnologia economia governo legge',
  'site:reuters.com technology AI regulation government antitrust',
  'site:apnews.com technology artificial intelligence law regulation',
  'site:politico.eu european union tech digital regulation privacy',
  'site:euronews.com digital law EU commission technology',
  'site:bbc.com/news technology government legal regulation',
  'site:agcm.it digitale piattaforme consumatori concorrenza',
  'site:ec.europa.eu digitale intelligenza artificiale piattaforme',
  'technology semiconductors export controls government tariffs economy',
 ],
 "gaming":[
  'videogame industry legislation political regulation rights',
  'stop killing games digital ownership servers consumer law',
  'videogame censorship child protection gaming policy',
  'games industry studios closures layoffs acquisitions',
  'video games artificial intelligence copyright lawsuit',
  'gaming platforms refunds consumer rights antitrust',
  'video game regulation European Commission Parliament player rights',
  'video game studio closures employees layoffs Japan US Europe',
  'online game shutdown access purchased games consumer rights',
  'gaming industry copyright law government investigations',
  'videogiochi legge tutela consumatori chiusura server',
  'site:ansa.it videogiochi tutela minori legge gaming',
  'site:reuters.com video games regulation antitrust consumer rights',
  'site:apnews.com video games law children regulation',
  'site:eurogamer.net video game consumer rights regulation',
  'site:gamesindustry.biz games industry acquisition layoffs law',
  'site:euronews.com online gaming child protection digital policy',
  'site:ec.europa.eu video games virtual currency consumer protection',
  'site:agcm.it videogiochi monete virtuali minori acquisti',
  'video game platform consumer protection antitrust Europe government',
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
# Targeted news search can return unrelated items from otherwise respected outlets.
# Apply minimal topical relevance before sending headlines to the fact checker.
TECH_RE=re.compile(
    r"(?i)\b(?:ai|ia|digital\w*|cyber\w*|hack\w*|privacy|cloud|"
    r"technolog\w*|tecnolog\w*|software|internet|social|smartphone|"
    r"semiconductor\w*|chip\w*|informatic\w*|algorithm\w*|algoritm\w*|"
    r"telecom\w*|microchip|nvidia|openai|anthropic|microsoft|google|"
    r"meta|tiktok|apple|artificial intelligence|intelligenza artificiale|"
    r"data breach|data center|ai act|digital services act|digital markets act)\b")
GAMING_RE=re.compile(
    r"(?i)\b(?:videogioc\w*|videogam\w*|videoludic\w*|gaming|"
    r"playstation|xbox|nintendo|steam|roblox|fortnite|diablo|"
    r"call of duty|in.game|loot.box\w*|tetris|esport\w*|"
    r"game developer\w*|games industry|video games|video game|"
    r"game studios|gaming platforms|giocator\w*)\b")
def relevant(section,title):
    return bool((GAMING_RE if section=="gaming" else TECH_RE).search(title))

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
    regions=[
        {"hl":"ja","gl":"JP","ceid":"JP:ja"},
        {"hl":"it","gl":"IT","ceid":"IT:it"},
        {"hl":"en-US","gl":"US","ceid":"US:en"}
    ]
    # Scan independent RSS searches concurrently; skip slow/unreachable
    # publishers rather than delaying every other verified news source.
    tasks=[(section,index,query) for section,queries in QUERIES.items()
           for index,query in enumerate(queries)]
    def scan_one(args):
        section,index,query=args
        region=regions[index % len(regions)]
        # Google News is a discovery index, never primary factual evidence.
        url="https://news.google.com/rss/search?"+urllib.parse.urlencode(
            {"q":query+" when:3d",**region})
        found=[]
        try:
            root=ET.fromstring(fetch(url))
            for item in root.findall(".//channel/item")[:12]:
                title=clean(item.findtext("title"))
                link=clean(item.findtext("link"))
                source=item.find("source")
                outlet=clean(source.text if source is not None else "")
                published=clean(item.findtext("pubDate"))
                try:
                    date=email.utils.parsedate_to_datetime(published).astimezone(dt.timezone.utc)
                except (TypeError,ValueError):
                    continue
                if not title or not link.startswith("https://") or not outlet:
                    continue
                if not (dt.timedelta(0)<=now-date<=dt.timedelta(hours=75)):
                    continue
                if not relevant(section,title):
                    continue
                ident=hashlib.sha256((section+"|"+link).encode()).hexdigest()[:20]
                found.append({"id":ident,"section":section,"title":title[:220],
                              "source":outlet[:100],"source_url":link,
                              "published_utc":date.isoformat(),
                              "status":"research_only"})
            return found,None
        except Exception as exc:
            return [],{"query":query,"error":str(exc)[:160]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for items,problem in pool.map(scan_one,tasks):
            for article in items:
                fresh[article["id"]]=article
            if problem:
                errors.append(problem)
    # Preserve up to seven days of previously discovered leads and their status.
    for key,item in existing.items():
        try:age=now-dt.datetime.fromisoformat(item["published_utc"])
        except (ValueError,KeyError,TypeError):continue
        if age<=dt.timedelta(days=7) and key not in fresh:fresh[key]=item
    # Keep a wider range of independent reports, not just the very last
    # headlines of a few publishers. Final selection remains evidence-based.
    ordered=sorted(fresh.values(),key=lambda x:x["published_utc"],reverse=True)[:400]
    payload={"generated_utc":now.isoformat(),"publication_enabled":False,
             "disclaimer":"Discovery only: every story requires independent verification, original writing, rights review and approval before publication.",
             "items":ordered,"errors":errors}
    output=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    if not OUT.exists() or OUT.read_text(encoding="utf-8")!=output:OUT.write_text(output,encoding="utf-8")
    print("Leads:",len(ordered),"feed errors:",len(errors),"published: 0")
if __name__=="__main__":discover()
