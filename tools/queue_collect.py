#!/usr/bin/env python3
"""Accumulate original ZazoomTek YouTube records on the non-deploying editorial-queue branch."""
from datetime import datetime, timezone, time as datetime_time
from zoneinfo import ZoneInfo
from pathlib import Path
import json
import os
import re
import urllib.request
import time as time_module
import xml.etree.ElementTree as ET
from community_youtube import discover, title_type
from sync_videos import CHANNEL_ID, NS, classify

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
ROME=ZoneInfo("Europe/Rome")

def classify_upload(title):
    """Keep every authentic channel upload for Ultimi Video, not only reviews."""
    original=classify(title)
    if original:return original
    low=title.casefold()
    if "short" in low:return "short","general"
    if "gameplay" in low:return "gameplay","gaming"
    if "trailer" in low:return "trailer","gaming"
    return "video","general"

def write_if_changed(path, payload):
    value=json.dumps(payload,ensure_ascii=False,indent=2)+"\n"
    if not path.exists() or path.read_text(encoding="utf-8")!=value:
        path.write_text(value,encoding="utf-8")
        return True
    return False

def load(name,key):
    path=DATA/name
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (UnicodeError,ValueError) as error:
        raise RuntimeError("Refusing to overwrite damaged queue snapshot: "+name) from error
    if not isinstance(obj,dict) or not isinstance(obj.get(key),list):
        raise RuntimeError("Invalid queue snapshot structure: "+name)
    return obj[key]

def in_intake_window(clock):
    return (
        datetime_time(9,0)<=clock<=datetime_time(12,20) or
        datetime_time(12,31)<=clock<=datetime_time(15,50) or
        datetime_time(16,1)<=clock<=datetime_time(19,20)
    )

def ingest(now=None):
    now=now or datetime.now(timezone.utc)
    local=now.astimezone(ROME)
    clock=local.time()
    # Leave a ten-minute import cutoff before each of the three release slots.
    intake_windows=in_intake_window(clock)
    if not intake_windows and os.environ.get("ZAZOOMTEK_FORCE_COLLECT") != "1":
        print("Outside editorial intake window, nothing changed:",local.isoformat())
        return False
    if not intake_windows:
        print("EDITORIAL QUEUE RECOVERY ONLY (NO DEPLOY) at",local.isoformat(),flush=True)
    stamp=now.isoformat(timespec="seconds")
    dirty=False
    source_failures=[]

    published=json.loads((DATA/"videos.json").read_text(encoding="utf-8")).get("videos",[])
    videos=load("queue_videos.json","videos")
    known={x.get("id") for x in published+videos}
    try:
        uri="https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL_ID
        root=None
        last_error=None
        for attempt in range(3):
            try:
                req=urllib.request.Request(uri,headers={"User-Agent":"Mozilla/5.0 ZazoomTek YouTube importer"})
                with urllib.request.urlopen(req,timeout=25) as response:
                    root=ET.fromstring(response.read(2_000_000))
                break
            except Exception as error:
                last_error=error
                if attempt<2:time_module.sleep(1+attempt)
        if root is None:
            raise RuntimeError("YouTube video RSS unavailable after 3 attempts") from last_error
        for entry in root.findall("atom:entry",NS):
            vid=entry.findtext("yt:videoId",default="",namespaces=NS)
            title=entry.findtext("atom:title",default="",namespaces=NS)
            published_at=entry.findtext("atom:published",default="",namespaces=NS)
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or not title or not published_at or vid in known:
                continue
            kind,topic=classify_upload(title)
            videos.append({"id":vid,"title":title,"date":published_at,
                "topic":topic,"kind":kind,"first_seen_at":stamp})
            known.add(vid)
        print("Video feed checked; queued:",len(videos))
    except Exception as error:
        source_failures.append("videos")
        print("VIDEO IMPORT FAILED; existing queue preserved for retry:",
              type(error).__name__,str(error)[:200],flush=True)
    dirty|=write_if_changed(DATA/"queue_videos.json",{"videos":videos})

    try:
        archive_obj=json.loads((DATA/"community_full.json").read_text(encoding="utf-8"))
        archived=archive_obj.get("posts",[]) if isinstance(archive_obj,dict) else []
        if not isinstance(archived,list):archived=[]
    except (OSError,UnicodeError,ValueError,TypeError) as error:
        # Legacy archives are duplicate hints only; they must never block a live import.
        print("WARNING: legacy Community archive unavailable; live import continues:",
              type(error).__name__,str(error)[:160],flush=True)
        archived=[]
    seen={p.get("id") for p in archived+load("community_imported.json","posts")
          if isinstance(p,dict)}
    posts=load("queue_community.json","posts")
    seen|={p.get("id") for p in posts}
    try:
        records=discover(limit=160,max_pages=12)
        for item in records:
            pid=item.get("id")
            if not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}",str(pid)) or pid in seen:
                continue
            # Never create an article from an incomplete or unclassified Community excerpt.
            if not item.get("text_complete") or not item.get("type") or len(item.get("text",""))<60:
                continue
            item["first_seen_at"]=stamp
            posts.append(item)
            seen.add(pid)
        print("Community checked; queued:",len(posts))
    except Exception as error:
        source_failures.append("community")
        print("COMMUNITY IMPORT FAILED; existing queue preserved for retry:",
              type(error).__name__,str(error)[:200],flush=True)
    dirty|=write_if_changed(DATA/"queue_community.json",{"posts":posts})
    print("YOUTUBE QUEUE RESULT:",{
        "videos_total":len(videos),"community_total":len(posts),
        "source_failures":source_failures,"queue_changed":dirty
    },flush=True)
    if source_failures:
        raise RuntimeError("YouTube queue import incomplete; next scheduled run must retry: "
                           + ", ".join(source_failures))
    return dirty

if __name__=="__main__":
    ingest()
