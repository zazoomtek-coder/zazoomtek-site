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
import json,re
from html import escape

def update():
    path=ROOT/"notizie-dal-web.json"
    page=ROOT/"index.html"
    data=json.loads(path.read_text(encoding="utf-8"))
    items=data.get("items",[])[:5]
    tiles=[]
    for x in items:
        url=x.get("url","");img=x.get("image","");title=x.get("original_title") or x.get("title","")
        if not url or not img or not title:continue
        tiles.append(f'<a class="zt-webnews-item" href="{escape(url,quote=True)}"><img src="{escape(img,quote=True)}" loading="lazy" alt="{escape(title,quote=True)}"><span class="zt-webnews-info"><small>{escape(str(x.get("source","")))}</small><strong>{escape(title)}</strong></span></a>')
    if not tiles:return
    html=page.read_text(encoding="utf-8")
    panel='<section id="zt-webnews-home" class="zt-webnews-home" aria-label="NOTIZIE DAL WEB"><header class="zt-webnews-head"><h2>NOTIZIE DAL WEB</h2></header><div class="zt-webnews-grid">'+''.join(tiles)+'</div></section>'
    html,n=re.subn(r'<section\b[^>]*id="zt-webnews-home"[^>]*>[\s\S]*?</section>',lambda _:panel,html,count=1)
    if n:page.write_text(html,encoding="utf-8")
if __name__=="__main__":update()
