#!/usr/bin/env python3
"""Standalone YouTube Community acquisition -> Cloudflare Worker D1 API.

No Git commits, no site builds, no Master orchestration, and no Pages deploy.
The Worker stores records idempotently. A failed batch is retried next run.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from urllib import request, error

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
CACHE=ROOT/".youtube-posts.json"

def scan():
    spec=importlib.util.spec_from_file_location("zt_community_source",ROOT/"scripts/update-youtube-posts.py")
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    previous=json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.is_file() else []
    if not isinstance(previous,list):
        previous=[]
    known={row.get("id") for row in previous if isinstance(row,dict)}
    try:
        fresh,complete=mod.parse(mod.fetch(),known)
        merged,complete=mod.augment_recent_posts(fresh,previous,complete)
    except Exception as exc:
        if not previous:
            raise RuntimeError("YouTube unavailable and no saved history exists") from exc
        print("WARNING: YouTube unavailable; replaying persisted GitHub inventory:",str(exc),flush=True)
        merged=previous
    by_id={}
    for item in [*merged,*previous]:
        if isinstance(item,dict) and item.get("id") and isinstance(item.get("text"),str):
            by_id.setdefault(item["id"],item)
    # Replay old and new records: safe D1 upserts make retries idempotent.
    return list(by_id.values())

def send(endpoint,token,posts):
    payload=json.dumps({"posts":[{
        "id":p["id"],"text":p["text"],"published_iso":p.get("published_iso","")
    } for p in posts]},ensure_ascii=False).encode("utf-8")
    url=endpoint.rstrip("/")+"/community/ingest"
    req=request.Request(url,data=payload,method="POST",headers={
        "Content-Type":"application/json","Authorization":"Bearer "+token
    })
    last=None
    for attempt in range(4):
        try:
            with request.urlopen(req,timeout=40) as response:
                result=json.load(response)
            if result.get("failed"):
                raise RuntimeError("Rejected IDs: "+repr(result["failed"][:5]))
            return int(result["accepted"])
        except (error.URLError,TimeoutError,ValueError,RuntimeError) as exc:
            last=exc
            if attempt<3:
                time.sleep(min(15,2**attempt*2))
    raise RuntimeError("Cloudflare ingestion failed after 4 attempts: "+str(last))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--backfill",action="store_true",help="Send all cached posts, not only the latest 50")
    args=ap.parse_args()
    endpoint=os.environ.get("ZT_COMMUNITY_WORKER_ENDPOINT","").strip()
    token=os.environ.get("ZT_COMMUNITY_INGEST_TOKEN","").strip()
    if not endpoint.startswith("https://") or not token:
        raise SystemExit("Missing HTTPS Worker endpoint or ingestion token")
    posts=scan()
    if not posts:
        raise SystemExit("No Community posts; import deferred")
    selected=posts if args.backfill else posts[:50]
    count=0
    for offset in range(0,len(selected),50):
        count+=send(endpoint,token,selected[offset:offset+50])
    print(f"WORKER COMMUNITY: accepted {count} idempotent posts; total inventory {len(posts)}")

if __name__=="__main__":
    main()
