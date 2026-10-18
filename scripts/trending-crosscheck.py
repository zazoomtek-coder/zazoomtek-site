#!/usr/bin/env python3
"""Compare ZazoomTek with its own Community and sixteen international/Italian news sources.

--sources: read public homepage headlines and RSS fallbacks (no article bodies).
--apply: keep four latest published Tech and one latest Gaming even after
         days without posts; prioritize editorial matches at major portals
         within the freshest publication day.
         User-pinned special stories are exempt from automatic rotation.
--test:   deterministic matcher and placement checks, no network or writes.

No third-party content/images are imported into published pages.
"""
import argparse
import concurrent.futures
import datetime as dt
import email.utils
import html
from html.parser import HTMLParser
import json
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import unicodedata
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/"trending-sources.json"
REPORT=ROOT/"trending-match-report.json"
INDEX=ROOT/"index.html"
NOW=lambda: dt.datetime.now(dt.timezone.utc)

SITES=[
 ("hdblog","HDblog","tech","https://www.hdblog.it/","https://www.hdblog.it/rss/"),
 ("dday","DDay","tech","https://www.dday.it/","https://www.dday.it/rss"),
 ("smartworld","SmartWorld","tech","https://www.smartworld.it/","https://www.smartworld.it/feed/"),
 ("tomshw","Tom's Hardware Italia","tech","https://www.tomshw.it/","https://www.tomshw.it/feed/"),
 ("hwupgrade","Hardware Upgrade","tech","https://www.hwupgrade.it/","https://feeds.hwupgrade.it/rss_news.xml"),
 ("multiplayer","Multiplayer.it","gaming","https://multiplayer.it/","https://multiplayer.it/feed/rss/news/"),
 ("everyeye","Everyeye.it","gaming","https://www.everyeye.it/","https://www.everyeye.it/feed/feed_news_rss.asp"),
 ("spaziogames","SpazioGames","gaming","https://www.spaziogames.it/","https://www.spaziogames.it/feed/"),
 ("ign","IGN Italia","gaming","https://it.ign.com/","https://it.ign.com/feed.xml"),
 ("gamesurf","Gamesurf","gaming","https://www.gamesurf.it/","https://www.gamesurf.it/feed"),
 ("igncom","IGN.com","gaming","https://www.ign.com/news","https://www.ign.com/rss/articles/feed"),
 ("gamespot","GameSpot.com","gaming","https://www.gamespot.com/news/","https://www.gamespot.com/feeds/news/"),
 ("eurogamer","Eurogamer.net","gaming","https://www.eurogamer.net/","https://www.eurogamer.net/feed/news"),
 ("polygon","Polygon.com","gaming","https://www.polygon.com/","https://www.polygon.com/rss/index.xml"),
 ("pcgamer","PCGamer.com","mixed","https://www.pcgamer.com/","https://www.pcgamer.com/feeds.xml"),
 ("zazoom","Zazoom.it","mixed","https://www.zazoom.it/tecnologia/","https://www.zazoom.it/rss/"),
]
STOP=set("""la il lo gli le l un uno una i del della delle degli dei di da a ad al allo alla alle agli ai
in su per tra fra e ed o che con come non nel nella nelle negli nei sulla sulle sul sui è sono era
anche dopo nuovo nuova nuovi nuove oggi domani ieri tutto tutti tuta quello quella questo questa
piu piu importante prime primo primi tutti ultimi arriva arrivano ci si alla dalle dai dal edizione
notizie news video videogiochi videogame videogioco videogames tecnologia tech gaming
svela svelato ecco cosa quanto quando potrebbe alcune dello quindi ecco grande grandi
2026 2027 italia italiano italiana italiani italiane davvero meglio annuncia annunciato annunciate
""".split())
GAMING=set("""ps5 ps4 playstation xbox nintendo switch steam videogiochi videogioco gaming
giochi gioco fifa ea games game forza horizon gta rockstar ubisoft capcom sega
final fantasy battlefield mario zelda pokemon Pokémon playstation pc gamer remaster dlc""".lower().split())
POLICY=set("""legge leggi norme normative normativa rimborsi rimborso tutela regolamento regolamenti antitrust agcm garante
privacy censura censurare censurato censurati tribunale giudice giudici governo parlamentare
parlamento europeo ue europa commissione indagine processo multa sanzione copyright
diritti proprieta proprietà divieto vietare sicurezza hacker cyberattacco cyberattacchi
cybersicurezza fbi violazione denunce denunciato ricorso magistratura minori consumatori
istituzioni politica politico decreto data breach data-breach gdpr dsa dma""".split())
GAMING_POLICY=set("""censura censurare proprieta proprietà copyright minori diritti leggi legge
normative regolamento antitrust agcm divieto vietare tutela rimborsi rimborso consumatori
acquisizione chiusura server discriminazione privacy indagine controversia sanzione""".split())
COMMERCIAL=set("""offerte offerta sconto sconti coupon amazon prime day migliori prezzi
acquista compralo guida acquisto classifica promozione promozioni""".split())
UA="Mozilla/5.0 (compatible; ZazoomTekTrendMatcher/1.0; +https://zazoomtek.it/contatti.html)"

def norm(s):
    s=unicodedata.normalize("NFKD",html.unescape(str(s))).encode("ascii","ignore").decode().lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def tokens(s):
    return [t for t in norm(s).split() if (len(t)>2 or t.isdigit()) and t not in STOP]

