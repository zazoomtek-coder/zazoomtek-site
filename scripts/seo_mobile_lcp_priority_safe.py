#!/usr/bin/env python3
"""Keep exactly one high-priority featured image, with responsive CDN sizes.

Run last, after historical featured-image eager normalization. No layout, text,
images, JS, CSS or news content changes: only featured <img> attributes.
"""
import argparse
import re
from pathlib import Path

START = "<!-- FEATURED_NEWS_START -->"
END = "<!-- FEATURED_NEWS_END -->"
IMG = re.compile(r"<img\b[^>]*>", re.I)
SRC = re.compile(r'src="([^"]+)"', re.I)
CDN = re.compile(r"^(https://yt3\.ggpht\.com/[A-Za-z0-9_-]{20,})=s(?:1600|1200)-rw-nd-v1$", re.I)

def replace_attr(tag, name, value):
    pattern = re.compile(r'\s'+re.escape(name)+r'\s*=\s*"[^"]*"', re.I)
    att = ' '+name+'="'+value+'"'
    if pattern.search(tag):
        return pattern.sub(lambda _:att,tag,count=1)
    return tag[:-1]+att+">"

def remove_attr(tag,name):
    return re.sub(r'\s'+re.escape(name)+r'\s*=\s*"[^"]*"', "", tag, flags=re.I)

def transform(html):
    if html.count(START)!=1 or html.count(END)!=1:
        raise RuntimeError("Featured News markers changed; no optimization")
    a=html.index(START)+len(START)
    b=html.index(END,a)
    block=html[a:b]
    tags=IMG.findall(block)
    if len(tags)!=6:
        raise RuntimeError("Expected six featured images; no optimization")
    changed=[]
    for i,tag in enumerate(tags):
        src=SRC.search(tag)
        if not src: raise RuntimeError("Featured image src missing")
        if i==0:
            tag=replace_attr(tag,"loading","eager")
            tag=replace_attr(tag,"fetchpriority","high")
            cdn=CDN.fullmatch(src.group(1))
            if cdn:
                stem=cdn.group(1)
                tag=replace_attr(tag,"src",stem+"=s960-rw-nd-v1")
                tag=replace_attr(tag,"srcset",", ".join(
                    stem+f"=s{n}-rw-nd-v1 {n}w" for n in (480,720,960,1200)))
                tag=replace_attr(tag,"sizes","(max-width: 768px) 100vw, (max-width: 1200px) 60vw, 560px")
        else:
            tag=replace_attr(tag,"loading","lazy")
            tag=remove_attr(tag,"fetchpriority")
            # Do not change other featured image URLs or visual quality.
        changed.append(tag)
    it=iter(changed)
    newblock=IMG.sub(lambda _:next(it),block)
    return html[:a]+newblock+html[b:]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("."))
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    path=args.root/"index.html"
    before=path.read_text(encoding="utf-8")
    after=transform(before)
    assert transform(after)==after, "Not idempotent"
    print("Mobile featured LCP: 1 priority cover, 5 lazy covers, responsive primary image; changed=",before!=after)
    if not args.check and after!=before:path.write_text(after,encoding="utf-8")
if __name__=="__main__":main()
