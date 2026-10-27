#!/usr/bin/env python3
"""ZazoomTek SpotNews: generatore statico con menu/layout universali."""
from pathlib import Path
from html import escape as esc
import json,os,re,shutil
import urllib.request,xml.etree.ElementTree as ET
from html import unescape as unesc
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse
P=Path(__file__).resolve().parents[1]; O=P/"dist"
NAV=[("HOME","/"),("NEWS","/news.html"),("RECENSIONI","/recensioni.html"),("GUIDE","/guide.html"),("SPECIALI","/speciali.html"),("EXTRA","/extra.html"),("VIDEO","https://www.youtube.com/@ZazoomTek")]
TYPES={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra","video":"Video"}
GROUPS={"news":["news-tech","news-gaming"],"recensioni":["recensioni-tech","recensioni-gaming"],"guide":["guide"],"speciali":["speciali"],"extra":["extra"],"video":["video"],**{k:[k] for k in TYPES}}
PREVIEW=os.getenv("CF_PAGES_BRANCH","feature/spotnews-clean-rebuild")!="main"
def category_for_post(item):
 explicit=item.get("category")
 if explicit in TYPES and explicit!="video":return explicit
 kind=str(item.get("type","")).strip().lower()
 text=(str(item.get("title",""))+" "+str(item.get("text",""))[:250]).lower()
 if kind not in ("news","review","recensione","guida","guide","speciale","speciali","extra"):
  if text.startswith("news:"):kind="news"
  elif text.startswith(("review:","recensione:")):kind="review"
  elif text.startswith(("guida:","guide:")):kind="guide"
  elif text.startswith(("speciale:","special:")):kind="speciali"
  elif text.startswith("extra:"):kind="extra"
  else:return None
 if kind in ("guida","guide"):return "guide"
 if kind in ("speciale","speciali"):return "speciali"
 if kind=="extra":return "extra"
 topic=str(item.get("topic","")).lower()
 if topic not in ("tech","gaming"):
  gaming=("gaming","videogioc","playstation"," ps5"," ps4","xbox","nintendo","switch 2","gameplay","gta ","call of duty","modern warfare","walto","sesame street","ace combat","battlefield","tomb raider")
  tech=("tecnologia","hardware","smartphone","smart glasses","occhiali","dash cam","70mai","thermomate","intel","ryzen","nvidia","notebook","mini pc","router","android","apple","iphone","fotocamera","elettronica","stampante 3d")
  is_game=any(w in text for w in gaming); is_tech=any(w in text for w in tech)
  if is_game==is_tech:return None
  topic="gaming" if is_game else "tech"
 return ("news-" if kind=="news" else "recensioni-")+topic
def parse_day(value):
 try:return datetime.fromisoformat(str(value).replace("Z","+00:00")).date()
 except (ValueError,TypeError):return None
def community_posts():
 """Le Community sono importate SOLO da testo autentico in data/community.json."""
 path=P/"data/community.json"
 if not path.exists():return []
 raw=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(raw,dict) or not isinstance(raw.get("posts"),list):raise ValueError("Invalid community data")
 cutoff=datetime.now(timezone.utc).date()-timedelta(days=14)
 today=datetime.now(timezone.utc).date()
 result=[]
 for item in raw["posts"]:
  if not isinstance(item,dict):continue
  cat=category_for_post(item)
  day=parse_day(item.get("date"))
  if not cat or (not day and cat.startswith("news-")) or (day and day>today):continue
  # News historical entries stay available; the home allocator expands 14d -> 21d -> archive if needed.
  title=item.get("title"); text=item.get("text")
  if not isinstance(title,str) or not title.strip() or not isinstance(text,str) or not text.strip():continue
  post_id=str(item.get("id",""))
  if not post_id:continue
  slug="community-"+re.sub(r"[^a-z0-9]+","-",post_id.lower()).strip("-")
  if not slug or len(slug)>150:continue
  image=item.get("image","")
  image=safe_image(image)
  result.append({"slug":slug,"category":cat,"title":title.strip(),"body":[p.strip() for p in re.split(r"\n\s*\n",text) if p.strip()],"date":day.isoformat() if day else "","source":"youtube-community","image":image,"source_url":item.get("url",""),"featured":bool(item.get("featured",False)),"editorial_pick":bool(item.get("editorial_pick",False))})
 return result
def posts():
 obj=json.loads((P/"data/posts.json").read_text(encoding="utf-8"))
 if not isinstance(obj.get("posts"),list):raise ValueError("posts must be a list")
 rows=obj["posts"]+community_posts(); seen=set()
 cutoff=datetime.now(timezone.utc).date()-timedelta(days=14)
 for r in rows:
  slug=r["slug"]
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or slug in seen or slug in GROUPS:raise ValueError("Slug invalid/duplicate")
  if r["category"] not in TYPES or not isinstance(r["title"],str):raise ValueError("Post category/title invalid")
  seen.add(slug)
 return sorted([r for r in rows if not r["category"].startswith("news-") or parse_day(r.get("date")) is not None],key=lambda x:(x.get("date") or "",x.get("slug","")),reverse=True)
def videos():
 obj=json.loads((P/"data/videos.json").read_text(encoding="utf-8"))
 allowed={"review","test","unboxing"}
 seen=set();result=[]
 for v in obj.get("videos",[]):
  vid=v.get("id","")
  if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or vid in seen:continue
  if v.get("kind") not in allowed or v.get("topic") not in ("tech","gaming") or not isinstance(v.get("title"),str):continue
  seen.add(vid);result.append(v)
 return sorted(result,key=lambda x:x.get("date",""),reverse=True)
def playlist_latest():
 """Fetch playlist RSS, selecting newest PUBLISHED entry per playlist; never mix playlists."""
 playlists=json.loads((P/"data/playlists.json").read_text(encoding="utf-8")).get("playlists",[])
 output=[]
 ns={"atom":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
 for pl in playlists:
  pid=pl.get("id","")
  if not re.fullmatch(r"PL[A-Za-z0-9_-]{10,}",pid):continue
  record=None
  try:
   req=urllib.request.Request("https://www.youtube.com/feeds/videos.xml?playlist_id="+pid,headers={"User-Agent":"Mozilla/5.0"})
   with urllib.request.urlopen(req,timeout=6) as res:xml=ET.fromstring(res.read(1024*1024))
   for en in xml.findall("atom:entry",ns):
    vid=en.findtext("yt:videoId",namespaces=ns,default="")
    pub=en.findtext("atom:published",namespaces=ns,default="")
    name=en.findtext("atom:title",namespaces=ns,default="")
    if re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) and pub and name and (record is None or pub>record["date"]):
     record={"id":vid,"title":name,"date":pub}
  except Exception:pass
  # When the feed is inaccessible, do NOT masquerade the playlist cover as its latest video.
  output.append({"playlist_id":pid,"playlist":pl["title"],"video":record})
 return output
def playlist_cards():
 rows=playlist_latest()
 if not rows:return blank()
 result=[]
 for p in rows:
  pid=p["playlist_id"]; v=p.get("video")
  if v:
   vid=v["id"]
   url="https://www.youtube.com/watch?v="+vid+"&list="+pid
   pic="https://i.ytimg.com/vi/"+vid+"/hqdefault.jpg"
   title=v["title"];sub=p["playlist"]
  else:
   url="https://www.youtube.com/playlist?list="+pid
   pic=p.get("thumbnail","");title=p["playlist"];sub="Playlist · ultimo video non verificato"
  img='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic.startswith("https://i.ytimg.com/vi/") else ""
  result.append('<article class="card video-card"><a class="thumb play-thumb" href="'+esc(url,quote=True)+'" rel="noopener" aria-label="Apri su YouTube: '+esc(title,quote=True)+'">'+img+'</a><small>'+esc(sub)+'</small><h3><a href="'+esc(url,quote=True)+'" rel="noopener">'+esc(title)+'</a></h3></article>')
 return '<div class="video-magazine"><div class="video-feature">'+result[0]+'</div><div class="video-secondary">'+''.join(result[1:])+'</div></div>'
def video_cards(rows):
 if not rows:return blank()
 return '<div class="cards">'+''.join('<article class="card video-card"><a class="thumb play-thumb" href="https://www.youtube.com/watch?v='+v["id"]+'" rel="noopener"><img src="https://i.ytimg.com/vi/'+v["id"]+'/hqdefault.jpg" loading="lazy" alt=""></a><small>'+esc(v["kind"].title())+' · '+esc(v["topic"].title())+'</small><h3><a href="https://www.youtube.com/watch?v='+v["id"]+'" rel="noopener">'+esc(v["title"])+'</a></h3></article>' for v in rows)+'</div>'
def shell(title,inner):
 nav="".join('<a href="'+u+'">'+n+'</a>' for n,u in NAV)
 return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' | ZazoomTek</title><meta name="robots" content="'+("noindex,nofollow" if PREVIEW else "index,follow")+'"><link rel="stylesheet" href="/assets/css/spotnews.css?v=20261027-homeunique-10"></head><body><header class="header"><div class="wrap"><a class="logo" href="/">Zazoom<span>Tek</span></a><button id="mobile-menu" aria-controls="nav" aria-expanded="false">Menu</button><nav id="nav" aria-label="Navigazione universale">'+nav+'</nav></div></header><main class="wrap">'+inner+'</main><footer class="footer"><div class="wrap">ZazoomTek.it · Tecnologia e Gaming</div></footer><script defer src="/assets/js/site.js"></script></body></html>')
