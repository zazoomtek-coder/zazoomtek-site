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
from html.parser import HTMLParser
from html import unescape

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


# Zazoom's topical index supplies leads, NOT independent verification.
# The original publisher/official record must still substantiate every claim.
ZAZOOM_TECH_INDEX="https://www.zazoom.it/tecnologia/"
ZAZOOM_PUBLIC_RE=re.compile(
    r"(?i)(attacc|cyber|hacker|frode|privacy|oblio|deindicizz|certificat|"
    r"truff|giudic|tribunale|legge|normativ|regolament|antitrust|"
    r"licenziament|riorganizz|tutela|diritt|sicurezza|inchiest|"
    r"process|multa|restructur|protest|accord|sanzion|controll|"
    r"crisi|copyright|censura|sorveglianz|politic|fondi|"
    r"union|autorità|autorita|governo|dipendent|amplia)")
ZAZOOM_GAMING_RE=re.compile(
    r"(?i)(videogioc|videoludic|gaming|playstation|xbox|nintendo|"
    r"ubisoft|activision|the coalition|gears of war|massive entertainment|"
    r"steam|roblox|game studios|games industry|giocator|giochi online)")

class ZazoomHeadlineParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title=False;self.href="";self.parts=[];self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag=="h3":
            self.in_title=True;self.href="";self.parts=[]
        elif tag=="a" and self.in_title and not self.href:
            self.href=dict(attrs).get("href","")
    def handle_data(self,data):
        if self.in_title:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=="h3" and self.in_title:
            title=clean("".join(self.parts))
            if title and self.href:self.items.append((self.href,title))
            self.in_title=False

