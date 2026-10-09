#!/usr/bin/env python3
"""Generate an RSS 2.0 feed of NEW ordinary News only, for Facebook Autolist."""
import datetime as dt
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from email.utils import format_datetime

ROOT=Path(__file__).resolve().parent.parent
SITE="https://zazoomtek.it"
# Social feed launch: do not bulk-publish the site's existing archive.
START=dt.datetime(2026,10,9,16,44,0,tzinfo=dt.timezone.utc)
MEDIA="http://search.yahoo.com/mrss/"
ET.register_namespace("media", MEDIA)

def load(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def timestamp(s):
    try:
        d=dt.datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return d.replace(tzinfo=dt.timezone.utc) if d.tzinfo is None else d.astimezone(dt.timezone.utc)
    except (ValueError, TypeError):
        return None

def listed_news():
    approved=set()
    for n in range(1,6):
        path=ROOT/("news.html" if n==1 else f"news-{n}.html")
        if not path.exists(): continue
        s=path.read_text(encoding="utf-8")
        a=s.find('<div class="news-list" id="newsList">')
        if a<0: raise RuntimeError("News listing not found in "+path.name)
        b=s.find('</div><nav class="archive-pagination"',a)
        if b<0: raise RuntimeError("News pagination not found in "+path.name)
        approved.update(re.findall(r'href="/(news-[A-Za-z0-9_-]+\.html)"',s[a:b]))
    if not approved: raise RuntimeError("News archive empty: refusing feed overwrite")
    return approved

def main():
    approved=listed_news()
    records={}
    manual=load(ROOT/"manual-news.json",{}).get("items",[])
    for p in manual:
        if not isinstance(p,dict):continue
        slug=p.get("slug","")
        date=timestamp(p.get("published_at"))
        if slug in approved and date and date>START and p.get("kind") not in ("special","political"):
            records[slug]=dict(slug=slug,title=p.get("title",""),body=p.get("excerpt",""),date=date,image=p.get("image",""))
    posts=load(ROOT/".youtube-posts.json",[])
    if not isinstance(posts,list):raise RuntimeError("Community state is invalid")
    for p in posts:
        if not isinstance(p,dict) or p.get("is_review"):continue
        slug="news-"+str(p.get("id",""))+".html"
        date=timestamp(p.get("published_iso"))
        if slug not in approved or not date or date<=START:continue
        title=p.get("title") or re.sub(r"^News:\s*","",str(p.get("text") or "").split("\n")[0],flags=re.I)
        records[slug]=dict(slug=slug,title=title or "News ZazoomTek",body=p.get("text") or "",date=date,image=p.get("image") or "")
    # Metricool may reject an RSS channel with zero items.
    # Add exactly one clearly identified existing standard story as a
    # temporary setup item. It must be removed from the Autolist queue before
    # enabling scheduling; never bulk-import the historical archive.
    if not records:
        eligible=[p for p in manual if isinstance(p,dict)
                  and p.get("slug") in approved
                  and p.get("kind") not in ("special","political")
                  and timestamp(p.get("published_at"))]
        eligible.sort(key=lambda p: timestamp(p.get("published_at")),reverse=True)
        if eligible:
            p=eligible[0]
            records[p["slug"]]=dict(slug=p["slug"],title=p.get("title",""),
                                     body=p.get("excerpt",""),date=timestamp(p["published_at"]),
                                     image=p.get("image",""))
    rss=ET.Element("rss",{"version":"2.0"})
    channel=ET.SubElement(rss,"channel")
    for tag,value in (("title","ZazoomTek | Ultime News"),("link",SITE+"/news.html"),("description","Nuove notizie di tecnologia e gaming pubblicate nella sezione News di ZazoomTek.it."),("language","it-it")):
        ET.SubElement(channel,tag).text=value
    for p in sorted(records.values(),key=lambda v:v["date"],reverse=True)[:40]:
        item=ET.SubElement(channel,"item")
        url=SITE+"/"+p["slug"]
        for tag,value in (("title",str(p["title"])),("link",url),("guid",url),("description",str(p["body"])[:900]),("pubDate",format_datetime(p["date"]))):
            attrs={"isPermaLink":"true"} if tag=="guid" else {}
            ET.SubElement(item,tag,attrs).text=value
        if str(p["image"]).startswith("https://") or str(p["image"]).startswith("/"):
            image=str(p["image"])
            if image.startswith("/"): image=SITE+image
            ET.SubElement(item,"{"+MEDIA+"}content",{"url":image,"medium":"image"})
    output=ET.tostring(rss,encoding="unicode",xml_declaration=True)
    ET.fromstring(output)
    (ROOT/"rss.xml").write_text(output+"\n",encoding="utf-8")
    print(f"Verified rss.xml: {len(records)} News entries, at most one setup sample when no new stories")
if __name__=="__main__":main()
