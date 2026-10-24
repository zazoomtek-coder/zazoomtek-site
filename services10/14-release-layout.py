#!/usr/bin/env python3
"""Apply shared site header and overflow fixes to all editorial HTML pages.

The approved Home stays byte-for-byte unchanged. No remote calls, browser
tests, or staging. Future Studio pages are also covered by Studio layouts.
"""
from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CSS='<link rel="stylesheet" href="/zt-release-layout.css?v=20261024">'
JS='<script src="/zt-release-menu.js?v=20261024" defer></script>'

def update(page):
    doc=page.read_text(encoding="utf-8")
    if "</head>" not in doc or "</body>" not in doc:
        return False
    original=doc
    if CSS not in doc:
        doc=doc.replace("</head>",CSS+"\n</head>",1)
    if JS not in doc:
        doc=doc.replace("</body>",JS+"\n</body>",1)
    if original!=doc:
        page.write_text(doc,encoding="utf-8")
    return original!=doc

def main():
    pages=[p for p in ROOT.glob("*.html") if p.name!="index.html"]
    watch=ROOT/"watch"
    if watch.is_dir():
        pages.extend(p for p in watch.glob("*.html") if p.name!="index.html")
    count=0
    for page in pages:
        try:count+=int(update(page))
        except UnicodeError:continue
    print("Consistent navigation installed in",count,"pages; Home unchanged")

if __name__=="__main__":main()
