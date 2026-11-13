"""Fail deployment if any internal page link or redirect is broken/circular."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
from article_routes import build_article_url, CATEGORY_PREFIX, ALLOWED_PREFIXES
from route_link_cleanup import strip_orphan_community_anchors

class LinkReader(HTMLParser):
 def __init__(self):
  super().__init__()
  self.hrefs=[]
 def handle_starttag(self,tag,attrs):
  if tag not in ("a","link"):return
  href=dict(attrs).get("href")
  if href:self.hrefs.append(href)

class PageIdentity(HTMLParser):
 def __init__(self):
  super().__init__();self.title=False;self.h1=False;self.title_text="";self.h1_text="";self.canonicals=[]
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=="title":self.title=True
  if tag=="h1":self.h1=True
  if tag=="link" and attrs.get("rel")=="canonical":self.canonicals.append(attrs.get("href",""))
 def handle_endtag(self,tag):
  if tag=="title":self.title=False
  if tag=="h1":self.h1=False
 def handle_data(self,data):
  if self.title:self.title_text+=data
  if self.h1:self.h1_text+=data

def check_dist(root,rows=None):
 root=Path(root)
 documents=list(root.rglob("*.html"))
 def route_for(page):
  rel=page.relative_to(root).with_suffix("").as_posix()
  if rel=="index":return "/"
  if rel.endswith("/index"):rel=rel.rsplit("/",1)[0]
  return "/"+rel
 real_pages={route_for(page).lstrip("/") for page in documents}
 errors=[]
 warnings=[]
 def page_is_release_critical(doc):
  rel=doc.relative_to(root).with_suffix("").as_posix()
  if rel=="index":return True
  parts=rel.split("/")
  if len(parts)>1 and parts[0] in ALLOWED_PREFIXES:return True
  stem=parts[-1]
  archive_names={"recensioni","news","speciali","guide","extra","news-tech","news-gaming",
                 "recensioni-tech","recensioni-gaming"}
  return stem in archive_names or any(stem.startswith(name+"-page-") or stem.startswith(name+"-archivio")
                                      for name in archive_names)
 def page_issue(doc,message):
  critical=page_is_release_critical(doc)
  (errors if critical else warnings).append(message)
 # Route every public request through the canonical URL middleware so the
 # www host, HTTP and physical .html aliases cannot be indexed separately.
 routes_file=root/"_routes.json"
 middleware_file=root.parent/"functions"/"_middleware.js"
 try:
  route_config=json.loads(routes_file.read_text(encoding="utf-8"))
  if "/*" not in route_config.get("include",[]):
   errors.append("Canonical middleware is not routed across public URLs")
  if not middleware_file.is_file():
   errors.append("Canonical URL middleware source is missing")
  else:
   middleware=middleware_file.read_text(encoding="utf-8")
   for required in ('www.zazoomtek.it','.html','CATEGORY_ROUTE','Response.redirect','context.next()','301'):
    if required not in middleware:
     errors.append("Canonical middleware missing rule: "+required)
 except (OSError,ValueError,TypeError) as error:
  errors.append("Canonical middleware routing configuration is invalid: "+str(error))
 # Pages interprets /slug as dist/slug.html and normalizes /slug.html -> /slug.
 def pretty(path):
  return path.removesuffix(".html").rstrip("/") or "/"
 for doc in documents:
  markup=doc.read_text(encoding="utf-8")
  markup,warnings=strip_orphan_community_anchors(markup,real_pages)
  for orphan in warnings:
   print("WARNING: removed orphan Community link in "+doc.name+": "+orphan+" (anchor text preserved)",flush=True)
  if warnings:
   doc.write_text(markup,encoding="utf-8")
  reader=LinkReader()
  reader.feed(markup)
  for href in reader.hrefs:
   u=urlsplit(href)
   if u.scheme or u.netloc or not href.startswith("/"):continue
   path=unquote(u.path)
   if path.startswith("/assets/"):
    if not (root/path.lstrip("/")).is_file():page_issue(doc,f"{doc.name} links to missing asset {path}")
    continue
   if path=="/":continue
   if path=="/feed.xml":
    if not (root/"feed.xml").is_file():page_issue(doc,"RSS feed missing: /feed.xml")
    continue
   if path.endswith(".html"):
    page_issue(doc,f"{doc.name} uses noncanonical .html URL: {path}")
   route=pretty(path)
   if route.lstrip("/") not in real_pages:
    is_v2=any(route.startswith("/"+prefix+"/") for prefix in ALLOWED_PREFIXES)
    is_archive=route in ("/recensioni","/news","/speciali","/guide","/extra")
    if is_v2 or is_archive:
     page_issue(doc,f"{doc.name} links to absent protected route {route}")
    else:
     page_issue(doc,"unresolved legacy link in "+doc.name+": "+route)
 redirect_file=root/"_redirects"
 redirects={}
 if redirect_file.is_file():
  for line in redirect_file.read_text(encoding="utf-8").splitlines():
   if not line.strip():continue
   parts=line.split()
   if len(parts)!=3 or parts[2] not in ("301","302","307","308"):
    errors.append("Invalid redirect: "+line);continue
   source,target,_=parts
   if source in redirects:errors.append("Duplicate redirect source "+source)
   redirects[source]=target
   if pretty(source)==pretty(target):
    errors.append("Automatic Cloudflare HTML normalization would loop: "+line)
   if target.endswith(".html"):
    errors.append("Redirect target is noncanonical "+line)
   if pretty(target).lstrip("/") not in real_pages:
    errors.append("Redirect target does not exist "+line)
   if source.removesuffix(".html").lstrip("/") in real_pages:
    errors.append("Redirect overrides an actual HTML page "+line)
 for source,target in redirects.items():
  if target in redirects or target+".html" in redirects:
   errors.append("Redirect chain/cycle risk: "+source+" -> "+target)
  if target=="/":
   errors.append("Article/legacy redirect must never send visitors to homepage: "+source)
 # Regression guard for the exact Razer result reported in Google.
 # This URL is already a generated canonical article path, not a redirect alias.
 razer_old="/community-ugkxhw4e98tezptpdc7opr4e9dcs53bsioey"
 existing=root/(razer_old.lstrip("/")+".html")
 if not existing.is_file():
  warnings.append("Historical Razer Google URL has no generated article page: "+razer_old)
 else:
  identity=PageIdentity();identity.feed(existing.read_text(encoding="utf-8"))
  if "razer hammerhead v3 chroma" not in (identity.title_text+" "+identity.h1_text).casefold():
   warnings.append("Historical Razer Google URL does not resolve to the Hammerhead V3 Chroma article: "+razer_old)
  if identity.canonicals!=["https://zazoomtek.it"+razer_old]:
   warnings.append("Historical Razer article canonical does not match its article URL: "+razer_old)
  if redirects.get(razer_old) or redirects.get(razer_old+".html"):
   errors.append("Historical Razer canonical article is incorrectly redirected: "+razer_old)
 # Explicitly verify all four legal pages and editorial archives.
 for name in ("news","news-tech","news-gaming","recensioni","recensioni-tech",
              "recensioni-gaming","guide","speciali","extra","privacy-policy",
              "cookie-policy","disclaimer","note-legali","chi-siamo","contatti"):
  if name not in real_pages:errors.append("Required page missing: /"+name)
 # The five public category archives must be physical, self-canonical 200 pages.
 for name in ("recensioni","news","speciali","guide","extra"):
  page=root/(name+".html")
  if not page.is_file():
   errors.append("Required category archive missing: /"+name)
   continue
  identity=PageIdentity();identity.feed(page.read_text(encoding="utf-8"))
  expected="https://zazoomtek.it/"+name
  if identity.canonicals!=[expected]:
   errors.append("Category archive canonical mismatch: /"+name)
  if not identity.title_text.strip() or not identity.h1_text.strip():
   errors.append("Category archive title/H1 missing: /"+name)
  elif not identity.title_text.strip().startswith(identity.h1_text.strip()):
   errors.append("Category archive title is incoherent with H1: /"+name)
 if any(source.startswith("/community-") for source in redirects):
  errors.append("Historical Community URLs must not be redirected or rewritten")
 # Dataset -> public URL -> nested file -> canonical must be a one-to-one mapping.
 if rows is not None:
  for row in rows:
   route=build_article_url(row)
   page=root/(route.lstrip("/")+".html")
   if not page.is_file():
    (errors if row.get("route_version") in (2,"2","v2") else warnings).append("Dataset route has no physical HTML file: "+route)
    continue
   identity=PageIdentity();identity.feed(page.read_text(encoding="utf-8"))
   expected="https://zazoomtek.it"+route
   if identity.canonicals!=[expected]:
    (errors if row.get("route_version") in (2,"2","v2") else warnings).append("Dataset route/canonical mismatch: "+route)
   if row.get("route_version") in (2,"2","v2"):
    prefix=CATEGORY_PREFIX.get(row.get("category"))
    if not prefix or not route.startswith("/"+prefix+"/"):
     errors.append("route_version v2 does not match category: "+route)
   elif row.get("legacy_path") and route!=row["legacy_path"]:
    warnings.append("Historical legacy_path changed: "+str(row.get("legacy_path")))
   if route.startswith("/community-") and (route in redirects or route+".html" in redirects):
    errors.append("Historical Community route was redirected: "+route)

 # Exercise the generated Pages-style file resolver over HTTP, including real 404s.
 from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
 from threading import Thread
 from functools import partial
 from urllib.request import urlopen
 from urllib.error import HTTPError
 class PagesHandler(SimpleHTTPRequestHandler):
  def translate_path(self,path):
   mapped=Path(super().translate_path(path))
   if not mapped.is_file() and mapped.suffix=="":
    candidate=Path(str(mapped)+".html")
    if candidate.is_file():return str(candidate)
   return str(mapped)
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(("127.0.0.1",0),partial(PagesHandler,directory=str(root)))
 worker=Thread(target=server.serve_forever,daemon=True);worker.start()
 try:
  base="http://127.0.0.1:"+str(server.server_address[1])
  checks=["/recensioni","/news","/speciali","/guide","/extra"]
  fixture_file=None
  if rows:
   nested=next((build_article_url(row) for row in rows if row.get("route_version") in (2,"2","v2")),None)
   legacy=next((build_article_url(row) for row in rows if build_article_url(row).startswith("/community-")),None)
   if nested:checks.append(nested)
   else:
    fixture={"route_version":2,"category":"guide","public_slug":"route-integration-fixture",
             "public_path":"/guide/route-integration-fixture"}
    nested=build_article_url(fixture)
    fixture_file=root/(nested.lstrip("/")+".html")
    fixture_file.parent.mkdir(parents=True,exist_ok=True)
    fixture_file.write_text('<!doctype html><title>Route fixture</title><link rel="canonical" href="https://zazoomtek.it'+nested+'">',encoding="utf-8")
    checks.append(nested)
   if legacy:checks.append(legacy)
  for route in checks:
   with urlopen(base+route,timeout=3) as response:
    if response.status!=200:errors.append("Generated route is not HTTP 200: "+route)
  for route in ("/blog/titolo-prova","/guide/articolo-inesistente"):
   try:
    with urlopen(base+route,timeout=3) as response:
     errors.append("Unknown route unexpectedly returned HTTP "+str(response.status)+": "+route)
   except HTTPError as response:
    if response.code!=404:errors.append("Unknown route did not return HTTP 404: "+route)
 finally:
  server.shutdown();server.server_close();worker.join(timeout=2)
  if fixture_file and fixture_file.exists():
   fixture_file.unlink()
   try:fixture_file.parent.rmdir()
   except OSError:pass
 # Internal search and breaking news datasets must resolve to actual published articles.
 for name,key in (("search-index.json","articles"),("news-ticker.json","items")):
  target=root/name
  if not target.is_file():
   errors.append("Missing discovery dataset: "+name)
   continue
  try:
   payload=json.loads(target.read_text(encoding="utf-8"))
   entries=payload.get(key)
   if not isinstance(entries,list):raise ValueError("Expected JSON array "+key)
   if name=="search-index.json" and not entries:
    raise ValueError("Search index is empty")
   if name=="news-ticker.json" and len(entries)!=10:
    raise ValueError("Breaking ticker has fewer than 10 real headlines")
   seen=set()
   for entry in entries:
    path=entry.get("url","")
    if not isinstance(path,str) or not path.startswith("/") or path.endswith(".html"):
     raise ValueError("Invalid canonical entry URL "+str(path))
    if path.lstrip("/") not in real_pages:
     raise ValueError("Linked article does not exist "+path)
    if name=="news-ticker.json":
     if path in seen:raise ValueError("Duplicate ticker headline "+path)
     seen.add(path)
  except (ValueError,TypeError,KeyError) as error:
   errors.append("Invalid discovery dataset "+name+": "+str(error))
 # RSS item URLs must point to real category/legacy article paths without suffixes.
 feed=root/"feed.xml"
 if not feed.is_file():
  errors.append("RSS feed file missing: /feed.xml")
 else:
  try:
   from xml.etree import ElementTree as ET
   feed_root=ET.parse(feed).getroot()
   links=[node.text or "" for node in feed_root.findall(".//item/link")]
   if len(links)!=len(set(links)):
    errors.append("RSS feed contains duplicate article URLs")
   for value in links:
    parsed=urlsplit(value)
    path=parsed.path
    if not path.startswith("/") or path.endswith(".html") or (path!="/" and path.endswith("/")):
     errors.append("RSS feed contains a noncanonical URL: "+value)
    elif path.lstrip("/") not in real_pages:
     errors.append("RSS feed links to a missing article: "+value)
  except (OSError,ValueError,TypeError) as error:
   errors.append("RSS feed XML is invalid: "+str(error))
 # Verify the Home-only Amazon showcase and its requested affiliate destination.
 homepage=root/"index.html"
 if homepage.is_file():
  markup=homepage.read_text(encoding="utf-8")
  a=markup.find('class="box editorial-box amazon-feature-box"')
  first=markup.find("I più letti")
  after=markup.find("Da non perdere",a)
  if min(a,first,after)<0 or not(first<a<after):
   errors.append("Amazon showcase not between I più letti and Da non perdere")
  for phrase in (
   "Prodotti recensiti da ZazoomTek",
   "Scopri su Amazon i prodotti tech, accessori e gadget recensiti e consigliati da ZazoomTek.",
   "Link affiliato Amazon. In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei senza alcun costo per l’utente.",
   'href="https://link.amazon/A0dJXv9PO"',
   'rel="sponsored noopener noreferrer"'
  ):
   if phrase not in markup:errors.append("Amazon box lacks correct content: "+phrase[:48])
  # The Amazon HTML has always been generated in its intended second slot;
  # the client-side sidebar fitter must NEVER hide a panel without rows.
  sitejs=(root/"assets/js/site.js").read_text(encoding="utf-8")
  for check in (
   'const amazon=home?panels.find(box=>box.classList.contains("amazon-feature-box")):null;',
   'if(amazon)amazon.hidden=false;',
   'x.panel!==amazon'
  ):
   if check not in sitejs:
    errors.append("Amazon rail runtime protection missing: "+check[:90])
  # Require cache-busting URL to match the actual shipped JavaScript bytes.
  import hashlib
  version=hashlib.sha256((root/"assets/js/site.js").read_bytes()).hexdigest()[:12]
  if '/assets/js/site.js?v='+version+'"' not in markup:
   errors.append("Home has stale site.js cache and may hide Amazon")
  if markup.count('class="box editorial-box amazon-feature-box"')!=1:
   errors.append("Home must have exactly one Amazon affiliate box")
  for asset in ("amazon-laptop.svg","amazon-smartphone.svg","amazon-headphones.svg"):
   if not (root/"assets/images"/asset).is_file():
    errors.append("Amazon asset missing: "+asset)
 else:errors.append("Home not found for Amazon showcase verification")
 if not (root/"feed.xml").is_file():errors.append("Required RSS feed missing")
 else:
  from xml.etree.ElementTree import parse
  try:
   parsed=parse(root/"feed.xml").getroot()
   if parsed.tag!="rss" or not parsed.find("./channel/item"):
    errors.append("RSS feed is empty or invalid")
  except Exception as exc:errors.append("RSS XML could not be parsed: "+str(exc))
 if errors:
  raise ValueError("Site route verification failed:\n"+"\n".join(errors[:50]))
 print(f"Route verification successful: {len(documents)} HTML pages, all links resolved, {len(redirects)} safe redirect aliases",flush=True)
