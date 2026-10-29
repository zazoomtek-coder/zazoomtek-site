"""End-to-end SEO audit: every generated article, archive and canonical page."""
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
import json,re
from seo import DOMAIN,metadata,full_image,keywords,description

class MetaParser(HTMLParser):
 def __init__(self):
  super().__init__()
  self.title=""
  self.current_title=False
  self.meta={}
  self.links=[]
  self.ld=[]
  self.script=False
  self.text=""
  self.h1=0
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag=="title":self.current_title=True
  if tag=="meta":
   k=attrs.get("name") or attrs.get("property")
   if k:self.meta[k]=attrs.get("content","")
  if tag=="link":self.links.append(attrs)
  if tag=="script" and attrs.get("type")=="application/ld+json":
   self.script=True
   self.text=""
  if tag=="h1":self.h1+=1
 def handle_endtag(self,tag):
  if tag=="title":self.current_title=False
  if tag=="script" and self.script:
   try:self.ld.append(json.loads(self.text))
   except ValueError:self.ld.append({"invalid":self.text[:160]})
   self.script=False
 def handle_data(self,data):
  if self.current_title:self.title+=data
  if self.script:self.text+=data

def check_seo(root,rows,groups,preview):
 root=Path(root)
 ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
 document=ET.parse(root/"sitemap.xml").getroot()
 urls=[x.text for x in document.findall(".//sm:url/sm:loc",ns)]
 if not urls:raise AssertionError("Sitemap contains zero indexed URLs")
 if len(urls)!=len(set(urls)):raise AssertionError("Sitemap duplicate canonical URL")
 if any(not x.startswith(DOMAIN+"/") for x in urls):
  raise AssertionError("Sitemap includes noncanonical URL")
 if (DOMAIN+"/404") in urls:raise AssertionError("404 must not be in sitemap")
 count=0
 bad=[]
 for page in root.glob("*.html"):
  parser=MetaParser()
  parser.feed(page.read_text(encoding="utf-8"))
  path="/" if page.stem=="index" else "/"+page.stem
  expected=DOMAIN+path if path!="/" else DOMAIN+"/"
  if page.stem=="404":continue
  if not parser.title or len(parser.title)>125:bad.append((page.name,"missing/overlong title"))
  if page.stem=="index" and parser.h1!=1:
   bad.append((page.name,"Home must have exactly one semantic H1"))
  archive_page=re.search(r"-page-(\d+)$",page.stem)
  if archive_page and ("Pagina "+archive_page.group(1)) not in parser.title:
   bad.append((page.name,"Paginated archive title missing page number"))
  if page.stem=="index":
   html=page.read_text(encoding="utf-8")
   for archive in ("/recensioni-tech","/recensioni-gaming","/video"):
    if ('href="'+archive+'"') not in html:
     bad.append((page.name,"Missing crawlable internal archive link "+archive))
  if not (40<=len(parser.meta.get("description",""))<=300):
   bad.append((page.name,"description missing or poor length"))
  if parser.meta.get("og:title")!=parser.title:
   bad.append((page.name,"OG headline mismatch"))
  if parser.meta.get("og:description")!=parser.meta.get("description"):
   bad.append((page.name,"OG description mismatch"))
  if parser.meta.get("og:url")!=expected:
   bad.append((page.name,"OG canonical mismatch"))
  canonicals=[x.get("href") for x in parser.links if x.get("rel")=="canonical"]
  if canonicals!=[expected]:bad.append((page.name,"canonical missing or duplicates"))
  if path.startswith("/notizia-web-"):
   if expected in urls:bad.append((page.name,"Thin external-link gateway included in sitemap"))
   if "noindex" not in parser.meta.get("robots",""):
    bad.append((page.name,"External gateway must be noindex"))
  elif expected not in urls:
   bad.append((page.name,"missing sitemap URL"))
  if not parser.ld or any("invalid" in x for x in parser.ld):
   bad.append((page.name,"missing/invalid structured data"))
  if preview and "noindex" not in parser.meta.get("robots",""):
   bad.append((page.name,"Preview is not noindex"))
  if not preview and not path.startswith("/notizia-web-") and "max-image-preview:large" not in parser.meta.get("robots",""):
   bad.append((page.name,"Production discover image preview missing"))
  count+=1
 for row in rows:
  p=root/(row["slug"]+".html")
  parser=MetaParser()
  parser.feed(p.read_text(encoding="utf-8"))
  item=next((x for x in parser.ld if x.get("@type") in ("Article","NewsArticle","Review")),None)
  if not item:bad.append((p.name,"no article schema"))
  if str(row.get("category") or "").startswith("recensioni-"):
   from article_templates import score as actual_score,paragraphs
   rating=actual_score(row,paragraphs(row))
   if rating is not None and float(rating.replace(",","."))>0 and (not item or item.get("@type")!="Review"):
    bad.append((p.name,"Visible review vote missing Review schema"))
  else:
   if item.get("description")!=parser.meta.get("description"):
    bad.append((p.name,"Article structured description mismatch"))
   if not keywords(row) or not item.get("keywords"):
    bad.append((p.name,"No content-derived topic"))
   if item.get("image") and item["image"][0]!=full_image(row.get("image")):
    bad.append((p.name,"Incorrect original cover URL"))
 if bad:
  raise AssertionError("SEO audit FAILED "+str(len(bad))+" violations: "+"; ".join(str(x) for x in bad[:22]))
 robots=(root/"robots.txt").read_text(encoding="utf-8")
 if preview and "Disallow: /" not in robots:raise AssertionError("Preview not disallowed")
 if not preview and DOMAIN+"/sitemap.xml" not in robots:raise AssertionError("Production sitemap not advertised")
 print("SEO AUDIT PASS:",count,"HTML pages and",len(urls),"canonical sitemap URLs",flush=True)
