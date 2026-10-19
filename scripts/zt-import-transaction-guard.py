#!/usr/bin/env python3
"""Stage-ownership and last-good-inventory guard for ZazoomTek YouTube.
Read-only; runs after git add -A but before committing. Fail closed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
ALLOWED_KINDS=("community","videos","auxiliary")
COMMUNITY_HTML=re.compile(r"(?:index|news(?:-\d+)?|news-Ugkx[^/]*|recensione-[\w-]+|recensioni-scritte(?:-\d+)?|extra(?:-\d+)?|pagina-\d+)\.html",re.I)
VIDEO_HTML=re.compile(r"(?:index|recensioni|test|unboxing|gaming|analogiktek)\.html",re.I)
PUBLIC_HTML=re.compile(r"[A-Za-z0-9_.-]+\.html")
LOCKED={"featured-carousel.json","featured-editorial-pins.json","special-featured.json",
        "standard-news.json","cloudflare-release-trigger.txt","zt-home-live.js",
        "zt-visual.js","zt-design.css","firebase.json",".firebaserc"}
META={"sitemap.xml","google-sitemap.xml","sitemap.txt","robots.txt"}
# Legitimate review archive outputs from the Community importer. These are
# content lists, not authorization to change the protected Home structure.
REVIEW_CATEGORY_ARCHIVES={"recensioni-tech.html","recensioni-gaming.html"}
COMMUNITY_STATE={".youtube-posts.json","manual-news.json",".manual-news-build-state.json"}
COMMUNITY_COMMANDS={".force-community-full-scan"}
VIDEO_STATE={".youtube-latest.json","home-video-feed.json",".youtube-master-render-cache.json"}
PRIMARY_PAGE=re.compile(r"(?:news-Ugkx[^/]*|recensione-Ugkx[^/]*)\.html",re.I)
MIN_KEEP=.70

def allowed(kind,path):
    if (not path or path in LOCKED or "/" in path or path.startswith(".github/")
            or path.startswith("scripts/") or path.startswith("dist/")):
        return False
    if kind=="community":
        return (bool(COMMUNITY_HTML.fullmatch(path))
                or path in COMMUNITY_STATE|META|COMMUNITY_COMMANDS|REVIEW_CATEGORY_ARCHIVES
                or path in ("tech-today.html","gaming-today.html"))
    if kind=="videos":
        return bool(VIDEO_HTML.fullmatch(path)) or path in VIDEO_STATE
    return bool(PUBLIC_HTML.fullmatch(path)) or path=="search-index.json"

def changes():
    data=subprocess.run(["git","diff","--cached","--name-status","-z","--no-renames"],
                        cwd=ROOT,check=True,stdout=subprocess.PIPE).stdout
    parts=data.decode("utf-8").strip("\0").split("\0") if data else []
    if len(parts)%2:raise RuntimeError("Malformed staged Git diff")
    return list(zip(parts[0::2],parts[1::2]))

def validate_scope(kind,items):
    errors=[]
    for status,path in items:
        if not allowed(kind,path):errors.append(f"Unowned file in {kind} transaction: {path}")
        if status=="D" and path in REVIEW_CATEGORY_ARCHIVES:
            errors.append(f"Do not delete review category archive during import: {path}")
        if status=="D" and PRIMARY_PAGE.fullmatch(path):
            errors.append(f"Do not delete already published YouTube article: {path}")
        if status=="D" and path in COMMUNITY_STATE|VIDEO_STATE:
            errors.append(f"Do not delete import inventory: {path}")
        if status not in ("A","M","D","T"):
            errors.append(f"Unexpected staged status {status} for {path}")
    return errors

def inventory_errors(old,new,name):
    if not isinstance(new,list) or not new:return [f"{name}: invalid/empty inventory"]
    if not all(isinstance(x,dict) and x.get("id") for x in new):
        return [f"{name}: item missing source ID"]
    new_ids={str(x["id"]) for x in new}
    if len(new_ids)!=len(new):return [f"{name}: duplicate source IDs"]
    if not isinstance(old,list):return [f"{name}: malformed last-good inventory"]
    old_ids={str(x["id"]) for x in old if isinstance(x,dict) and x.get("id")}
    if old_ids and (len(new_ids)<len(old_ids)*MIN_KEEP or
                    len(old_ids&new_ids)<len(old_ids)*MIN_KEEP):
        return [f"{name}: source unexpectedly lost/replaced over 30% of the known archive; "
                "keep the last-good inventory and retry"]
    return []

def read_previous(path):
    proc=subprocess.run(["git","show","HEAD:"+path],cwd=ROOT,
                        stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
    if proc.returncode:return []
    return json.loads(proc.stdout.decode("utf-8"))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--kind",choices=ALLOWED_KINDS)
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    if args.self_test:
        assert allowed("community","news-Ugkx123_abc.html")
        assert allowed("community","index.html")
        assert allowed("community","tech-today.html")
        assert allowed("community","gaming-today.html")
        assert allowed("community","recensioni-tech.html")
        assert allowed("community","recensioni-gaming.html")
        assert allowed("community",".manual-news-build-state.json")
        assert allowed("community",".force-community-full-scan")
        assert allowed("videos","home-video-feed.json")
        assert allowed("videos",".youtube-master-render-cache.json")
        assert not allowed("community",".youtube-master-render-cache.json")
        assert allowed("auxiliary","news-foo.html")
        assert not allowed("videos","news-Ugkx123.html")
        assert not allowed("community","zt-home-live.js")
        assert not allowed("community","recensioni-gaming.css")
        assert not validate_scope("community",[
            ("M","recensioni-tech.html"),("M","recensioni-gaming.html"),
            ("M","index.html"),("A","news-UgkxNewExample.html")])
        assert validate_scope("community",[("D","recensioni-tech.html")])
        assert not allowed("auxiliary","featured-carousel.json")
        assert validate_scope("community",[("D","news-Ugkx123.html")])
        assert not validate_scope("videos",[("M","index.html"),("M",".youtube-latest.json")])
        baseline=[{"id":str(i)} for i in range(100)]
        assert not inventory_errors(baseline,baseline,"test")
        assert inventory_errors(baseline,baseline[:10],"test")
        assert inventory_errors(baseline,[{"id":str(i+1000)} for i in range(100)],"test")
        print("PASS: harmless Community updates (incl. review categories), protected Home, no archive deletion, last-good inventory")
        return
    if not args.kind:ap.error("--kind is required")
    staged=changes()
    errors=validate_scope(args.kind,staged)
    state=(".youtube-posts.json" if args.kind=="community" else
           ".youtube-latest.json" if args.kind=="videos" else None)
    if state and any(path==state for _,path in staged):
        try:
            current=json.loads((ROOT/state).read_text(encoding="utf-8"))
            errors.extend(inventory_errors(read_previous(state),current,state))
        except (OSError,ValueError,UnicodeError) as exc:
            errors.append(f"Unreadable {state}: {exc}")
    if any(path=="index.html" for _,path in staged):
        result=subprocess.run([sys.executable,str(ROOT/"scripts/verify-home-layout-lock.py")],
                              cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if result.returncode:errors.append("The locked Home layout was modified by an import")
    if errors:
        for error in errors:print("::error::"+error,file=sys.stderr)
        raise SystemExit(1)
    print(f"PASS: {args.kind} owns all {len(staged)} staged files; no unwanted data loss")
if __name__=="__main__":main()