def classify(title,hint=""):
    original=norm(title)
    title=" ".join(tokens(title))
    words=set(title.split())
    # A legal, political, consumer-rights or cyber topic, not a routine release.
    politics=bool(words&POLICY)
    gaming=bool(words&GAMING) or bool(re.search(r"\b(acornia|nba\s+bounce|expeditions\s+samurai|fire emblem|grand theft auto|gta\s*(?:vi|6)|call of duty|playstation|video game|videogioc\w*|game pass|steam|fortnite|pubg mobile|pubg|battlefield|ace combat|talos principle|elden ring|resident evil|gran turismo|metal gear|arc raiders|silent hill|the witcher|god of war|the last of us|yakuza|ghost of tsushima|dragons dogma|dragon s dogma|beyond the dark|nightwatch|horror cooperativo|skate|two point museum|mafia iii|risk of rain|cosmic invasion)\b",original))
    # Recognize specific named videogames even when the headline only says
    # "update", "release" or "JRPG", without platform/gameplay keywords.
    if re.search(r"\b(wreckfest(?:\s*2)?|forge of the fae|acts of blood)\b", original):
        return "gaming"
    if politics and gaming and (bool(words&GAMING_POLICY) or "norme" in words):return "gaming-inside"
    if politics and not gaming:return "tech-impact"
    # Gaming-branded hardware is still technology, not video-game news.
    device=bool(re.search(r"\b(cuffie|auricolari|headset|microfono|notebook|laptop|smartphone|router|tastiera|mouse|monitor|scheda grafica|videocamera|audio spaziale|tablet|fotocamera|ssd|dash cam)\b",original))
    if device:return "tech"
    # A named videogame and its alpha/beta/gameplay announcement must not occupy a Tech slot.
    if re.search(r"\b(vaultbreakers|pvpve|pvp|pve|gameplay|alpha test|beta test|playtest|early access)\b",original):return "gaming"
    # EA SPORTS FC is a football video game, not a consumer-technology launch.
    if re.search(r"\b(ea sports fc(?:\s*\d{2})?|ea fc(?:\s*\d{2})?|fifa|efootball|football manager|pro evolution soccer|wwe\s*2k\d{2}|street fighter|tekken|mortal kombat|nba\s*2k\d{2})\b",original):return "gaming"
    return "gaming" if gaming or hint=="gaming" else "tech"

def similarity(a,b):
    left,right=set(tokens(a)),set(tokens(b))
    both=left&right
    if len(both)<3:return 0.0
    unique=both-{"playstation","nintendo","sony","microsoft","apple","game","games","gaming","console","smartphone","android","xbox","google","steam","windows"}
    if len(unique)<2:return 0.0
    # A different numbered product or sequel must not match on brand alone.
    ln={x for x in left if x.isdigit() and 1<=len(x)<=4}
    rn={x for x in right if x.isdigit() and 1<=len(x)<=4}
    if ln and rn and not (ln&rn):return 0.0
    overlap=len(both)/max(1,min(len(left),len(right)))
    jac=len(both)/max(1,len(left|right))
    seq=SequenceMatcher(None,norm(a),norm(b)).ratio()
    if (overlap<.63 or jac<.29) and not (seq>=.72 and jac>=.27):return 0.0
    return round(.48*overlap+.33*jac+.19*seq,4)

def safe_url(url,site):
    p=urlsplit(url)
    original=urlsplit(site)
    domain=(p.hostname or "").lower().removeprefix("www.")
    official=(original.hostname or "").lower().removeprefix("www.")
    if p.scheme not in ("https","http") or not domain:return False
    if domain!=official:return False
    path=p.path.lower()
    if len(path)<20 or path in ("/notizie/","/news/","/feed/"):return False
    if re.search(r"/(tag|category|categoria|autore|author|search|page|forum|feed|offerte|promo|coupon|shop|wikis|wiki|special|guides|guide|videos|video|reviews|review|walkthroughs)/",path):return False
    # Reject evergreen walkthroughs and cheat sheets. They are not current news.
    if re.search(r"(?:-locations|-location|-puzzle|-solutions|-walkthrough|-how-to|-cheats|-tips|-quest-guide|-collectibles|-ending-explained)(?:/|$)",path):return False
    if domain=="ign.com" and not ("/articles/" in path or path.startswith("/news/")):return False
    if len(path.split("/"))<3 and "-" not in path:return False
    return True

class Anchors(HTMLParser):
    def __init__(self,site):
        super().__init__(convert_charrefs=True)
        self.site=site;self.link=None;self.depth=0;self.words=[];self.found=[];self.seen=set()
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if tag=="a" and self.link is None:
            href=urljoin(self.site,d.get("href",""))
            if safe_url(href,self.site):
                self.link=href;self.words=[];self.depth=1
        elif self.link is not None:
            if tag=="a":self.depth+=1
            if tag=="img" and d.get("alt"):self.words.append(d["alt"])
    def handle_data(self,data):
        if self.link is not None:self.words.append(data)
    def handle_endtag(self,tag):
        if tag!="a" or self.link is None:return
        self.depth-=1
        if self.depth:return
        title=re.sub(r"\s+"," "," ".join(self.words)).strip()
        key=norm(title)
        if 25<=len(title)<=210 and len(tokens(title))>=4 and not (set(tokens(title))&COMMERCIAL) and key not in self.seen:
            self.found.append((title,self.link))
            self.seen.add(key)
        self.link=None;self.words=[]

def download(url):
    req=Request(url,headers={"User-Agent":UA,"Accept-Language":"it-IT,it;q=.9","Accept":"text/html,application/rss+xml,application/xml,text/xml"})
    with urlopen(req,timeout=14) as res:
        size=res.read(1_600_001)
        if len(size)>1_600_000:raise ValueError("Source exceeds public headline scan limit")
        return size.decode("utf-8","replace")

def feed_entries(content,site):
    root=ET.fromstring(content)
    entries=[]
    for entry in list(root.findall(".//item"))+list(root.findall("{http://www.w3.org/2005/Atom}entry")):
        title=entry.findtext("title") or entry.findtext("{http://www.w3.org/2005/Atom}title") or ""
        url=entry.findtext("link") or ""
        if not url:
            a=entry.find("{http://www.w3.org/2005/Atom}link")
            if a is not None:url=a.attrib.get("href","")
        title=re.sub(r"\s+"," ",html.unescape(title)).strip()
        if 25<=len(title)<=210 and len(tokens(title))>=4 and safe_url(url,site) and not (set(tokens(title))&COMMERCIAL):
            entries.append((title,url))
    return entries[:20]

