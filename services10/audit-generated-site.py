#!/usr/bin/env python3
"""Audit the complete isolated static snapshot without blocking old content.

Never deletes pages. Report pre-existing broken links separately from missing
required artifacts and references introduced by independent services10 pages.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote,urlsplit

REQUIRED=("index.html","news.html","watch/index.html","studio/index.html")
GENERATED=("<!-- SERVICES10_GENERATED -->","data-services10-generated")
PARTIAL_DIRS={"includes","partials","fragments"}
VERIFY=re.compile(r"(?:google[a-z0-9]+|bing[a-z0-9]+|yandex_[a-z0-9]+)\.html$",re.I)

def audit(dist:Path):
    problems=[];legacy_warnings=[];count=0
    pages=list(dist.rglob("*.html"))
    if not pages:problems.append("No HTML pages generated")
    for name in REQUIRED:
        if not (dist/name).is_file():
            problems.append("Missing public page "+name)
    for page in pages:
        count+=1
        rel=page.relative_to(dist)
        if any(part in PARTIAL_DIRS for part in rel.parts[:-1]) or VERIFY.fullmatch(rel.name):
            continue
        content=page.read_text(encoding="utf-8",errors="replace")
        changed=any(mark in content for mark in GENERATED)
        errors=problems if changed else legacy_warnings
        if not re.search(r"<html\b",content,re.I):
            errors.append(str(rel)+": missing html element")
        if not re.search(r"</html\s*>",content,re.I):
            errors.append(str(rel)+": missing closing html element")
        if not re.search(r"<title\b",content,re.I):
            errors.append(str(rel)+": missing title")
        seen=set()
        for value in re.findall(r'(?:href|src)\s*=\s*["\x27]([^"\x27]+)["\x27]',content,re.I):
            if not value or value.startswith(("#","data:","mailto:","tel:","javascript:")):
                continue
            url=urlsplit(value)
            if url.scheme or url.netloc or value.startswith("//"):
                continue
            target=unquote(url.path)
            if not target:continue
            target=target.lstrip("/") if target.startswith("/") else (rel.parent/target).as_posix()
            if target in seen:continue
            seen.add(target)
            candidate=dist/target
            if not (candidate.is_file() or (candidate/"index.html").is_file()):
                errors.append(str(rel)+": missing asset/link "+target)
                if len(errors)>150:break
    return {"html_pages":count,"blocking_problems":problems[:100],
            "legacy_warnings":legacy_warnings[:100],
            "legacy_warning_total":len(legacy_warnings),
            "ok":not problems}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dist",type=Path,default=Path("dist"))
    args=parser.parse_args()
    result=audit(args.dist)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result["ok"] else 1)
