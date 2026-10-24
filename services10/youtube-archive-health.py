#!/usr/bin/env python3
"""Report durable YouTube import coverage; never claim 100% external visibility."""
from __future__ import annotations
import json
import os
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FILES={"community":ROOT/"services10-data/community.json",
       "videos":ROOT/"services10-data/videos.json",
       "pending":ROOT/"services10-data/pending-videos.json"}

def load(path):
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,list) else []
    except (OSError,ValueError):
        return []

def main():
    archives={key:load(path) for key,path in FILES.items()}
    counts={}
    for key,records in archives.items():
        ids={str(row.get("id")) for row in records if isinstance(row,dict) and row.get("id")}
        counts[key]=len(ids)
        if len(ids)!=len(records):
            print("WARNING:",key,"contains",len(records)-len(ids),"duplicate/invalid IDs")
    if not any(counts.values()):
        raise SystemExit("ERROR: no Community or video archive recovered")
    print("YouTube archived unique IDs:",counts)
    print("Source coverage cannot be certified when YouTube omits private,"
          " unavailable, deleted or undiscoverable posts.")
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as out:
            out.write("## ZazoomTek YouTube archive\n\n")
            for key,count in counts.items():
                out.write("- "+key+": **"+str(count)+"** unique archived IDs\n")
            out.write("\nArchive totals indicate retained data, not guaranteed"
                      " completeness of public YouTube responses.\n")

if __name__=="__main__":
    main()
