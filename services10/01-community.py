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
POST_ID=re.compile(r"^[A-Za-z0-9_-]{6,128}$")

def walk(node):
    if isinstance(node,dict):
        yield node
        for child in node.values():yield from walk(child)
    elif isinstance(node,list):
        for child in node:yield from walk(child)

def text(node):
    if isinstance(node,str):return node
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
        def pixel_area(item):
            try:return int(item.get("width") or 0)*int(item.get("height") or 0)
            except (ValueError,TypeError):return 0
        best=max(candidates,key=pixel_area)
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
    m=re.fullmatch(r"(\d+)\s+(second[oi]|minut[oi]|ora|ore|giorn[oi]|settiman[ae])\s+fa",raw)
    if m:
        n=int(m.group(1));unit=m.group(2)
        if unit.startswith("second"):duration=timedelta(seconds=n)
        elif unit.startswith("minut"):duration=timedelta(minutes=n)
        elif unit in ("ore","ora"):duration=timedelta(hours=n)
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
    """Extract public Community posts from supported YouTube bootstrap layouts.

    This parser is intentionally independent of news rendering and video
    metadata. Unknown layouts never delete the previously saved archive.
    """
    candidates=(
        r"(?:var\s+)?ytInitialData\s*=",
        r"""window\[['"]ytInitialData['"]\]\s*=""",
        r"window\.ytInitialData\s*=",
    )
    root=None
    for pattern in candidates:
        marker=re.search(pattern,page)
        if marker is None:continue
        try:
            root,_=json.JSONDecoder().raw_decode(page[marker.end():].lstrip())
            if isinstance(root,dict):break
        except (json.JSONDecodeError,ValueError):
            continue
    if not isinstance(root,dict):
        return []
    found=[];seen=set()
    now=datetime.now(timezone.utc).isoformat()
    for obj in walk(root):
        post=obj.get("backstagePostRenderer") or obj.get("postRenderer") or obj.get("backstagePostThreadRenderer")
        if not isinstance(post,dict):continue
        pid=str(post.get("postId") or post.get("backstagePostId") or post.get("id") or "")
        if not POST_ID.fullmatch(pid) or pid in seen:continue
        body=text(post.get("contentText") or post.get("backstagePostText") or post.get("content") or {}).strip()
        pictures=images_from_post(post)
        # Public polls and image-only posts are also Community posts.
        if not body:
            for item in walk(post):
                if "pollRenderer" in item:
                    poll=item["pollRenderer"]
                    if isinstance(poll,dict):
                        body=text(poll.get("question") or poll.get("questionText") or {})
                    if body:break
        if not body:
            attachment=post.get("backstageAttachment") or post.get("attachment") or {}
            has_video=any("videoRenderer" in node or "reelItemRenderer" in node
                          for node in walk(attachment))
            has_poll=any("pollRenderer" in node and
                         isinstance(node["pollRenderer"],dict) and
                         bool(node["pollRenderer"].get("choices"))
                         for node in walk(post))
            if pictures:
                body="Post fotografico Community YouTube "+pid
            elif has_poll:
                body="Sondaggio Community YouTube "+pid
            elif has_video:
                body="Video condiviso nella Community YouTube "+pid
            else:
                # Save an identified post even if the frontend omitted its text.
                # A later scan can replace the placeholder with complete content.
                body="Contenuto Community YouTube "+pid
        label=text(post.get("publishedTimeText") or post.get("publishedTime") or {})
        seen.add(pid)
        found.append({"id":pid,"title":body.splitlines()[0][:180],
           "text":body,"url":"https://www.youtube.com/post/"+pid,
           "image":pictures[0] if pictures else "",
           "images":pictures,"published":label,
           "published_iso":published_at(label),"first_seen":now})
    return found

def merge(old,new):
    """Merge by stable YouTube post ID without degrading complete older records."""
    by_id={}
    for item in (old if isinstance(old,list) else [])+(new if isinstance(new,list) else []):
        if not isinstance(item,dict) or not POST_ID.fullmatch(str(item.get("id") or "")):
            continue
        ident=item["id"]
        previous=by_id.get(ident,{})
        updated={**previous}
        for key,value in item.items():
            if value in ("",None,[]):continue
            if key=="text" and previous.get("text"):
                old_text=str(previous["text"])
                new_text=str(value)
                placeholder=new_text.startswith((
                    "Contenuto Community YouTube ","Post fotografico Community YouTube ",
                    "Video condiviso nella Community YouTube ","Sondaggio Community YouTube "))
                if placeholder and not old_text.startswith("Contenuto Community YouTube "):
                    continue
                if len(new_text)<len(old_text) and not old_text.startswith("Contenuto Community YouTube "):
                    continue
            if key=="images":
                merged=list(dict.fromkeys(
                    (previous.get("images") or [])+(value if isinstance(value,list) else [])))
                if merged:updated[key]=merged
                continue
            if key in ("first_seen","published_iso") and previous.get(key):
                # Publication dates from relative labels must not drift on rescans.
                continue
            updated[key]=value
        if updated.get("images") and not updated.get("image"):
            updated["image"]=updated["images"][0]
        by_id[ident]=updated
    return sorted(by_id.values(),key=lambda p:str(p.get("published_iso") or p.get("first_seen") or ""),reverse=True)

def main():
    try:
        previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
        if not isinstance(previous,list):previous=[]
    except (OSError,ValueError):previous=[]
    # Repair previously archived posts labelled '1 giorno fa' / '1 settimana
    # fa' whose original importer omitted the ISO timestamp. Anchor to the
    # FIRST collection time; never falsely date them as today's posts.
    for post in previous:
        if not isinstance(post,dict) or post.get("published_iso") or not post.get("published"):
            continue
        try:
            anchor=datetime.fromisoformat(str(post["first_seen"]).replace("Z","+00:00"))
        except (KeyError,ValueError,TypeError):
            anchor=datetime.now(timezone.utc)
        iso=published_at(post["published"],now=anchor)
        if iso:post["published_iso"]=iso
    discovered=[]
    urls=(f"https://www.youtube.com/@{HANDLE.lstrip('@')}/posts",
          f"https://www.youtube.com/@{HANDLE.lstrip('@')}/community",
          f"https://www.youtube.com/channel/{CHANNEL}/community")
    for url in urls:
        for attempt in range(2):
            try:
                request=urllib.request.Request(url,headers={
                    "User-Agent":"Mozilla/5.0 (compatible; ZazoomTekCommunity/1.0)",
                    "Accept-Language":"it-IT,it;q=0.9",
                    "Cache-Control":"no-cache",
                    "Accept":"text/html,application/xhtml+xml"})
                with urllib.request.urlopen(request,timeout=20) as response:
                    page=response.read().decode("utf-8","replace")
                parsed=extract(page)
                discovered=merge(discovered,parsed)
                if parsed:break
                print("Community page returned no recognized posts:",url)
            except Exception as exc:
                print("Community source unavailable:",url,"attempt:",attempt+1,
                      "reason:",type(exc).__name__)
    if not discovered:
        print("Community source returned no parseable posts; retaining",
              len(previous),"archived records; current coverage unverified")
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
