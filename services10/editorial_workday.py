#!/usr/bin/env python3
"""One Europe/Rome workday edition and a 24-hour editorial rotation.

Every scheduled production build calls the same selection policy for Home,
archives, editorial rails, and the public JSON feed. Fresh arrivals take
priority on their actual publication day. In their absence, the latest
historical posts cycle DAILY, not on every deployment. Never falsifies a
publication date or deletes archives.
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

ROME=ZoneInfo("Europe/Rome")
FALLBACK="/assets/zt-editorial-fallback.svg"
RECENT_WINDOW_DAYS=14
ROTATING_POOL=16

def clock(now:datetime|None=None)->datetime:
    if now is None:return datetime.now(ROME)
    if now.tzinfo is None:raise ValueError("An aware datetime is required")
    return now.astimezone(ROME)

def edition(now:datetime|None=None)->dict:
    moment=clock(now)
    return {"edition_day":moment.date().isoformat(),
            "generated_at":moment.isoformat(timespec="seconds"),
            "timezone":"Europe/Rome","rotation_hours":24}

def stable_index(seed:str,count:int)->int:
    if count<1:return 0
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12],16)%count

def editorial_order(rows:list[dict],*,group:str="",page:str="",now:datetime|None=None,
                    excluded:set[str]|None=None)->list[dict]:
    """Prefer same-workday news, rotate recent older stories on each new day.

    URL (or video ID) is the identity; two distinct posts with identical
    titles must not suppress one another. Rotation stays identical across
    all five slots on one day but changes on the following workday.
    """
    today=clock(now).date()
    excluded=excluded or set()
    unique={}
    for row in rows:
        if not isinstance(row,dict):continue
        key=str(row.get("url") or row.get("id") or "").split("?",1)[0].lower()
        if not key or key in excluded:continue
        existing=unique.get(key)
        if existing is None or str(row.get("published") or "")>str(existing.get("published") or ""):
            unique[key]=row
    ordered=sorted(unique.values(),key=lambda r:(
        str(r.get("published") or ""),str(r.get("url") or "")),reverse=True)
    day=today.isoformat()
    today_rows=[row for row in ordered if str(row.get("published") or "")[:10]==day]
    other=[row for row in ordered if str(row.get("published") or "")[:10]!=day]
    cutoff=(today-timedelta(days=RECENT_WINDOW_DAYS)).isoformat()
    recent=[row for row in other if str(row.get("published") or "")[:10]>=cutoff]
    archive=[row for row in other if row not in recent]
    # The most recent editorial subset rotates once per calendar workday.
    # The upper tier is bounded so old historical items never displace
    # fresh stories when the recent set is plentiful.
    rotation=recent[:ROTATING_POOL] or archive[:ROTATING_POOL]
    if rotation:
        start=stable_index(f"{day}:{group}:{page}",len(rotation))
        rotation=rotation[start:]+rotation[:start]
    if recent:
        tail=recent[ROTATING_POOL:]+archive
    else:
        tail=archive[ROTATING_POOL:]
    return today_rows+rotation+tail

def select(rows:list[dict],limit:int,*,group:str="",page:str="",
           now:datetime|None=None,excluded:set[str]|None=None)->list[dict]:
    return editorial_order(rows,group=group,page=page,now=now,excluded=excluded)[:max(0,limit)]
