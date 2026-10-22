#!/usr/bin/env python3
"""Build a BROWSER-RENDERED offline preview of the actual approved 3-column Home.

The HTML is generated from the site's real HTML+CSS+JS using headless Chromium
on localhost (not a mockup). The frozen, interactive links work by double-click,
without Python or a server on the editor's Windows PC. No site deployment.
"""
from __future__ import annotations
from functools import partial
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote
from zipfile import ZipFile, ZIP_DEFLATED
import contextlib
import re
import shutil
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"ZazoomTek-Notizie-dal-Web-LIVE.zip"
ARCHIVES=("news.html","recensioni-tech.html","recensioni-gaming.html","guide.html",
          "extra.html","speciali.html","cybercultura.html","recensioni-scritte.html",
          "pagina-2.html","pagina-3.html","pagina-4.html","pagina-5.html")
SKIP_SCRIPTS=("zt-home-live.js","zt-home-graphic-layout-20261016.js","zt-web-news-live.js")

class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def urls(markup):
    # relative and root URL references, including cache busting
    return re.findall(r'''(?:(?:src|href|poster)\s*=\s*["']|url\(\s*["']?)(/[^"'\)\s<>]+)''',markup,re.I)

def own_asset(root,name):
    name=unquote(urlsplit(name).path).lstrip("/")
    if not name or ".." in Path(name).parts or not re.search(r"\.(?:css|js|jpeg|jpg|png|webp|svg|ico|json|woff2?)$",name,re.I):
        return None
    p=root/name
    return name if p.is_file() and p.is_relative_to(root) else None

def collect_assets(root,webroot,seed):
    backlog=[seed]
    taken=set()
    while backlog:
        text=backlog.pop()
        for u in urls(text):
            name=own_asset(root,u)
            if not name or name in taken:continue
            taken.add(name)
            original=root/name
            dst=webroot/name
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(original,dst)
            if original.suffix.lower() in (".css",".js",".html"):
                backlog.append(original.read_text(encoding="utf-8",errors="replace")[:240000])
    # Main styling/behavior; dynamic JS inserts its own stylesheet.
    mandatory=("zt-design.css","zt-thumbnails.css","zt-home-cover-focus.css",
               "zt-home-live.js","zt-home-graphic-layout-20261016.js",
               "zt-home-graphic-layout-20261016.css","zt-web-news-live.js",
               "zt-visual.js","zt-analytics.js","ChatGPT.png","home-video-feed.json")
    for name in mandatory:
        if (root/name).is_file() and name not in taken:
            dst=webroot/name;dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(root/name,dst);taken.add(name)
    return taken

def convert_links(text,available,homepage=False):
    # Frozen HTML must work as a double-clicked file:/// URL, with no web server.
    # Unknown editorial pages link to REAL live ZazoomTek articles, not 404s.
    def link(m):
        attr,url,closer=m.group(1),m.group(2),m.group(3)
        if url.startswith(("#","mailto:","tel:","data:","http:","https:","javascript:")):
            return m.group(0)
        if not url.startswith("/"):return m.group(0)
        name=unquote(urlsplit(url).path).lstrip("/")
        if name in available:
            return attr+"./"+url.lstrip("/")+closer
        if not name and homepage:return attr+"./index.html"+closer
        # original links to non-packaged site pages open their real live page.
        return attr+"https://zazoomtek.it"+url+closer
    return re.sub(r'''((?:src|href|poster)=["'])(/[^"']*)(["'])''',link,text,flags=re.I)

def freeze_home(page,available):
    # Scripts that BUILD the 3-column DOM must not run a second time under
    # file:/// or they could recreate obsolete 2-column markup.
    for script in SKIP_SCRIPTS:
        page=re.sub(r'<script\b[^>]*\bsrc=["\'][^"\']*/?'+re.escape(script)+r'(?:\?[^"\']*)?["\'][^>]*>\s*</script>',"",page,flags=re.I)
    return convert_links(page,available,homepage=True)

