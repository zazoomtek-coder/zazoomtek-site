#!/usr/bin/env python3
"""On Cloudflare output only, replace retired category archive sitemap entries.

Never rewrite editorial articles or imported source inventory. Both old
category archive URLs are 301 to /cybercultura.html, while every published
article URL remains canonical and continues to be listed.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

BASE="https://zazoomtek.it/"
NEW=BASE+"cybercultura.html"
OLD={BASE+"tech-today.html",BASE+"gaming-today.html"}


def apply(root:Path)->None:
    for name in ("sitemap.xml","google-sitemap.xml"):
        target=root/name
        if not target.is_file():continue
        old=target.read_text(encoding="utf-8")
        value=old
        for url in OLD:
            value,count=re.subn(r'\s*<url><loc>'+re.escape(url)+r'</loc>(?:[\s\S]*?)</url>',
                                "",value,count=1)
            if count!=1:
                raise RuntimeError(f"Cannot find retired sitemap URL {url} in {name}")
        if NEW not in value:
            value=value.replace("</urlset>",'  <url><loc>'+NEW+'</loc></url>\n</urlset>',1)
        if value.count(NEW)!=1:
            raise RuntimeError("Cybercultura sitemap URL duplicated")
        ET.fromstring(value)
        if old!=value:target.write_text(value,encoding="utf-8")
        print("CYBERCULTURA SITEMAP:",name)
    p=root/"sitemap.txt"
    if p.is_file():
        before=p.read_text(encoding="utf-8")
        urls=[line for line in before.splitlines() if line.strip() not in OLD|{NEW}]
        urls.append(NEW)
        output="\n".join(urls)+"\n"
        if output!=before:p.write_text(output,encoding="utf-8")
        print("CYBERCULTURA SITEMAP: sitemap.txt")


if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("Usage: sync-cybercultura-sitemaps.py dist")
    target=Path(sys.argv[1])
    if not target.is_dir():raise SystemExit("Cloudflare dist is missing")
    apply(target)