def scan_one(site):
    sid,name,kind,url,rss=site
    errors=[];front=[]
    try:
        parser=Anchors(url)
        parser.feed(download(url))
        front=parser.found
    except Exception as e:
        errors.append("homepage: "+type(e).__name__)

    # Prominent editorial links only: exclude navigation, reviews, guides,
    # affiliate content, sponsored stories and picture descriptions.
    def editorial(title,link):
        clean=norm(title)
        path=urlsplit(link).path.lower()
        if sid=="igncom" and not path.startswith("/articles/"):
            return False
        if sid=="gamespot" and not path.startswith("/articles/"):
            return False
        if sid=="eurogamer" and re.search(r"\b(locations?|walkthrough|guide|codes?|solutions?|how to|get the|tips and tricks)\b",clean):
            return False
        if sid=="polygon" and re.search(r"^(a picture of|an image of|a photo of|key art|a docked|a screenshot of)\b",clean):
            return False
        if re.search(r"\b(sponsored|advertisement|advertorial|promo code|coupon|affiliate|buy now|deal of the day)\b",clean):
            return False
        if re.search(r"\b(naked|fully nude|explicit scene)\b",clean):
            return False
        return True

    homepage=[];seen=set()
    for title,link in front:
        if link in seen or not editorial(title,link):
            continue
        seen.add(link);homepage.append((title,link))
        if len(homepage)>=20:break
    items=list(homepage)
    if len(items)<9:
        try:
            for title,link in feed_entries(download(rss),url):
                if link not in seen and editorial(title,link):
                    seen.add(link);items.append((title,link))
                if len(items)>=25:break
        except Exception as e:
            errors.append("rss: "+type(e).__name__)

    rows=[]
    for i,(title,link) in enumerate(items[:25]):
        section=classify(title) if kind=="mixed" else kind
        from_home=i<len(homepage)
        rows.append({"source":sid,"name":name,"kind":section,"title":title,
                     "url":link,"rank":i+1,"homepage":from_home,
                     "featured_priority":max(0,20-i) if from_home else 0,
                     "rss_fallback":not from_home})
    return sid,name,kind,rows,errors

def scan_sources():
    now=NOW().isoformat()
    previous={"items":[]}
    if STATE.exists():
        try:previous=json.loads(STATE.read_text(encoding="utf-8"))
        except (OSError,ValueError):pass
    old={(x.get("source"),x.get("url")):x for x in previous.get("items",[]) if isinstance(x,dict)}
    status={};counts={};seen=set();collected=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        results=list(pool.map(scan_one,SITES))
    for sid,name,kind,items,errors in results:
        status[sid]={"headlines":len(items),"errors":errors}
        counts[kind]=counts.get(kind,0)+len(items)
        for x in items:
            key=(sid,x["url"]);seen.add(key)
            old_entry=old.get(key,{})
            x["first_seen"]=old_entry.get("first_seen",now)
            x["last_seen"]=now
            collected.append(x)
    # Headlines seen at 10:00 remain eligible for an article posted at noon.
    threshold=NOW()-dt.timedelta(hours=72)
    for key,x in old.items():
        if key in seen:continue
        try:stamp=dt.datetime.fromisoformat(x.get("last_seen",""))
        except ValueError:continue
        if stamp>=threshold:collected.append(x)
    collected.sort(key=lambda x:x.get("last_seen",""),reverse=True)
    collected=collected[:550]
    report={"generated_utc":now,"sites":status,"items":collected}
    STATE.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SCANNED PORTALS: ",json.dumps(status,ensure_ascii=False))
    print("CURRENT HEADLINES:",sum(v["headlines"] for v in status.values()),"; cached:",len(collected))
    return report

# Date-only publication metadata is preferable to guessed upload times or archive order.
ITALIAN_MONTHS = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

def published_date(value):
    """Parse verified ZazoomTek calendar dates (ISO or Italian archive metadata)."""
    value = html.unescape(str(value or "")).strip().lower()
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", value)
    if match:
        try:
            return dt.date(*(int(x) for x in match.groups()))
        except ValueError:
            return None
    match = re.search(r"\b(\d{1,2})\s+([a-zà]+)\s+(\d{4})\b", value)
    if match and match.group(2) in ITALIAN_MONTHS:
        try:
            return dt.date(int(match.group(3)), ITALIAN_MONTHS[match.group(2)], int(match.group(1)))
        except ValueError:
            return None
    return None

def recency_bonus(article, on_date=None):
    """Prioritize publication in the last 48 h; never invent an unknown date.

    Up to 72 points for a story posted today; drops noticeably after day 2.
    The score from the ten independent publishers is still considered separately.
    """
    reference = on_date or NOW().date()
    if isinstance(reference, dt.datetime):
        reference = reference.date()
    published = published_date(article.get("published_at") or article.get("published_date"))
    if not published:
        return 0
    age = (reference - published).days
    if age < 0:
        return 0
    if age == 0:
        return 72
    if age == 1:
        return 62
    if age == 2:
        return 40
    if age == 3:
        return 23
    if age <= 5:
        return 12
    if age <= 7:
        return 5
    return 0

def ordinary_priority(article, on_date=None):
    """Trade off date and relevance: recent article + credible portal matches wins."""
    relevance = max(0.0, min(120.0, float(article.get("trend_score") or 0)))
    recent = recency_bonus(article, on_date)
    score = round(.65 * relevance + recent, 2)
    return (score, recent, relevance, article.get("freshness", 0))

