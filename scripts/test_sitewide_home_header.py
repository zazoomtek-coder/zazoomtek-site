#!/usr/bin/env python3
"""Read-only regression for deployed, static Home-sourced mastheads."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
from pathlib import Path
import re

NAV=("Home","News","Recensioni","Guide","Tech Impact","Gaming Inside","Extra","Community","Video")
HEADER=re.compile(r"<header\b[^>]*>[\s\S]*?</header>",re.I)
NAV_RE=re.compile(r'<nav\b[^>]*class=["\']nav["\'][^>]*>[\s\S]*?</nav>',re.I)

class Nav(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.inside=False
        self.text=""
        self.labels=[]
    def handle_starttag(self,tag,attrs):
        if tag=="a":
            self.inside=True;self.text=""
    def handle_endtag(self,tag):
        if tag=="a" and self.inside:
            self.labels.append(" ".join(self.text.split()))
            self.inside=False
    def handle_data(self,data):
        if self.inside:self.text+=data

def validate(root:Path):
    home=(root/"index.html").read_text(encoding="utf-8")
    source=HEADER.search(home)
    assert source and "class=\"shell topbar\"" in source.group(),"Locked Home header absent"
    checked=0
    for path in sorted(root.glob("*.html")):
        if path.name.startswith(("preview-","anteprima-","audit-","test-")):
            continue
        text=path.read_text(encoding="utf-8",errors="replace")
        header=HEADER.search(text)
        if not header or not any(x in header.group().upper() for x in ("ZAZOOM","CHATGPT.PNG")):
            continue
        nav=NAV_RE.search(header.group())
        assert nav,path.name+" has no actual Home menu"
        parser=Nav();parser.feed(nav.group())
        assert tuple(parser.labels)==NAV,(path.name,parser.labels)
        assert header.group().count('class="shell topbar"')==1,path.name
        assert header.group().count('class="ticker-video-links"')==1,path.name
        assert 'class="brand-logo-img"' in header.group(),path.name
        assert "zt-unified-header.js" not in text,path.name+" still has obsolete async swap"
        if path.name not in ("index.html",) and not re.fullmatch(r"pagina-\d+\.html",path.name):
            assert header.group().startswith('<header id="zt-site-home-header">'),path.name
            assert text.count('id="zt-site-home-header-style"')==1,path.name
            assert not re.match(r"\s*<div\b[^>]*class=[^>]*zt-strip",
                                text[header.end():],re.I),path.name+" duplicate ticker"
            # Keep page bodies/sidebars and one static root-absolute masthead.
            assert 'href="/news.html"' in header.group(),path.name
            assert 'href="/tech-today.html"' in header.group(),path.name
            assert 'href="/extra.html"' in header.group(),path.name
        checked+=1
    assert checked>=50,("Insufficient sitewide coverage",checked)
    for sample in ("news.html","tech-today.html","gaming-today.html",
                   "extra.html","guide.html","recensioni-scritte.html"):
        assert (root/sample).is_file(),sample+" absent"
        page=(root/sample).read_text(encoding="utf-8")
        assert 'id="zt-site-home-header"' in page,sample+" not normalized"
    watch_dir=root/"watch"
    video_pages=sorted(watch_dir.glob("*.html"))
    assert len(video_pages)>=10,("Missing generated video watch pages",len(video_pages))
    for video in video_pages:
        markup=video.read_text(encoding="utf-8")
        assert 'id="zt-site-home-header"' in markup,video.name
        assert markup.count('id="zt-site-home-header-style"')==1,video.name
        assert 'class="ticker-video-links"' in markup,video.name
    print("PASS:",len(video_pages),"generated video watch pages use the same static Home header")
    print("PASS: static Home logo, nine menu links, search/ticker and no async swap on",checked,"pages")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("dist"))
    validate(p.parse_args().root)
