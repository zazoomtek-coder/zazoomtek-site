#!/usr/bin/env python3
"""ZazoomTek: sidebar editoriali con miniature e layout recensioni uniforme.
Preparazione dello snapshot prima del deploy; mai interventi su homepage o testi.
"""
from __future__ import annotations
import html
import random
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES={"news.html","recensioni-tech.html","recensioni-gaming.html",
          "recensioni-scritte.html","tech-today.html","gaming-today.html",
          "speciali.html","guide.html","extra.html"}
CSS_LINK='<link rel="stylesheet" href="/zt-unified-editorial.css?v=20261024">'
RAIL_START="<!-- ZT_UNIFIED_EDITORIAL_START -->"
RAIL_END="<!-- ZT_UNIFIED_EDITORIAL_END -->"
ASIDE_RE=re.compile(r'(?is)<aside\b(?=[^>]*\bclass=["\'][^"\']*(?:news-sidebar|article-side|zt-ec-auto-rail)[^"\']*["\'])[^>]*>')
TITLE_RE=re.compile(r'(?is)<h1\b[^>]*>(.*?)</h1>')
IMAGE_RE=re.compile(r'(?is)<meta\b[^>]*\bproperty=["\']og:image["\'][^>]*\bcontent=["\']([^"\']+)')
FIRST_IMG=re.compile(r'(?is)<img\b[^>]*\bsrc=["\']([^"\']+)')
DATE_RE=re.compile(r'(?i)(20\d\d-\d\d-\d\d)')

def clean(value):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]*>","",value or ""))).strip()

def cover_from(text):
    """Read og:image regardless of HTML attribute order; never use header logo."""
    src=""
    for tag in re.findall(r"<meta\b[^>]*>",text,re.I):
        if not re.search(r'property=["\']og:image["\']',tag,re.I):
            continue
        m=re.search(r'content=["\']([^"\']+)',tag,re.I)
        if m:src=html.unescape(m.group(1)).strip();break
    if not src:
        main=re.search(r"(?is)<main\b",text)
        fragment=text[main.start():] if main else ""
        for tag in re.findall(r"<img\b[^>]*>",fragment,re.I):
            if re.search(r'class=["\'][^"\']*(?:hero|cover|article-image)[^"\']*["\']',tag,re.I):
                m=re.search(r'src=["\']([^"\']+)',tag,re.I)
                if m:src=html.unescape(m.group(1)).strip();break
    if not src:return ""
    if src.startswith("/") and not (ROOT/src.lstrip("/")).is_file():return ""
    return src if src.startswith(("https://","/")) else ""

def stories():
    found={}
    for path in ROOT.glob("*.html"):
        if path.name in ARCHIVES or path.name=="index.html" or path.name.startswith(("anteprima-","watch-")):
            continue
        try:doc=path.read_text(encoding="utf-8")
        except UnicodeError:continue
        match=TITLE_RE.search(doc)
        if not match:continue
        title=clean(match.group(1));cover=cover_from(doc)
        if not title or not cover:continue
        date=DATE_RE.search(doc)
        found[path.name]={"href":"/"+path.name,"title":title,"cover":cover,
                          "date":date.group(1) if date else ""}
    return found

def card(item,cls):
    title=html.escape(item["title"],quote=True)
    return ('<a class="'+cls+'" href="'+html.escape(item["href"],quote=True)+'">'
            '<img src="'+html.escape(item["cover"],quote=True)+'" alt="'+title+
            '" loading="lazy" decoding="async"><span><strong>'+title+'</strong></span></a>')

