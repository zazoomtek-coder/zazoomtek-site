#!/usr/bin/env python3
"""Promote only existing ZazoomTek news by comparison with ten Italian publishers.

--sources: read public homepage headlines and RSS fallbacks (no article bodies).
--apply: use cached trend headlines to reshuffle 10 existing ZazoomTek carousel
         links, and cross-list eligible own news in the two dedicated archives.
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
    gaming=bool(words&GAMING) or bool(re.search(r"\b(call of duty|playstation|video game|videogioc\w*|game pass|steam|fortnite|battlefield|ace combat|talos principle|elden ring|resident evil|gran turismo|metal gear|arc raiders|silent hill|the witcher|god of war|the last of us|yakuza|ghost of tsushima|dragons dogma|dragon s dogma|beyond the dark|nightwatch|horror cooperativo|skate|two point museum|mafia iii|risk of rain|cosmic invasion)\b",original))
    if politics and gaming and (bool(words&GAMING_POLICY) or "norme" in words):return "gaming-inside"
    if politics and not gaming:return "tech-impact"
    # Gaming-branded hardware is still technology, not video-game news.
    device=bool(re.search(r"\b(cuffie|auricolari|headset|microfono|notebook|laptop|smartphone|router|tastiera|mouse|monitor|scheda grafica|videocamera|audio spaziale|tablet|fotocamera|ssd|dash cam)\b",original))
    if device:return "tech"
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
    if re.search(r"/(tag|category|categoria|autore|author|search|page|forum|feed|offerte|promo|coupon|shop)/",path):return False
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
    items=[];errors=[]
    try:
        parser=Anchors(url);parser.feed(download(url))
        items=parser.found[:20]
    except Exception as e:errors.append("homepage: "+type(e).__name__)
    if len(items)<8:
        try:
            for title,link in feed_entries(download(rss),url):
                if not any(norm(title)==norm(p[0]) for p in items):items.append((title,link))
        except Exception as e:errors.append("rss: "+type(e).__name__)
    return sid,name,kind,[{"source":sid,"name":name,"kind":kind,"title":t,"url":u,
                         "rank":i+1,"homepage":i<20 and len(items)>0} for i,(t,u) in enumerate(items[:25])],errors

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
    collected=collected[:360]
    report={"generated_utc":now,"sites":status,"items":collected}
    STATE.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SCANNED PORTALS: ",json.dumps(status,ensure_ascii=False))
    print("CURRENT HEADLINES:",sum(v["headlines"] for v in status.values()),"; cached:",len(collected))
    return report

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
        cards.append({"url":link,"title":title,"image":image,
                      "summary":html.unescape(re.sub(r"<[^>]*>","",summary.group(1))).strip() if summary else "",
                      "row":row})
    return cards

def owned_candidates():
    regular=extract_cards((ROOT/"news.html").read_text(encoding="utf-8"))
    special=[]
    for kind,page in (("tech-impact","tech-today.html"),("gaming-inside","gaming-today.html")):
        for x in extract_cards((ROOT/page).read_text(encoding="utf-8")):
            x["section"]=kind
            special.append(x)
    by_url={}
    for i,x in enumerate(regular+special):
        if x["url"] in by_url:continue
        x["section"]=x.get("section") or classify(x["title"]+" "+x.get("summary",""))
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
        if article["section"]=="tech" and matched:
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
        article["trend_score"]=round(score*100+max(0,independent-1)*9+
                                min(10,article["freshness"]*.06),2) if score else 0
    return owned

def pick(articles):
    for a in articles:a["promoted_section"]=a["section"]
    ordinary_tech=sorted((a for a in articles if a["section"]=="tech"),key=lambda a:(a["trend_score"],a["freshness"]),reverse=True)
    ordinary_game=sorted((a for a in articles if a["section"]=="gaming"),key=lambda a:(a["trend_score"],a["freshness"]),reverse=True)
    special_tech=sorted((a for a in articles if a["section"]=="tech-impact"),key=lambda a:(a["trend_score"],a["freshness"]),reverse=True)
    special_game=sorted((a for a in articles if a["section"]=="gaming-inside"),key=lambda a:(a["trend_score"],a["freshness"]),reverse=True)
    has_st=any(a["trend_score"]>=55 for a in special_tech)
    has_sg=any(a["trend_score"]>=55 for a in special_game)
    if has_st and has_sg:quotas=[(special_tech,2),(special_game,2),(ordinary_tech,3),(ordinary_game,3)]
    elif has_st:quotas=[(special_tech,2),(ordinary_tech,4),(ordinary_game,4)]
    elif has_sg:quotas=[(special_game,2),(ordinary_tech,4),(ordinary_game,4)]
    else:quotas=[(ordinary_tech,5),(ordinary_game,5)]
    chosen=[];seen=set()
    def add(article):
        if article["url"] in seen:return
        seen.add(article["url"]);chosen.append(article)
    for group,n in quotas:
        for x in group[:n]:add(x)
    # Do not duplicate or fabricate articles; rebalance slots if fewer than 10.
    rest=sorted(ordinary_tech+ordinary_game+special_tech+special_game,
                key=lambda a:(a["trend_score"],a["freshness"]),reverse=True)
    for a in rest:
        if len(chosen)>=10:break
        add(a)
    return chosen[:10]

def slide_markup(chosen):
    cards=[]
    for n,x in enumerate(chosen):
        cards.append('<article class="news-slide'+(' active' if n==0 else '')+
           '" data-slide="'+str(n)+'" data-trend-category="'+x["section"]+
           '" data-trend-matched="'+str(bool(x["trend_score"])).lower()+'"><a href="'+
           html.escape(x["url"],quote=True)+'"><img src="'+
           html.escape(x["image"],quote=True)+'" alt="'+html.escape(x["title"],quote=True)+
           '" loading="lazy"></a></article>')
    return '<div class="news-slider" id="newsSlider"><div class="news-slides">'+("\n".join(cards))+'</div></div>'

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
        print("NO SOURCE CACHE: preserving previously published carousel")
        return
    state=json.loads(STATE.read_text(encoding="utf-8"))
    articles=matches(owned_candidates(),state)
    matched=[x for x in articles if x["trend_score"]>0]
    if not matched:
        print("NO RELIABLE TREND MATCHES: preserving existing carousel and special pages")
        REPORT.write_text(json.dumps({"checked_at":NOW().isoformat(),"matches":0,
             "note":"No new promotion until same-event trend matches exist."},indent=2)+"\n")
        return
    chosen=pick(articles)
    if len(chosen)<8:raise RuntimeError("Insufficient own published news for a balanced slider")
    index=INDEX.read_text(encoding="utf-8")
    index=set_featured(index,chosen)
    index=omit_from_home_feed(index,chosen)
    INDEX.write_text(index,encoding="utf-8")
    for section,path in (("tech-impact","tech-today.html"),("gaming-inside","gaming-today.html")):
        relevant=[a for a in articles if a["section"]==section and a["trend_score"]>=55
                  and a["url"].startswith("/news-")]
        inject_archive(path,sorted(relevant,key=lambda a:a["trend_score"],reverse=True))
    report={"checked_at":NOW().isoformat(),
            "source_sites":len({x["source"] for x in state.get("items",[])}),
            "matches":len(matched),
            "selected":[{"title":a["title"],"section":a["section"],"url":a["url"],
                         "trend_score":a["trend_score"],"sources":a["matched_sources"]}
                        for a in chosen]}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("MATCHED OWN NEWS:",len(matched))
    print("CAROUSEL 10:",json.dumps([{k:a[k] for k in ("section","title","trend_score")}
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
    assert classify("The Talos Principle 3 mostra gameplay e trailer")=="gaming"
    assert classify("Sony ECM-AX10 porta audio spaziale professionale su smartphone")=="tech"
    assert classify("Dragon’s Dogma 2: Dark Arisen disponibile il nuovo aggiornamento")=="gaming"
    assert classify("Beyond the Dark: Nightwatch horror cooperativo in uscita")=="gaming"
    assert classify("Amazon annuncia Alexa Tablet e Google Play Store")=="tech"
    assert classify("CORSAIR HS80 v2 MAX cuffie wireless per il gaming competitivo")=="tech"
    assert len(SITES)==10 and len({s[0] for s in SITES})==10
    print("TREND MATCHER SELF TEST PASSED: 10 sources, exact-event guards and categories")

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