def extract_cards(page,selector="news-row"):
    # Work only with published cards, never parse or recreate article body.
    rows=re.findall(r'<article\b[^>]*class="'+re.escape(selector)+r'[^"]*"[^>]*>.*?</article>',page,re.S)
    cards=[];seen=set()
    for row in rows:
        a=re.search(r'<h[23][^>]*><a href="([^"]+)">(.*?)</a>',row,re.S)
        pic=re.search(r'<img\b[^>]*\bsrc="([^"]+)"',row,re.S)
        if not a or not pic:continue
        link=html.unescape(a.group(1)).strip()
        title=html.unescape(re.sub(r"<[^>]+>","",a.group(2))).strip()
        image=html.unescape(pic.group(1))
        if not link.startswith("/"):link="/"+link
        if not re.fullmatch(r"/(?:news|tech-impact|gaming-inside)-[a-zA-Z0-9_-]+\.html",link):continue
        if not (ROOT/link.lstrip("/")).is_file():continue
        if link in seen:continue
        seen.add(link)
        summary=re.search(r'<p\b[^>]*>(.*?)</p>',row,re.S)
        metadata=re.search(r'<div\b[^>]*class="[^"]*news-meta[^"]*"[^>]*>(.*?)</div>',row,re.S)
        verified_date=published_date(re.sub(r"<[^>]*>"," ",metadata.group(1))) if metadata else None
        cards.append({"url":link,"title":title,"image":image,
                      "summary":html.unescape(re.sub(r"<[^>]*>","",summary.group(1))).strip() if summary else "",
                      "published_date":verified_date.isoformat() if verified_date else None,
                      "row":row})
    return cards

def community_explicit_categories():
    """Honor the editorial label from the original YouTube post, not title guesses."""
    try:
        posts=json.loads((ROOT/".youtube-posts.json").read_text(encoding="utf-8"))
    except (OSError,ValueError):
        return {}
    result={}
    for post in posts if isinstance(posts,list) else []:
        if not isinstance(post,dict) or not post.get("id"):
            continue
        lines=[x.strip() for x in (post.get("text") or "").splitlines() if x.strip()]
        if not lines:continue
        special_header=re.match(r"^news\s+(tech\s+impact|gaming\s+inside)\s*:",lines[0],re.I)
        if special_header:
            result["/news-"+post["id"]+".html"]="tech-impact" if special_header.group(1).lower().startswith("tech") else "gaming-inside"
            continue
        header=re.match(r"^news\s+(tech|game|gaming|extra)\s*(?::|$)",lines[0],re.I)
        if header:
            kind=header.group(1).lower()
            result["/news-"+post["id"]+".html"]="gaming" if kind in ("game","gaming") else kind
    return result

def owned_candidates():
    explicit=community_explicit_categories()
    # Pages are already ordered chronologically by the YouTube importer.
    # Read the next archive pages as well: a shortage of Tech on page one is
    # NOT a reason to leave a gap when fresh Tech exists slightly below.
    regular=[]
    for page in ("news.html","news-2.html","news-3.html","news-4.html","news-5.html"):
        archive=ROOT/page
        if archive.is_file():
            regular.extend(extract_cards(archive.read_text(encoding="utf-8")))
    special=[]
    for kind,page in (("tech-impact","tech-today.html"),("gaming-inside","gaming-today.html")):
        for x in extract_cards((ROOT/page).read_text(encoding="utf-8")):
            x["section"]=kind
            special.append(x)
    by_url={}
    for i,x in enumerate(regular+special):
        if x["url"] in by_url:continue
        x["section"]=x.get("section") or explicit.get(x["url"]) or classify(x["title"])
        if re.match(r"^News\s+(?:Tech\s+Impact|Gaming\s+Inside)\s*:",x["title"],re.I):
            x["section"]="tech-impact" if re.match(r"^News\s+Tech\s+Impact",x["title"],re.I) else "gaming-inside"
        x["editorial_category"]=x["url"] in explicit
        x["freshness"]=max(0,80-i)
        by_url[x["url"]]=x
    return list(by_url.values())

def matches(owned,state):
    sources=state.get("items",[])
    for article in owned:
        matched=[]
        for item in sources:
            s=similarity(article["title"],item.get("title",""))
            if s>0.0:
                matched.append((s,item))
        matched.sort(key=lambda y:y[0],reverse=True)
        # The topic of a game's launch is a gaming news item even when the
        # headline does not literally contain the words "videogame" or "PS5".
        # Use corroborating *category only*, never publisher content or imagery.
        if article["section"]=="tech" and matched and not article.get("editorial_category"):
            game_sites={m[1]["source"] for m in matched if m[0]>=.52 and m[1]["kind"]=="gaming"}
            tech_sites={m[1]["source"] for m in matched if m[0]>=.52 and m[1]["kind"]=="tech"}
            hardware=bool(re.search(r"(?i)cuffie|headset|notebook|laptop|scheda grafica|monitor|processore|smartphone|periferic|driver|mouse|tastiera|hardware|router",article["title"]))
            if game_sites and len(game_sites)>=len(tech_sites) and not hardware:
                article["section"]="gaming"
        independent=len({m[1]["source"] for m in matched if m[0]>=.54})
        article["match_count"]=independent
        article["matched_sources"]=[{"site":item["name"],"title":item["title"],"score":score}
                                    for score,item in matched[:4]]
        score=max((q for q,_ in matched),default=0)
        # Portal relevance is kept separate from publication recency.
        article["trend_score"]=round(score*100+max(0,independent-1)*9,2) if score else 0
    return owned

def prefer_latest_verified_special(selected,eligible):
    """Never let an old pinned Impact/Inside nominee hide a NEWER published item.

    The archive contains approved ZazoomTek special articles. We prefer a
    strictly newer real publication date, never a guessed discovery timestamp.
    If nothing newer exists, preserve the editor's current selection.
    """
    dated=[x for x in eligible if published_date(x.get("published_date"))]
    if not dated:
        return selected
    newest=max(dated,key=lambda x:(published_date(x.get("published_date")),
                                    x.get("trend_score",0),
                                    x.get("freshness",0)))
    previous=published_date((selected or {}).get("published_date"))
    fresh=published_date(newest.get("published_date"))
    return newest if selected is None or (fresh and (previous is None or fresh>previous or (fresh==previous and (newest.get("trend_score",0),newest.get("freshness",0)) > (selected.get("trend_score",0),selected.get("freshness",0))))) else selected


