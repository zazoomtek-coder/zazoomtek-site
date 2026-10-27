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
  if cat.startswith("news-") and day<cutoff:continue
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
 return sorted([r for r in rows if not r["category"].startswith("news-") or (parse_day(r.get("date")) is not None and parse_day(r["date"])>=cutoff)],key=lambda x:x.get("date",""),reverse=True)
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
 return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' | ZazoomTek</title><meta name="robots" content="'+("noindex,nofollow" if PREVIEW else "index,follow")+'"><link rel="stylesheet" href="/assets/css/spotnews.css?v=20261027-unified-7"></head><body><header class="header"><div class="wrap"><a class="logo" href="/">Zazoom<span>Tek</span></a><button id="mobile-menu" aria-controls="nav" aria-expanded="false">Menu</button><nav id="nav" aria-label="Navigazione universale">'+nav+'</nav></div></header><main class="wrap">'+inner+'</main><footer class="footer"><div class="wrap">ZazoomTek.it · Tecnologia e Gaming</div></footer><script defer src="/assets/js/site.js"></script></body></html>')
def safe_image(value):
 if not isinstance(value,str):return ""
 if value.startswith("/") and not value.startswith("//") and ".." not in value and not any(c in value for c in '<>"\\'):return value
 from urllib.parse import urlparse
 u=urlparse(value)
 if u.scheme=="https" and u.hostname in ("yt3.ggpht.com","i.ytimg.com","mcusercontent.com") and not u.username and not u.password:return value
 return ""
