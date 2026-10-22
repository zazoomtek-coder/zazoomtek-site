#!/usr/bin/env python3
"""Restore owner-edited original HTML after automatic imports, before shared rendering."""
from __future__ import annotations
import json
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"editorial/studio-overrides"
NAME=re.compile(r"^(?:[a-zA-Z0-9][a-zA-Z0-9._-]*|watch/[a-zA-Z0-9_-]{11})\.html$")
def apply(root:Path=ROOT):
    folder=root/"editorial/studio-overrides"
    if not folder.exists():return 0
    updated=0
    for marker in sorted(folder.rglob("*.json")):
        obj=json.loads(marker.read_text(encoding="utf-8"))
        path=obj.get("path")
        if obj.get("version")!=1 or not obj.get("owner_edited") or not isinstance(path,str) or not NAME.fullmatch(path) or path=="index.html" or marker.relative_to(folder).as_posix()!=path[:-5]+".json":
            raise RuntimeError("Invalid Studio override: "+marker.name)
        content=obj.get("html")
        if not isinstance(content,str) or len(content)>2_000_000 or not re.search(r"<article\b[^>]*class=['\"][^'\"]*(?:article-main|story|zt-main|zt-watch-article)",content,re.I) or not re.search(r"<h1\b",content,re.I) or not re.search(r'<link\b[^>]*rel=["\']canonical["\']',content,re.I):
            raise RuntimeError("Unsafe or incomplete Studio override: "+marker.name)
        target=root/path
        if not target.is_file():
            print("Studio override waiting for original page:",path)
            continue
        existing=target.read_text(encoding="utf-8")
        if existing!=content:
            target.write_text(content,encoding="utf-8")
            updated+=1
    print("Protected Studio owner overrides applied:",updated)
    return updated
def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        root=Path(t);base=root/"editorial/studio-overrides";base.mkdir(parents=True)
        page="demo-review.html"
        (root/page).write_text("automatically imported",encoding="utf-8")
        html='<html><head><link rel="canonical" href="/demo-review.html"></head><body><article class="article-main"><h1>Changed manually</h1></article></body></html>'
        (base/"demo-review.json").write_text(json.dumps({"version":1,"owner_edited":True,"path":page,"html":html}),encoding="utf-8")
        assert apply(root)==1 and (root/page).read_text()==html
        (root/page).write_text("import reset",encoding="utf-8")
        assert apply(root)==1 and (root/page).read_text()==html
        print("PASS: subsequent imports cannot overwrite the approved manual edit")
if __name__=="__main__":
    import sys
    self_test() if "--self-test" in sys.argv else apply()
