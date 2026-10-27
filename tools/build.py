#!/usr/bin/env python3
"""ZazoomTek SpotNews: generatore statico con menu/layout universali."""
from pathlib import Path
from html import escape as esc
import json,os,re,shutil
P=Path(__file__).resolve().parents[1]; O=P/"dist"
NAV=[("HOME","/"),("NEWS","/news.html"),("RECENSIONI","/recensioni.html"),("GUIDE","/guide.html"),("SPECIALI","/speciali.html"),("EXTRA","/extra.html"),("VIDEO","/video.html")]
TYPES={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra","video":"Video"}
GROUPS={"news":["news-tech","news-gaming"],"recensioni":["recensioni-tech","recensioni-gaming"],"guide":["guide"],"speciali":["speciali"],"extra":["extra"],"video":["video"],**{k:[k] for k in TYPES}}
PREVIEW=os.getenv("CF_PAGES_BRANCH","feature/spotnews-clean-rebuild")!="main"
def posts():
 obj=json.loads((P/"data/posts.json").read_text(encoding="utf-8")); rows=obj["posts"]; seen=set()
 for r in rows:
  slug=r["slug"]
  if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or slug in seen or slug in GROUPS:raise ValueError("Slug invalid/duplicate")
  if r["category"] not in TYPES or not isinstance(r["title"],str):raise ValueError("Post category/title invalid")
  seen.add(slug)
 return sorted(rows,key=lambda x:x.get("date",""),reverse=True)
def shell(title,inner):
 nav="".join('<a href="'+u+'">'+n+'</a>' for n,u in NAV)
 return ('<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' | ZazoomTek</title><meta name="robots" content="'+("noindex,nofollow" if PREVIEW else "index,follow")+'"><link rel="stylesheet" href="/assets/css/spotnews.css?v=20261027-menu-2"></head><body><header class="header"><div class="wrap"><a class="logo" href="/">Zazoom<span>Tek</span></a><button id="mobile-menu" aria-controls="nav" aria-expanded="false">Menu</button><nav id="nav" aria-label="Navigazione universale">'+nav+'</nav></div></header><main class="wrap">'+inner+'</main><footer class="footer"><div class="wrap">ZazoomTek.it · Tecnologia e Gaming</div></footer><script defer src="/assets/js/site.js"></script></body></html>')
def blank():return '<div class="blank">Nessun contenuto pubblicato</div>'
def cards(rows):
 return '<div class="cards">'+''.join('<article class="card"><a class="thumb" href="/'+r["slug"]+'.html">'+('<img loading="lazy" src="'+esc(r["image"],quote=True)+'" alt="">' if r.get("image","").startswith("/") and ".." not in r.get("image","") else "")+'</a><small>'+esc(TYPES[r["category"]])+'</small><h3><a href="/'+r["slug"]+'.html">'+esc(r["title"])+'</a></h3></article>' for r in rows)+'</div>' if rows else blank()
def section(title,content):return '<section class="section"><h2>'+title+'</h2>'+content+'</section>'
def box(name,rows):
 return '<section class="box"><h2>'+name+'</h2>'+('<ul>'+''.join('<li><a href="/'+r["slug"]+'.html">'+esc(r["title"])+'</a></li>' for r in rows)+'</ul>' if rows else blank())+'</section>'
def sidebar(rows,home=False):
 seen=set()
 def select(stream):
  chosen=[]
  for r in stream:
   if r["slug"] not in seen:
    chosen.append(r);seen.add(r["slug"])
   if len(chosen)==5:break
  return chosen
 parts=[("I più letti",select(sorted([r for r in rows if isinstance(r.get("views"),int) and r["views"]>0],key=lambda r:r["views"],reverse=True))),("Da non perdere",select(r for r in rows if r.get("featured"))),("Dalla redazione",select(r for r in rows if r.get("editorial_pick"))),("Ultime notizie",select(r for r in rows if r["category"].startswith("news-"))),("Ultime recensioni",select(r for r in rows if r["category"].startswith("recensioni-")))]
 return '<aside class="sidebar '+("home-sidebar" if home else "inner-sidebar")+'">' + ''.join(box(name,subset) for name,subset in parts)+'</aside>'
def related(rows,exclude="",category=None):
 found=[r for r in rows if r["slug"]!=exclude and (category is None or r["category"]==category)][:8]
 return '<section class="related"><h2>Articoli correlati</h2>'+('<ul>'+''.join('<li><a href="/'+r["slug"]+'.html"><strong>'+esc(r["title"])+'</strong></a></li>' for r in found)+'</ul>' if found else blank())+'</section>'
def home(rows):
 def by(*keys):return [r for r in rows if r["category"] in keys]
 features=[r for r in by("news-tech","news-gaming") if r.get("featured")][:4]
 raw=json.loads((P/"data/web.json").read_text(encoding="utf-8"))["items"]
 web=[w for w in raw if isinstance(w,dict) and isinstance(w.get("url"),str) and w["url"].startswith("https://") and isinstance(w.get("title"),str)]
 links='<ul>'+''.join('<li><a rel="noopener noreferrer" href="'+esc(w["url"],quote=True)+'">'+esc(w["title"])+'</a></li>' for w in web[:8])+'</ul>' if web else blank()
 sections=[("In evidenza",cards(features)),("News Tech",cards(by("news-tech")[:6])),("News Gaming",cards(by("news-gaming")[:6])),("Ultime Recensioni",cards(by("recensioni-tech","recensioni-gaming")[:6])),("Guide e Extra",cards(by("guide","extra")[:6])),("Ultimi Video",cards(by("video")[:6])),("Notizie Web",links)]
 return shell("Home",'<div class="home-layout"><div class="home-column">'+''.join(section(name,content) for name,content in sections)+'</div>'+sidebar(rows,True)+'</div>')
def inside(title,content,rows,exclude="",cat=None):
 return shell(title,'<div class="inner-layout"><div class="inner-column">'+content+'</div>'+sidebar(rows)+'</div>'+related(rows,exclude,cat))
def archive(key,rows):
 categories=GROUPS[key]; label=key.replace("-"," ").title()
 return inside(label,'<h1>'+esc(label)+'</h1>'+cards([r for r in rows if r["category"] in categories]),rows,cat=categories[0] if len(categories)==1 else None)
def article(r,rows):
 cover=('<img class="cover" src="'+esc(r["image"],quote=True)+'" alt="">') if r.get("image","").startswith("/") and ".." not in r.get("image","") else ""
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
 for key in GROUPS:(O/(key+".html")).write_text(archive(key,rows),encoding="utf-8")
 for r in rows:(O/(r["slug"]+".html")).write_text(article(r,rows),encoding="utf-8")
 (O/"404.html").write_text(shell("Pagina non trovata","<h1>Pagina non trovata</h1>"),encoding="utf-8")
 (O/"_headers").write_text("/*\n  X-Content-Type-Options: nosniff\n"+("  X-Robots-Tag: noindex, nofollow\n" if PREVIEW else ""),encoding="utf-8")
 print("SpotNews build OK:",len(rows),"articoli,",len(GROUPS)+2,"pagine.")
if __name__=="__main__":main()
