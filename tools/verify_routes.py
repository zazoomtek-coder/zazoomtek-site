"""Fail deployment if any internal page link or redirect is broken/circular."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote

class LinkReader(HTMLParser):
 def __init__(self):
  super().__init__()
  self.hrefs=[]
 def handle_starttag(self,tag,attrs):
  if tag not in ("a","link"):return
  href=dict(attrs).get("href")
  if href:self.hrefs.append(href)

def check_dist(root):
 root=Path(root)
 documents=list(root.glob("*.html"))
 real_pages={p.stem for p in documents}
 real_pages.discard("index")
 errors=[]
 # Pages interprets /slug as dist/slug.html and normalizes /slug.html -> /slug.
 def pretty(path):
  return path.removesuffix(".html").rstrip("/") or "/"
 for doc in documents:
  reader=LinkReader()
  reader.feed(doc.read_text(encoding="utf-8"))
  for href in reader.hrefs:
   u=urlsplit(href)
   if u.scheme or u.netloc or not href.startswith("/"):continue
   path=unquote(u.path)
   if path.startswith("/assets/"):
    if not (root/path.lstrip("/")).is_file():errors.append(f"{doc.name} links to missing asset {path}")
    continue
   if path=="/":continue
   if path=="/feed.xml":
    if not (root/"feed.xml").is_file():errors.append("RSS feed missing: /feed.xml")
    continue
   if path.endswith(".html"):
    errors.append(f"{doc.name} uses noncanonical .html URL: {path}")
   route=pretty(path)
   if route.lstrip("/") not in real_pages:
    errors.append(f"{doc.name} links to absent page {route}")
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
 # Explicitly verify all four legal pages and editorial archives.
 for name in ("news","news-tech","news-gaming","recensioni","recensioni-tech",
              "recensioni-gaming","guide","speciali","extra","privacy-policy",
              "cookie-policy","disclaimer","note-legali","contatti"):
  if name not in real_pages:errors.append("Required page missing: /"+name)
 # Internal search and breaking news datasets must resolve to actual published articles.
 for name,key in (("search-index.json","articles"),("news-ticker.json","items")):
  target=root/name
  if not target.is_file():
   errors.append("Missing discovery dataset: "+name)
   continue
  try:
   import json
   payload=json.loads(target.read_text(encoding="utf-8"))
   entries=payload.get(key)
   if not isinstance(entries,list):raise ValueError("Expected JSON array "+key)
   if name=="search-index.json" and not entries:
    raise ValueError("Search index is empty")
   if name=="news-ticker.json" and len(entries)<10:
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