def blank():return '<div class="blank">Nessun contenuto pubblicato</div>'
def cards(rows):
 return '<div class="cards">'+''.join('<article class="card"><a class="thumb" href="/'+r["slug"]+'.html">'+('<img loading="lazy" src="'+esc(r["image"],quote=True)+'" alt="">' if bool(safe_image(r.get("image",""))) else "")+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="/'+r["slug"]+'.html">'+esc(r["title"])+'</a></h3></article>' for r in rows)+'</div>' if rows else blank()
SECTION_URLS={"In evidenza":"/news.html","News Tech":"/news-tech.html","News Gaming":"/news-gaming.html","Ultime Recensioni":"/recensioni.html","Guide e Extra":"/guide.html","Ultimi Video":"https://www.youtube.com/@ZazoomTek","Notizie Web":"/notizie-web.html"}
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
 image='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic else '<span class="tile-no-image"></span>'
 label=esc(TYPES.get(r["category"],"ZazoomTek"))
 date=date_label(r)
 stamp='<span class="tile-date">'+esc(date)+'</span>' if date else ""
 return '<article class="'+kind+'"><a class="tile-link" href="'+esc(link,quote=True)+'">'+image+'<span class="tile-gradient"></span><span class="tile-copy"><span class="tile-category">'+label+'</span><strong class="tile-title">'+esc(r["title"])+'</strong>'+stamp+'</span></a></article>'
def featured_showcase(rows):
 if not rows:return blank()
 lead=next((p for p in rows if p["category"]=="news-tech"),rows[0])
 rest=[p for p in rows if p["slug"]!=lead["slug"]][:4]
 markup=overlay_card(lead,"spotlight-hero")+''.join(overlay_card(r,"spotlight-tile") for r in rest)
 if len(rest)<4:
  markup+=''.join('<div class="spotlight-placeholder" aria-hidden="true"></div>' for _ in range(4-len(rest)))
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
  image='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic else '<span class="editorial-image-fallback"></span>'
  stamp=date_label(r)
  compact.append('<article class="editorial-row"><a class="editorial-thumb" href="'+link+'">'+image+'</a><div class="editorial-row-copy"><a href="'+link+'"><strong>'+esc(r["title"])+'</strong></a>'+('<time>'+esc(stamp)+'</time>' if stamp else "")+'</div></article>')
 return '<section class="box editorial-box">'+heading+big+'<div class="editorial-links">'+''.join(compact)+'</div></section>'
def sidebar(rows,home=False):
 def choose(items,n=3):
  seen=set();out=[]
  for item in items:
   if item["slug"] in seen:continue
   seen.add(item["slug"]);out.append(item)
   if len(out)>=n:break
  return out
 popular=choose(sorted([r for r in rows if isinstance(r.get("views"),int) and r["views"]>0],key=lambda r:r["views"],reverse=True))
 picks=choose(r for r in rows if r.get("featured"))
 editorial=choose(r for r in rows if r.get("editorial_pick"))
 if not editorial:editorial=choose(r for r in rows if r["category"] in ("speciali","guide","extra"))
 tech=choose(r for r in rows if r["category"]=="news-tech")
 gaming=choose(r for r in rows if r["category"]=="news-gaming")
 recent=choose(r for r in rows if r["category"].startswith("news-"))
 reviews=choose(r for r in rows if r["category"].startswith("recensioni-") and r.get("source")=="youtube-community")
 guides=choose(r for r in rows if r["category"] in ("guide","speciali","extra"))
 # The homepage retains all editorial labels, including statistics pending for Most Read.
 sections=[("I più letti",popular),("Da non perdere",picks),("Dalla redazione",editorial),
           ("News Tech",tech),("News Gaming",gaming),("Ultime notizie",recent),
           ("Ultime recensioni",reviews),("Guide e Extra",guides)]
 inner=''.join(box(label,entries,"Dati di lettura non ancora disponibili.") for label,entries in sections)
 # On article pages, the sidebar is clipped to the actual text column, never the related stories.
 return '<aside class="sidebar '+("home-sidebar" if home else "inner-sidebar")+'" aria-label="Box editoriali"><div class="sidebar-stack">'+inner+'</div></aside>'
def related(rows,exclude="",category=None):
 found=[r for r in rows if r["slug"]!=exclude and (category is None or r["category"]==category)][:8]
 return '<section class="related"><h2>Articoli correlati</h2>'+('<ul>'+''.join('<li><a href="/'+r["slug"]+'.html"><strong>'+esc(r["title"])+'</strong></a></li>' for r in found)+'</ul>' if found else blank())+'</section>'
def feature_mini_cards(items):
 rendered=[]
 for r in items[:2]:
  href="/"+r["slug"]+".html"
  image=safe_image(r.get("image",""))
  pic='<img loading="lazy" src="'+esc(image,quote=True)+'" alt="">' if image else ""
  rendered.append('<article class="card"><a class="thumb" href="'+href+'">'+pic+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="'+href+'">'+esc(r["title"])+'</a></h3></article>')
 for _ in range(2-len(rendered)):
  rendered.append('<div class="mini-empty" aria-label="Posizione riservata a una prossima notizia">Nuove guide in arrivo</div>')
 return '<div class="cards">'+''.join(rendered)+'</div>'
def feature_box(label,items):
 primary=items[:1]; secondary=items[1:3]
 href="/guide.html" if label=="GUIDE" else "/speciali.html"
 return '<div class="spotnews-feature">'+bar(label,href,"feature")+'<div class="feature-main">'+cards(primary)+'</div><div class="feature-small">'+feature_mini_cards(secondary)+'</div></div>'
def feature_pair(guides,extras):
 return '<div class="feature-pair">'+feature_box("GUIDE",guides)+feature_box("SPECIALI ED EXTRA",extras)+'</div>'
def home(rows):
 def by(*keys):return [r for r in rows if r["category"] in keys]
 candidates=by("news-tech","news-gaming")
 marked=[p for p in candidates if p.get("featured")]
 features=(marked+[p for p in candidates if p["slug"] not in {f["slug"] for f in marked} and bool(safe_image(p.get("image","")))])[:5]
 raw=json.loads((P/"data/web.json").read_text(encoding="utf-8"))["items"]
 web=[w for w in raw if isinstance(w,dict) and isinstance(w.get("url"),str) and w["url"].startswith("https://") and isinstance(w.get("title"),str)]
 links='<ul>'+''.join('<li><a rel="noopener noreferrer" href="'+esc(w["url"],quote=True)+'">'+esc(w["title"])+'</a></li>' for w in web[:8])+'</ul>' if web else blank()
 top=section("In evidenza",featured_showcase(features))
 sections=[
  ("News Tech",cards(by("news-tech")[:6])),
  ("News Gaming",cards(by("news-gaming")[:6])),
  ("Ultime Recensioni",cards([r for r in by("recensioni-tech","recensioni-gaming") if r.get("source")=="youtube-community"][:6])),
  ("Guide e Extra",feature_pair(by("guide"),by("speciali","extra"))),
  ("Ultimi Video",playlist_cards()),
  ("Notizie Web",links)
 ]
 return shell("Home",'<div class="featured-wide">'+top+'</div><div class="home-layout"><div class="home-column">'+''.join(section(name,content) for name,content in sections)+'</div>'+sidebar(rows,True)+'</div>')
def web_archive(rows):
 items=json.loads((P/"data/web.json").read_text(encoding="utf-8")).get("items",[])
 links=['<li><a href="'+esc(item["url"],quote=True)+'" target="_blank" rel="noopener noreferrer">'+esc(item["title"])+'</a></li>' for item in items if isinstance(item,dict) and isinstance(item.get("title"),str) and isinstance(item.get("url"),str) and item["url"].startswith("https://")]
 content='<h1>Notizie Web</h1>'+('<ul class="web-links">'+''.join(links)+'</ul>' if links else blank())
 return inside("Notizie Web",content,rows)
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
