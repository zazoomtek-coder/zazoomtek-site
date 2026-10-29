"""Source-grounded ZazoomTek SEO for the complete static site."""
from collections import Counter
from datetime import datetime,timezone
from html import escape as esc,unescape
from pathlib import Path
from xml.etree.ElementTree import Element,SubElement,ElementTree,register_namespace
from math import ceil
import json,re

DOMAIN="https://zazoomtek.it"
DESC="Notizie, recensioni, guide e approfondimenti originali su tecnologia, videogiochi, hardware e innovazione."
SECTIONS={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra"}
STOP=set(("di a da in con tra fra per su al alla allo alle del della delle degli dei il la le lo gli i e ed è che chi come ma non sono un uno una anche più nei nel nello nella sul sulla alla quando cosa quale si ha hanno hanno essere dal alle oppure dopo ancora the and with for from this that which have has are you your into about more their video review news tech gaming recensione recensioni guida guide extra speciale speciali zazoomtek oggi").split())
def plain(value):
 s=unescape(str(value or ""))
 s=re.sub(r"<[^>]*>"," ",s)
 s=re.sub(r"!?\[([^\]]+)\]\([^)]+\)",r"\1",s)
 s=re.sub(r"(?m)^\s*#{1,6}\s*","",s)
 return re.sub(r"\s+"," ",s.replace("**","").replace("__","")).strip()

def prose(row):
 raw=row.get("body") or []
 if isinstance(raw,str):raw=[raw]
 return [plain(x if isinstance(x,str) else x.get("text") or x.get("content"))
         for x in raw if isinstance(x,(str,dict)) and plain(x if isinstance(x,str) else x.get("text") or x.get("content"))]
def terms(s):
 return [x.lower() for x in re.findall(r"[a-zA-ZÀ-ÿ0-9]+(?:[-'][a-zA-ZÀ-ÿ0-9]+)?",plain(s)) if len(x)>2 and x.lower() not in STOP and not x.isdigit()]
def keywords(row):
 locked=row.get("seo_lock")
 if isinstance(locked,dict) and isinstance(locked.get("keywords"),list) and locked["keywords"]:
  return [plain(x) for x in locked["keywords"] if plain(x)][:8]
 title=terms(row.get("title"))
 corpus=terms(" ".join(prose(row))) # entire article, never only the teaser
 freq=Counter(corpus)
 freq.update({x:5 for x in title})
 found=[]
 for word in title+[x for x,n in freq.most_common(30)]:
  if word not in found:found.append(word)
 return found[:8]
def title_tag(row):
 """Preserve meaningful complete headlines; never cut at 70 chars then add a brand."""
 locked=row.get("seo_lock")
 if isinstance(locked,dict) and plain(locked.get("title")):
  return plain(locked["title"])[:115]
 name=plain(row.get("title"))
 if not name:return "ZazoomTek | Tecnologia e Gaming"
 # Full original H1 takes priority over cosmetic brand suffix.
 if len(name)<=72:
  return name if "zazoomtek" in name.casefold() else name+" | ZazoomTek"
 if len(name)<=115:return name
 # An exceptionally long title should end at a natural phrase boundary,
 # not with dangling Italian conjunctions or prepositions.
 parts=re.split(r"\s+[|–—]\s+",name)
 chosen=parts[0]
 for part in parts[1:]:
  proposal=chosen+" | "+part
  if len(proposal)>110:break
  chosen=proposal
 if len(chosen)>110:
  chosen=chosen[:110].rsplit(" ",1)[0]
 chosen=re.sub(r"\s+(?:e|ed|di|del|della|dei|per|con|tra|fra|in|su|a|da|il|la|le|lo|gli|i|un|una)$","",chosen,flags=re.I)
 return chosen.strip(" ,;:-–—") or name[:110]
def description(row):
 locked=row.get("seo_lock")
 if isinstance(locked,dict) and plain(locked.get("description")):
  return plain(locked["description"])[:165]
 parts=prose(row)
 if not parts:return DESC
 title_words=set(terms(row.get("title")))
 candidates=[]
 for i,part in enumerate(parts):
  if len(part)<60 or part.startswith("#"):continue
  sentences=re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Ý0-9])",part)
  text=" ".join(sentences[:2])
  if len(text)<70:text=part
  score=len(title_words.intersection(terms(text)))*5-min(8,i)
  candidates.append((score,text))
 text=max(candidates,key=lambda x:x[0])[1] if candidates else " ".join(parts)
 text=plain(text)
 if len(text)>165:text=text[:160].rsplit(" ",1)[0].rstrip(" ,;:-–—")+"…"
 return text or DESC