def safe_image(value):
 if not isinstance(value,str):return ""
 if value.startswith("/") and not value.startswith("//") and ".." not in value and not any(c in value for c in '<>"\\'):return value
 from urllib.parse import urlparse
 u=urlparse(value)
 if u.scheme=="https" and u.hostname in ("yt3.ggpht.com","i.ytimg.com","mcusercontent.com") and not u.username and not u.password:return value
 return ""
def blank():return '<div class="blank">Nessun contenuto pubblicato</div>'
def cards(rows):
 if not rows:return ""
 entries=[]
 for r in rows:
  cover=safe_image(r.get("image",""))
  if cover:
   visual='<img loading="lazy" src="'+esc(cover,quote=True)+'" alt="">'
  else:
   # Explicit editorial visual when the original post has no image (not a fake photograph).
   visual='<span class="editorial-cover"><span>'+esc(TYPES[r["category"]])+'</span><strong>'+esc(r["title"])+'</strong></span>'
  url="/"+r["slug"]+".html"
  entries.append('<article class="card"><a class="thumb" href="'+url+'">'+visual+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="'+url+'">'+esc(r["title"])+'</a></h3></article>')
 return '<div class="cards">'+''.join(entries)+'</div>'
SECTION_URLS={"In evidenza":"/news.html","News Tech":"/news-tech.html","News Gaming":"/news-gaming.html","Ultime Recensioni":"/recensioni.html","Guide e Extra":"/guide.html","Speciali":"/speciali.html","Ultimi Video":"https://www.youtube.com/@ZazoomTek","Notizie Web":"/notizie-web.html"}
def bar(title,link,style="section"):
 tag="h2" if style=="section" else "h3"
 button='<a class="bar-more" href="'+esc(link,quote=True)+'">Vedi tutte</a>' if link else ""
 return '<div class="bar bar-'+style+'"><'+tag+'>'+esc(title)+'</'+tag+'>'+button+'</div>'
def section(title,content):
 return '<section class="section">'+bar(title,SECTION_URLS.get(title,""))+content+'</section>'
def date_label(r):
 value=str(r.get("date",""))[:10]
 try:return datetime.strptime(value,"%Y-%m-%d").strftime("%d/%m/%Y")
 except ValueError:return ""
def overlay_card(r,kind="feature-tile"):
 link="/"+r["slug"]+".html"
 pic=safe_image(r.get("image",""))
 image='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic else '<span class="tile-no-image"><strong>'+esc(r["title"])+'</strong></span>'
 label=esc(TYPES.get(r["category"],"ZazoomTek"))
 date=date_label(r)
 stamp='<span class="tile-date">'+esc(date)+'</span>' if date else ""
 return '<article class="'+kind+'"><a class="tile-link" href="'+esc(link,quote=True)+'">'+image+'<span class="tile-gradient"></span><span class="tile-copy"><span class="tile-category">'+label+'</span><strong class="tile-title">'+esc(r["title"])+'</strong>'+stamp+'</span></a></article>'
def featured_showcase(rows):
 if not rows:return blank()
 lead=rows[0]
 rest=[p for p in rows if p["slug"]!=lead["slug"]][:4]
 markup=overlay_card(lead,"spotlight-hero")+''.join(overlay_card(r,"spotlight-tile") for r in rest)
 # More compact grid when there are fewer than five authentic reports.
 return '<div class="spotlight-grid">'+markup+'</div>'
def box(name,rows,notice=""):
 archive={"I più letti":"","Da non perdere":"/news.html","Dalla redazione":"/speciali.html",
          "Ultime notizie":"/news.html","Ultime recensioni":"/recensioni.html",
          "News Tech":"/news-tech.html","News Gaming":"/news-gaming.html",
          "Guide e Extra":"/guide.html","Speciali":"/speciali.html"}.get(name,"")
 heading=bar(name,archive,"sidebar")
 if not rows:
  return '<section class="box editorial-box">'+heading+'<p class="editorial-status">'+esc(notice or "Non ci sono ancora articoli disponibili.")+'</p></section>'
 big=overlay_card(rows[0],"editorial-hero")
 compact=[]
 for r in rows[1:3]:
  link="/"+r["slug"]+".html"
  pic=safe_image(r.get("image",""))
  image='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic else '<span class="editorial-cover editorial-cover-mini"><strong>'+esc(r["title"])+'</strong></span>'
  stamp=date_label(r)
  compact.append('<article class="editorial-row"><a class="editorial-thumb" href="'+link+'">'+image+'</a><div class="editorial-row-copy"><a href="'+link+'"><strong>'+esc(r["title"])+'</strong></a>'+('<time>'+esc(stamp)+'</time>' if stamp else "")+'</div></article>')
 return '<section class="box editorial-box">'+heading+big+'<div class="editorial-links">'+''.join(compact)+'</div></section>'
def sidebar(rows,home=False,used=None):
 used=used if used is not None else set()
 # Sidebar home only receives content not already displayed anywhere else on Home.
 groups=[
  ("I più letti",sort_by_date_desc([r for r in rows if isinstance(r.get("views"),int) and r["views"]>0])),
  ("Da non perdere",[r for r in rows if r.get("featured")]),
  ("Dalla redazione",[r for r in rows if r.get("editorial_pick") or r["category"] in ("speciali","guide","extra")]),
  ("Ultime notizie",[r for r in rows if r["category"].startswith("news-")]),
  ("Ultime recensioni",[r for r in rows if r["category"].startswith("recensioni-") and r.get("source")=="youtube-community"])
 ]
 result=[]
 for label,candidates in groups:
  selected=take_unique(candidates,3,used)
  if selected:result.append(box(label,selected))
 # Any remaining real posts can complete the last editorial box without duplicating.
 remaining=take_unique(rows,3,used)
 if remaining:result.append(box("Dagli archivi",remaining))
 return '<aside class="sidebar '+("home-sidebar" if home else "inner-sidebar")+'" aria-label="Box editoriali"><div class="sidebar-stack">'+''.join(result)+'</div></aside>'
def related(rows,exclude="",category=None):
 found=[r for r in rows if r["slug"]!=exclude and (category is None or r["category"]==category)][:8]
 return '<section class="related"><h2>Articoli correlati</h2>'+('<ul>'+''.join('<li><a href="/'+r["slug"]+'.html"><strong>'+esc(r["title"])+'</strong></a></li>' for r in found)+'</ul>' if found else blank())+'</section>'
def feature_mini_cards(items):
 rendered=[]
 for r in items[:2]:
  href="/"+r["slug"]+".html"
  image=safe_image(r.get("image",""))
  pic='<img loading="lazy" src="'+esc(image,quote=True)+'" alt="">' if image else '<span class="editorial-cover editorial-cover-mini"><strong>'+esc(r["title"])+'</strong></span>'
  rendered.append('<article class="card"><a class="thumb" href="'+href+'">'+pic+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="'+href+'">'+esc(r["title"])+'</a></h3></article>')
 # Do not generate empty placeholders or invented articles.
 return '<div class="cards">'+''.join(rendered)+'</div>'
def feature_box(label,items):
 primary=items[:1]; secondary=items[1:3]
 href="/guide.html" if label=="GUIDE" else "/extra.html"
 return '<div class="spotnews-feature">'+bar(label,href,"feature")+'<div class="feature-main">'+cards(primary)+'</div><div class="feature-small">'+feature_mini_cards(secondary)+'</div></div>'
def special_gallery(rows):
 return '<div class="specials-thumbnails">'+cards(rows[:2])+'</div>' if rows else blank()
def feature_pair(guides,extras):
 return '<div class="feature-pair">'+feature_box("GUIDE",guides)+feature_box("EXTRA",extras)+'</div>'
# Feed RSS pubblici di sei testate italiane, un articolo per testata, fonte esterna esplicita.
_WEB_NEWS_CACHE=None
def tech_sources():
 return json.loads((P/"data/web_sources.json").read_text(encoding="utf-8"))["sources"]
def clean_feed_text(value):
 return re.sub(r"\s+"," ",unesc(re.sub(r"<[^>]*>"," ",str(value or "")))).strip()
def tech_article_link(value,site_domain):
 u=urlparse(unesc(str(value or "").strip()))
 domain=(u.hostname or "").lower()
 domain=domain.removeprefix("www.")
 return u.scheme=="https" and (domain==site_domain or domain.endswith("."+site_domain)) and not u.username and not u.password
def rss_card_for_source(source,cutoff):
 from email.utils import parsedate_to_datetime
 u=source["feed"]
 try:
  req=urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0 (compatible; ZazoomTekWebNews/1.0; +https://zazoomtek.it)","Accept":"application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
  with urllib.request.urlopen(req,timeout=5) as response:
   xml=ET.fromstring(response.read(1_800_000))
 except Exception:
  return None
 ns_media="{http://search.yahoo.com/mrss/}"
 ns_content="{http://purl.org/rss/1.0/modules/content/}"
 ns_dc="{http://purl.org/dc/elements/1.1/}"
 rows=xml.findall(".//item")
 if not rows:rows=xml.findall("{http://www.w3.org/2005/Atom}entry")
 best=None
 for en in rows[:30]:
  title=clean_feed_text(en.findtext("title") or en.findtext("{http://www.w3.org/2005/Atom}title"))
  url=en.findtext("link")
  if not url:
   al=en.find("{http://www.w3.org/2005/Atom}link")
   if al is not None:url=al.get("href")
  if not title or not tech_article_link(url,source["domain"]):continue
  raw_date=en.findtext("pubDate") or en.findtext(ns_dc+"date") or en.findtext("{http://www.w3.org/2005/Atom}published") or en.findtext("{http://www.w3.org/2005/Atom}updated")
  if not raw_date:continue
  day=parse_day(raw_date)
  if day is None:
   try:day=parsedate_to_datetime(raw_date).date()
   except (TypeError,ValueError):continue
  if day<cutoff or day>datetime.now(timezone.utc).date():continue
  img=""
  for node in (en.find(ns_media+"content"),en.find(ns_media+"thumbnail"),en.find("enclosure"),en.find("{http://www.w3.org/2005/Atom}link")):
   if node is None:continue
   proposed=node.get("url","") if node.tag!="{http://www.w3.org/2005/Atom}link" else ""
   if proposed.startswith("https://") and (node.get("type","").startswith("image/") or proposed.lower().split("?")[0].endswith((".jpg",".jpeg",".png",".webp")) or node.tag in (ns_media+"content",ns_media+"thumbnail")):
    img=proposed;break
  if not img:
   content=en.findtext(ns_content+"encoded") or en.findtext("description") or en.findtext("{http://www.w3.org/2005/Atom}summary") or ""
   m=re.search(r'<img[^>]+(?:src|data-src)\s*=\s*["\'](https://[^"\']+)',unesc(content),re.I)
   if m:img=m.group(1)
  if not img.startswith("https://") or len(img)>1500:img=""
  row={"source":source["name"],"title":title,"url":url.strip(),"image":img,"date":day.isoformat(),"from_feed":True}
  if best is None or row["date"]>best["date"]:best=row
 return best
def web_news():
 global _WEB_NEWS_CACHE
 if _WEB_NEWS_CACHE is not None:return _WEB_NEWS_CACHE
 sources=tech_sources()
 snapshots=json.loads((P/"data/web.json").read_text(encoding="utf-8")).get("items",[])
 backup={x.get("source"):x for x in snapshots if isinstance(x,dict)}
 cutoff=datetime.now(timezone.utc).date()-timedelta(days=14)
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=6) as pool:
  future=[pool.submit(rss_card_for_source,s,cutoff) for s in sources]
  live=[]
  for f in future:
   try:live.append(f.result())
   except Exception:live.append(None)
 cards=[]
 for source,actual in zip(sources,live):
  if actual:cards.append(actual);continue
  b=backup.get(source["name"])
  if b and tech_article_link(b.get("url"),source["domain"]) and (parse_day(b.get("date")) or datetime.min.date())>=cutoff:
   cards.append({"source":source["name"],"title":b["title"],"url":b["url"],"image":b.get("image",""),"date":b.get("date",""),"from_feed":False})
  else:
   # Unavailable feed: link to source only, never a fabricated article.
   cards.append({"source":source["name"],"title":"Leggi le ultime notizie di "+source["name"],"url":source["home"],"image":"","date":"","from_feed":False,"source_only":True})
 _WEB_NEWS_CACHE=cards
 return cards
def web_news_cards(items):
 if not items:return blank()
 out=[]
 for item in items[:6]:
  url=esc(item["url"],quote=True)
  name=esc(item["source"])
  title=esc(item["title"])
  image=item.get("image","")
  safe_image_url=image if isinstance(image,str) and image.startswith("https://") and not any(ch in image for ch in '<>"\'') else ""
  visual=('<img src="'+esc(safe_image_url,quote=True)+'" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.hidden=true">' if safe_image_url else '<span class="web-news-fallback">'+name+'</span>')
  datelabel=str(item.get("date",""))
  when='<time datetime="'+esc(datelabel,quote=True)+'">'+esc(datelabel[8:10]+"/"+datelabel[5:7]+"/"+datelabel[0:4])+'</time>' if re.fullmatch(r"\d{4}-\d{2}-\d{2}",datelabel) else ""
  sub='<span class="web-source">'+name+'</span>'
  if item.get("source_only"):sub+='<span class="web-source-only">Feed temporaneamente non disponibile</span>'
  out.append('<article class="web-news-card"><a class="web-news-thumb" href="'+url+'" target="_blank" rel="noopener noreferrer" aria-label="Apri la fonte originale: '+title+'">'+visual+'</a>'+sub+'<h3><a href="'+url+'" target="_blank" rel="noopener noreferrer">'+title+'</a></h3>'+when+'</article>')
 return '<div class="web-news-grid">'+''.join(out)+'</div>'

# Every Home content is allocated once: the same post/video/url is never placed in two widgets.
def home_identity(r):
 url=str(r.get("source_url") or r.get("url") or "").strip().lower()
 if url.startswith("https://"):return "url:"+url.split("?",1)[0].rstrip("/")
 name=re.sub(r"[^a-z0-9]+","",unesc(str(r.get("title","")).casefold()))
 return "title:"+name if name else "slug:"+str(r.get("slug",""))
def sort_by_date_desc(items):
 return sorted(items,key=lambda r:(str(r.get("date") or ""),str(r.get("slug") or "")),reverse=True)
def take_unique(items,count,used):
 result=[]
 for row in sort_by_date_desc(items):
  identity=home_identity(row)
  if identity in used:continue
  used.add(identity)
  result.append(row)
  if len(result)>=count:break
 return result
def adaptive_news(items,count,used):
 today=datetime.now(timezone.utc).date()
 # Priority: last 14 days, then 21, then any earlier authentic archive entry.
 for days in (14,21,None):
  if days is None:pool=items
  else:
   cutoff=today-timedelta(days=days)
   pool=[r for r in items if (parse_day(r.get("date")) or datetime.min.date())>=cutoff]
  remaining=count-len([x for x in used if x.startswith("home:")]) if False else None
  # Candidates are passed to the same global registry on every pass.
  result=[] if days==14 else result
  for r in sort_by_date_desc(pool):
   key=home_identity(r)
   if key in used:continue
   result.append(r);used.add(key)
   if len(result)==count:return result
 return result
def home(rows):
 global_used=set()
 tech=[r for r in rows if r["category"]=="news-tech"]
 gaming=[r for r in rows if r["category"]=="news-gaming"]
 all_news=sort_by_date_desc(tech+gaming)
 # The latest dated news leads regardless of category or editorial flag.
 spotlight=adaptive_news(all_news,5,global_used)
 tech_low=adaptive_news(tech,6,global_used)
 gaming_low=adaptive_news(gaming,4,global_used)
 reviews=take_unique([r for r in rows if r["category"] in ("recensioni-tech","recensioni-gaming") and r.get("source")=="youtube-community"],4,global_used)
 specials=take_unique([r for r in rows if r["category"]=="speciali"],2,global_used)
 guides=take_unique([r for r in rows if r["category"]=="guide"],3,global_used)
 extras=take_unique([r for r in rows if r["category"]=="extra"],3,global_used)
 video_section=playlist_cards()
 external=web_news()
 # URLs/titles selected for Notizie Web are external; mark them as used to avoid repeated home references.
 unique_web=[]
 for entry in sort_by_date_desc(external):
  ident=home_identity(entry)
  if ident in global_used:continue
  global_used.add(ident);unique_web.append(entry)
 sections=[
  ("News Tech",cards(tech_low)),
  ("News Gaming",cards(gaming_low)),
  ("Ultime Recensioni",cards(reviews)),
  ("Speciali",special_gallery(specials)+feature_pair(guides,extras)),
  ("Ultimi Video",video_section),
  ("Notizie Web",web_news_cards(unique_web))
 ]
 # Sidebar is last by design, so its articles can never duplicate the primary blocks.
 sidebar_html=sidebar(rows,True,global_used)
 top=section("In evidenza",featured_showcase(spotlight))
 return shell("Home",'<div class="featured-wide">'+top+'</div><div class="home-layout"><div class="home-column">'+''.join(section(name,content) for name,content in sections)+'</div>'+sidebar_html+'</div>')
def web_archive(rows):
 content='<h1>Notizie Web</h1><p class="web-archive-intro">Sei fonti italiane di tecnologia. Ogni collegamento apre la notizia sul sito originale.</p>'+web_news_cards(web_news())
 return inside("Notizie Web",content,rows,show_related=False)
def inside(title,content,rows,exclude="",cat=None,show_related=True):
 # Article/archive content determines the height. Related articles always start after its end.
 extra=related(rows,exclude,cat) if show_related else ""
 return shell(title,'<div class="inner-layout"><div class="inner-column">'+content+'</div>'+sidebar(rows)+'</div>'+extra)
ARCHIVE_PAGE_SIZE=9
def pagination_links(key,page,total_pages):
 if total_pages<=1:return ""
 links=[]
 for n in range(1,total_pages+1):
  href="/"+key+(".html" if n==1 else "-page-"+str(n)+".html")
  if n==page:links.append('<span class="page-current" aria-current="page">'+str(n)+'</span>')
  else:links.append('<a href="'+href+'" aria-label="Pagina '+str(n)+'">'+str(n)+'</a>')
 return '<nav class="pagination" aria-label="Paginazione archivio">'+''.join(links)+'</nav>'
def archive(key,rows,page=1):
 categories=GROUPS[key]
 label={"news":"News","news-tech":"News Tech","news-gaming":"News Gaming",
        "recensioni":"Recensioni","recensioni-tech":"Recensioni Tech",
        "recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali",
        "extra":"Extra","video":"Video"}.get(key,key.replace("-"," ").title())
 selected=[r for r in rows if r["category"] in categories]
 if key=="video":return inside(label,'<h1>'+esc(label)+'</h1>'+playlist_cards(),rows,show_related=False)
 import math
 count=max(1,math.ceil(len(selected)/ARCHIVE_PAGE_SIZE))
 offset=(page-1)*ARCHIVE_PAGE_SIZE
 visible=selected[offset:offset+ARCHIVE_PAGE_SIZE]
 content='<h1>'+esc(label)+'</h1>'+cards(visible)+pagination_links(key,page,count)
 return inside(label,content,rows,show_related=False)
def article(r,rows):
 cover=('<img class="cover" src="'+esc(r["image"],quote=True)+'" alt="">') if bool(safe_image(r.get("image",""))) else ""
 text=''.join('<p>'+esc(p)+'</p>' for p in r.get("body",[]) if isinstance(p,str))
 video=('<div class="player"><iframe title="Video YouTube" loading="lazy" allowfullscreen src="https://www.youtube-nocookie.com/embed/'+r["youtube_id"]+'"></iframe></div>') if re.fullmatch(r"[A-Za-z0-9_-]{11}",r.get("youtube_id","")) else ""
 body='<article class="article"><h1>'+esc(r["title"])+'</h1><p class="category">'+esc(TYPES[r["category"]])+'</p>'+cover+video+'<div class="article-text">'+text+'</div></article>'
 return inside(r["title"],body,rows,r["slug"],r["category"])
def main():
 rows=posts()
 if O.exists():shutil.rmtree(O)
 (O/"assets/css").mkdir(parents=True);(O/"assets/js").mkdir(parents=True)
 shutil.copy2(P/"assets/css/spotnews.css",O/"assets/css/spotnews.css")
 shutil.copy2(P/"assets/js/site.js",O/"assets/js/site.js")
 (O/"index.html").write_text(home(rows),encoding="utf-8")
 for key in GROUPS:
  (O/(key+".html")).write_text(archive(key,rows),encoding="utf-8")
  if key!="video":
   import math
   count=sum(r["category"] in GROUPS[key] for r in rows)
   for page in range(2,max(1,math.ceil(count/ARCHIVE_PAGE_SIZE))+1):
    (O/(key+"-page-"+str(page)+".html")).write_text(archive(key,rows,page),encoding="utf-8")
 (O/"notizie-web.html").write_text(web_archive(rows),encoding="utf-8")
 for r in rows:(O/(r["slug"]+".html")).write_text(article(r,rows),encoding="utf-8")
 (O/"404.html").write_text(shell("Pagina non trovata","<h1>Pagina non trovata</h1>"),encoding="utf-8")
 (O/"_headers").write_text("/*\n  X-Content-Type-Options: nosniff\n"+("  X-Robots-Tag: noindex, nofollow\n" if PREVIEW else ""),encoding="utf-8")
 print("SpotNews build OK:",len(rows),"articoli,",len(GROUPS)+2,"pagine.")
if __name__=="__main__":main()