def editorial_pins():
    """Only explicitly requested Tech Impact / Gaming Inside articles enter featured.

    Missing or invalid pin data is an error, never grounds to silently
    unpin existing editorial choices.
    """
    path=ROOT/"featured-editorial-pins.json"
    state=json.loads(path.read_text(encoding="utf-8"))
    items=state.get("items")
    if not isinstance(items,list) or len(items)>2:
        raise RuntimeError("Curated featured pins must be a list of at most two")
    if items:
        raise RuntimeError("Tech Impact and Gaming Inside are reserved for their editorial boxes and archive pages")
    sections=set()
    urls=set()
    selected=[]
    for item in items:
        if not isinstance(item,dict):
            raise RuntimeError("Invalid editorial pin")
        section=item.get("section")
        url=item.get("url")
        title=item.get("title")
        image=item.get("image")
        if section not in ("tech-impact","gaming-inside") or section in sections:
            raise RuntimeError("Only one pin per authorized special section")
        if not isinstance(url,str) or not re.fullmatch(
                r"/"+re.escape(section)+r"-[a-z0-9-]+\.html",url):
            raise RuntimeError("Invalid curated special URL")
        if url in urls or not (ROOT/url.lstrip("/")).is_file():
            raise RuntimeError("Curated featured article is missing or duplicated: "+url)
        if not isinstance(title,str) or len(title.strip())<12:
            raise RuntimeError("Editorial pin lacks a verified title")
        if not isinstance(image,str) or not image.startswith("/assets/") or not (
                ROOT/image.lstrip("/")).is_file():
            raise RuntimeError("Editorial pin cover must be an existing local asset")
        sections.add(section);urls.add(url)
        selected.append({"section":section,"url":url,"title":title.strip(),
                         "image":image,"trend_score":0,"freshness":0,
                         "matched_sources":[],"summary":""})
    return selected

ITALY_TIMEZONE=ZoneInfo("Europe/Rome")

def publication_instant(article):
    """Verified original hour from this published article's Article metadata.

    Archive cards keep an Italian calendar date but do not store the hour.
    The canonical article meta timestamp takes priority, so a misleading
    stale archive row cannot promote an older story as today's news.
    """
    url=article.get("url","")
    path=ROOT/str(url).lstrip("/")
    raw=None
    if path.is_file() and path.suffix==".html":
        body=path.read_text(encoding="utf-8",errors="replace")
        match=re.search(
            r'<meta[^>]*property="article:published_time"[^>]*content="([^"]+)"',
            body,re.I)
        if match:
            raw=html.unescape(match.group(1))
    if not raw:
        raw=article.get("published_at")
    if isinstance(raw,str):
        try:
            value=dt.datetime.fromisoformat(raw.strip().replace("Z","+00:00"))
            if value.tzinfo:
                return value.astimezone(ITALY_TIMEZONE)
        except ValueError:
            pass
    # Explicit date-only metadata ranks after time-stamped stories that day.
    day=published_date(article.get("published_date") or article.get("date") or raw)
    return dt.datetime.combine(day,dt.time.min,tzinfo=ITALY_TIMEZONE) if day else None

def local_publication_date(article):
    stamp=publication_instant(article)
    return stamp.date() if stamp is not None else None

def allowed_featured_date(article,on_date=None):
    """Any genuinely published article is eligible until newer articles replace it."""
    reference=on_date or NOW().astimezone(ITALY_TIMEZONE).date()
    if isinstance(reference,dt.datetime):
        reference=reference.astimezone(ITALY_TIMEZONE).date() if reference.tzinfo else reference.date()
    day=local_publication_date(article)
    return day is not None and day<=reference

def expected_featured_sections(pins=None):
    """Maximum possible slots, NOT an instruction to fill with old content."""
    pins=editorial_pins() if pins is None else pins
    return ["tech"]*(4-len(pins))+["gaming"]+[x["section"] for x in pins]

def valid_featured_sections(items,pins=None):
    """Four real Tech plus one real Gaming, always preserve original category.

    Editorial tags are never faked. When fewer than four dated real Tech stories exist, leave available
    slots empty; never substitute extra Gaming or fake Tech categories.
    """
    pins=editorial_pins() if pins is None else pins
    if not isinstance(items,list) or len(items)!=5 or len(pins)!=0:
        return False
    sections=[x.get("section") for x in items]
    special=[x["section"] for x in pins]
    if special and sections[-len(special):]!=special:
        return False
    ordinary=sections[:len(sections)-len(special)] if special else sections
    tech_count=ordinary.count("tech")
    game_count=ordinary.count("gaming")
    return (tech_count==4 and game_count==1
            and ordinary==["tech"]*4+["gaming"])


def verified_public_article(article):
    """Never display unpublished articles or a missing/invalid cover."""
    url=article.get("url")
    image=article.get("image")
    if not isinstance(url,str) or not re.fullmatch(r"/news-[a-zA-Z0-9_-]+\.html",url):
        return False
    if not (ROOT/url.lstrip("/")).is_file():
        return False
    if not isinstance(image,str) or not image:
        return False
    return (image.startswith("https://") or
            (image.startswith("/assets/") and (ROOT/image.lstrip("/")).is_file()))

