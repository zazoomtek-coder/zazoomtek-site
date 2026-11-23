#!/usr/bin/env python3
"""Accumulate original ZazoomTek YouTube records on the non-deploying editorial-queue branch."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from community_youtube import discover, title_type, date_from_relative
from sync_videos import CHANNEL_ID, NS, classify, discover_uploads

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
def in_intake_window(clock=None):
    """Collection is allowed 24/7; release slots are enforced elsewhere."""
    return True

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
    except (ValueError,TypeError) as exc:
        raise RuntimeError("Damaged editorial queue snapshot: "+name) from exc
    if not isinstance(obj,dict) or not isinstance(obj.get(key,[]),list):
        raise RuntimeError("Invalid editorial queue snapshot: "+name)
    return obj.get(key,[])

def ingest(now=None):
    now=now or datetime.now(timezone.utc)
    local=now.astimezone(timezone.utc)
    print("YOUTUBE COLLECTION RUN (NO DEPLOY):",local.isoformat(),flush=True)
    stamp=now.isoformat(timespec="seconds")
    dirty=False
    video_rss_ok=False
    video_scan_ok=False
    community_ok=False

    published=json.loads((DATA/"videos.json").read_text(encoding="utf-8")).get("videos",[])
    published_ids={x.get("id") for x in published if isinstance(x,dict)}
    videos=[x for x in load("queue_videos.json","videos")
            if isinstance(x,dict) and x.get("id") not in published_ids]
    known=published_ids|{x.get("id") for x in videos}
    try:
        req=urllib.request.Request(
            "https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL_ID,
            headers={"User-Agent":"Mozilla/5.0 ZazoomTek YouTube importer"})
        with urllib.request.urlopen(req,timeout=20) as response:
            root=ET.fromstring(response.read())
        video_rss_ok=True
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
        print("Video feed unavailable; existing queue preserved:",type(error).__name__,str(error)[:200])
    # Supplement the 15-entry RSS feed with paginated channel uploads so
    # temporary missed cycles do not permanently lose older videos.
    try:
        uploads=discover_uploads(limit=180,max_pages=12)
        video_scan_ok=True
        for item in uploads:
            vid=item.get("id")
            title=item.get("title")
            published_at=date_from_relative(item.get("published_label",""),now)
            if not re.fullmatch(r"[A-Za-z0-9_-]{11}",str(vid or "")) or not title or not published_at or vid in known:
                continue
            kind,topic=classify_upload(title)
            videos.append({"id":vid,"title":title,"date":published_at,
                "topic":topic,"kind":kind,"first_seen_at":stamp})
            known.add(vid)
        print("Paginated YouTube channel scan; queued:",len(videos),flush=True)
    except Exception as error:
        print("Paginated video scan unavailable; RSS queue preserved:",
              type(error).__name__,str(error)[:180],flush=True)
    dirty|=write_if_changed(DATA/"queue_videos.json",{"videos":videos})

    archived=json.loads((DATA/"community_full.json").read_text(encoding="utf-8")).get("posts",[])
    imported=json.loads((DATA/"community_imported.json").read_text(encoding="utf-8")).get("posts",[])
    published_post_ids={p.get("id") for p in archived+imported if isinstance(p,dict)}
    posts=[p for p in load("queue_community.json","posts")
           if isinstance(p,dict) and p.get("id") not in published_post_ids]
    seen=published_post_ids|{p.get("id") for p in posts}
    try:
        records=discover(limit=160,max_pages=12,known_ids=seen)
        community_ok=True
        for item in records:
            pid=item.get("id")
            if not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}",str(pid)) or pid in seen:
                continue
            # discover() returns only Community posts verified on their individual detail pages.
            if not item.get("type") or len(item.get("text",""))<60:
                continue
            item["first_seen_at"]=stamp
            posts.append(item)
            seen.add(pid)
        print("Community checked; queued:",len(posts))
    except Exception as error:
        print("Community unavailable; existing queue preserved:",type(error).__name__,str(error)[:200])
    dirty|=write_if_changed(DATA/"queue_community.json",{"posts":posts})
    print("YOUTUBE COLLECTION SOURCE STATUS:",
          {"videos": video_rss_ok or video_scan_ok, "community": community_ok}, flush=True)
    if not (video_rss_ok or video_scan_ok) or not community_ok:
        raise RuntimeError("YouTube collection incomplete; successfully collected queue data was saved for retry")
    return dirty

if __name__=="__main__":
    ingest()
