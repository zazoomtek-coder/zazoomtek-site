#!/usr/bin/env python3
"""Independent best-effort importer of WRITTEN YouTube Community posts.

Collects public text, image galleries and published labels from the channel's
Community pages. Never imports Shorts/videos through this pipeline. Missing
YouTube data must not erase the previously collected archive.
"""
from __future__ import annotations
import html
import json
import os
import re
import tempfile
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"services10-data"/"community.json"
HANDLE=os.environ.get("ZT_YOUTUBE_HANDLE","ZazoomTek")
CHANNEL=os.environ.get("ZT_YOUTUBE_CHANNEL_ID","UCJs0ZT10hUiPRD0UZtUpI1Q")
POST_ID=re.compile(r"^Ugkx[A-Za-z0-9_-]{5,100}$")

def walk(node):
    if isinstance(node,dict):
        yield node
        for child in node.values():yield from walk(child)
    elif isinstance(node,list):
        for child in node:yield from walk(child)

def text(node):
    if not isinstance(node,dict):return ""
    if node.get("simpleText") is not None:
        return str(node["simpleText"])
    runs=node.get("runs") or []
    return "".join(str(x.get("text","")) for x in runs if isinstance(x,dict))

def normalized_image(url):
    value=html.unescape(str(url or "").replace("\\u0026","&"))
    if not value.startswith("https://"):return ""
    if "yt3.ggpht.com/" in value:
        value=re.sub(r"=s\d+(?:-[^?]*)?$","=s1600-rw-nd-v1",value)
    return value

def images_from_post(post):
    urls=[];seen=set()
    attachment=post.get("backstageAttachment") or post.get("attachment") \
        or post.get("postMultiImageRenderer") or {}
    for obj in walk(attachment):
        thumbs=obj.get("thumbnails") if isinstance(obj,dict) else None
        if not isinstance(thumbs,list):continue
        candidates=[v for v in thumbs if isinstance(v,dict) and
                    str(v.get("url") or "").startswith("https://")]
        if not candidates:continue
        best=max(candidates,key=lambda x:int(x.get("width") or 0)*
                 int(x.get("height") or 0))
        url=normalized_image(best.get("url"))
        # Thumbnail resizing variants are the same photo, not extra images.
        identity=re.sub(r"=s\d+.*$","",url)
        if url and identity not in seen:
            seen.add(identity);urls.append(url)
    return urls

def published_at(label,now=None):
    """Best-effort chronology; preserve originals if YouTube only shows labels."""
    raw=str(label or "").strip().lower()
    if not raw:return ""
    if re.match(r"^\d{4}-\d\d-\d\d(?:T.*)?$",raw):return raw
    now=now or datetime.now(timezone.utc)
    relative={"ieri":timedelta(days=1),
              "un'ora fa":timedelta(hours=1),"un’ora fa":timedelta(hours=1),
              "un giorno fa":timedelta(days=1),
              "un minuto fa":timedelta(minutes=1)}
    duration=relative.get(raw)
    m=re.fullmatch(r"(\d+)\s+(secondi?|minuti?|ore|giorni?|settimane?)\s+fa",raw)
    if m:
        n=int(m.group(1));unit=m.group(2)
        if unit.startswith("second"):duration=timedelta(seconds=n)
        elif unit.startswith("minut"):duration=timedelta(minutes=n)
        elif unit=="ore":duration=timedelta(hours=n)
        elif unit.startswith("giorn"):duration=timedelta(days=n)
        elif unit.startswith("settiman"):duration=timedelta(weeks=n)
    if duration is not None:
        return (now-duration).replace(microsecond=0).isoformat()
    months={m:i+1 for i,m in enumerate(
        "gennaio febbraio marzo aprile maggio giugno luglio agosto settembre ottobre novembre dicembre".split())}
    m=re.fullmatch(r"(\d{1,2})\s+([a-zà-ÿ]+)\s+(\d{4})",raw)
    if m and m.group(2) in months:
        try:return datetime(int(m.group(3)),months[m.group(2)],int(m.group(1)),
                            tzinfo=timezone.utc).date().isoformat()
        except ValueError:pass
    return ""

def extract(page):
    marker=re.search(r"(?:var\s+ytInitialData\s*=|window\[[\"']ytInitialData[\"']\]\s*=)\s*",page)
    if not marker:return []
    try:root,_=json.JSONDecoder().raw_decode(page[marker.end():].lstrip())
    except (json.JSONDecodeError,ValueError):return []
    found=[];seen=set()
    for obj in walk(root):
        post=obj.get("backstagePostRenderer") or obj.get("postRenderer")
        if not isinstance(post,dict):continue
        pid=str(post.get("postId") or post.get("backstagePostId") or post.get("id") or "")
        if not POST_ID.fullmatch(pid) or pid in seen:continue
        body=text(post.get("contentText") or post.get("backstagePostText") or post.get("content") or {}).strip()
        # Text is mandatory. Other YouTube uploads are owned by the video importer.
        if not body:continue
        seen.add(pid)
        pictures=images_from_post(post)
        label=text(post.get("publishedTimeText") or {})
        now=datetime.now(timezone.utc).isoformat()
        found.append({"id":pid,"title":body.splitlines()[0][:180],
           "text":body,"url":"https://www.youtube.com/post/"+pid,
           "image":pictures[0] if pictures else "",
           "images":pictures,"published":label,
           "published_iso":published_at(label),"first_seen":now})
    return found

def merge(old,new):
    by_id={}
    for item in (old if isinstance(old,list) else [])+(new if isinstance(new,list) else []):
        if not isinstance(item,dict) or not POST_ID.fullmatch(str(item.get("id") or "")):continue
        prior=by_id.get(item["id"],{})
        updated={**prior}
        updated.update({key:value for key,value in item.items() if value not in ("",None,[])})
        if prior.get("first_seen"):updated["first_seen"]=prior["first_seen"]
        if prior.get("published_iso") and not prior.get("published_iso","").startswith("2026-10-23T"):
            # Preserve a stable original date when a later relative label changes.
            updated["published_iso"]=prior["published_iso"]
        if prior.get("images") and not item.get("images"):
            updated["images"]=prior["images"]
        by_id[item["id"]]=updated
    return list(by_id.values())

def main():
    try:
        previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
        if not isinstance(previous,list):previous=[]
    except (OSError,ValueError):previous=[]
    discovered=[]
    urls=(f"https://www.youtube.com/@{HANDLE.lstrip('@')}/posts",
          f"https://www.youtube.com/@{HANDLE.lstrip('@')}/community",
          f"https://www.youtube.com/channel/{CHANNEL}/community")
    for url in urls:
        try:
            request=urllib.request.Request(url,headers={
                "User-Agent":"Mozilla/5.0",
                "Accept-Language":"it-IT,it;q=0.9",
                "Cache-Control":"no-cache"})
            with urllib.request.urlopen(request,timeout=20) as response:
                page=response.read().decode("utf-8","replace")
            discovered=merge(discovered,extract(page))
        except Exception as exc:
            print("Community source temporarily unavailable:",str(exc)[:120])
    if not discovered:
        print("Community unavailable: retaining",len(previous),"existing posts")
        return
    result=merge(previous,discovered)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",
                                     dir=OUT.parent,delete=False) as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        name=stream.name
    os.replace(name,OUT)
    print("Community written posts observed:",len(discovered),"archived:",len(result))
if __name__=="__main__":
    main()
