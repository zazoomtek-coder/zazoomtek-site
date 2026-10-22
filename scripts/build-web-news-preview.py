#!/usr/bin/env python3
"""Pack full *real* ZazoomTek Home with local WebP/CSS/JS into a local ZIP.
Other production links open the live site; no deploy and no Cloudflare builds.
"""
from __future__ import annotations
import html
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"ZazoomTek-Notizie-dal-Web-LIVE.zip"
def build(root=ROOT,dest=DEST):
    page=(root/"index.html").read_text(encoding="utf-8")
    if page.count('id="ztWebNews"')!=1:
        raise RuntimeError("Real Home missing the five-card press-review section")
    page=page.replace('href="/', 'href="https://zazoomtek.it/')
    selected=set()
    # Local assets are served as files inside ZIP, never hotlinked third-party images.
    for attr in ["src","poster"]:
        pat=re.compile(r'('+attr+r'=["\'])(/[^"\']+)(["\'])')
        def change(m):
            asset=unquote(urlsplit(m.group(2)).path).lstrip("/")
            if asset.startswith(("assets/","zt-")) or asset in ("ChatGPT.png","favicon.ico"):
                file=root/asset
                if file.is_file() and ".." not in asset:
                    selected.add(asset)
                    return m.group(1)+"./"+asset+m.group(3)
            return m.group(0)
        page=pat.sub(change,page)
    # Make styles and scripts local (includes query-string cache busters).
    for attr in ["href","src"]:
        pat=re.compile(r'('+attr+r'=["\'])https://zazoomtek\.it/([^"\']+)(["\'])')
        def style_link(m):
            asset=unquote(urlsplit(m.group(2)).path)
            if (root/asset).is_file() and (asset.endswith((".css",".js",".png",".jpg",".webp",".svg"))):
                selected.add(asset)
                return m.group(1)+"./"+m.group(2)+m.group(3)
            return m.group(0)
        page=pat.sub(style_link,page)
    # Preserve the original approved full homepage, including all 5 cards.
    if page.count('class="zt-webnews-item"')!=4 or page.count('class="zt-webnews-feature"')!=1:
        raise RuntimeError("Not exactly one featured and four smaller external stories")
    with tempfile.TemporaryDirectory() as tmp:
        base=Path(tmp)/"ZazoomTek-Notizie-dal-Web-LIVE"
        base.mkdir(parents=True)
        (base/"index.html").write_text(page,encoding="utf-8")
        for asset in sorted(selected):
            if ".." in asset:continue
            target=base/asset
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/asset,target)
        (base/"ISTRUZIONI.txt").write_text(
            "ANTEPRIMA LIVE LOCALE - NOTIZIE DAL WEB\n"
            "1. Estrai completamente lo ZIP in una cartella.\n"
            "2. Apri index.html in Firefox, Chrome o Edge.\n"
            "3. Scorri oltre Ultimi Articoli e la numerazione delle pagine.\n"
            "4. Troverai NOTIZIE DAL WEB, 5 notizie e il box GUIDE subito sotto.\n"
            "5. Puoi aprire ogni articolo originale nel sito della testata.\n"
            "Questa anteprima usa la vera home di ZazoomTek.it, con asset locali\n"
            "quando presenti nel repository. Alcuni video/immagini della home\n"
            "originaria richiedono internet. Non pubblica e non modifica il sito.\n",
            encoding="utf-8")
        with ZipFile(dest,"w",ZIP_DEFLATED,compresslevel=8) as z:
            for f in sorted(base.rglob("*")):
                if f.is_file():z.write(f,f.relative_to(base.parent))
    print("PREVIEW ZIP:",dest.name," local dependencies:",len(selected))
if __name__=="__main__":build()
