"""End-to-end SEO audit: every generated article, archive and canonical page."""
from html.parser import HTMLParser
from datetime import datetime,timezone,timedelta
from pathlib import Path
from xml.etree import ElementTree as ET
from urllib.parse import urlparse
import json,re
from seo import DOMAIN,metadata,full_image,keywords,description
from article_routes import build_article_url, CATEGORY_PREFIX
from editorial_scope import imported_ids, is_release_critical

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
  self.current_h1=False
  self.h1_text=""
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
  if tag=="h1":self.h1+=1;self.current_h1=True
 def handle_endtag(self,tag):
  if tag=="title":self.current_title=False
  if tag=="h1":self.current_h1=False
  if tag=="script" and self.script:
   try:self.ld.append(json.loads(self.text))
   except ValueError:self.ld.append({"invalid":self.text[:160]})
   self.script=False
 def handle_data(self,data):
  if self.current_title:self.title+=data
  if self.current_h1:self.h1_text+=data
  if self.script:self.text+=data

def check_seo(root,rows,groups,preview):
 root=Path(root)
 strict_ids=imported_ids(root.parent)
 bad=[]
 warnings=[]
 def page_is_critical(page):
  rel=page.relative_to(root).with_suffix("").as_posix()
  if rel=="index":return True
  parts=rel.split("/")
  if len(parts)>1 and parts[0] in set(CATEGORY_PREFIX.values()):return True
  stem=parts[-1]
  archives={"recensioni","news","speciali","guide","extra","news-tech","news-gaming",
            "recensioni-tech","recensioni-gaming"}
  return stem in archives or any(stem.startswith(name+"-page-") or stem.startswith(name+"-archivio")
                                 for name in archives)
 def page_issue(page,issue):
  (bad if page_is_critical(page) else warnings).append(issue)
 def path_is_critical(path):
  route=str(path or "").lstrip("/")
  return route.split("/",1)[0] in set(CATEGORY_PREFIX.values()) or route in ("recensioni","news","speciali","guide","extra")
 ns={"sm":"http://www.sitemaps.org/schemas/sitemap/0.9"}
 document=ET.parse(root/"sitemap.xml").getroot()
 urls=[x.text for x in document.findall(".//sm:url/sm:loc",ns)]
 if not urls:raise AssertionError("Sitemap contains zero indexed URLs")
 if len(urls)!=len(set(urls)):raise AssertionError("Sitemap contains duplicate canonical URLs")
 for value in urls:
  path=urlparse(value).path
  if not value.startswith(DOMAIN) or "//" in path or path.endswith(".html") or (path!="/" and path.endswith("/")):
   raise AssertionError("Noncanonical sitemap URL: "+str(value))
 news_doc=ET.parse(root/"news-sitemap.xml").getroot()
 news_urls=[x.text for x in news_doc.findall(".//sm:url/sm:loc",ns)]
 if len(news_urls)!=len(set(news_urls)):raise AssertionError("News sitemap contains duplicate URLs")
 if any(url not in urls for url in news_urls):
  raise AssertionError("News sitemap contains a URL absent from the main sitemap")
 for value in news_urls:
  path=urlparse(value).path
  if not value.startswith(DOMAIN) or "//" in path or path.endswith(".html") or path.endswith("/"):
   raise AssertionError("Noncanonical Google News sitemap URL: "+str(value))
 # Fail a release when the sitemap references a missing, noindex or mismatched page.
 # Old deleted URLs are NOT reintroduced just to satisfy Search Console.
 for sitemap_url in urls:
  rel=sitemap_url.removeprefix(DOMAIN).strip("/")
  target=root/("index.html" if not rel else rel+".html")
  if not target.is_file():
   path=urlparse(sitemap_url).path
   message="Sitemap references missing generated page: "+sitemap_url
   (bad if path.lstrip("/").split("/",1)[0] in set(CATEGORY_PREFIX.values()) or path.lstrip("/") in ("recensioni","news","speciali","guide","extra") else warnings).append(message)
   continue
  meta=MetaParser()
  meta.feed(target.read_text(encoding="utf-8"))
  if not preview and "noindex" in meta.meta.get("robots","").lower():
   message="Sitemap references noindex page: "+sitemap_url
   (bad if path_is_critical(urlparse(sitemap_url).path) else warnings).append(message)
  page_canon=[x.get("href") for x in meta.links if x.get("rel")=="canonical"]
  if page_canon!=[sitemap_url]:
   path=urlparse(sitemap_url).path
   message="Sitemap canonical mismatch: "+sitemap_url
   (bad if path.lstrip("/").split("/",1)[0] in set(CATEGORY_PREFIX.values()) or path.lstrip("/") in ("recensioni","news","speciali","guide","extra") else warnings).append(message)

 # Google News sitemap is a strict subset of canonical, indexable site articles.
 news_doc=ET.parse(root/"news-sitemap.xml").getroot()
 news_ns={"news":"http://www.google.com/schemas/sitemap-news/0.9"}
 news_links=[]
 now=datetime.now(timezone.utc)
 for entry in news_doc.findall("sm:url",ns):
  url=entry.findtext("sm:loc",namespaces=ns)
  stamp=entry.findtext("news:news/news:publication_date",namespaces=news_ns)
  title=entry.findtext("news:news/news:title",namespaces=news_ns)
  name=entry.findtext("news:news/news:publication/news:name",namespaces=news_ns)
  language=entry.findtext("news:news/news:publication/news:language",namespaces=news_ns)
  if url not in urls or not stamp or not title or name!="ZazoomTek" or language!="it":
   raise AssertionError("Invalid Google News sitemap entry: "+str(url))
  date=datetime.fromisoformat(stamp.replace("Z","+00:00"))
  if date.tzinfo is None or not now-timedelta(days=2,minutes=2)<=date<=now+timedelta(minutes=2):
   raise AssertionError("Google News sitemap must contain only recent publications: "+str(url))
  if url not in {DOMAIN+build_article_url(r) for r in rows if r.get("category") in ("news-tech","news-gaming")}:
   raise AssertionError("Google News sitemap contains a non-news article: "+str(url))
  news_links.append(url)
 if len(news_links)!=len(set(news_links)):
  raise AssertionError("Google News sitemap duplicates an article")
 if len(urls)!=len(set(urls)):raise AssertionError("Sitemap duplicate canonical URL")
 if any(not x.startswith(DOMAIN+"/") for x in urls):
  raise AssertionError("Sitemap includes noncanonical URL")
 if (DOMAIN+"/404") in urls:raise AssertionError("404 must not be in sitemap")
 count=0
 for page in root.rglob("*.html"):
  if page.relative_to(root).parts[0] in ("studio","studio-v2"):
   continue
  parser=MetaParser()
  parser.feed(page.read_text(encoding="utf-8"))
  path="/" if page.relative_to(root).as_posix()=="index.html" else "/"+page.relative_to(root).with_suffix("").as_posix()
  expected=DOMAIN+path if path!="/" else DOMAIN+"/"
  if page.stem=="404":continue
  if not parser.title or len(parser.title)>125:page_issue(page,(page.name,"missing/overlong title"))
  if page.stem=="index" and parser.h1!=1:
   page_issue(page,(page.name,"Home must have exactly one semantic H1"))
  archive_page=re.search(r"-page-(\d+)$",page.stem)
  if archive_page and ("Pagina "+archive_page.group(1)) not in parser.title:
   page_issue(page,(page.name,"Paginated archive title missing page number"))
  if page.stem=="index":
   html=page.read_text(encoding="utf-8")
   for archive in ("/recensioni-tech","/recensioni-gaming","/video"):
    if ('href="'+archive+'"') not in html:
     page_issue(page,(page.name,"Missing crawlable internal archive link "+archive))
  if not (40<=len(parser.meta.get("description",""))<=300):
   page_issue(page,(page.name,"description missing or poor length"))
  if parser.meta.get("og:title")!=parser.title:
   page_issue(page,(page.name,"OG headline mismatch"))
  if parser.meta.get("og:description")!=parser.meta.get("description"):
   page_issue(page,(page.name,"OG description mismatch"))
  if parser.meta.get("og:url")!=expected:
   page_issue(page,(page.name,"OG canonical mismatch"))
  canonicals=[x.get("href") for x in parser.links if x.get("rel")=="canonical"]
  if canonicals!=[expected]:page_issue(page,(page.name,"canonical missing or duplicates"))
  if path.startswith("/notizia-web-"):
   if expected in urls:page_issue(page,(page.name,"Thin external-link gateway included in sitemap"))
   if "noindex" not in parser.meta.get("robots",""):
    page_issue(page,(page.name,"External gateway must be noindex"))
  elif expected not in urls:
   page_issue(page,(page.name,"missing sitemap URL"))
  if not parser.ld or any("invalid" in x for x in parser.ld):
   page_issue(page,(page.name,"missing/invalid structured data"))
  if preview and "noindex" not in parser.meta.get("robots",""):
   page_issue(page,(page.name,"Preview is not noindex"))
  if not preview and expected in urls and "noindex" in parser.meta.get("googlebot","").lower():
   page_issue(page,(page.name,"Googlebot is blocked on a sitemap URL"))
  if not preview and expected in urls and "noindex" in parser.meta.get("robots","").lower():
   page_issue(page,(page.name,"Sitemap URL is noindex"))
  if not preview and not path.startswith("/notizia-web-") and "max-image-preview:large" not in parser.meta.get("robots",""):
   page_issue(page,(page.name,"Production discover image preview missing"))
  count+=1
 for category in ("recensioni","news","speciali","guide","extra"):
  page=root/(category+".html")
  if not page.is_file():
   bad.append((category,"category archive file missing"))
   continue
  parser=MetaParser();parser.feed(page.read_text(encoding="utf-8"))
  expected=DOMAIN+"/"+category
  canonicals=[x.get("href") for x in parser.links if x.get("rel")=="canonical"]
  if canonicals!=[expected]:bad.append((category,"category archive canonical mismatch"))
  if parser.h1!=1 or not parser.h1_text.strip():bad.append((category,"category archive H1 missing"))
  if not parser.title or not parser.title.startswith(parser.h1_text.strip()):
   bad.append((category,"category archive title is not coherent with H1"))
  if expected not in urls:bad.append((category,"category archive missing from sitemap"))
 for row in rows:
  p=root/(build_article_url(row).lstrip("/")+".html")
  critical=is_release_critical(row,strict_ids)
  if not p.is_file():
   (bad if critical else warnings).append((p.as_posix(),"article HTML missing"))
   continue
  parser=MetaParser()
  parser.feed(p.read_text(encoding="utf-8"))
  item=next((x for x in parser.ld if x.get("@type") in ("Article","NewsArticle","Review")),None)
  article_issue=lambda message: (bad if critical else warnings).append((p.as_posix(),message))
  if not item:article_issue("no article schema")
  if row.get("route_version") in (2,"2","v2"):
   crumbs=next((x for x in parser.ld if x.get("@type")=="BreadcrumbList"),{})
   elements=crumbs.get("itemListElement",[])
   if len(elements)!=3:article_issue("v2 article must have a three-level BreadcrumbList")
   else:
    parent=CATEGORY_PREFIX.get(row.get("category"))
    if elements[1].get("item")!=DOMAIN+"/"+str(parent):
     article_issue("breadcrumb parent does not match public category")
  if str(row.get("category") or "").startswith("recensioni-"):
   from article_templates import score as actual_score,paragraphs
   rating=actual_score(row,paragraphs(row))
   if rating is not None and float(rating.replace(",","."))>0 and (not item or item.get("@type")!="Review"):
    article_issue("Visible review vote missing Review schema")
  else:
   if item.get("description")!=parser.meta.get("description"):
    article_issue("Article structured description mismatch")
   if not keywords(row) or not item.get("keywords"):
    article_issue("No content-derived topic")
   if item.get("image") and item["image"][0]!=full_image(row.get("image")):
    article_issue("Incorrect original cover URL")
 for warning in warnings:
  print("WARNING: historical SEO diagnostic:",warning,flush=True)
 if bad:
  raise AssertionError("SEO audit FAILED "+str(len(bad))+" release-critical violations: "+"; ".join(str(x) for x in bad[:22]))
 robots=(root/"robots.txt").read_text(encoding="utf-8")
 if preview and "Disallow: /" not in robots:raise AssertionError("Preview not disallowed")
 if not preview and DOMAIN+"/sitemap.xml" not in robots:raise AssertionError("Production sitemap not advertised")
 if not preview and DOMAIN+"/news-sitemap.xml" not in robots:raise AssertionError("Google News sitemap not advertised")
 print("SEO AUDIT PASS:",count,"HTML pages and",len(urls),"canonical sitemap URLs",flush=True)