def pick(articles,on_date=None):
    """Keep the newest five verified ZazoomTek posts; never expire on idle days."""
    reference=on_date or NOW().astimezone(ITALY_TIMEZONE).date()
    if isinstance(reference,dt.datetime):
        reference=reference.astimezone(ITALY_TIMEZONE).date() if reference.tzinfo else reference.date()
    pins=editorial_pins()
    selected=[];seen=set()
    # Keep the categories from verified ZazoomTek publications, including
    # the original Community labels, never guesses from source-site headlines.
    candidates=[]
    for x in articles:
        if x.get("section") not in ("tech","gaming"):
            continue
        if not verified_public_article(x) or not allowed_featured_date(x,reference):
            continue
        if not (x.get("editorial_category") or classify(x.get("title",""))==x["section"]):
            continue
        candidates.append(x)

    auto_path=ROOT/"featured-auto-news.json"
    if auto_path.is_file():
        try:
            state=json.loads(auto_path.read_text(encoding="utf-8"))
            stamp=dt.datetime.fromisoformat(state["generated_utc"].replace("Z","+00:00"))
            stamp=stamp if stamp.tzinfo else stamp.replace(tzinfo=dt.timezone.utc)
            autos=state.get("selected",[]) if dt.timedelta(0)<=NOW()-stamp<=dt.timedelta(hours=8) else []
        except (OSError,ValueError,KeyError,TypeError):
            autos=[]
        for x in autos:
            if not isinstance(x,dict):
                continue
            kind=x.get("section")
            item={"url":x.get("url"),"title":x.get("title"),"image":x.get("image"),
                  "section":kind,"published_date":x.get("date"),
                  "trend_score":120,"freshness":100,"matched_sources":[],
                  "summary":x.get("summary",""),"selection_boost":1}
            if (kind in ("tech","gaming") and classify(item["title"] or "")==kind
                    and verified_public_article(item) and allowed_featured_date(item,reference)):
                candidates.append(item)

    manual_path=ROOT/"manual-news.json"
    manual=json.loads(manual_path.read_text(encoding="utf-8")).get("items",[]) if manual_path.is_file() else []
    for x in manual:
        if not isinstance(x,dict):continue
        slug=x.get("slug")
        url="/"+slug if isinstance(slug,str) else ""
        title=x.get("title","")
        kind=classify(title)
        if kind not in ("tech","gaming"):continue
        try:
            expiry=dt.datetime.fromisoformat(str(x.get("featured_until","")).replace("Z","+00:00"))
            active=expiry.tzinfo is not None and expiry>NOW() and x.get("featured_section")==kind
        except ValueError:
            active=False
        item={"url":url,"title":title,"image":x.get("image",""),
              "section":kind,"published_at":x.get("published_at"),
              "published_date":x.get("date"),"trend_score":120 if active else 0,
              "freshness":100 if active else 0,"matched_sources":[],
              "summary":x.get("excerpt",""),"selection_boost":2 if active else 0}
        if verified_public_article(item) and allowed_featured_date(item,reference):
            candidates.append(item)

    standard_path=ROOT/"standard-news.json"
    standard=json.loads(standard_path.read_text(encoding="utf-8")).get("articles",[]) if standard_path.is_file() else []
    for x in standard:
        if not isinstance(x,dict):continue
        kind=x.get("kind")
        title=x.get("title","")
        slug=x.get("slug")
        if kind not in ("tech","gaming") or classify(title)!=kind or not isinstance(slug,str):continue
        item={"url":"/news-"+slug+".html","title":title,
              "image":"/assets/special/news-"+slug+".webp","section":kind,
              "published_at":x.get("published_at"),"published_date":x.get("date"),
              "trend_score":0,"freshness":0,"matched_sources":[],"summary":""}
        if verified_public_article(item) and allowed_featured_date(item,reference):
            candidates.append(item)

    # Prefer the latest publication TIMES; only use older days to fill empty slots.
    # Among a day's published ZazoomTek articles, independent portal matches
    # determine which four Tech stories are the most newsworthy.
    # Never promote an older article merely because the external coverage is viral.
    def priority(item):
        # The original article publication timestamp determines which story
        # appeared first today or yesterday. Source portal trend score only
        # breaks ties: older stories can never outrank fresh ones.
        instant=publication_instant(item)
        return (instant or dt.datetime.min.replace(tzinfo=ITALY_TIMEZONE),
                item.get("match_count",0)>0,
                ordinary_priority(item,reference)[0],
                bool(item.get("selection_boost")),
                item.get("freshness",0))
    def add_best(kind,quota):
        count=0
        for item in sorted((x for x in candidates if x["section"]==kind),
                           key=priority,reverse=True):
            if count>=quota:break
            if item["url"] in seen:continue
            seen.add(item["url"])
            row=dict(item)
            row["published_date"]=local_publication_date(item).isoformat()
            selected.append(row)
            count+=1
        return count

    # Editorial policy: always select four latest verified Tech and
    # exactly one latest Gaming. Never promote extra Gaming to Tech slots.
    # If not enough Tech exist today/yesterday, leave unused slots empty.
    required_tech=4-len(pins)
    tech_count=add_best("tech",required_tech)
    add_best("gaming",1)
    # Fail closed on a broken/partial import: never overwrite the last
    # complete approved carousel with 0-4 cards, and never put Gaming in Tech.
    if tech_count!=required_tech or len(selected)!=5:
        raise RuntimeError(
            f"Refusing partial featured update: {tech_count}/{required_tech} Tech "
            f"and {len(selected)-tech_count}/1 Gaming; keep last published five.")
    # Four newest real Tech stories by original publication time.
    # Keep the newest real Gaming article in its dedicated fifth slot.
    # One Gaming story is always LAST, in the bottom-right small card.
    tech_news=[x for x in selected if x["section"]=="tech"]
    gaming_news=[x for x in selected if x["section"]=="gaming"]
    tech_news.sort(key=priority,reverse=True)
    gaming_news.sort(key=priority,reverse=True)
    selected=tech_news+gaming_news
    for pin in pins:
        if pin["url"] in seen:
            raise RuntimeError("Curated special news conflicts with existing feature")
        selected.append(pin)
        seen.add(pin["url"])
    if not valid_featured_sections(selected,pins):
        raise RuntimeError("Feature selection exceeds the strict editorial quotas")
    if any(not allowed_featured_date(x,reference) for x in selected
           if x["section"] in ("tech","gaming")):
        raise RuntimeError("Old article reached the featured grid")
    return selected

