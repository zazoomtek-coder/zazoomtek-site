#!/usr/bin/env python3
"""ZazoomTek SpotNews: generatore statico con menu/layout universali."""
from pathlib import Path
from html import escape as esc
import json,os,re,shutil,sys,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parent))
import urllib.request,xml.etree.ElementTree as ET
from html import unescape as unesc
from datetime import datetime,timezone,timedelta
from urllib.parse import urlparse
P=Path(__file__).resolve().parents[1]; O=P/"dist"
JS_ASSET_VERSION=hashlib.sha256((P/"assets/js/site.js").read_bytes()).hexdigest()[:12]
NAV=[("HOME","/"),("NEWS","/news"),("RECENSIONI","/recensioni"),("GUIDE","/guide"),("SPECIALI","/speciali"),("EXTRA","/extra"),("VIDEO","https://www.youtube.com/@ZazoomTek")]
TYPES={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra","video":"Video"}
GROUPS={"news":["news-tech","news-gaming"],"recensioni":["recensioni-tech","recensioni-gaming"],"guide":["guide"],"speciali":["speciali"],"extra":["extra"],"video":["video"],**{k:[k] for k in TYPES}}
PREVIEW=os.getenv("CF_PAGES_BRANCH","feature/spotnews-clean-rebuild")!="main"
TICKER_ROWS=[]  # Populated before all page shells are generated.
_WEB_NEWS_CACHE=None  # Cached external tech feeds; initialize before the Home calls web_news().
def original_routes():
 data=json.loads((P/"data/editorial_classification.json").read_text(encoding="utf-8"))
 if len(data.get("items",[]))!=14:raise ValueError("Editorial classification manifest incomplete")
 return data["items"]
def classification_for_post(item):
 pid=str(item.get("id") or "").casefold()
 slug=str(item.get("slug") or item.get("original_slug") or "").casefold()
 title=str(item.get("title") or "")
 for row in original_routes():
  if pid and str(row.get("post_id") or "").casefold()==pid:return row["category"]
  if slug and slug in (str(row["path"]).casefold(),str(row.get("canonical_slug") or "").casefold()):return row["category"]
  if title and normalized_title(title)==normalized_title(row["title"]):return row["category"]
 return None
def category_for_post(item):
 locked=classification_for_post(item)
 if locked:return locked
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
def chronological_key(row):
 """Absolute instant, not lexicographical ordering of mixed ISO offsets."""
 value=str(row.get("published_at") or row.get("date") or "")
 try:
  result=datetime.fromisoformat(value.replace("Z","+00:00"))
  if result.tzinfo is None:result=result.replace(tzinfo=timezone.utc)
  return result.timestamp()
 except (ValueError,TypeError,OverflowError):return float("-inf")
def load_remote_community():
 """Extract canonical FULL Community posts at each build, without YouTube Data API."""
 try:
  from community_youtube import discover
  live=discover(limit=160,max_pages=12)
  print("Community YouTube: full posts verified:",len(live),flush=True)
  return live
 except Exception as exc:
  print("Community YouTube temporarily unavailable:",type(exc).__name__,str(exc)[:300],flush=True)
  return []
def community_posts():
 """Merge verified full-text public posts with the existing archived extracts.
    Older short excerpts are labeled as such, never presented as complete.
 """
 path=P/"data/community.json"
 raw=json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"posts":[]}
 if not isinstance(raw,dict) or not isinstance(raw.get("posts"),list):
  raise ValueError("Invalid stored Community data")
 historical=raw["posts"]
 alias_entries=json.loads((P/"data/community_aliases.json").read_text(encoding="utf-8")).get("entries",[])
 if len(alias_entries)!=30:raise ValueError("30 Community short-to-full aliases expected")
 abbreviated={entry["old_id"] for entry in alias_entries}
 canonical_category={entry["new_id"]:entry["category"] for entry in alias_entries}
 archive_path=P/"data/community_full.json"
 archived=json.loads(archive_path.read_text(encoding="utf-8")).get("posts",[]) if archive_path.exists() else []
 # New YouTube imports are promoted from the editorial queue at 12:30 or 19:30.
 # Never fetch the live Community in the static production build.
 imported_path=P/"data/community_imported.json"
 imported=json.loads(imported_path.read_text(encoding="utf-8")).get("posts",[]) if imported_path.exists() else []
 result=[]
 for item in list(imported)+list(archived)+list(historical):
  if not isinstance(item,dict):continue
  if str(item.get("id") or "") in abbreviated:
   continue  # The full archive version supersedes this historical short excerpt.
  text=item.get("text")
  if not isinstance(text,str) or not text.strip():continue
  cat=category_for_post(item)
  post_id=str(item.get("id","")).strip()
  cat=canonical_category.get(post_id,cat)
  if not cat:continue
  if not post_id:continue
  youtube_full=bool(item.get("text_complete")) and bool(re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}",post_id))
  archive_full=bool(item.get("archived_full")) and len(text)>=500
  is_full=youtube_full or archive_full
  slug="community-"+re.sub(r"[^a-z0-9]+","-",post_id.lower()).strip("-")
  if len(slug)>150 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug):continue
  date=parse_day(item.get("date"))
  if not date and cat.startswith("news-"):continue
  if date and date>datetime.now(timezone.utc).date():continue
  title=item.get("title")
  if not isinstance(title,str) or not title.strip():continue
  image=safe_image(item.get("image",""))
  original_url=str(item.get("url") or item.get("source_url") or "")
  if is_full and not re.fullmatch(r"https://www\.youtube\.com/post/Ug[A-Za-z0-9_-]{12,}",original_url):
   original_url="https://www.youtube.com/post/"+post_id
  if not is_full:original_url=""
  result.append({
   "slug":slug,"category":cat,"title":title.strip(),
   "body":[part.strip() for part in re.split(r"\n\s*\n",text) if part.strip()],
   "date":date.isoformat() if date else "",
   "published_at":str(item.get("published_at") or item.get("date") or ""),
   "source":"youtube-community" if youtube_full else ("community-archive-full" if archive_full else "archived-community-excerpt"),
   "is_excerpt":not is_full,"source_url":original_url,"image":image,
   "headings":item.get("headings",[]) if isinstance(item.get("headings"),list) else [],
   "featured":bool(item.get("featured",False)),
   "editorial_pick":bool(item.get("editorial_pick",False))
  })
 return result
def clean_title(text):
 """Avoid category labels, image numbering and arbitrary editorial prefixes in titles/H1/cards."""
 title=str(text or "").strip()
 title=re.sub(r"^\s*#*\s*(?:(?:News|Review|Recensione)(?:\s+(?:Tech|Gaming|Extra))?|Articolo)\s*[:\u2013\u2014-]\s*","",title,flags=re.I)
 title=re.sub(r"^\s*(?:Foto|Immagine|Picture|Photo)\s*\d+\s*[:\u2013\u2014-]\s*","",title,flags=re.I)
 title=re.sub(r"\s*[\u2013\u2014|:-]\s*(?:Foto|Immagine|Picture|Photo)\s*(?:n[.°]\s*)?\d+\s*$","",title,flags=re.I)
 return title.strip()
def normalized_title(text):
 text=re.sub(r"(?i)^\s*#*\s*(news\s*(?:tech|gaming)?|review\s*(?:tech|gaming)?|recensione|guida|guide|speciale|extra)\s*:\s*","",str(text)).strip()
 return re.sub(r"[^a-z0-9]+","",unesc(text.casefold()))