def build_rail(pool,path,article):
    now=datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    entries=[v for name,v in pool.items() if name!=path]
    # Permutazione editoriale giornaliera: casuale, ripetibile nell'unico rilascio
    # e senza duplicare titoli oppure link all'interno della pagina.
    random.Random(now+":"+path).shuffle(entries)
    unique=[];seen=set()
    for entry in entries:
        key=clean(entry["title"]).casefold()
        if key in seen:continue
        seen.add(key);unique.append(entry)
    # Fino al fondo del corpo articolo: aumenta le miniature con la lunghezza.
    text_length=len(clean(re.sub(r"(?is)<(?:script|style)\b.*?</(?:script|style)>","",article)))
    img_count=len(re.findall(r"<img\b",article,re.I))
    wanted=max(12,(text_length//255)+img_count*2)
    # Riservare, se possibile, 4 collegamenti diversi per i correlati in fondo.
    available=max(0,len(unique)-4)
    selected=unique[:min(wanted,available)]
    others=unique[len(selected):len(selected)+4]
    boxes=[]
    for i in range(0,len(selected),7):
        group=selected[i:i+7]
        heading="ULTIME NOTIZIE" if i==0 else ("DA NON PERDERE" if i==7 else "DALLA REDAZIONE")
        boxes.append('<section class="zt-ue-rail side-box"><h2>'+heading+
                     '</h2><div class="zt-ue-rail-list">'+
                     "".join(card(v,"zt-ue-card") for v in group)+'</div></section>')
    related=('<section class="zt-ue-related side-box"><h2>ARTICOLI CORRELATI</h2>'+
             '<div class="zt-ue-related-list">'+
             "".join(card(v,"zt-ue-card") for v in others)+'</div></section>') if others else ""
    return RAIL_START+"".join(boxes)+related+RAIL_END

def update(path,pool):
    document=path.read_text(encoding="utf-8")
    if "<main" not in document.lower():return False
    if path.name not in ARCHIVES and not TITLE_RE.search(document):return False
    match=ASIDE_RE.search(document)
    if not match:return False
    # Elimina solo i rail generati in precedenza, non il corpo editoriale.
    doc=re.sub(r'(?s)<!-- ZT_UNIFIED_EDITORIAL_START -->.*?<!-- ZT_UNIFIED_EDITORIAL_END -->',"",document)
    doc=re.sub(r'(?s)<!-- ZT_EDITORIAL_RAIL_START -->.*?<!-- ZT_EDITORIAL_RAIL_END -->',"",doc)
    doc=re.sub(r'(?s)<!-- ZT_EDITORIAL_RELATED_START -->.*?<!-- ZT_EDITORIAL_RELATED_END -->',"",doc)
    match=ASIDE_RE.search(doc)
    if not match:return False
    stop=doc.find("</aside>",match.end())
    if stop<0:return False
    aside=doc[match.end():stop]
    # I vecchi box misti senza immagini non sono box editoriali fotografici.
    aside=re.sub(r'(?is)<section\b[^>]*class=["\'][^"\']*\bzt-mix-(?:feature|recent|video|editorial)\b[^"\']*["\'][^>]*>.*?</section>',"",aside)
    def keep_pictured(m):
        fragment=m.group(0)
        return fragment if re.search(r'<(?:img|iframe|video)\b',fragment,re.I) or "zt-amazon-partner" in fragment else ""
    aside=re.sub(r'(?is)<section\b[^>]*class=["\'][^"\']*\bside-box\b[^"\']*["\'][^>]*>.*?</section>',keep_pictured,aside)
    main_head=doc.find("<main")
    main_end=doc.find("</main>",main_head) if main_head>=0 else -1
    if main_end<0:main_end=stop
    editorial_body=doc[main_head:main_end]
    rail=build_rail(pool,path.name,editorial_body)
    opening=doc[match.start():match.end()]
    if "zt-unified-editorial-aside" not in opening:
        opening=re.sub(r'(class=["\'])',r'\1zt-unified-editorial-aside ',opening,count=1)
    doc=doc[:match.start()]+opening+aside+rail+doc[stop:]
    if CSS_LINK not in doc and "</head>" in doc:doc=doc.replace("</head>",CSS_LINK+"\n</head>",1)
    # Tutte le recensioni Tech/Gaming condividono le geometrie e i box voto
    # della A900 Ultra. Non modificare le sezioni editoriali, le immagini o i voti.
    if "recensione" in path.stem.lower() and path.name not in ARCHIVES:
        tag=re.search(r"<body\b[^>]*>",doc,re.I)
        if tag and "zt-a900-unified-review" not in tag.group(0):
            opening=tag.group(0)
            if re.search(r'\bclass=["\']',opening,re.I):
                opening=re.sub(r'(class=["\'])',r'\1zt-a900-unified-review ',opening,count=1)
            else:
                opening=re.sub(r"(?i)<body\b",'<body class="zt-a900-unified-review"',opening,count=1)
            doc=doc[:tag.start()]+opening+doc[tag.end():]
    if doc!=document:path.write_text(doc,encoding="utf-8")
    return doc!=document

def run():
    pool=stories();changed=0
    for path in ROOT.glob("*.html"):
        if path.name=="index.html" or path.name.startswith("anteprima-"):continue
        changed+=int(update(path,pool))
    print("Unified image editorials:",changed,"pages, available genuine covers:",len(pool))

if __name__=="__main__":
    run()