def slide_markup(chosen):
    """Five-image editorial mosaic, clickable covers without overlays."""
    cards=[]
    for n,a in enumerate(chosen):
        title=html.escape(re.sub(r"(?i)^news\s*:\s*","",str(a["title"])),quote=True)
        image=html.escape(str(a["image"]),quote=True)
        url=html.escape(str(a["url"]),quote=True)
        class_name="zt-feature-small"
        section=html.escape(str(a["section"]),quote=True)
        cards.append('<a class="zt-feature-card '+class_name+'" href="'+url+
            '" data-feature-section="'+section+'" aria-label="'+title+'" title="'+title+'"><img src="'+image+
            '" alt="'+title+'" loading="'+("eager" if n==0 else "lazy")+
            '" decoding="async"></a>')
    return '<div class="zt-featured-grid" id="ztFeaturedGrid" aria-label="Cinque news ZazoomTek in evidenza">'+"".join(cards)+"</div>"


def set_featured(index,chosen):
    start,end="<!-- FEATURED_NEWS_START -->","<!-- FEATURED_NEWS_END -->"
    assert index.count(start)==index.count(end)==1
    left=index.index(start)+len(start);right=index.index(end,left)
    replacement="\n"+slide_markup(chosen)+"\n"
    return index[:left]+replacement+index[right:]

def inject_archive(page,cards):
    text=(ROOT/page).read_text(encoding="utf-8")
    begin="<!-- TRENDING_OWN_NEWS_START -->";end="<!-- TRENDING_OWN_NEWS_END -->"
    text=re.sub(re.escape(begin)+r".*?"+re.escape(end),"",text,flags=re.S)
    allowed=[a for a in cards if a["url"].lstrip("/") not in
             re.findall(r'href="/([^"]+)"',text)]
    rows=[]
    for a in allowed[:10]:
        name=html.escape(a["title"],quote=True);url=html.escape(a["url"],quote=True)
        cover=html.escape(a["image"],quote=True)
        summary=html.escape(a["summary"][:300],quote=True)
        rows.append('<article class="news-row" data-trending-own-news="true"><a href="'+url+
                    '"><img src="'+cover+'" alt="'+name+'" loading="lazy"></a><div class="news-copy">'+
                    '<h2><a href="'+url+'">'+name+'</a></h2><div class="news-meta">ZazoomTek · News già pubblicata</div>'+
                    '<p>'+summary+'</p><a class="news-read" href="'+url+'">Leggi tutto</a></div></article>')
    match=re.search(r'<div class="news-list" id="newsList" data-auto-articles="(?:tech|gaming)">',text)
    if not match:raise RuntimeError("Missing special archive list marker: "+page)
    text=text[:match.end()]+"\n"+begin+"\n"+"\n".join(rows)+"\n"+end+"\n"+text[match.end():]
    (ROOT/page).write_text(text,encoding="utf-8")

def omit_from_home_feed(index,chosen):
    # Preserve 15 synced DOM rows and their dates but never display special
    # promoted news inside ordinary latest-news list on homepage.
    specials={a["url"].lstrip("/") for a in chosen
              if a["section"] in ("tech-impact","gaming-inside")}
    if not specials:return index
    start,end="<!-- ARTICLE_FEED_START -->","<!-- ARTICLE_FEED_END -->"
    if start not in index or end not in index:return index
    a=index.index(start)+len(start);b=index.index(end,a);section=index[a:b]
    def hide(m):
        row=m.group()
        if any(re.search(r'href="/?'+re.escape(slug)+r'"',row) for slug in specials):
            return re.sub(r'<article\b', '<article data-trending-special-hidden="true" style="display:none"',row,count=1)
        return row
    section=re.sub(r'<article class="article-row"[\s\S]*?</article>',hide,section)
    return index[:a]+section+index[b:]

def apply():
    if not STATE.exists():
        print("NO SOURCE CACHE: ranking owned published news without portal matches")
        state={"items":[]}
    else:
        state=json.loads(STATE.read_text(encoding="utf-8"))
    articles=matches(owned_candidates(),state)
    matched=[x for x in articles if x["trend_score"]>0]
    if not matched:
        print("NO RELIABLE TREND MATCHES: preserve latest verified own Tech/Gaming NEWS")
    chosen=pick(articles)
    for item in chosen:
        if item["section"] in ("tech","gaming"):
            item["freshness_bonus"]=recency_bonus(item)
            item["selection_score"]=ordinary_priority(item)[0]
    if not valid_featured_sections(chosen):
        raise RuntimeError("Featured mosaic must always have 4 Tech then 1 Gaming")
    # STRICT OWNERSHIP: the carousel updates its own JSON only.
    # index.html, the Community News archive and YouTube review/video pages are
    # exclusively owned by YouTube sync. Never modify or commit them here.
    carousel={"generated_utc":NOW().isoformat(),"items":[
        {"section":a["section"],"url":a["url"],"title":a["title"],"image":a["image"],
         **({"published_date":a["published_date"]} if a["section"] in ("tech","gaming") else {})}
        for a in chosen]}
    target=ROOT/"featured-carousel.json"
    # Do not redeploy identical six news merely because the scan timestamp moved.
    if target.is_file():
        try:
            previous=json.loads(target.read_text(encoding="utf-8"))
            if previous.get("items")==carousel["items"]:
                carousel["generated_utc"]=previous.get("generated_utc",carousel["generated_utc"])
        except (OSError,ValueError,TypeError,AttributeError):
            pass
    rendered=json.dumps(carousel,ensure_ascii=False,indent=2)+"\n"
    if not target.exists() or target.read_text(encoding="utf-8")!=rendered:
        target.write_text(rendered,encoding="utf-8")
        print("Updated isolated featured-carousel.json (not index.html).")
    report={"checked_at":NOW().isoformat(),
            "source_sites":len({x["source"] for x in state.get("items",[])}),
            "matches":len(matched),
            "selected":[{"title":a["title"],"section":a["section"],"url":a["url"],
                         "trend_score":a["trend_score"],"published_date":a.get("published_date"),
                         "freshness_bonus":a.get("freshness_bonus"),"selection_score":a.get("selection_score"),
                         "sources":a["matched_sources"]}
                        for a in chosen]}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MATCHED OWN NEWS:",len(matched))
    print("FEATURED GRID",len(chosen),":",json.dumps([{k:a[k] for k in ("section","title","trend_score")}
                                    for a in chosen],ensure_ascii=False))