def posts():
 obj=json.loads((P/"data/posts.json").read_text(encoding="utf-8"))
 if not isinstance(obj.get("posts"),list):raise ValueError("posts must be a list")
 studio_data=json.loads((P/"data/studio_posts.json").read_text(encoding="utf-8"))
 all_rows=obj["posts"]+community_posts()+studio_data.get("posts",[])
 unique={};seen_slugs=set()
 for r in all_rows:
  slug=r.get("slug","")
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or slug in GROUPS:continue
  if r.get("category") not in TYPES or not isinstance(r.get("title"),str):continue
  r["category"]=classification_for_post(r) or r["category"]
  key=(r["category"],normalized_title(r["title"]))
  if not key[1]:continue
  current=unique.get(key)
  # A full verified post always supersedes an excerpt with the same title.
  if current is None or (current.get("is_excerpt",False) and not r.get("is_excerpt",False)):
   unique[key]=r
 rows=list(unique.values())
 deduplicated=[]
 for r in rows:
  # Same canonical YouTube post may have a different display title in the old site archive.
  if r["slug"] in seen_slugs:continue
  seen_slugs.add(r["slug"])
  deduplicated.append(r)
 # Studio edits win over YouTube imports without modifying the original post.
 overrides=json.loads((P/"data/studio_overrides.json").read_text(encoding="utf-8")).get("overrides",{})
 for row in deduplicated:
  changed=overrides.get(row.get("slug"))
  if isinstance(changed,dict):
   for key,value in changed.items():
    if key not in ("slug","date","published_at","id","source_url","is_excerpt"):
     row[key]=value
   row["studio_blocks"]=True
   row["source"]="studio-editor"
 rows=sorted(deduplicated,key=chronological_key,reverse=True)
 from review_image_archive import populate_review_covers
 populate_review_covers(rows,P,safe_image)
 review_data=json.loads((P/"data/review_editorial.json").read_text(encoding="utf-8")).get("editorial_data",{})
 for r in rows:
  # Normalize *display* title only after category and canonical-slug resolution.
  if r["category"].startswith("recensioni-"):
   post_id=str(r.get("slug","")).removeprefix("community-")
   extra=next((v for k,v in review_data.items() if
               (k.lower().replace("_","-")==post_id) or k==r["slug"]),None)
   if extra:
    for field in ("score","pros","cons","conclusion"):
     if field in extra and not r.get(field):r[field]=extra[field]
  r["title"]=clean_title(r["title"])
 print("Articles:",len(rows),"verified Community:",sum(x.get("source")=="youtube-community" for x in rows),
       "archived excerpts:",sum(x.get("is_excerpt",False) for x in rows),flush=True)
 return rows
def videos():
 obj=json.loads((P/"data/videos.json").read_text(encoding="utf-8"))
 allowed={"review","test","unboxing"}
 seen=set();result=[]
 for v in obj.get("videos",[]):
  vid=v.get("id","")
  if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or vid in seen:continue
  if v.get("kind") not in allowed or v.get("topic") not in ("tech","gaming") or not isinstance(v.get("title"),str):continue
  seen.add(vid);result.append(v)
 return sorted(result,key=chronological_key,reverse=True)
def playlist_latest():
 """Use ONLY uploads already approved in an editorial publication slot."""
 playlists=json.loads((P/"data/playlists.json").read_text(encoding="utf-8")).get("playlists",[])
 return [{"playlist_id":pl.get("id",""),"playlist":pl.get("title","Playlist"),
  "video":None,"thumbnail":pl.get("thumbnail","")} for pl in playlists]
def playlist_cards():
 """Always render the latest verified channel uploads, including gameplay and Shorts.

 Video cards are sourced from the same approved data/videos.json snapshot
 that the editor publishes to Cloudflare. Only fall back to curated playlists
 when the imported upload collection is actually empty.
 """
 raw=json.loads((P/"data/videos.json").read_text(encoding="utf-8")).get("videos",[])
 recent=[]
 seen=set()
 for v in sorted(raw,key=chronological_key,reverse=True):
  vid=str(v.get("id") or "")
  title=str(v.get("title") or "").strip()
  if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or not title or vid in seen:continue
  seen.add(vid);recent.append(v)
  if len(recent)==4:break
 result=[]
 for v in recent:
  vid=v["id"];title=v["title"]
  url="https://www.youtube.com/watch?v="+vid
  pic="https://i.ytimg.com/vi/"+vid+"/hqdefault.jpg"
  kind={"review":"Recensione","unboxing":"Unboxing","test":"Test","gameplay":"Gameplay","short":"Short","trailer":"Trailer"}.get(str(v.get("kind") or "").lower(),"Video")
  sub=kind+" · "+str(v.get("date") or "")[:10]
  img='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">'
  result.append('<article class="card video-card"><a class="thumb play-thumb" href="'+esc(url,quote=True)+'" rel="noopener" aria-label="Apri su YouTube: '+esc(title,quote=True)+'">'+img+'</a><small>'+esc(sub)+'</small><h3><a href="'+esc(url,quote=True)+'" rel="noopener">'+esc(title)+'</a></h3></article>')
 if result:
  return '<div class="video-magazine"><div class="video-feature">'+result[0]+'</div><div class="video-secondary">'+''.join(result[1:])+'</div></div>'
 rows=playlist_latest()
 for p in rows:
  pid=p["playlist_id"]
  url="https://www.youtube.com/playlist?list="+pid
  pic=p.get("thumbnail","")
  title=p["playlist"]
  img='<img loading="lazy" src="'+esc(pic,quote=True)+'" alt="">' if pic.startswith("https://i.ytimg.com/vi/") else '<span class="video-thumb-fallback">Playlist</span>'
  result.append('<article class="card video-card"><a class="thumb play-thumb" href="'+esc(url,quote=True)+'" rel="noopener" aria-label="Apri su YouTube: '+esc(title,quote=True)+'">'+img+'</a><small>Playlist</small><h3><a href="'+esc(url,quote=True)+'" rel="noopener">'+esc(title)+'</a></h3></article>')
 return '<div class="video-magazine"><div class="video-feature">'+result[0]+'</div><div class="video-secondary">'+''.join(result[1:])+'</div></div>' if result else ""
def video_cards(rows):
 if not rows:return blank()
 return '<div class="cards">'+''.join('<article class="card video-card"><a class="thumb play-thumb" href="https://www.youtube.com/watch?v='+v["id"]+'" rel="noopener"><img src="https://i.ytimg.com/vi/'+v["id"]+'/hqdefault.jpg" loading="lazy" alt=""></a><small>'+esc(v["kind"].title())+' · '+esc(v["topic"].title())+'</small><h3><a href="https://www.youtube.com/watch?v='+v["id"]+'" rel="noopener">'+esc(v["title"])+'</a></h3></article>' for v in rows)+'</div>'
LEGAL_LINKS=[("Privacy Policy","/privacy-policy"),("Cookie Policy","/cookie-policy"),
             ("Disclaimer","/disclaimer"),("Note legali","/note-legali")]
FOOTER_SOCIAL_LINKS=[
 ("▶","YouTube","https://www.youtube.com/@ZazoomTek"),
 ("♥","Patreon","https://www.patreon.com/cw/ZazoomTek"),
 ("♫","TikTok","https://www.tiktok.com/@zazoomtek"),
 ("◉","WhatsApp","https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S"),
 ("◔","RSS","/feed.xml"),
 ("✉","Contatti","/contatti")
]
def ticker_items(rows):
 """Ten most recent genuine Tech/Gaming headlines, one displayed at a time."""
 news=sort_by_date_desc([r for r in rows if r.get("category") in ("news-tech","news-gaming")])
 result=[];seen=set()
 for r in news:
  key=normalized_title(r.get("title",""))
  if not key or key in seen:continue
  seen.add(key)
  result.append({"title":clean_title(r["title"]),"url":"/"+r["slug"],
                 "date":str(r.get("date") or r.get("published_at") or "")[:10],
                 "category":TYPES.get(r["category"],"News")})
  if len(result)==10:break
 if len(result)<10:raise ValueError("Breaking ticker requires at least 10 authentic news articles")
 return result

def breaking_ticker_markup():
 """Server-rendered accessible ticker. JS duplicates the group for seamless movement."""
 if not TICKER_ROWS:return ""
 links="".join('<a href="'+esc(x["url"],quote=True)+'" class="ticker-link">'
               ''
               +esc(x["title"])+'</a>' for x in TICKER_ROWS)
 return ('<section class="breaking-ticker" aria-label="Notizie in primo piano">'
         '<div class="wrap breaking-ticker-inner">'
         '<span class="breaking-label">PRIMO PIANO</span>'
         '<div class="ticker-viewport" id="ticker-viewport" tabindex="0" aria-label="Scorri le ultime notizie">'
         '<div class="ticker-track" id="ticker-track"><div class="ticker-group" aria-live="off">'+links+'</div></div></div>'
         '</div></section>')

