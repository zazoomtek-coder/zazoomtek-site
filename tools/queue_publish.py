#!/usr/bin/env python3
"""Promote queued records to production only at 12:30 and 19:30 Europe/Rome.

The editor and intake pipeline never write live content. This job reads an
independent queue branch and performs one atomic main-branch editorial commit.
"""
from datetime import datetime,timezone,time,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
import json,subprocess,os

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
QUEUE="origin/editorial-queue"
ROME=ZoneInfo("Europe/Rome")
FILES=("queue_videos.json","queue_community.json","studio_posts.json","studio_overrides.json")

def queued_file(filename):
    try:
        out=subprocess.check_output(["git","show",QUEUE+":data/"+filename],cwd=ROOT,stderr=subprocess.DEVNULL)
        return json.loads(out.decode("utf-8"))
    except (subprocess.CalledProcessError,UnicodeError,ValueError):
        return {}

def load(filename,fallback):
    try:return json.loads((DATA/filename).read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):return fallback

def store(filename,obj):
    path=DATA/filename
    value=json.dumps(obj,ensure_ascii=False,indent=2)+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==value:return False
    path.write_text(value,encoding="utf-8")
    print("Updated:",filename)
    return True

def before_cutoff(row,cutoff):
    value=row.get("first_seen_at") or row.get("updated_at") or row.get("queued_at")
    if not value:return True # Legacy staged records remain publishable
    try:
        stamp=datetime.fromisoformat(str(value).replace("Z","+00:00"))
        if stamp.tzinfo is None:stamp=stamp.replace(tzinfo=timezone.utc)
        return stamp<=cutoff
    except (ValueError,TypeError):return False

def run():
    local=datetime.now(ROME)
    slot=os.environ.get("EDITORIAL_SLOT","").strip()
    if slot not in ("12:30","19:30"):
        raise SystemExit("EDITORIAL_SLOT must be 12:30 or 19:30")
    # Scheduled jobs can start late, but cannot publish the next window early.
    target=local.replace(hour=int(slot[:2]),minute=30,second=0,microsecond=0)
    if local.date()!=target.date() or local<target or local>target+timedelta(minutes=45):
        raise SystemExit("Slot not reached: "+slot)
    cutoff=target.replace(hour=int(slot[:2]),minute=20,second=0,microsecond=0).astimezone(timezone.utc)
    changed=False

    current=load("videos.json",{"videos":[]})
    rows={x["id"]:x for x in current.get("videos",[]) if x.get("id")}
    for row in queued_file("queue_videos.json").get("videos",[]):
        if row.get("id") and before_cutoff(row,cutoff):
            clean={k:v for k,v in row.items() if k!="first_seen_at"}
            rows.setdefault(row["id"],clean)
    ordered=sorted(rows.values(),key=lambda x:x.get("date",""),reverse=True)
    current["videos"]=ordered
    changed|=store("videos.json",current)

    current=load("community_imported.json",{"posts":[]})
    rows={x["id"]:x for x in current.get("posts",[]) if x.get("id")}
    for row in queued_file("queue_community.json").get("posts",[]):
        if row.get("id") and before_cutoff(row,cutoff):
            clean={k:v for k,v in row.items() if k!="first_seen_at"}
            rows.setdefault(row["id"],clean)
    current["posts"]=sorted(rows.values(),key=lambda x:x.get("published_at") or x.get("date") or "",reverse=True)
    changed|=store("community_imported.json",current)

    # Studio records are snapshots; filter changes made after the cutoff.
    current=load("studio_posts.json",{"posts":[]})
    rows={x["slug"]:x for x in current.get("posts",[]) if x.get("slug")}
    for row in queued_file("studio_posts.json").get("posts",[]):
        if row.get("slug") and before_cutoff(row,cutoff):
            rows[row["slug"]]=row
    current["posts"]=sorted(rows.values(),key=lambda x:x.get("published_at") or x.get("date") or "",reverse=True)
    changed|=store("studio_posts.json",current)

    current=load("studio_overrides.json",{"overrides":{}})
    pending=queued_file("studio_overrides.json").get("overrides",{})
    for slug,row in pending.items():
        if isinstance(row,dict) and before_cutoff(row,cutoff):
            current.setdefault("overrides",{})[slug]=row
    changed|=store("studio_overrides.json",current)
    print("Slot:",slot,"cutoff:",cutoff.isoformat(),"editorial files changed:",changed)
    return changed

if __name__=="__main__":
    run()
