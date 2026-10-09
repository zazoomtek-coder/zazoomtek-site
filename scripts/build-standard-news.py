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
    page='''<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="canonical" href="https://zazoomtek.it/'''+article+'''"><title>'''+esc(title)+''' | ZazoomTek</title><meta name="description" content="'''+esc(x["summary"])+'''"><meta property="og:type" content="article"><meta property="og:title" content="'''+esc(title)+'''"><meta property="og:image" content="https://zazoomtek.it'''+article_img+'''"><style>body{margin:0;background:#10131a;color:#f1f2f5;font:17px/1.75 Arial,sans-serif}header{background:#191c24;padding:20px 5%;border-bottom:3px solid #df3243}header a{color:white;text-decoration:none;font-weight:bold}main{max-width:880px;margin:40px auto;padding:0 20px}h1{font-size:clamp(27px,4vw,43px);line-height:1.2}figure{margin:20px 0}figure img{display:block;width:100%;max-width:100%;height:auto;object-fit:contain;aspect-ratio:auto;border-radius:9px}figcaption{font-size:12px;color:#b9c1ca}figcaption a{color:#9ed8ff}.summary{font-size:20px;color:#c4cbd8}a{color:#8acfff}.meta{color:#f3a75b;font-size:13px}p{margin:20px 0}</style></head><body><header><a href="/">Zazoom<span style="color:#ee3447">Tek</span>.it</a> · <a href="/news.html">NEWS</a></header><main><div class="meta">NEWS · '''+esc(x["date"])+''' · '''+esc(x["kind"].upper())+'''</div><h1>'''+esc(title)+'''</h1><p class="summary">'''+esc(x["summary"])+'''</p><figure><img src="'''+article_img+'''" alt="'''+esc(title)+'''" loading="eager" decoding="async">'''+credit+'''</figure>'''+paragraphs+'''<p><a href="/news.html">← Torna alle NEWS</a></p></main></body></html>'''
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