def build_live_discovery(rows):
 """Write two small, same-origin datasets at every site build, including YouTube import cycles."""
 from datetime import datetime,timezone
 items=[]
 for r in rows:
  slug=r.get("slug") or ""
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug):continue
  body=r.get("body") or []
  if isinstance(body,str):body=[body]
  text=" ".join(block.strip() for block in body if isinstance(block,str))
  text=re.sub(r"\s+"," ",re.sub(r"(?m)^\s*#{1,3}\s+","",text)).strip()
  items.append({
   "title":clean_title(r.get("title","")),
   "category":TYPES.get(r.get("category"),"Articolo"),
   "date":str(r.get("date") or r.get("published_at") or "")[:10],
   "url":"/"+slug,
   "excerpt":text[:245],
   "text":text[:36000]
  })
 if not items:raise ValueError("Cannot publish an empty internal search index")
 (O/"search-index.json").write_text(json.dumps({
  "version":1,"updated_utc":datetime.now(timezone.utc).isoformat(),
  "count":len(items),"articles":items
 },ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 ticker=ticker_items(rows)
 (O/"news-ticker.json").write_text(json.dumps({"version":1,"items":ticker},
  ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 print("Discovery:",len(items),"searchable articles,",len(ticker),"ticker headlines",flush=True)
 return ticker

def shell(title,inner,seo_row=None,seo_path="/",seo_summary=None):
 nav="".join('<a href="'+u+'">'+n+'</a>' for n,u in NAV)
 search_control=('<button id="site-search-open" class="site-search-open" type="button"'
                 ' aria-label="Cerca nel sito" aria-controls="site-search-panel" aria-expanded="false"'
                 ' title="Cerca nel sito">'
                 '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="23" height="23"'
                 ' fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"'
                 ' stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle>'
                 '<path d="m20 20-4-4"></path></svg></button>')
 search_panel=('<section id="site-search-panel" class="site-search-panel" hidden'
               ' role="search" aria-label="Ricerca interna ZazoomTek">'
               '<div class="wrap site-search-inner">'
               '<form id="site-search-form" role="search" autocomplete="off">'
               '<label for="site-search-input">Cerca fra news, recensioni, guide e articoli</label>'
               '<div class="site-search-form-row"><input id="site-search-input" type="search"'
               ' placeholder="Cerca un argomento, prodotto o videogame..."'
               ' aria-describedby="site-search-status" maxlength="120">'
               '<button class="site-search-submit" type="submit">Cerca</button>'
               '<button id="site-search-close" class="site-search-close" type="button"'
               ' aria-label="Chiudi la ricerca">×</button></div></form>'
               '<p id="site-search-status" class="site-search-status" aria-live="polite"></p>'
               '<div id="site-search-results" class="site-search-results"></div>'
               '<button id="site-search-more" type="button" class="site-search-more" hidden>'
               'Mostra altri risultati</button></div></section>')
 footer_menu="".join('<a href="'+esc(url,quote=True)+'">'+esc(label.title())+'</a>' for label,url in NAV)
 footer_links="".join('<a href="'+url+'">'+esc(label)+'</a>' for label,url in LEGAL_LINKS)
 social_links="".join('<a href="'+esc(url,quote=True)+'"'+
                      (' target="_blank" rel="noopener noreferrer"' if url.startswith("https://") else '')+
                      '><span aria-hidden="true" class="footer-social-symbol">'+esc(symbol)+'</span> '+esc(name)+'</a>'
                      for symbol,name,url in FOOTER_SOCIAL_LINKS)
 footer=('<footer class="footer"><div class="wrap">'
         '<nav class="footer-main-links" aria-label="Navigazione nel footer">'+footer_menu+'</nav>'
         '<nav class="footer-social-links" aria-label="Canali ZazoomTek e contatti">'+social_links+'</nav>'
         '<nav class="footer-legal" aria-label="Informative e note legali">'+footer_links+'</nav>'
         '<div class="footer-brand">© 2026 ZazoomTek · Tecnologia e Gaming.</div>'
         '</div></footer>')
 cookie=('<button id="cookie-preferences" class="cookie-shortcut" type="button" aria-controls="cookie-panel" aria-expanded="false">Cookie</button>'
         '<section id="cookie-panel" class="cookie-panel" role="dialog" aria-modal="false" aria-label="Preferenze cookie" hidden>'
         '<h2>Preferenze cookie</h2><p>Google Analytics 4 è facoltativo e si attiva soltanto con il tuo consenso.</p>'
         '<div class="cookie-actions"><button id="cookie-reject" type="button">Rifiuta</button>'
         '<button id="cookie-accept" type="button">Accetta Analytics</button></div>'
         '<a href="/cookie-policy">Leggi la Cookie Policy</a></section>')
 scroll_top=('<button type="button" class="back-to-top" id="back-to-top"'
             ' aria-label="Torna all’inizio della pagina" title="Torna su" hidden>'
             '<span aria-hidden="true">↑</span></button>')
 from seo import metadata
 tags=metadata(title,seo_path,seo_row,PREVIEW,seo_summary)
 return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+tags+
         '<link rel="alternate" type="application/rss+xml" title="ZazoomTek - Feed RSS" href="/feed.xml">'
         '<link rel="stylesheet" href="/assets/css/spotnews.css?v=20261028-spotnews-production-1"></head><body>'
         '<header class="header"><div class="wrap"><a class="logo" href="/">Zazoom<span>Tek</span></a>'
         '<button id="mobile-menu" aria-controls="nav" aria-expanded="false">Menu</button>'
         '<nav id="nav" aria-label="Navigazione universale">'+nav+'</nav>'+search_control+'</div></header>'
         +search_panel+breaking_ticker_markup()
         +'<main class="wrap">'+inner+'</main>'+footer+cookie+scroll_top+
         '<script defer src="/assets/js/site.js?v='+JS_ASSET_VERSION+'"></script></body></html>')

def legal_pages(rows):
 data=json.loads((P/"data/legal.json").read_text(encoding="utf-8"))
 allowed={"privacy-policy","cookie-policy","disclaimer","note-legali"}
 if len(data["pages"])!=4 or set(p["slug"] for p in data["pages"])!=allowed:raise ValueError("Missing required legal pages")
 for page in data["pages"]:
  body='<article class="legal-article"><h1>'+esc(page["title"])+'</h1><p class="legal-updated">'+esc(page["updated"])+'</p>'
  for block in page["blocks"]:
   if block["type"]=="heading":body+='<h2>'+esc(block["text"])+'</h2>'
   elif block["type"]=="paragraph":body+='<p>'+esc(block["text"])+'</p>'
   else:raise ValueError("Invalid legal content block")
  body+='</article>'
  (O/(page["slug"]+".html")).write_text(inside(page["title"],body,rows,show_related=False,seo_path="/"+page["slug"],seo_summary="Informazioni ufficiali ZazoomTek: "+page["title"]+"."),encoding="utf-8")

def safe_image(value):
 if not isinstance(value,str):return ""
 if value.startswith("/") and not value.startswith("//") and ".." not in value and not any(c in value for c in '<>"\\'):
  return value if (P/value.lstrip("/")).is_file() else ""
 from urllib.parse import urlparse
 u=urlparse(value)
 if u.scheme=="https" and u.hostname in ("yt3.ggpht.com","i.ytimg.com","mcusercontent.com","images.volleyballworld.com") and not u.username and not u.password:return value
 # Studio supports editor-supplied HTTPS covers; no data:, javascript: or
 # SVG-based active content is permitted as an uploaded image.
 if u.scheme=="https" and u.hostname and not u.username and not u.password and len(value)<1800 and not u.path.lower().endswith(".svg"):
  return value
 # Verified public-domain Sony PS2 product photograph by Evan-Amos on Wikimedia Commons.
 if (u.scheme=="https" and u.hostname=="upload.wikimedia.org" and
     u.path=="/wikipedia/commons/c/c3/Sony-PlayStation-2-30001-wController-L.jpg" and
     not u.username and not u.password):return value
 return ""
def blank():return '<div class="blank">Nessun contenuto pubblicato</div>'
def cover_focus_attributes(row):
 """Per-cover focus percentages; Studio/import data may supply focus_x/focus_y.
 The Trust Black Friday artwork explicitly protects the LEFT-side lettering.
 """
 x=row.get("cover_focus_x",row.get("focus_x"))
 y=row.get("cover_focus_y",row.get("focus_y"))
 mode=str(row.get("cover_fit") or "").lower()
 name=clean_title(row.get("title","")).casefold()
 if x is None and "trust" in name and "black friday" in name:
  x=0
  mode="cover"
 attrs=[]
 css=[]
 for axis,value in (("x",x),("y",y)):
  try:
   if value is not None:
    number=float(str(value).strip().rstrip("%"))
    if 0<=number<=100:
     value_str=str(round(number,2))
     attrs.append(' data-cover-focus-'+axis+'="'+value_str+'"')
     css.append('--cover-'+axis+':'+value_str+'%;')
  except (ValueError,TypeError):pass
 for field,cssname,bounds,unit in (("cover_zoom","--cover-zoom",(100,250),""),("cover_rotation","--cover-rotation",(-180,180),"deg")):
  try:
   v=float(row.get(field,100 if field=="cover_zoom" else 0))
   if bounds[0]<=v<=bounds[1]:
    css.append(cssname+":"+str(round(v/100 if field=="cover_zoom" else v,3))+unit+";")
  except (TypeError,ValueError):pass
 if mode in ("cover","contain"):attrs.append(' data-cover-fit="'+mode+'"')
 if css:attrs.append(' style="'+''.join(css)+'"')
 return "".join(attrs)

def editorial_cover(row):
 """Every cover is a complete original photo within a 16:9 frame; the same photo fills the background."""
 url=safe_image(row.get("image",""))
 title=esc(clean_title(row.get("title","ZazoomTek")))
 section=esc(TYPES.get(row.get("category"),"ZazoomTek"))
 if url:
  src=esc(url,quote=True)
  return ('<span class="editorial-media-frame"'+cover_focus_attributes(row)+'>'
          '<img class="editorial-media-fg" loading="lazy" src="'+src+'" alt="'+title+'">'
          '<span class="editorial-media-fallback" aria-hidden="true"><small>'+section+'</small><strong>'+title+'</strong></span>'
          '</span>')
 return '<span class="editorial-media-frame is-fallback"><span class="editorial-media-fallback"><small>'+section+'</small><strong>'+title+'</strong></span></span>'
def cards(rows):
 if not rows:return ""
 entries=[]
 for r in rows:
  url="/"+r["slug"]
  visual=editorial_cover(r)
  entries.append('<article class="card"><a class="thumb" href="'+url+'">'+visual+'</a>'
                 '<small>'+esc(TYPES[r["category"]])+'</small><h3><a href="'+url+'">'+esc(clean_title(r["title"]))+'</a></h3></article>')
 return '<div class="cards">'+''.join(entries)+'</div>'
def gaming_article_preview(row,limit=225):
 """Preserve useful news prose, remove only duplicate category/title from the original excerpt."""
 body=row.get("body") or []
 if isinstance(body,str):body=[body]
 headline=clean_title(row.get("title","")).strip()
 for part in body:
  if not isinstance(part,str):continue
  candidate=part.strip()
  if not candidate or candidate.startswith(("## ","# ","**")):continue
  candidate=re.sub(r"\*\*(.*?)\*\*",r"\1",candidate)
  candidate=re.sub(r"\s+"," ",candidate).strip()
  candidate=re.sub(r"^(?:News\s+Gaming|Gaming\s+News)\s*[:\u2013\u2014-]\s*","",candidate,flags=re.I)
  # Imported Community text sometimes repeats the full article headline as its first line.
  if headline and candidate.casefold().startswith(headline.casefold()):
   candidate=candidate[len(headline):].lstrip(" :.-–—")
  if len(candidate)<18:continue
  if len(candidate)>limit:
   short=candidate[:limit].rsplit(" ",1)[0].rstrip(".,;:") or candidate[:limit]
   return short+"…"
  return candidate
 return ""

def news_tech_magazine(rows):
 """Homepage-only, image-first News Tech: 2 large stories + 6 smaller (3x2).
 All records come from the same dated, deduplicated first-party YouTube feed.
 No external example articles, fake image cards or alterations to other modules.
 """
 if not rows:return ""
 def item(row,large=False):
  href="/"+row["slug"]
  title=esc(clean_title(row["title"]))
  stamp=date_label(row)
  raw_date=str(row.get("date") or row.get("published_at") or "")[:10]
  date_html=('<time datetime="'+esc(raw_date,quote=True)+'">'+esc(stamp)+'</time>' if stamp else "")
  return ('<article class="news-tech-card '+("news-tech-card-large" if large else "news-tech-card-small")+'">'
          '<a class="news-tech-cover" href="'+href+'" aria-label="Leggi News Tech: '+esc(clean_title(row["title"]),quote=True)+'">'
          +editorial_cover(row)+'</a>'
          '<span class="news-tech-category">News Tech</span>'
          '<h3><a href="'+href+'">'+title+'</a></h3>'
          +date_html+'</article>')
 big="".join(item(row,True) for row in rows[:2])
 small="".join(item(row) for row in rows[2:8])
 return ('<div class="news-tech-showcase" aria-label="Ultime otto News Tech">'
         '<div class="news-tech-lead-grid">'+big+'</div>'
         +('<div class="news-tech-small-grid">'+small+'</div>' if small else '')+
         '</div>')

def gaming_magazine(rows):
 """SpotNews editorial layout: one large story left, up to four compact vertical items right."""
 if not rows:return ""
 lead=rows[0]
 url="/"+lead["slug"]
 title=esc(clean_title(lead["title"]))
 author=esc(str(lead.get("author") or "Redazione ZazoomTek"))
 date=date_label(lead)
 excerpt=gaming_article_preview(lead)
 feature=('<article class="gaming-magazine-lead">'
          '<a class="gaming-magazine-lead-image" href="'+url+'">'+editorial_cover(lead)+'</a>'
          '<span class="gaming-magazine-badge">News Gaming</span>'
          '<h3><a href="'+url+'">'+title+'</a></h3>'
          '<p class="gaming-magazine-byline">di <strong>'+author+'</strong>'+
          (' · <time>'+esc(date)+'</time>' if date else "")+'</p>'
          +(('<p class="gaming-magazine-excerpt">'+esc(excerpt)+'</p>') if excerpt else '')+
          '</article>')
 compact=[]
 for row in rows[1:5]:
  href="/"+row["slug"]
  date=date_label(row)
  compact.append('<article class="gaming-magazine-item">'
                 '<a class="gaming-magazine-thumb" href="'+href+'">'+editorial_cover(row)+'</a>'
                 '<div class="gaming-magazine-item-copy">'
                 '<h3><a href="'+href+'">'+esc(clean_title(row["title"]))+'</a></h3>'
                 +('<time>'+esc(date)+'</time>' if date else '')+
                 '</div></article>')
 return ('<div class="gaming-magazine">'
         +feature+'<div class="gaming-magazine-list">'+''.join(compact)+'</div></div>')

def reviews_three_column(rows):
 """Native Notizie Web gallery styling, with exactly three latest unique written reviews."""
 if not rows:return ""
 out=[]
 for item in rows[:3]:
  href="/"+item["slug"]
  title=esc(clean_title(item["title"]))
  category=esc(TYPES.get(item["category"],"Recensione"))
  date=date_label(item)
  date_html='<time datetime="'+esc(str(item.get("date",""))[:10],quote=True)+'">'+esc(date)+'</time>' if date else ""
  out.append('<article class="web-news-card home-review-web-card">'
             '<a class="web-news-thumb" href="'+href+'" aria-label="Apri recensione: '+title+'">'
             +editorial_cover(item)+'</a>'
             '<span class="web-source">'+category+'</span>'
             '<h3><a href="'+href+'">'+title+'</a></h3>'
             +date_html+'</article>')
 return '<div class="web-news-grid home-review-web-grid">'+''.join(out)+'</div>'

SECTION_URLS={"In evidenza":"/news","News Tech":"/news-tech","News Gaming":"/news-gaming","Ultime Recensioni":"/recensioni","Guide e Extra":"/guide","Speciali":"/speciali","Ultimi Video":"https://www.youtube.com/@ZazoomTek","Notizie Web":"/notizie-web"}
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
 link="/"+r["slug"]
 pic=safe_image(r.get("image",""))
 image=('<img class="spotlight-cover-foreground" loading="lazy" src="'+esc(pic,quote=True)+'" alt="'+esc(clean_title(r["title"]),quote=True)+'">'
        if pic else '<span class="tile-no-image"><strong>'+esc(r["title"])+'</strong></span>')
 label=esc(TYPES.get(r["category"],"ZazoomTek"))
 date=date_label(r)
 stamp='<span class="tile-date">'+esc(date)+'</span>' if date else ""
 return '<article class="'+kind+'"'+cover_focus_attributes(r)+'><a class="tile-link" href="'+esc(link,quote=True)+'">'+image+'<span class="tile-gradient"></span><span class="tile-copy"><span class="tile-category">'+label+'</span><strong class="tile-title">'+esc(r["title"])+'</strong>'+stamp+'</span></a></article>'
def featured_showcase(rows):
 """Five latest first-party news: Tech hero + three Tech, Gaming bottom right."""
 if not rows:return blank()
 lead=rows[0]  # Most recently published News Tech, selected first.
 rest=[p for p in rows if p["slug"]!=lead["slug"]][:4]
 markup=overlay_card(lead,"spotlight-hero")+''.join(
  overlay_card(r,"spotlight-tile"+(" spotlight-gaming" if r["category"]=="news-gaming" else ""))
  for r in rest)
 return '<div class="spotlight-grid">'+markup+'</div>'
def box(name,rows,notice=""):
 archives={"I più letti":"/news-tech","Amazon":"",
           "Da non perdere":"/news","Dalla redazione":"/news","Altre news":"/news",
           "Ultime news":"/news","Ultime notizie":"/news","Ultime recensioni":"/recensioni",
           "Archivio Tech":"/news-tech","Archivio Gaming":"/news-gaming","Dagli archivi":"/news"}
 if not rows:return ""
 cards=[]
 for r in rows:
  href="/"+r["slug"]
  image=safe_image(r.get("image",""))
  thumb='<img loading="lazy" src="'+esc(image,quote=True)+'" alt="">' if image else '<span class="editorial-cover editorial-cover-mini"><strong>'+esc(TYPES.get(r["category"],"ZazoomTek"))+'</strong></span>'
  date=date_label(r)
  cards.append('<article class="editorial-row"><a class="editorial-thumb" href="'+href+'"'+cover_focus_attributes(r)+'>'+thumb+'</a><div class="editorial-row-copy"><a href="'+href+'"><strong>'+esc(r["title"])+'</strong></a>'+('<time>'+esc(date)+'</time>' if date else '')+'</div></article>')
 return '<section class="box editorial-box compact-editorial-box">'+bar(name,archives.get(name,""),"sidebar")+'<div class="editorial-links">'+''.join(cards)+'</div></section>'
def sidebar_select(items,count,used):
 """Preserve editorial order; one card per story across Home and sidebars."""
 chosen=[]
 for row in items:
  keys=home_keys(row)
  if used.intersection(keys):continue
  used.update(keys)
  chosen.append(row)
  if len(chosen)>=count:break
 return chosen

def daily_shuffle(items,salt="home"):
 """Daily stable random selection without changing article publication order in archives."""
 import hashlib,random
 today=datetime.now(timezone.utc).date().isoformat()
 digest=hashlib.sha256((today+"|"+salt).encode("utf-8")).hexdigest()
 result=list(items)
 random.Random(int(digest[:16],16)).shuffle(result)
 return result

def amazon_provisional_box():
 """ZazoomTek Amazon Associates showcase — second Home sidebar element only."""
 url="https://link.amazon/A0dJXv9PO"
 products=(
  ("Laptop","/assets/images/amazon-laptop.svg"),
  ("Smartphone","/assets/images/amazon-smartphone.svg"),
  ("Accessori","/assets/images/amazon-headphones.svg"),
 )
 thumbs="".join('<span class="amazon-feature-product">'
                '<img loading="lazy" decoding="async" width="240" height="180"'
                ' src="'+esc(img,quote=True)+'" alt="'+esc(label,quote=True)+'">'
                '<small>'+esc(label)+'</small></span>'
                for label,img in products)
 return ('<section class="box editorial-box amazon-feature-box" aria-labelledby="amazon-feature-title">'
         '<div class="amazon-feature-labels"><span class="amazon-feature-badge">VETRINA TECH</span>'
         '<span class="amazon-feature-partner">Amazon Partners</span></div>'
         '<h2 class="amazon-feature-title" id="amazon-feature-title">Prodotti recensiti da ZazoomTek</h2>'
         '<p class="amazon-feature-intro">Scopri su Amazon i prodotti tech, accessori e gadget recensiti e consigliati da ZazoomTek.</p>'
         '<div class="amazon-feature-products" aria-label="Categorie di prodotti tech">'+thumbs+'</div>'
         '<p class="amazon-feature-disclosure">Link affiliato Amazon. In qualità di Affiliato Amazon '
         'ricevo un guadagno dagli acquisti idonei senza alcun costo per l’utente.</p>'
         '<a class="amazon-feature-cta" href="'+esc(url,quote=True)+'" target="_blank"'
         ' rel="sponsored noopener noreferrer"'
         ' aria-label="Vedi i prodotti recensiti su Amazon, link affiliato">'
         'VEDI I PRODOTTI SU AMAZON <span aria-hidden="true">↗</span></a></section>')

def sidebar(rows,home=False,used=None):
 used=set(used or ())
 news=sort_by_date_desc([r for r in rows if r.get("category") in ("news-tech","news-gaming")])
 reviews=sort_by_date_desc([r for r in rows if str(r.get("category") or "").startswith("recensioni-")])
 selected=[]
 if home:
  tech=[r for r in news if r.get("category")=="news-tech"]
  # Until genuine view counts exist, show recent Tech news rather than invent rankings.
  if any(isinstance(r.get("views"),int) and r["views"]>0 for r in tech):
   tech=sorted(tech,key=lambda r:(r.get("views",0),str(r.get("date") or "")),reverse=True)
  first=sidebar_select(tech,12,used)
  if first:selected.append(box("I più letti",first))
  selected.append(amazon_provisional_box())
  mixed=daily_shuffle(news,"home-random-news")
  # Reserve at least three unique stories for EACH editorial group first.
  # Additional rows are allocated round-robin to avoid starving "Altre news".
  labels=("Da non perdere","Dalla redazione","Altre news")
  groups={label:sidebar_select(mixed,3,used) for label in labels}
  for _ in range(17):
   for label in labels:
    found=sidebar_select(mixed,1,used)
    if found:groups[label].extend(found)
  for label in labels:
   if groups[label]:selected.append(box(label,groups[label]))
 else:
  latest_news=sidebar_select(news,12,used)
  latest_reviews=sidebar_select(reviews,12,used)
  if latest_news:selected.append(box("Ultime news",latest_news))
  if latest_reviews:selected.append(box("Ultime recensioni",latest_reviews))
  mixed=daily_shuffle(rows,"inner-"+",".join(sorted(used)[:8]))
  for label in ("Da non perdere","Dalla redazione","Altre news","Archivio Tech","Archivio Gaming","Dagli archivi"):
   if label=="Archivio Tech":pool=[r for r in mixed if r.get("category")=="news-tech"]
   elif label=="Archivio Gaming":pool=[r for r in mixed if r.get("category")=="news-gaming"]
   else:pool=mixed
   subset=sidebar_select(pool,14,used)
   if subset:selected.append(box(label,subset))
 return '<aside class="sidebar '+("home-sidebar" if home else "inner-sidebar")+'" aria-label="Box editoriali"><div class="sidebar-stack">'+''.join(selected)+'</div></aside>'

def related_articles(rows,exclude="",category=None):
 candidates=sorted(rows,key=lambda r:str(r.get("published_at") or r.get("date") or ""),reverse=True)
 same=[r for r in candidates if r.get("category")==category]
 different=[r for r in candidates if r.get("category")!=category]
 chosen=[];seen=set()
 for row in same+different:
  if row.get("slug")==exclude:continue
  key=normalized_title(row.get("title",""))
  if not key or key in seen:continue
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",str(row.get("slug",""))):continue
  seen.add(key);chosen.append(row)
  if len(chosen)==3:break
 if len(chosen)!=3:raise ValueError("Exactly three distinct related articles required: "+exclude)
 return chosen

def related_markup(chosen):
 if len(chosen)!=3:raise ValueError("Related markup needs exactly three articles")
 return '<section class="related"><h2>Articoli correlati</h2><ul>'+''.join(
  '<li><a href="/'+r["slug"]+'"><strong>'+esc(clean_title(r["title"]))+'</strong></a></li>'
  for r in chosen)+'</ul></section>'

def feature_mini_cards(items):
 if not items:return ""
 rendered=[]
 for r in items[:2]:
  href="/"+r["slug"]
  image=safe_image(r.get("image",""))
  pic='<img loading="lazy" src="'+esc(image,quote=True)+'" alt="">' if image else '<span class="editorial-cover editorial-cover-mini"><strong>'+esc(r["title"])+'</strong></span>'
  rendered.append('<article class="card"><a class="thumb" href="'+href+'">'+pic+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="'+href+'">'+esc(r["title"])+'</a></h3></article>')
 # Do not generate empty placeholders or invented articles.
 return '<div class="cards">'+''.join(rendered)+'</div>'

def compact_cards(rows):
 if not rows:return ""
 out=[]
 for r in rows:
  href="/"+r["slug"]
  day=date_label(r)
  out.append('<article class="compact-item"><a class="compact-item-image" href="'+href+'">'+editorial_cover(r)+'</a>'
             '<div class="compact-item-text"><span class="compact-item-type">'+esc(TYPES.get(r["category"],""))+'</span>'
             '<h3><a href="'+href+'">'+esc(clean_title(r["title"]))+'</a></h3>'
             +('<time>'+esc(day)+'</time>' if day else "")+'</div></article>')
 return '<div class="cards-compact">'+''.join(out)+'</div>'

def feature_box(label,items):
 href="/guide" if label=="GUIDE" else "/extra"
 if not items:return ""
 primary=items[0]
 url="/"+primary["slug"]
 main=('<article class="feature-main-item"><a class="feature-main-thumb" href="'+url+'">'
       +editorial_cover(primary)+'</a>'
       '<div class="feature-main-description"><h3><a href="'+url+'">'+esc(clean_title(primary["title"]))+'</a></h3></div></article>')
 small=compact_cards(items[1:3]) if len(items)>1 else ""
 return '<div class="spotnews-feature feature-editorial">'+bar(label,href,"feature")+main+small+'</div>'

def feature_pair(guides,extras):
 return '<div class="feature-pair standalone-feature-pair">'+feature_box("GUIDE",guides)+feature_box("EXTRA",extras)+'</div>'

def special_gallery(rows):
 return '<div class="specials-showcase">'+cards(rows)+'</div>' if rows else ""

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
  if actual:
   # Use only the original image from the same source URL.
   previous=backup.get(source["name"])
   if not actual.get("image") and previous and actual.get("url")==previous.get("url"):
    actual["image"]=previous.get("image","")
   cards.append(actual);continue
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
  gateway=item.get("internal_path") if not item.get("source_only") else ""
  href=esc(gateway,quote=True) if gateway else url
  external_attributes='' if gateway else ' target="_blank" rel="noopener noreferrer external"'
  label=('Leggi approfondimenti ZazoomTek e fonte originale: ' if gateway else 'Apri la fonte originale: ')+title
  out.append('<article class="web-news-card"><a class="web-news-thumb" href="'+href+'"'+external_attributes+' aria-label="'+label+'">'+visual+'</a>'+sub+'<h3><a href="'+href+'"'+external_attributes+'>'+title+'</a></h3>'+when+'</article>')
 return '<div class="web-news-grid">'+''.join(out)+'</div>'

# Every Home content is allocated once: the same post/video/url is never placed in two widgets.

def home_keys(r):
 keys=set()
 title=re.sub(r"[^a-z0-9]+","",unesc(str(r.get("title","")).casefold()))
 if title:keys.add("title:"+title)
 url=str(r.get("source_url") or r.get("url") or "").strip().lower()
 if url.startswith("https://"):keys.add("url:"+url.split("?",1)[0].rstrip("/"))
 body=r.get("body",[])
 if isinstance(body,list) and body:
  opening=re.sub(r"[^a-z0-9]+","",unesc(str(body[0]).casefold()))
  if len(opening)>=95:keys.add("opening:"+opening[:95])
 if not keys:keys.add("slug:"+str(r.get("slug","")))
 return keys

def sort_by_date_desc(items):
 # Use exact publisher timestamp when provided. If only the day exists, preserve source order.
 return sorted(items,key=chronological_key,reverse=True)

def take_unique(items,count,used):
 result=[]
 for row in sort_by_date_desc(items):
  keys=home_keys(row)
  if used.intersection(keys):continue
  used.update(keys);result.append(row)
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
  # Candidates are passed to the same global registry on every pass.
  if days==14:result=[]
  for r in sort_by_date_desc(pool):
   keys=home_keys(r)
   if used.intersection(keys):continue
   result.append(r);used.update(keys)
   if len(result)==count:return result
 return result

def latest_featured_news(tech,gaming,used):
 """Reserve precisely the newest four Tech and newest one Gaming for the Home.
 Re-evaluate after EVERY build/import/Studio change; used prevents duplicates
 in lower Home grids and editorial sidebars. Replaced items rejoin their pool.
 """
 featured_tech=take_unique(tech,4,used)
 featured_gaming=take_unique(gaming,1,used)
 return featured_tech+featured_gaming

def home(rows):
 global_used=set()
 tech=[r for r in rows if r["category"]=="news-tech"]
 gaming=[r for r in rows if r["category"]=="news-gaming"]
 # The newest first-party Tech and Gaming stories are reserved for Spotlight,
 # BEFORE lower Home modules. Categories are independent, so a fresh Gaming post
 # never displaces any Tech card (and vice versa).
 # Reserve Special/Guide/Extra before news: their classifications are distinct.
 specials=take_unique([r for r in rows if r["category"]=="speciali"],2,global_used)
 guides=take_unique([r for r in rows if r["category"]=="guide"],3,global_used)
 extras=take_unique([r for r in rows if r["category"]=="extra"],3,global_used)
 spotlight=latest_featured_news(tech,gaming,global_used)
 tech_low=adaptive_news(tech,8,global_used)
 gaming_low=adaptive_news(gaming,5,global_used)
 reviews=take_unique([r for r in rows if r["category"] in ("recensioni-tech","recensioni-gaming") and r.get("source") in ("youtube-community","community-archive-full","manual-editorial","studio-editor")],3,global_used)
 video_section=playlist_cards()
 external=web_news()
 # URLs/titles selected for Notizie Web are external; mark them as used to avoid repeated home references.
 unique_web=[]
 for entry in sort_by_date_desc(external):
  identities=home_keys(entry)
  if global_used.intersection(identities):continue
  global_used.update(identities);unique_web.append(entry)
 sections=[
  ("News Tech",news_tech_magazine(tech_low)),
  ("News Gaming",gaming_magazine(gaming_low)),
  ("Ultime Recensioni",reviews_three_column(reviews)),
  ("Speciali",special_gallery(specials)),
  ("Guide e Extra",feature_pair(guides,extras)),
  ("Ultimi Video",video_section),
  ("Notizie Web",web_news_cards(unique_web))
 ]
 # Sidebar is last by design, so its articles can never duplicate the primary blocks.
 sidebar_html=sidebar(rows,True,global_used)
 top=section("In evidenza",featured_showcase(spotlight))
 return shell("Home",'<div class="featured-wide">'+top+'</div><div class="home-layout"><div class="home-column">'+''.join(content if name=="Guide e Extra" else section(name,content) for name,content in sections)+'</div>'+sidebar_html+'</div>')

def web_archive(rows):
 content='<h1>Notizie Web</h1><p class="web-archive-intro">Sei fonti italiane di tecnologia. Ogni notizia apre una scheda con eventuali approfondimenti ZazoomTek e il collegamento alla fonte originale.</p>'+web_news_cards(web_news())
 return inside("Notizie Web",content,rows,show_related=False,seo_path="/notizie-web",seo_summary="Notizie dal web: sei fonti italiane di tecnologia con articoli, aggiornamenti e collegamenti ai siti originali.")
def inside(title,content,rows,exclude="",cat=None,show_related=True,seo_row=None,seo_path="/",seo_summary=None):
 # One two-column grid: page content and matching-height sidebar on row one;
 # related links occupy only the article column on row two.
 related_rows=related_articles(rows,exclude,cat) if show_related else []
 section=related_markup(related_rows) if show_related else ""
 reserved_slugs={exclude}
 reserved_slugs.update(x["slug"] for x in related_rows)
 reserved=set()
 for r in rows:
  if r.get("slug") in reserved_slugs:reserved.update(home_keys(r))
 rail=sidebar(rows,False,reserved)
 content_html=('<div class="inner-layout"><div class="inner-column">'+content+'</div>'
               +rail+section+'</div>')
 return shell(title,content_html,seo_row=seo_row,seo_path=seo_path,seo_summary=seo_summary)
ARCHIVE_PAGE_SIZE=9
def pagination_links(key,page,total_pages):
 if total_pages<=1:return ""
 links=[]
 for n in range(1,total_pages+1):
  href="/"+key+("" if n==1 else "-page-"+str(n))
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
 if key=="video":return inside(label,'<h1>'+esc(label)+'</h1>'+playlist_cards(),rows,show_related=False,seo_path="/video",seo_summary="Video, recensioni, gameplay, test e unboxing pubblicati da ZazoomTek su YouTube.")
 import math
 count=max(1,math.ceil(len(selected)/ARCHIVE_PAGE_SIZE))
 offset=(page-1)*ARCHIVE_PAGE_SIZE
 visible=selected[offset:offset+ARCHIVE_PAGE_SIZE]
 content='<h1>'+esc(label)+'</h1>'+cards(visible)+pagination_links(key,page,count)
 return inside(label,content,rows,show_related=False,seo_path="/"+key+("" if page==1 else "-page-"+str(page)),seo_summary="Archivio "+label+" di ZazoomTek con notizie, recensioni e contenuti originali in ordine di pubblicazione."+((" Pagina "+str(page)+".") if page>1 else ""))
def article(r,rows):
 from article_templates import render
 return inside(r["title"],render(r,safe_image),rows,r["slug"],r["category"],seo_row=r,seo_path="/"+r["slug"])
def legacy_article_redirects(rows):
 """Only redirect genuine legacy ALIASES to extensionless canonical pages.
 A physical slug.html is automatically served at /slug by Cloudflare Pages.
 Neither /slug nor /slug.html may redirect back to each other.
 """
 by_slug={r["slug"]:r for r in rows}
 by_title={normalized_title(r["title"]):r for r in rows}
 # This excludes archives, legal pages, news and all canonical articles.
 occupied={p.stem for p in O.glob("*.html")}
 lines=[];sources=set();linked=0
 for entry in original_routes():
  old=str(entry["path"]).removesuffix(".html")
  if not re.fullmatch(r"[A-Za-z0-9_-]+",old):
   raise ValueError("Unsafe legacy article path: "+old)
  desired=entry.get("canonical_slug") or ""
  post_id=entry.get("post_id") or ""
  if not desired and post_id:
   desired="community-"+re.sub(r"[^a-z0-9]+","-",post_id.lower()).strip("-")
  found=by_slug.get(desired) or by_title.get(normalized_title(entry["title"]))
  if not found:
   print("Unresolved legacy source, no redirect created:",old,flush=True)
   continue
  if found["category"]!=entry["category"]:
   raise ValueError("Legacy URL category disagrees with article: "+old)
  dest="/"+found["slug"]
  # Physical pages and clean paths resolve to the same Cloudflare destination.
  if old==found["slug"] or old in occupied:
   continue
  for alias in ("/"+old,"/"+old+".html"):
   canonicalized_alias=alias.removesuffix(".html")
   if canonicalized_alias==dest:continue
   if alias in sources:continue
   sources.add(alias)
   lines.append(alias+" "+dest+" 301")
  linked+=1
 # Abbreviated historic Community posts must open their full-text canonicals.
 alias_entries=json.loads((P/"data/community_aliases.json").read_text(encoding="utf-8")).get("entries",[])
 for entry in alias_entries:
  old="community-"+re.sub(r"[^a-z0-9]+","-",entry["old_id"].lower()).strip("-")
  target="community-"+re.sub(r"[^a-z0-9]+","-",entry["new_id"].lower()).strip("-")
  if old==target or old in occupied:continue
  # Some exact-title Community posts may be superseded by a preferred archive edition.
  found=by_slug.get(target)
  if not found:
   target=next((r["slug"] for r in rows if normalized_title(r["title"])==normalized_title(entry["full_title"]) and r["category"]==entry["category"]),"")
  if not target:
   raise ValueError("Missing full-text alias target for "+entry["short_title"])
  for alias in ("/"+old,"/"+old+".html"):
   if alias in sources:continue
   sources.add(alias)
   lines.append(alias+" /"+target+" 301")
 (O/"_redirects").write_text("\n".join(lines)+("\n" if lines else ""),encoding="utf-8")
 print("Verified legacy URL aliases:",linked,"of",len(original_routes()),flush=True)

def contacts_page(rows):
 # Editor-approved Italian text. The email link opens the reader's own mail app.
 lines=[
 "Vuoi collaborare con ZazoomTek? Sei un'azienda, un brand, un'agenzia PR o un appassionato di tecnologia e videogiochi?",
 "ZazoomTek.it è un portale dedicato al mondo della tecnologia e del gaming, affiancato dal canale YouTube ZazoomTek, dove condividiamo recensioni, prove prodotto, unboxing, gameplay, notizie e approfondimenti.",
 "Siamo disponibili a valutare collaborazioni con aziende e agenzie di comunicazione, richieste di recensioni, invio di prodotti da testare, codici review per videogiochi, comunicati stampa e anteprime.",
 "Il nostro obiettivo è offrire contenuti originali, informativi e indipendenti, aiutando lettori e spettatori a conoscere meglio prodotti, tecnologie e videogiochi.",
 "Hai una proposta, vuoi segnalarci una notizia o semplicemente entrare in contatto con la redazione?",
 "Scrivici direttamente via email. Saremo lieti di valutare il tuo messaggio."
 ]
 body='<article class="contacts-article"><h1>Contatti</h1>'+''.join('<p>'+esc(line)+'</p>' for line in lines)
 body+='<p class="contacts-email">✉ <a href="mailto:zazoomtek@gmail.com">zazoomtek@gmail.com</a></p></article>'
 (O/"contatti.html").write_text(inside("Contatti",body,rows,show_related=False,seo_path="/contatti",seo_summary="Contatta ZazoomTek per collaborazioni, recensioni, notizie e richieste stampa."),encoding="utf-8")

def rss_feed(rows):
 """Generate a real RSS 2.0 feed with only first-party editorial content."""
 from xml.etree.ElementTree import Element,SubElement,ElementTree
 from email.utils import format_datetime
 from datetime import datetime,timezone
 base=((os.getenv("CF_PAGES_URL") or "https://zazoomtek-spotnews-preview.pages.dev") if PREVIEW else "https://zazoomtek.it").rstrip("/")
 # CF_PAGES_URL might not be set in a local build; never emit localhost links.
 if not base.startswith("https://"):base="https://zazoomtek.it"
 rss=Element("rss",{"version":"2.0"})
 channel=SubElement(rss,"channel")
 for key,value in (("title","ZazoomTek - Tecnologia e Gaming"),("link",base+"/"),("description","Ultime notizie, recensioni, guide e approfondimenti di ZazoomTek."),("language","it-it")):
  SubElement(channel,key).text=value
 posted=set()
 for row in sorted(rows,key=lambda r:str(r.get("published_at") or r.get("date") or ""),reverse=True):
  slug=row.get("slug","")
  if not slug or slug in posted:continue
  if row.get("category") not in TYPES or row.get("category")=="video":continue
  posted.add(slug)
  item=SubElement(channel,"item")
  url=base+"/"+slug
  SubElement(item,"title").text=clean_title(row.get("title") or "")
  SubElement(item,"link").text=url
  SubElement(item,"guid",{"isPermaLink":"true"}).text=url
  data=row.get("published_at") or row.get("date") or ""
  try:
   when=datetime.fromisoformat(str(data).replace("Z","+00:00"))
   if when.tzinfo is None:when=when.replace(tzinfo=timezone.utc)
   SubElement(item,"pubDate").text=format_datetime(when)
  except (ValueError,TypeError):pass
  SubElement(item,"category").text=TYPES.get(row.get("category"),"Articolo")
  body=row.get("body") or []
  if isinstance(body,str):body=[body]
  first=next((v if isinstance(v,str) else str(v.get("text") or "") for v in body
   if (isinstance(v,str) and v.strip() and not v.strip().startswith(("##","**"))) or
      (isinstance(v,dict) and v.get("type")=="paragraph" and str(v.get("text") or "").strip())),"")
  SubElement(item,"description").text=first.strip()[:500]
  if len(posted)>=50:break
 (O/"feed.xml").parent.mkdir(parents=True,exist_ok=True)
 ElementTree(rss).write(O/"feed.xml",encoding="utf-8",xml_declaration=True)
 print("RSS feed generated:",len(posted),"articles",flush=True)

def audit_published_articles(rows):
 """A whole-site audit: no article with only a title, cover or archived snippet."""
 issues=[]
 for row in rows:
  body=row.get("body") or []
  if isinstance(body,str):body=[body]
  text=" ".join(
   block if isinstance(block,str) else str(block.get("text") or "")
   for block in body if (isinstance(block,str) and not block.lstrip().startswith(("## ","# "))) or
   (isinstance(block,dict) and block.get("type") in ("paragraph","quote"))
  ).strip()
  if len(text)<260 or row.get("is_excerpt"):
   issues.append((row.get("slug"),len(text),bool(row.get("is_excerpt"))))
 for needed in (
  "guida-come-usare-playstation-2-tv-4k-moderna",
  "news-ugkxkbtuhabtov7gniqycpz9y8wdggjht3fn",
  "news-ugkxkcgzvny03vubwn5axlj9ewtxj-nqr69p",
  "news-ugkx0t7fvagel0nyuihyegzoxio0wc9nvsm7",
  "news-ugkxyi2ggon-auahc8nr5898ffno84i-kepe"
 ):
  if not any(r.get("slug")==needed for r in rows):
   issues.append((needed,"missing",True))
 ps2=next((r for r in rows if r.get("slug")=="guida-come-usare-playstation-2-tv-4k-moderna"),{})
 if not safe_image(ps2.get("image","")):
  issues.append(("PS2 cover","missing",True))
 if issues:
  raise ValueError("Editorial audit failed: "+repr(issues[:25]))
 print("Editorial audit PASS:",len(rows),"unique published articles with substantive text, 0 excerpts, PS2 photo ready",flush=True)

def main():
 from verify_article_typography import verify
 verify()
 rows=posts()
 audit_published_articles(rows)
 from web_editorial import attach_links, gateway_html
 web_items=attach_links(web_news(),rows)
 if O.exists():shutil.rmtree(O)
 # Copy the actual covers and other local editorial assets, not CSS/JS alone.
 shutil.copytree(P/"assets",O/"assets",dirs_exist_ok=True)
 from studio_build import build_studio
 build_studio(O,rows)
 from studio_v2_build import build_studio_v2
 build_studio_v2(O,rows)
 global TICKER_ROWS
 TICKER_ROWS=build_live_discovery(rows)
 (O/"index.html").write_text(home(rows),encoding="utf-8")
 for key in GROUPS:
  (O/(key+".html")).write_text(archive(key,rows),encoding="utf-8")
  if key!="video":
   import math
   count=sum(r["category"] in GROUPS[key] for r in rows)
   for page in range(2,max(1,math.ceil(count/ARCHIVE_PAGE_SIZE))+1):
    (O/(key+"-page-"+str(page)+".html")).write_text(archive(key,rows,page),encoding="utf-8")
 (O/"notizie-web.html").write_text(web_archive(rows),encoding="utf-8")
 for entry in web_items:
  path=entry.get("internal_path") or ""
  if not path:continue
  if not re.fullmatch(r"/notizia-web-[a-f0-9]{16}",path):
   raise ValueError("Unsafe external gateway URL: "+str(path))
  summary=("Notizia segnalata da "+entry["source"]+": "+entry["title"]+
           ". Scopri gli approfondimenti ZazoomTek e consulta la fonte.")
  destination=O/(path.lstrip("/")+".html")
  destination.write_text(inside(entry["title"],gateway_html(entry,rows),rows,
        show_related=False,seo_path=path,seo_summary=summary),encoding="utf-8")
 legal_pages(rows)
 contacts_page(rows)
 rss_feed(rows)
 for r in rows:(O/(r["slug"]+".html")).write_text(article(r,rows),encoding="utf-8")
 from verify_studio import verify_studio
 verify_studio(O,rows)
 from verify_studio_v2 import verify_studio_v2
 verify_studio_v2(O,rows)
 from verify_editorial_layout import check_all
 check_all(rows,O,P/"assets/css/spotnews.css")
 legacy_article_redirects(rows)
 missing_page=("<article class=\"legal-article\" style=\"min-height:320px\">"
               "<h1>Pagina non trovata</h1><p>Il contenuto richiesto non è disponibile.</p>"
               "<p><a href=\"/\">Torna alla Home di ZazoomTek</a></p></article>")
 (O/"404.html").write_text(inside("Pagina non trovata",missing_page,rows,show_related=False,seo_path="/404"),encoding="utf-8")
 (O/"_headers").write_text(
  "/*\n  X-Content-Type-Options: nosniff\n"+
  ("  X-Robots-Tag: noindex, nofollow\n" if PREVIEW else "")+
  "/studio/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: private, no-store\n"+
  "/studio-v2/*\n  X-Robots-Tag: noindex, nofollow\n  Cache-Control: private, no-store\n",
  encoding="utf-8")
 # Pages Functions invoke ONLY protected Studio endpoints. Static traffic stays
 # free and cacheable; public pages are never routed through the editor API.
 (O/"_routes.json").write_text(json.dumps({
  "version":1,"include":["/api/studio/*"],"exclude":[]
 },separators=(",",":")),encoding="utf-8")
 from seo import write_indexing
 write_indexing(O,rows,GROUPS,ARCHIVE_PAGE_SIZE,PREVIEW)
 from verify_cover_layout import check_media
 check_media(O,P/"assets/css/spotnews.css",P/"assets/js/site.js")
 from verify_web_gateway import check_web_gateways
 check_web_gateways(O,web_items,rows)
 from verify_seo import check_seo
 check_seo(O,rows,GROUPS,PREVIEW)
 from verify_routes import check_dist
 check_dist(O)
 print("SpotNews build OK:",len(rows),"articoli,",len(GROUPS)+2,"pagine.")
if __name__=="__main__":main()
