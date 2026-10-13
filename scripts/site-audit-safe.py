#!/usr/bin/env python3
"""Read-only whole-site safety audit. No file is written or deployed."""
import collections
import html.parser
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT=Path(__file__).resolve().parent.parent
PAGES=sorted(p for p in ROOT.glob("*.html") if not p.name.startswith("preview-"))
FILES={p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts}
NAV_EXPECTED={"Home","News","Recensioni","Guide","Tech Impact","Gaming Inside","Community","Video"}

class Inspect(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs=[];self.media=[];self.canonicals=[];self.figcaption=0;self.images=0;self.missing_alt=0
        self.title="";self.title_on=False;self.navcount=0;self.links_count=0
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=="title":self.title_on=True
        if tag=="nav":self.navcount+=1
        if tag=="figcaption":self.figcaption+=1
        if tag=="a" and a.get("href"):
            self.hrefs.append(a["href"]);self.links_count+=1
        if tag=="img":
            self.images+=1
            if not a.get("alt"):self.missing_alt+=1
            for key in ("src","data-src"):
                if a.get(key):self.media.append(a[key])
        if tag=="script" and a.get("src"):self.media.append(a["src"])
        if tag=="link":
            if a.get("rel")=="canonical" and a.get("href"):self.canonicals.append(a["href"])
            if a.get("href") and (a.get("rel") or "").lower() in ("stylesheet","icon","preload"):self.media.append(a["href"])
    def handle_endtag(self,tag):
        if tag=="title":self.title_on=False
    def handle_data(self,data):
        if self.title_on:self.title+=data

def local_path(value):
    value=(value or "").strip()
    if not value or value.startswith(("data:","mailto:","tel:","javascript:","#","//")):return None
    parts=urlsplit(value)
    if parts.scheme and parts.netloc not in ("zazoomtek.it","www.zazoomtek.it"):return None
    raw=unquote(parts.path)
    if raw.startswith("/"):relative=raw.lstrip("/")
    else:relative=raw
    if not relative or raw.endswith("/"):relative=relative.rstrip("/")+"/index.html" if relative else "index.html"
    if ".." in Path(relative).parts:return None
    if relative.startswith(("api/","__/")):return None
    return relative

broken_media=[];broken_links=[];duplicate_canonical=collections.defaultdict(list)
no_canonical=[];bad_canonical=[];missing_alt=[];image_captions=[]
empty_titles=[];feed_reviews=[];pages_by_category=collections.Counter()
for p in PAGES:
    markup=p.read_text(encoding="utf-8",errors="replace")
    obj=Inspect();obj.feed(markup)
    name=p.name
    if not obj.title.strip():empty_titles.append(name)
    if not obj.canonicals:no_canonical.append(name)
    for canonical in obj.canonicals:
        if not canonical.startswith("https://zazoomtek.it/"):bad_canonical.append((name,canonical))
        duplicate_canonical[canonical].append(name)
    if obj.missing_alt:missing_alt.append((name,obj.missing_alt))
    if obj.figcaption:image_captions.append((name,obj.figcaption))
    for value in obj.media:
        path=local_path(value)
        if path and path not in FILES:
            broken_media.append((name,path))
    for value in obj.hrefs:
        path=local_path(value)
        if path and path not in FILES:
            broken_links.append((name,path))
    if name.startswith("news-"):pages_by_category["news"]+=1
    elif name.startswith("tech-impact-"):pages_by_category["tech-impact"]+=1
    elif name.startswith("gaming-inside-"):pages_by_category["gaming-inside"]+=1
    elif "recensione" in name:pages_by_category["recensioni"]+=1
    if "ARTICLE_FEED_START" in markup and "ARTICLE_FEED_END" in markup:
        segment=markup.split("<!-- ARTICLE_FEED_START -->",1)[1].split("<!-- ARTICLE_FEED_END -->",1)[0]
        if re.search(r'<article\b[^>]*class="article-row"[^>]*>[\s\S]*?href="/?recensione-',segment):
            feed_reviews.append(name)
features=json.loads((ROOT/"featured-carousel.json").read_text(encoding="utf-8")).get("items",[])
specials=json.loads((ROOT/"special-featured.json").read_text(encoding="utf-8")).get("items",[])
standard=json.loads((ROOT/"standard-news.json").read_text(encoding="utf-8")).get("articles",[])
urls=[x.get("url","") for x in features]
counts=collections.Counter(x.get("section") for x in features)
report={
    "pages":len(PAGES),"file_total":len(FILES),
    "categories":dict(pages_by_category),
    "featured":{"total":len(features),"counts":dict(counts),"unique_urls":len(set(urls)),
                "broken_urls":[u for u in urls if (local_path(u) or "") not in FILES]},
    "standard_news_count":len(standard),"special_selected_count":len(specials),
    "news_feed_has_reviews":feed_reviews,
    "broken_media":{"count":len(broken_media),"unique":len(set(x[1] for x in broken_media)),"samples":broken_media[:25]},
    "broken_links":{"count":len(broken_links),"unique":len(set(x[1] for x in broken_links)),"samples":broken_links[:30]},
    "duplicate_canonicals":{k:v[:7] for k,v in duplicate_canonical.items() if len(v)>1},
    "no_canonical":{"count":len(no_canonical),"samples":no_canonical[:12]},
    "bad_canonical":{"count":len(bad_canonical),"samples":bad_canonical[:10]},
    "pages_without_title":empty_titles[:12],
    "missing_image_alt":{"pages":len(missing_alt),"samples":missing_alt[:14]},
    "image_captions":{"pages":len(image_captions),"total":sum(x[1] for x in image_captions),"samples":image_captions[:14]}
}
print("SITE_AUDIT_JSON_BEGIN")
print(json.dumps(report,ensure_ascii=False,indent=2))
print("SITE_AUDIT_JSON_END")