def build(root=ROOT,dest=DEST):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Install playwright for the validation build, never on visitors' PCs") from exc
    source=(root/"index.html").read_text(encoding="utf-8")
    if source.count('id="ztWebNewsStaging"')!=1:
        raise RuntimeError("Five-card Home preview stage missing")
    with tempfile.TemporaryDirectory(prefix="zt-webnews-three-column-") as tmp:
        base=Path(tmp)/"ZazoomTek-Notizie-dal-Web-LIVE"
        base.mkdir()
        (base/"index.html").write_text(source,encoding="utf-8")
        # Copy actual site CSS/JS and referenced image files; no fake layout.
        assets=collect_assets(root,base,source)
        for name in ARCHIVES:
            if (root/name).is_file():
                (base/name).write_text((root/name).read_text(encoding="utf-8"),encoding="utf-8")
        handler=partial(Quiet,directory=str(base))
        http=ThreadingHTTPServer(("127.0.0.1",0),handler)
        threading.Thread(target=http.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as pw:
                exe=shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
                kwargs={"headless":True,"args":["--no-sandbox","--disable-dev-shm-usage"]}
                if exe:kwargs["executable_path"]=exe
                browser=pw.chromium.launch(**kwargs)
                pg=browser.new_page(viewport={"width":1600,"height":900},device_scale_factor=1)
                errors=[]
                pg.on("pageerror",lambda error:errors.append(str(error)[:260]))
                pg.goto(f"http://127.0.0.1:{http.server_address[1]}/",wait_until="domcontentloaded",timeout=30000)
                pg.wait_for_function("document.documentElement.dataset.ztWebNewsMounted === 'three-column'",timeout=18000)
                pg.wait_for_timeout(1100)
                verify=pg.evaluate("""() => {
                  const news=document.getElementById('ztWebNews');
                  const pager=document.getElementById('ztpNewsPager');
                  const panel=document.getElementById('ztp-guide-extra');
                  const guide=document.getElementById('ztHomeGuide');
                  const extra=document.getElementById('ztHomeExtra');
                  const rail=document.getElementById('ztpNewsRail');
                  const split=document.querySelector('.ztp-two-news-columns');
                  const main=document.querySelector('#articoli.ztp-news-area .ztp-primary-feed');
                  const order=[pager,news,panel].map(n=>n?.getBoundingClientRect().top);
                  return {threeColumns:!!document.querySelector('.ztp-final-three'),
                    hasTech:!!document.querySelector('.ztp-news-tech'),
                    hasGaming:!!document.querySelector('.ztp-news-gaming'),
                    newsInMain:!!news?.closest('.ztp-primary-feed'),
                    rightRail:!!rail?.querySelector('.zt-webnews-followup-rail'),
                    sameGuide:!!guide&&!!panel?.contains(guide),
                    realExtra:!!extra&&!!panel?.contains(extra),
                    order, cards:news?.querySelectorAll('.zt-webnews-feature,.zt-webnews-item').length,
                    columns:getComputedStyle(split).gridTemplateColumns,
                    title:document.title, width:document.documentElement.scrollWidth,
                    viewport:innerWidth};
                }""")
                print("REAL THREE-COLUMN BROWSER VERIFICATION:",verify,flush=True)
                if not (verify["threeColumns"] and verify["hasTech"] and verify["hasGaming"]
                        and verify["newsInMain"] and verify["rightRail"]
                        and verify["sameGuide"] and verify["realExtra"]
                        and verify["cards"]==5 and
                        verify["order"][0]<=verify["order"][1]<=verify["order"][2]):
                    raise RuntimeError("Actual browser doesn't match approved 3-col structure: "+str(verify))
                # Activate lazy images before capturing the long real Home;
                # otherwise Chromium's full-page screenshot paints off-screen
                # originals as blank dark rectangles, despite valid local WebP.
                pg.evaluate("""() => document.querySelectorAll('img[loading="lazy"]').forEach(img => {img.loading='eager';img.decoding='sync'})""")
                try:
                    pg.get_by_text("ACCETTA",exact=True).first.click(timeout=1500)
                except Exception:
                    pass
                pg.wait_for_timeout(1400)
                # Keep a full-page visual artifact, reviewable by the editor.
                pg.screenshot(path=str(base/"VERIFICA_HOME_3_COLONNE.png"),full_page=True,animations="disabled",timeout=30000)
                built=pg.content()
                browser.close()
        finally:
            http.shutdown();http.server_close()
        # Existing menu/archive pages actually open locally. The rest of the
        # links go to original published ZazoomTek pages, not imaginary stubs.
        available=set(assets)|{p.name for p in base.iterdir() if p.is_file()}
        for name in ARCHIVES:
            if (base/name).is_file():
                content=(base/name).read_text(encoding="utf-8",errors="replace")
                (base/name).write_text(convert_links(content,available),encoding="utf-8")
        built=freeze_home(built,available)
        (base/"index.html").write_text(built,encoding="utf-8")
        (base/"ISTRUZIONI.txt").write_text(
            "ZAZOOMTEK.IT — NOTIZIE DAL WEB, ANTEPRIMA REALE A TRE COLONNE\n\n"
            "Estrai lo ZIP e apri index.html con Chrome, Edge o Firefox.\n"
            "La Home e' stata renderizzata in un browser Chromium usando\n"
            "il codice reale e il layout editoriale approvato (Tech/Gaming/colonna destra).\n"
            "Scorri dopo il blocco numerato NEXT: segue NOTIZIE DAL WEB.\n"
            "Segue il modulo esistente GUIDE + EXTRA, senza sostituzioni.\n"
            "A destra trovi il rail editoriale con articoli reali.\n"
            "Il menu porta alle sezioni locali incluse, se disponibili.\n"
            "I collegamenti agli altri articoli puntano al sito ZazoomTek.it.\n"
            "I cinque link esterni portano alle testate di origine.\n"
            "Alcune immagini ospitate da terzi richiedono internet.\n"
            "VERIFICA_HOME_3_COLONNE.png mostra il layout finale completo.\n"
            "Questa anteprima NON effettua alcuna pubblicazione o deploy.\n",encoding="utf-8")
        dest.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(dest,"w",ZIP_DEFLATED,compresslevel=8) as arc:
            for file in sorted(base.rglob("*")):
                if file.is_file():arc.write(file,file.relative_to(base.parent))
    print("SUCCESS: real browser-rendered 30/50/20 layout, preview:",dest.name)
if __name__=="__main__":build()
