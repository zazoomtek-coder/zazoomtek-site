#!/usr/bin/env python3
"""Publish only approved standalone NEWS, without changing YouTube importers."""
import html,json,re,datetime as dt,io
from PIL import Image,ImageOps
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parent.parent
data=json.loads((ROOT/"standard-news.json").read_text(encoding="utf-8"))["articles"]
spec=importlib.util.spec_from_file_location("cover",ROOT/"scripts/build-special-covers.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
manifest_path=ROOT/"standard-cover-manifest.json"
manifest=json.loads(manifest_path.read_text(encoding="utf-8")).get("articles",{}) if manifest_path.exists() else {}
items=[]
for x in data:
    slug=x["slug"]
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug):raise ValueError(slug)
    title=x["title"]
    if len(x["paragraphs"])<4:raise ValueError("Not enough editorial content")
    key="standard/"+slug
    img="/assets/special/news-"+slug+".webp"
    file=ROOT/img.lstrip("/")
    # For mainstream games use original subject-labelled editorial artwork.
    # General Commons search can return legally reusable but misleading images
    # (e.g. unrelated buildings); avoid that for these titles.
    must_draw=(not file.exists()) or bool(x.get("cover_refresh"))
    if must_draw:
        photo,rights=mod.commons_cc0({**x,"section":x["kind"]})
        if photo is None or rights is None:
            raise RuntimeError("Missing rights-cleared photographic cover: "+slug)
        file.parent.mkdir(parents=True,exist_ok=True)
        file.write_bytes(mod.encode(mod.render({**x,"section":x["kind"]},photo)))
        manifest[key]={"path":img,"origin":rights or {"origin":"ZazoomTek original graphic","license":"Original in-house art"}}
        print("Verified WebP:",img,file.stat().st_size,"bytes")
    if key not in manifest or manifest[key].get("path")!=img:
        raise RuntimeError("Missing copyright provenance for cover: "+img)
    if file.stat().st_size>300000:raise ValueError("Cover too large")
    esc=lambda t:html.escape(str(t),quote=True)
    credit=""
    origin=manifest.get(key,{}).get("origin",{})
    if origin.get("license","").upper().startswith("CC BY") and origin.get("source_page","").startswith("https://commons.wikimedia.org/wiki/"):
        credit='<figcaption>Foto: '+esc(origin.get("photographer","Autore Wikimedia Commons"))+' · <a href="'+esc(origin["source_page"])+'">Wikimedia Commons</a> · <a href="'+esc(origin["license_url"])+'">'+esc(origin["license"])+'</a> · fotografia originale senza sovrapposizioni grafiche</figcaption>'
    note=x.get("image_note","")
    if note:
        credit += '<figcaption>'+esc(note)+'</figcaption>'
    # Keep clean, uncropped photographs in articles; editorial headline covers
    # are only for homepage/NEWS lists and are not inserted into article bodies.
    article_img="/assets/special/article-"+slug+".webp"
    clean_file=ROOT/article_img.lstrip("/")
    if not clean_file.is_file() or x.get("article_image_refresh"):
        photo,clean_rights=mod.commons_cc0({**x,"section":x["kind"]})
        if photo is None or clean_rights is None or clean_rights.get("file")!=origin.get("file"):
            raise RuntimeError("Cannot verify original article photograph rights: "+slug)
        clean=ImageOps.contain(photo,(1280,900),Image.Resampling.LANCZOS)
        clean_file.parent.mkdir(parents=True,exist_ok=True)
        buf=io.BytesIO()
        for quality in (83,77,70,62,54,46,38):
            buf.seek(0);buf.truncate()
            clean.save(buf,"WEBP",quality=quality,method=6)
            if buf.tell()<=300000:break
        else:
            raise RuntimeError("Article photograph exceeds 300 KB: "+slug)
        clean_file.write_bytes(buf.getvalue())
        print("Verified clean article photo:",article_img,clean_file.stat().st_size)
    if clean_file.stat().st_size > 300000:
        raise RuntimeError("Article photo too large: "+slug)
    article="news-"+slug+".html"
    paragraphs="".join("<p>"+esc(p)+"</p>" for p in x["paragraphs"])
    page='''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="https://zazoomtek.it/'''+article+'''"><title>'''+esc(title)+''' | ZazoomTek</title><meta name="description" content="'''+esc(x["summary"])+'''"><meta property="og:type" content="article"><meta property="og:title" content="'''+esc(title)+'''"><meta property="og:image" content="https://zazoomtek.it'''+article_img+'''"><style>*{box-sizing:border-box}body{margin:0;background:#10141b;color:#edf1f6;font:18px/1.8 Arial,Helvetica,sans-serif}a{color:#9bd8ff}.site-header{background:#171717;border-top:4px solid #d51232;border-bottom:1px solid #333}.site-bar{width:min(1480px,calc(100% - 24px));min-height:84px;margin:auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}.site-brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:#fff;font-size:24px;font-weight:bold}.site-brand img{width:52px;height:52px;object-fit:cover;border-radius:8px}.site-brand em{color:#ef344f;font-style:normal}.site-nav{display:flex;align-items:center;flex-wrap:wrap;gap:3px}.site-nav a{display:inline-flex;padding:13px 12px;text-decoration:none;color:#f3f3f3;font-size:13px;font-weight:bold;text-transform:uppercase}.site-nav a.active,.site-nav a:hover{background:#d51232;color:#fff}.article{width:min(1100px,calc(100% - 36px));margin:38px auto 72px}.breadcrumb{font-size:13px;color:#bdc9d6;margin:0 0 25px}.breadcrumb a{color:#c5d5e6;text-decoration:none}.meta{font-size:13px;color:#f4ad62;font-weight:bold;letter-spacing:.04em}.article h1{font-size:clamp(30px,3.5vw,50px);line-height:1.18;margin:16px 0 24px;letter-spacing:-.02em}.summary{font-size:clamp(18px,1.65vw,22px);color:#ccd7e5;line-height:1.6;margin:0 0 26px}.article-figure{margin:24px 0 32px}.article-figure img{display:block;width:100%;height:auto;aspect-ratio:auto;max-width:100%;object-fit:contain;border-radius:10px;background:#1b2330}.article-figure figcaption{font-size:12px;line-height:1.6;color:#afbac9;margin-top:8px}.article-figure figcaption a{color:#9dd9ff}.article-body{max-width:1000px;margin:auto}.article-body p{font-size:18px;line-height:1.85;margin:0 0 23px}.back-link{display:inline-block;background:#d51232;color:#fff;text-decoration:none;font-weight:bold;padding:13px 18px;border-radius:4px;margin-top:22px}.site-footer{background:#171717;border-top:1px solid #303640;color:#bcc7d4;padding:25px;text-align:center;font-size:14px}.site-footer a{color:#e3edf8}@media(max-width:900px){.site-bar{justify-content:center;padding:10px 0}.site-nav{justify-content:center}.site-nav a{font-size:12px;padding:9px}}@media(max-width:580px){.article{width:calc(100% - 26px);margin:22px auto 40px}.site-brand{font-size:21px}.site-brand img{width:45px;height:45px}.site-nav a{font-size:11px;padding:7px}.article-body p{font-size:17px}}</style></head><body><header class="site-header"><div class="site-bar"><a class="site-brand" href="/"><img src="/ChatGPT.png" width="52" height="52" alt=""><span>Zazoom<em>Tek</em></span></a><nav class="site-nav" aria-label="Menu principale"><a href="/">Home</a><a class="active" href="/news.html">News</a><a href="/recensioni-scritte.html">Recensioni</a><a href="/tech-today.html">Tech Impact</a><a href="/gaming-today.html">Gaming Inside</a><a href="https://www.youtube.com/@ZazoomTek/posts">Community</a><a href="https://www.youtube.com/@ZazoomTek/videos">Video</a></nav></div></header><main class="article"><nav class="breadcrumb" aria-label="Percorso"><a href="/">Home</a> › <a href="/news.html">News</a> › Articolo</nav><div class="meta">NEWS · '''+esc(x["date"])+''' · '''+esc(x["kind"].upper())+'''</div><h1>'''+esc(title)+'''</h1><p class="summary">'''+esc(x["summary"])+'''</p><figure class="article-figure"><img src="'''+article_img+'''" alt="'''+esc(title)+'''" loading="eager" decoding="async">'''+credit+'''</figure><div class="article-body">'''+paragraphs+'''</div><a class="back-link" href="/news.html">← Torna a tutte le News</a></main><footer class="site-footer">ZazoomTek · Tech · Gaming · Community · <a href="/">Home</a> · <a href="/news.html">News</a></footer></body></html>'''
    (ROOT/article).write_text(page,encoding="utf-8")
    items.append({"slug":article,"title":title,"image":img,"excerpt":x["summary"],"date":x["date"],"kind":x["kind"]})
# Preserve all older independently authored NEWS and their ordering.
manual_path=ROOT/"manual-news.json"
previous=[]
if manual_path.is_file():
    previous=json.loads(manual_path.read_text(encoding="utf-8")).get("items",[])
used={item["slug"] for item in items}
items.extend(item for item in previous if isinstance(item,dict) and item.get("slug") not in used)
manual_path.write_text(json.dumps({"items":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(ROOT/"standard-cover-manifest.json").write_text(json.dumps({"articles":manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Built",len(items),"NEWS with WebP covers")