def selftest():
    a="Battlefield 6 Stagione 5 porta Las Vegas e tre nuove mappe"
    b="Battlefield 6, Stagione 5: tutte le mappe nuove e Las Vegas"
    c="Battlefield 7 arriva su PS5: svelate tutte le mappe"
    assert similarity(a,b)>.3,(a,b,similarity(a,b))
    assert similarity(a,c)==0,(a,c,similarity(a,c))
    assert similarity("Apple annuncia il nuovo iPhone 19 Pro","Google annuncia Pixel 11 Pro")==0
    assert classify("Commissione europea propone nuove regole sulla privacy delle piattaforme")=="tech-impact"
    assert classify("Nuove norme sui rimborsi di giochi PlayStation")=="gaming-inside"
    assert classify("Nintendo Switch riceve un gioco Zelda")=="gaming"
    assert classify("ACE COMBAT 8 supera un milione di copie vendute")=="gaming"
    assert classify("PUBG Mobile Global Open 2026 Season 2, montepremi da 500.000 dollari")=="gaming"
    assert classify("The Talos Principle 3 mostra gameplay e trailer")=="gaming"
    assert classify("EA SPORTS FC 27, tornano le Stelle del Futuro")=="gaming"
    assert classify("EA SPORTS FC 27 apre i preorder")=="gaming"
    assert classify("Expeditions: Samurai, diario degli sviluppatori")=="gaming"
    assert classify("NBA BOUNCE si aggiorna per la stagione")=="gaming"
    assert classify("Sony ECM-AX10 porta audio spaziale professionale su smartphone")=="tech"
    assert classify("Dragon’s Dogma 2: Dark Arisen disponibile il nuovo aggiornamento")=="gaming"
    assert classify("Beyond the Dark: Nightwatch horror cooperativo in uscita")=="gaming"
    assert classify("Amazon annuncia Alexa Tablet e Google Play Store")=="tech"
    assert classify("ONE PIECE: Grand Gourmet arriva su Android, iOS, Switch e PC")=="gaming"
    assert classify("CORSAIR HS80 v2 MAX cuffie wireless per il gaming competitivo")=="tech"
    # Calendar dates, not row positions, now drive the freshness bonus.
    assert published_date("ZazoomTek · 11 ottobre 2026") == dt.date(2026,10,11)
    assert published_date("ZazoomTek · 2026-10-09") == dt.date(2026,10,9)
    assert published_date("no publication date") is None
    assert recency_bonus({"published_date":"2026-10-12"},dt.date(2026,10,12)) == 72
    assert recency_bonus({"published_date":"2026-10-11"},dt.date(2026,10,12)) == 62
    assert recency_bonus({"published_date":"2026-10-09"},dt.date(2026,10,12)) == 23
    assert recency_bonus({"published_date":"2026-10-13"},dt.date(2026,10,12)) == 0
    fresh={"published_date":"2026-10-11","trend_score":55,"freshness":10}
    stale={"published_date":"2026-10-07","trend_score":92,"freshness":80}
    assert ordinary_priority(fresh,dt.date(2026,10,12)) > ordinary_priority(stale,dt.date(2026,10,12))
    missing={"published_date":None,"trend_score":0,"freshness":80}
    assert recency_bonus(missing,dt.date(2026,10,12))==0
    old={"url":"/tech-impact-old.html","section":"tech-impact","published_date":"2026-10-11"}
    newer={"url":"/tech-impact-new.html","section":"tech-impact","published_date":"2026-10-13"}
    assert prefer_latest_verified_special(old,[old,newer])["url"]==newer["url"]
    assert prefer_latest_verified_special(newer,[old])["url"]==newer["url"]
    assert prefer_latest_verified_special(old,[])["url"]==old["url"]
    # Current archived content is changing daily; these tests must remain stable.
    reference=NOW().astimezone(ITALY_TIMEZONE).date()
    existing=matches(owned_candidates(),{"items":[]})
    sample=pick(existing,on_date=reference)
    assert valid_featured_sections(sample)
    assert len(set(x["url"] for x in sample))==len(sample)
    assert all(allowed_featured_date(x,reference) for x in sample
               if x["section"] in ("tech","gaming"))
    older=pick(existing,on_date=reference+dt.timedelta(days=10))
    assert len(older)==5 and [a["url"] for a in older]==[a["url"] for a in sample], (
        "Featured news may not disappear after ten days without new posts")
    # Only special slots require two distinct independent publisher matches.
    same_news = {"items":[
        {"source":"hdblog","name":"HDblog","kind":"tech",
         "title":"Commissione europea apre indagine sul nuovo sistema di privacy digitale"},
        {"source":"dday","name":"DDay","kind":"tech",
         "title":"Commissione europea apre indagine sul nuovo sistema di privacy digitale"},
        {"source":"dday","name":"DDay","kind":"tech",
         "title":"Commissione europea apre indagine sul nuovo sistema di privacy digitale"}]}
    candidate = {"url":"/tech-impact-test.html",
                 "title":"Commissione europea apre indagine sul nuovo sistema di privacy digitale",
                 "section":"tech-impact","freshness":20}
    scored = matches([candidate],same_news)[0]
    assert scored["match_count"] == 2, scored
    same_news["items"] = [same_news["items"][1],same_news["items"][2]]
    assert matches([dict(candidate)],same_news)[0]["match_count"] == 1
    assert len(SITES)==16 and len({s[0] for s in SITES})==16
    assert {s[0] for s in SITES}.issuperset({"igncom","gamespot","eurogamer","polygon","pcgamer","zazoom"})
    print("TREND MATCHER SELF TEST PASSED: 16 sources, exact-event guards and categories")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sources",action="store_true")
    group.add_argument("--apply",action="store_true")
    group.add_argument("--test",action="store_true")
    args=parser.parse_args()
    if args.test:selftest()
    elif args.sources:scan_sources()
    else:apply()