def zazoom_leads(now):
    req=urllib.request.Request(ZAZOOM_TECH_INDEX,headers={
        "User-Agent":"Mozilla/5.0 (compatible; ZazoomTekEditorialResearch/1.0; +https://zazoomtek.it/contatti.html)",
        "Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req,timeout=20) as response:
        doc=response.read(1_600_000).decode("utf-8","replace")
    reader=ZazoomHeadlineParser();reader.feed(doc)
    collected={}
    for link,title in reader.items[:90]:
        url=urllib.parse.urljoin(ZAZOOM_TECH_INDEX,unescape(link))
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!="https" or parsed.hostname not in ("www.zazoom.it","zazoom.it"):
            continue
        m=re.search(r"/news-notizia/post/\d+/(20\d{2})-(\d{2})-(\d{2})-",parsed.path)
        if not m or not ZAZOOM_PUBLIC_RE.search(title):
            continue
        game=bool(ZAZOOM_GAMING_RE.search(title))
        tech=bool(TECH_RE.search(title))
        if not game and not tech:continue
        section="gaming" if game else "tech"
        try:
            when=dt.datetime(int(m.group(1)),int(m.group(2)),int(m.group(3)),12,0,tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        age=now-when
        # Recent stories only; dates older than three days are never republished
        # just to fill quotas. Cross-run duplicate checks remain active.
        if not dt.timedelta(0)<=age<=dt.timedelta(hours=90):continue
        ident=hashlib.sha256((section+"|"+url).encode()).hexdigest()[:20]
        collected[ident]={"id":ident,"section":section,"title":title[:220],
                         "source":"Zazoom.it","source_url":url,
                         "published_utc":when.isoformat(),"status":"research_only"}
    return list(collected.values())

# The same six highlighted international/Zazoom outlets are examined for
# Tech Impact and Gaming Inside, in addition to the independent RSS searches.
# Headline caches are only research leads, never evidence for publication.
FEATURED_OUTLETS={"igncom","gamespot","eurogamer","polygon","pcgamer","zazoom"}
SPECIAL_TOPIC_RE=re.compile(
    r"(?i)(legge|leggi|normativ|regolament|politic|govern|parlament|"
    r"antitrust|indagin|sanzion|privacy|censur|copyright|diritt|"
    r"consumator|propriet|proprietà|licenziament|riorganizz|ristruttur|chiusur|server|"
    r"acquisizion|cyberattacc|hacker|violazion|sicurezza|"
    r"controvers|denunc|tutela|minori|rimbors|ai.act|gdpr|dsa|dma)")
def featured_policy_leads(now):
    path=ROOT/"trending-sources.json"
    if not path.is_file():return []
    try:
        rows=json.loads(path.read_text(encoding="utf-8")).get("items",[])
    except (ValueError,OSError):return []
    out={}
    for x in rows:
        if (x.get("source") not in FEATURED_OUTLETS
            or x.get("kind") not in ("tech","gaming")
            or not x.get("homepage") or int(x.get("rank",99))>12):continue
        title=x.get("title","")
        if not SPECIAL_TOPIC_RE.search(title):continue
        if x["kind"]=="gaming" and not (GAMING_RE.search(title) or ZAZOOM_GAMING_RE.search(title)):continue
        section=x["kind"];url=x.get("url","")
        if not url.startswith("https://"):continue
        try:
            seen=dt.datetime.fromisoformat(x["last_seen"])
            first=dt.datetime.fromisoformat(x["first_seen"])
        except (KeyError,ValueError,TypeError):continue
        if not (dt.timedelta(0)<=now-seen<=dt.timedelta(hours=4)
                and dt.timedelta(0)<=now-first<=dt.timedelta(hours=72)):continue
        ident=hashlib.sha256((section+"|"+url).encode()).hexdigest()[:20]
        out[ident]={"id":ident,"section":section,"title":title[:220],
                    "source":x.get("name","")[:100],"source_url":url,
                    "published_utc":first.isoformat(),"status":"research_only",
                    "date_is_first_seen":True}
    return list(out.values())

def zazoom_parser_self_test():
    p=ZazoomHeadlineParser()
    p.feed('<div><h3><a href="/news-notizia/post/1/2026-10-11-attacco-hacker-18-11/">Attacco hacker alle istituzioni</a></h3><h3><a href="/news-notizia/post/2/2026-10-11-ubisoft-licenziamenti-18-10/">Ubisoft: licenziamenti negli studi</a></h3></div>')
    assert len(p.items)==2 and p.items[0][1]=="Attacco hacker alle istituzioni"
    assert ZAZOOM_PUBLIC_RE.search(p.items[1][1])
    assert ZAZOOM_GAMING_RE.search(p.items[1][1])
    print("ZAZOOM TOPICAL SOURCE PARSER SELF TEST PASSED")

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
    # Include primary-topic leads from the Zazoom technology index.
    # Never promote an index headline directly into published content.
    try:
        discovered=zazoom_leads(now)
        for article in discovered:
            fresh[article["id"]]=article
        print("Zazoom.it policy/game-industry research leads:",len(discovered))
    except Exception as exc:
        errors.append({"query":ZAZOOM_TECH_INDEX,"error":str(exc)[:160]})
        print("::warning::Zazoom.it index unavailable; continuing with independent news feeds.")
    # Sixteen current editorial front pages also supply Tech Impact/Gaming
    # Inside research leads. Headlines alone NEVER qualify for publication.
    try:
        trend_path=ROOT/"trending-sources.json"
        trend=json.loads(trend_path.read_text(encoding="utf-8")) if trend_path.exists() else {}
        n=0
        for row in trend.get("items",[]):
            title=clean(row.get("title",""))
            url=row.get("url","")
            if not row.get("homepage") or row.get("rank",99)>14:
                continue
            if not isinstance(url,str) or not url.startswith("https://"):
                continue
            if not ZAZOOM_PUBLIC_RE.search(title):
                continue
            game=bool(ZAZOOM_GAMING_RE.search(title))
            is_game_policy=game and bool(re.search(
                r"(?i)(diritt|legge|licenziament|chiusur|acquisizi|"
                r"sindac|studio|protezi|regolament|antitrust|"
                r"copyright|censur|server|giocator|privacy|lavorator)",title))
            section="gaming" if is_game_policy else "tech" if not game and relevant("tech",title) else None
            if not section:continue
            try:
                when=dt.datetime.fromisoformat(row["first_seen"])
            except (ValueError,KeyError,TypeError):
                continue
            if not dt.timedelta(0)<=now-when<=dt.timedelta(hours=90):continue
            ident=hashlib.sha256((section+"|"+url).encode()).hexdigest()[:20]
            fresh[ident]={"id":ident,"section":section,"title":title[:220],
                "source":row.get("name","")[:100],"source_url":url,
                "published_utc":when.isoformat(),"status":"research_only"}
            n+=1
        print("Tech Impact / Gaming Inside featured research leads:",n)
    except Exception as exc:
        errors.append({"query":"trending-sources.json","error":type(exc).__name__})
    # Prioritize genuine homepage highlights from the six requested outlets.
    for article in featured_policy_leads(now):
        fresh[article["id"]]=article
    print("Highlighted international/Zazoom policy leads:",
          sum(x.get("source_url","").startswith("https://") and x["id"] in fresh
              for x in featured_policy_leads(now)))
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
if __name__=="__main__":
    import sys
    zazoom_parser_self_test() if "--self-test" in sys.argv else discover()
