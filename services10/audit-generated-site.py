#!/usr/bin/env python3
"""Offline generated-site smoke audit for the ten-services migration."""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED = ("index.html","news.html","watch/index.html","studio/index.html")
def audit(dist:Path):
    problems=[]
    pages=list(dist.rglob("*.html"))
    if not pages: problems.append("No HTML pages generated")
    for path in REQUIRED:
        if not (dist/path).is_file(): problems.append("Missing "+path)
    for page in pages:
        html=page.read_text(encoding="utf-8",errors="replace")
        if not re.search(r'<html\b',html,re.I):problems.append(str(page)+": missing html tag")
        if not re.search(r'</html\s*>',html,re.I):problems.append(str(page)+": missing closing html tag")
        if not re.search(r'<title\b',html,re.I):problems.append(str(page)+": missing title")
        for value in re.findall(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']',html,re.I):
            if not value or value.startswith(("#","data:","mailto:","tel:","javascript:")):continue
            url=urlsplit(value)
            if url.scheme or url.netloc: continue
            if value.startswith("//"):continue
            target=unquote(url.path)
            if not target:continue
            if target.startswith("/"): target=target.lstrip("/")
            else:target=(page.relative_to(dist).parent/target).as_posix()
            candidate=dist/target
            if not (candidate.is_file() or (candidate/"index.html").is_file()):
                problems.append(str(page.relative_to(dist))+": missing asset/link "+target)
                if len(problems)>150:break
    return {"html_pages":len(pages),"problems":problems[:160],"ok":not problems}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--dist",type=Path,default=Path("dist"))
    args=p.parse_args();res=audit(args.dist);print(json.dumps(res,ensure_ascii=False,indent=2))
    raise SystemExit(0 if res["ok"] else 1)