def canonical(path):
 path=str(path or "/")
 if not path.startswith("/"):path="/"+path
 if path!="/" and path.endswith(".html"):path=path[:-5]
 return DOMAIN+path
def full_image(value):
 url=str(value or "")
 if url.startswith("/") and not url.startswith("//"):return DOMAIN+url
 if url.startswith("https://") and not any(x in url for x in '"<>'):return url
 return ""
def datetime_iso(value):
 try:
  if not value:return ""
  d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
  return d.replace(tzinfo=timezone.utc).isoformat(timespec="seconds") if d.tzinfo is None else d.isoformat(timespec="seconds")
 except (TypeError,ValueError):return ""
def jsonld(value):
 return '<script type="application/ld+json">'+json.dumps(value,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+'</script>'
def breadcrumb(path,title,row):
 items=[{"@type":"ListItem","position":1,"name":"Home","item":DOMAIN+"/"}]
 if row and row.get("category") in SECTIONS:
  cat=row["category"]
  items.append({"@type":"ListItem","position":2,"name":SECTIONS[cat],"item":canonical("/"+cat)})
 if path!="/":
  items.append({"@type":"ListItem","position":len(items)+1,"name":plain(title),"item":canonical(path)})
 return {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":items}
def article_schema(row,url,desc,image):
 cat=row.get("category","")
 author=plain(row.get("author")) or "Redazione ZazoomTek"
 data={"@context":"https://schema.org","@type":"NewsArticle" if cat.startswith("news-") else "Article",
  "@id":url+"#article","mainEntityOfPage":{"@type":"WebPage","@id":url},
  "headline":plain(row.get("title"))[:300],"description":desc,"inLanguage":"it-IT",
  "articleSection":SECTIONS.get(cat,"Articoli"),
  "author":{"@type":"Organization","name":"ZazoomTek"} if author.lower()=="redazione zazoomtek" else {"@type":"Person","name":author},
  "publisher":{"@type":"Organization","name":"ZazoomTek","url":DOMAIN},
  "keywords":", ".join(keywords(row))}
 date=datetime_iso(row.get("published_at") or row.get("date"))
 update=datetime_iso(row.get("updated_at") or row.get("modified_at")) or date
 if date:data["datePublished"]=date
 if update:data["dateModified"]=update
 if image:data["image"]=[image]
 # Only mark up an actual rating; never manufacture a product review.
 score=row.get("score") or row.get("rating")
 # The editorial template may show a real vote extracted from original prose.
 # Reuse that SAME verified vote for structured data; never invent a rating.
 if cat.startswith("recensioni-") and score is None:
  from article_templates import score as visible_score,paragraphs
  score=visible_score(row,paragraphs(row))
 if cat.startswith("recensioni-") and score is not None:
  try:
   number=float(str(score).replace(",",".").split("/")[0])
   name=re.split(r"(?i)\brecensione\b",plain(row.get("title")))[0].split("|")[0].strip(" :-–—")
   if name and 0<number<=10:
    data["@type"]="Review"
    data["itemReviewed"]={"@type":"VideoGame" if cat=="recensioni-gaming" else "Product","name":name}
    data["reviewRating"]={"@type":"Rating","ratingValue":number,"bestRating":10,"worstRating":0}
  except (TypeError,ValueError):pass
 return data
def metadata(title,path="/",row=None,preview=True,summary=None):
 url=canonical(path)
 head=title_tag(row) if row else ("ZazoomTek | Tecnologia e Gaming" if path=="/" else plain(title)+" | ZazoomTek")
 # SERP title only: never truncate the real editorial H1.
 # Web gateway / archival headlines can exceed Google's practical title length.
 if len(head)>115:
  head=head[:115].rsplit(" ",1)[0].rstrip(" ,;:-–—")
 desc=description(row) if row else (summary or DESC)
 image=full_image(row.get("image")) if row else ""
 robot=("noindex,nofollow" if preview or path=="/404" else
       "noindex,follow" if path.startswith("/notizia-web-") else
       "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1")
 output=['<title>'+esc(head)+'</title>',
  '<meta name="description" content="'+esc(desc,quote=True)+'">',
  '<meta name="robots" content="'+robot+'">',
  '<meta name="googlebot" content="'+robot+'">',
  '<link rel="canonical" href="'+esc(url,quote=True)+'">',
  '<meta property="og:locale" content="it_IT"><meta property="og:site_name" content="ZazoomTek">',
  '<meta property="og:type" content="'+("article" if row else "website")+'">',
  '<meta property="og:url" content="'+esc(url,quote=True)+'">',
  '<meta property="og:title" content="'+esc(head,quote=True)+'">',
  '<meta property="og:description" content="'+esc(desc,quote=True)+'">',
  '<meta name="twitter:card" content="'+("summary_large_image" if image else "summary")+'">',
  '<meta name="twitter:title" content="'+esc(head,quote=True)+'">',
  '<meta name="twitter:description" content="'+esc(desc,quote=True)+'">']
 if image:
  output+=['<meta property="og:image" content="'+esc(image,quote=True)+'">',
    '<meta name="twitter:image" content="'+esc(image,quote=True)+'">']
 if row:
  date=datetime_iso(row.get("published_at") or row.get("date"))
  changed=datetime_iso(row.get("updated_at") or row.get("modified_at")) or date
  if date:output.append('<meta property="article:published_time" content="'+esc(date,quote=True)+'">')
  if changed:output.append('<meta property="article:modified_time" content="'+esc(changed,quote=True)+'">')
  output.append('<meta property="article:section" content="'+esc(SECTIONS.get(row.get("category"),"Articoli"),quote=True)+'">')
  for term in keywords(row)[:5]:
   output.append('<meta property="article:tag" content="'+esc(term,quote=True)+'">')
  output.append(jsonld(article_schema(row,url,desc,image)))
 elif path=="/":
  output.append(jsonld({"@context":"https://schema.org","@type":"WebSite","@id":DOMAIN+"/#website",
    "name":"ZazoomTek","url":DOMAIN+"/","inLanguage":"it-IT",
    "publisher":{"@type":"Organization","name":"ZazoomTek","url":DOMAIN}}))
 output.append(jsonld(breadcrumb(path,row.get("title") if row else title,row)))
 return "".join(output)

def write_indexing(output,rows,groups,page_size,preview):
 root=Path(output)
 found={}
 def add(path,stamp=""):
  name="index.html" if path=="/" else path.lstrip("/")+".html"
  if not (root/name).is_file():raise AssertionError("Sitemap target missing: "+path)
  found[path]=stamp
 add("/")
 for key,cats in groups.items():
  add("/"+key)
  if key!="video":
   count=sum(r.get("category") in cats for r in rows)
   for n in range(2,max(1,ceil(count/page_size))+1):add("/"+key+"-page-"+str(n))
 for page in ("notizie-web","privacy-policy","cookie-policy","disclaimer","note-legali","chi-siamo","contatti"):add("/"+page)
 for row in rows:
  date=datetime_iso(row.get("updated_at") or row.get("modified_at") or row.get("published_at") or row.get("date"))
  add("/"+row["slug"],date[:10] if date else "")
 register_namespace("","http://www.sitemaps.org/schemas/sitemap/0.9")
 ns="{http://www.sitemaps.org/schemas/sitemap/0.9}"
 pages=sorted(found.items())
 def write_part(rows,name):
  top=Element(ns+"urlset")
  for path,day in rows:
   item=SubElement(top,ns+"url")
   SubElement(item,ns+"loc").text=canonical(path)
   if day:SubElement(item,ns+"lastmod").text=day
  ElementTree(top).write(root/name,encoding="utf-8",xml_declaration=True)
 if len(pages)<=45000:write_part(pages,"sitemap.xml")
 else:
  top=Element(ns+"sitemapindex")
  for i in range(0,len(pages),45000):
   name="sitemap-"+str(i//45000+1)+".xml"
   write_part(pages[i:i+45000],name)
   SubElement(SubElement(top,ns+"sitemap"),ns+"loc").text=DOMAIN+"/"+name
  ElementTree(top).write(root/"sitemap.xml",encoding="utf-8",xml_declaration=True)
 if preview:robots="User-agent: *\nDisallow: /\n"
 else:robots="User-agent: *\nAllow: /\nSitemap: "+DOMAIN+"/sitemap.xml\n"
 (root/"robots.txt").write_text(robots,encoding="utf-8")
 print("SEO: "+str(len(pages))+" sitemap URLs, preview noindex: "+str(preview),flush=True)
