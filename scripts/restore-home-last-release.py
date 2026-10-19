#!/usr/bin/env python3
"""Restore only the Home page from the last verified production source commit.

This is a safety fallback for releases where an unrelated page/menu/editorial
change accidentally damages index.html. It never rewinds the rest of the site.
"""
from __future__ import annotations
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
TRIGGER=ROOT/"cloudflare-release-trigger.txt"
HOME=ROOT/"index.html"

class RestoreError(RuntimeError):
    pass

def git(*args: str) -> str:
    p=subprocess.run(["git",*args],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:
        raise RestoreError(p.stderr.strip() or "git command failed")
    return p.stdout

def last_good_source() -> str:
    if not TRIGGER.is_file():
        raise RestoreError("release trigger missing; cannot identify last verified Home")
    source=""
    for line in TRIGGER.read_text(encoding="utf-8").splitlines():
        if line.startswith("source_commit="):
            source=line.split("=",1)[1].strip()
            break
    if not re.fullmatch(r"[a-f0-9]{40}",source):
        raise RestoreError("invalid source_commit in release trigger")
    git("cat-file","-e",source+"^{commit}")
    return source

def restore() -> str:
    source=last_good_source()
    content=git("show",f"{source}:index.html")
    if len(content)<25000:
        raise RestoreError("last verified Home is unexpectedly small; refusing restore")
    HOME.write_text(content,encoding="utf-8")
    print(f"HOME ROLLBACK: restored index.html from last verified production source {source}")
    return source

def main():
    try:
        restore()
    except RestoreError as exc:
        print(f"HOME ROLLBACK FAILED: {exc}",file=sys.stderr)
        raise SystemExit(1)

if __name__=="__main__":
    main()
