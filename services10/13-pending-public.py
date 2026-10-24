#!/usr/bin/env python3
"""Promote archived, public YouTube uploads without a fictitious 16:9 guarantee.

The 26 former pending uploads were already indexed by YouTube Data API. Their
original title/id/date are preserved. Newer files win; duplicates are removed.
Runs even if the live metadata collector temporarily fails.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"services10-data"
VIDEO=DATA/"videos.json"
PENDING=DATA/"pending-videos.json"
ID=re.compile(r"^[A-Za-z0-9_-]{11}$")

def read(path):
    try:
        result=json.loads(path.read_text(encoding="utf-8"))
        return result if isinstance(result,list) else []
    except (OSError,ValueError):
        return []

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def main():
    imported=read(VIDEO)
    queue=read(PENDING)
    by_id={v["id"]:v for v in imported if isinstance(v,dict)
           and ID.fullmatch(str(v.get("id") or "")) and v.get("title")}
    restored=0
    retained=[]
    for entry in queue:
        if not isinstance(entry,dict):continue
        vid=str(entry.get("id") or "")
        if not ID.fullmatch(vid) or not entry.get("title"):
            retained.append(entry);continue
        try:duration=int(entry.get("duration_seconds") or 0)
        except (TypeError,ValueError):duration=0
        if duration<=0:
            retained.append(entry);continue
        if vid not in by_id:
            by_id[vid]={**entry,"type":"youtube_video",
                        "verification":"official_youtube_metadata_archived",
                        "orientation":"unverified","short":duration<=180}
            restored+=1
    videos=sorted(by_id.values(),key=lambda item:item.get("published") or "",reverse=True)
    if videos!=imported:write(VIDEO,videos)
    if retained!=queue:write(PENDING,retained)
    print("YouTube archived public uploads restored:",restored,
          "total:",len(videos),"still pending:",len(retained))

if __name__=="__main__":main()
