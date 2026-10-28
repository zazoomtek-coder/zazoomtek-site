#!/usr/bin/env python3
"""Accumulate original ZazoomTek YouTube records on the non-deploying editorial-queue branch."""
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
from pathlib import Path
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from community_youtube import discover, title_type
from sync_videos import CHANNEL_ID, NS, classify

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
ROME=ZoneInfo("Europe/Rome")

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
        return obj.get(key,[]) if isinstance(obj,dict) else []
    except (FileNotFoundError,ValueError,TypeError):
        return []

def ingest(now=None):
    now=now or datetime.now(timezone.utc)
    local=now.astimezone(ROME)
    clock=local.time()
    in_morning=time(9,0)<=clock<=time(12,20)
    in_evening=time(12,31)<=clock<=time(19,20)
    if not (in_morning or in_evening):
        print("Outside editorial intake window, nothing changed:",local.isoformat())
        return False
    stamp=now.isoformat(timespec="seconds")
    dirty=False

    published=json.loads((DATA/"videos.json").read_text(encoding="utf-8")).get("videos",[])
    videos=load("queue_videos.json","videos")
    known={x.get("id") for x in published+videos}
    try:
        req=urllib.request.Request(
            "https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL_ID,
            headers={"User-Agent":"Mozilla/5.0 ZazoomTek YouTube importer"})
        with urllib.request.urlopen(req,timeout=20) as response:
            root=ET.fromstring(response.read())
        for entry in root.findall("atom:entry",NS):
            vid=entry.findtext("yt:videoId",default="",namespaces=NS)
            title=entry.findtext("atom:title",default="",namespaces=NS)
            published_at=entry.findtext("atom:published",default="",namespaces=NS)
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or not title or not published_at or vid in known:
                continue
            kindtopic=classify(title)
            if not kindtopic: continue
            kind,topic=kindtopic
            videos.append({"id":vid,"title":title,"date":published_at,
                "topic":topic,"kind":kind,"first_seen_at":stamp})
            known.add(vid)
        print("Video feed checked; queued:",len(videos))
    except Exception as error:
        print("Video feed unavailable; existing queue preserved:",type(error).__name__,str(error)[:200])
    dirty|=write_if_changed(DATA/"queue_videos.json",{"videos":videos})

    archived=json.loads((DATA/"community_full.json").read_text(encoding="utf-8")).get("posts",[])
    seen={p.get("id") for p in archived+load("community_imported.json","posts")}
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
        print("Community unavailable; existing queue preserved:",type(error).__name__,str(error)[:200])
    dirty|=write_if_changed(DATA/"queue_community.json",{"posts":posts})
    return dirty

if __name__=="__main__":
    ingest()
