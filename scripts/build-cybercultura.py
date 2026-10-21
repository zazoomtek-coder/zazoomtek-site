#!/usr/bin/env python3
"""Rebuild the unified Cybercultura archive from the two existing public archives.
The legacy pages and article URLs are never deleted, redirected or noindexed.
Run inside the existing Cloudflare site build after the category generators.
"""
from __future__ import annotations
import html
import json
from pathlib import Path
import re
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES=(("tech-today.html","Tech Impact"),("gaming-today.html","Gaming Inside"))
TARGET=ROOT/"cybercultura.html"
ROW=re.compile(r'<article\b[^>]*class="[^"]*\bnews-row\b[^"]*"[^>]*>.*?</article>', re.I|re.S)
URL=re.compile(r'<a\b[^>]*href="(/(?:news-|tech-impact-|gaming-inside-)[^"#?]+\.html)"',re.I)
LIST=re.compile(r'(<div\b[^>]*class="news-list"[^>]*>)(.*?)(</article>\s*</div>)',re.I|re.S)
DATE=re.compile(r'<div\b[^>]*class="news-meta"[^>]*>.*?(\d{4}-\d{2}-\d{2})',re.I|re.S)

def build() -> None:
    base=(ROOT/ARCHIVES[0][0]).read_text(encoding="utf-8")
    entries={}
    for filename,label in ARCHIVES:
        source=(ROOT/filename).read_text(encoding="utf-8")
        match=LIST.search(source)
        if not match:
            raise RuntimeError("Missing category archive news list: "+filename)
        for row in ROW.finditer(match.group(2)):
            item=row.group()
            link=URL.search(item)
            if not link:
                raise RuntimeError("Missing article URL in "+filename)
            url=link.group(1)
            if url in entries:
                continue
            date=DATE.search(item)
            published=date.group(1) if date else "1970-01-01"
            tag='<span class="zt-cyber-category">'+html.escape(label)+'</span>'
            item=item.replace('<div class="news-copy">','<div class="news-copy">'+tag,1)
            entries[url]=(published,item)
    if not entries:
        raise RuntimeError("Cybercultura cannot publish an empty combined archive")
    ordered=sorted(entries.values(),key=lambda item:item[0],reverse=True)
    # Preserve the existing accessible and responsive page shell, sidebar and footer.
    base=base.replace("<title>Tech Impact | ZazoomTek</title>","<title>Cybercultura | Tecnologia, Gaming, Società e Diritti - ZazoomTek</title>",1)
    base=base.replace('https://zazoomtek.it/tech-today.html','https://zazoomtek.it/cybercultura.html',1)
    base=re.sub(r'(<meta name="description" content=")[^"]+(")',r'\1Cybercultura: approfondimenti su tecnologia, videogiochi, politica, sicurezza, diritti digitali e societa. Tutte le notizie Tech Impact e Gaming Inside.\2',base,count=1)
    base=base.replace('<strong>Tech Impact</strong>','<strong>Cybercultura</strong>',1)
    base=base.replace('<span>Notizie di tecnologia e innovazione</span>','<span>Tecnologia, videogiochi, politica, sicurezza e diritti digitali</span>',1)
    base=base.replace('<h1>Tech Impact</h1>','<h1>Cybercultura</h1>',1)
    opening=LIST.search(base)
    if not opening:
        raise RuntimeError("Cybercultura archive source structure changed")
    body='<div class="news-list" id="newsList" data-auto-articles="cybercultura">\n'+'\n'.join(item for _,item in ordered)+'\n</div>'
    base=base[:opening.start()]+body+base[opening.end():]
    base=base.replace('</head>','<style>.zt-cyber-category{display:inline-block;margin-bottom:8px;padding:5px 9px;background:#202020;color:#fff;font:800 11px Arial,Helvetica,sans-serif;text-transform:uppercase;border-left:3px solid #d51232}</style><meta property="og:type" content="website"><meta property="og:title" content="Cybercultura | ZazoomTek"><meta property="og:url" content="https://zazoomtek.it/cybercultura.html"></head>',1)
    # Legacy archive links are kept for Google; site-wide navigation gets
    # its authoritative menu from the Home in apply-site-design.py.
    TARGET.write_text(base,encoding="utf-8")
    sitemap=ROOT/"sitemap.xml"
    if sitemap.is_file():
        xml=sitemap.read_text(encoding="utf-8")
        locator="https://zazoomtek.it/cybercultura.html"
        if locator not in xml:
            if "</urlset>" not in xml:
                raise RuntimeError("Invalid sitemap")
            xml=xml.replace("</urlset>","  <url><loc>"+locator+"</loc></url>\n</urlset>",1)
            sitemap.write_text(xml,encoding="utf-8")
    print("CYBERCULTURA GENERATED:",len(ordered),"unique existing articles; legacy category URLs preserved",flush=True)

if __name__=="__main__":
    build()
