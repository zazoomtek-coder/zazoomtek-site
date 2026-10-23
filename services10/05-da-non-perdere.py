#!/usr/bin/env python3
"""Independent ZazoomTek component, intended for isolated build workspace.

Does not deploy to Cloudflare. No editorial approvals or central Master gateway.
"""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def run(script,*args):
    subprocess.run([sys.executable,str(ROOT/"scripts"/script),*args],cwd=ROOT,check=True)
import re
from html import escape

def update():
    page=ROOT/"index.html"
    html=page.read_text(encoding="utf-8")
    start="<!-- POPULAR_NEWS_ITEMS_START -->"; end="<!-- POPULAR_NEWS_ITEMS_END -->"
    if start not in html or end not in html: return
    feed=html.split("<!-- ARTICLE_FEED_START -->",1)[-1].split("<!-- ARTICLE_FEED_END -->",1)[0]
    cards=[];seen=set()
    for article in re.findall(r'<article\b[^>]*class="article-row"[^>]*>[\s\S]*?</article>',feed):
        if not re.search(r'data-post-category="tech"',article,re.I): continue
        m=re.search(r'<h3><a href="([^"]+)"[^>]*>([\s\S]*?)</a></h3>',article,re.I)
        im=re.search(r'<img\b[^>]*\bsrc="([^"]+)"',article,re.I)
        if not m or not im: continue
        href=m.group(1); href=href if href.startswith("/") else "/"+href
        if href in seen:continue
        seen.add(href)
        title=re.sub(r'<[^>]*>', '',m.group(2)).strip()
        cards.append('<a class="zt-popular-article" href="'+escape(href,quote=True)+'"><img src="'+escape(im.group(1),quote=True)+'" alt="'+escape(title,quote=True)+'" loading="lazy"><span class="zt-popular-copy"><span class="zt-popular-category">TECNOLOGIA</span><strong>'+escape(title)+'</strong></span></a>')
        if len(cards)==5:break
    if not cards:return
    pattern=r'(?<=<!-- POPULAR_NEWS_ITEMS_START -->)[\s\S]*?(?=<!-- POPULAR_NEWS_ITEMS_END -->)'
    html=re.sub(pattern,lambda _: '\\n'+'\\n'.join(cards)+'\\n',html,count=1)
    page.write_text(html,encoding="utf-8")
if __name__=="__main__":update()
