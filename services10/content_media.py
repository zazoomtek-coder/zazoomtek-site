#!/usr/bin/env python3
"""Shared source-first article cover + editorial snippet extractor.

Priority: OG/hero metadata, then the actual article's leading <img>,
<picture>, lazy image, CSS cover or video poster. A broken remote image can
retry the article-internal backup before falling back to local editorial SVG.
No user text is synthesized and no remote downloads are required.
"""
from __future__ import annotations
import html
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

FALLBACK="/assets/zt-editorial-fallback.svg"
SKIP_IMAGE=("logo","avatar","icon","sprite","1x1","pixel","tracker","blank.gif")
TAG_ATTR=re.compile(r'([:\w-]+)\s*=\s*(["\'])(.*?)\2',re.S)
META=re.compile(r'<meta\b[^>]*>',re.I)
P=re.compile(r'<p\b[^>]*>(.*?)</p>',re.I|re.S)
IMG=re.compile(r'<(?:img|source|video)\b[^>]*>',re.I)
TAGS=re.compile(r'<[^>]*>')
SPACE=re.compile(r'\s+')

def strip_markup(data:str)->str:
    data=re.sub(r'(?is)<(?:script|style|nav|footer|aside)\b[^>]*>.*?</(?:script|style|nav|footer|aside)>'," ",data)
    return SPACE.sub(" ",html.unescape(TAGS.sub(" ",data))).strip()

def attrs(fragment:str)->dict:
    return {k.lower():html.unescape(v) for k,_,v in TAG_ATTR.findall(fragment)}

def media_url(value:str,root:Path|None=None)->str:
    url=html.unescape(str(value or "").strip())
    if not url:return ""
    if url.startswith("//"):url="https:"+url
    if url.lower().startswith(("data:","javascript:","blob:")):return ""
    if url.startswith("https://"):
        if any(word in url.lower() for word in SKIP_IMAGE):return ""
        return url
    if url.startswith("http://"):
        return "https://"+url[7:]
    if not url.startswith("/"):url="/"+url.lstrip("./")
    if re.search(r"\.(?:svg|png|jpe?g|webp|gif|avif)(?:[?#]|$)",url,re.I) is None:return ""
    if any(word in url.lower() for word in SKIP_IMAGE):return ""
    if root is not None and not (root/url.split("?")[0].lstrip("/")).is_file():
        return ""
    return url

def first_of_srcset(source:str)->str:
    return str(source or "").split(",")[0].strip().split(" ")[0]

def cover_candidates(document:str,root:Path|None=None)->list[str]:
    main=re.search(r'<(?:main|article)\b[^>]*>',document,re.I)
    fragment=document[main.end():] if main else document
    cutoff=re.search(r'</main>',fragment,re.I)
    if cutoff:fragment=fragment[:cutoff.start()]
    candidates=[]
    # Prefer hero/cover-like images first; then actual body images.
    for element in IMG.findall(fragment):
        values=attrs(element)
        class_name=(values.get("class","")+" "+values.get("id","")).lower()
        if any(tag in class_name for tag in ("avatar","icon","logo","sprite","side-")):continue
        if values.get("width") in ("0","1") or values.get("height") in ("0","1"):continue
        raw=(values.get("src") or values.get("data-src") or
             values.get("data-lazy-src") or values.get("poster") or
             first_of_srcset(values.get("data-srcset") or values.get("srcset") or ""))
        # An img with a placeholder src but real data-src should prefer data-src.
        if "lazy" in class_name and values.get("data-src"):raw=values["data-src"]
        url=media_url(raw,root)
        if url and url not in candidates:candidates.append(url)
    # Inline cover backgrounds are legitimate only within main/article.
    for raw in re.findall(r'(?i)background(?:-image)?\s*:\s*url\(["\']?([^)"\']+)',fragment):
        url=media_url(raw,root)
        if url and url not in candidates:candidates.append(url)
    return candidates

def metadata(document:str)->tuple[str,str]:
    image="";description=""
    head=document.split("</head>",1)[0]
    for m in META.finditer(head):
        a=attrs(m.group())
        key=(a.get("property") or a.get("name") or "").lower()
        if key in ("og:image","twitter:image") and not image:
            image=a.get("content","")
        if key in ("description","og:description","twitter:description") and not description:
            description=strip_markup(a.get("content",""))
    return image,description

def lead_text(document:str,max_chars:int=215)->str:
    _,desc=metadata(document)
    if len(desc)>=35:return desc[:max_chars].rstrip()
    article=re.search(r'<(?:article|main)\b[^>]*>',document,re.I)
    relevant=document[article.end():] if article else document
    # Any approved paragraph of at least 40 characters is suitable.
    for found in P.finditer(relevant):
        lead=strip_markup(found.group(1))
        if len(lead)>=40 and not re.match(r'(?i)^(cookie|privacy|iscriviti|acquista)',lead):
            return lead[:max_chars].rstrip()
    return desc[:max_chars] if desc else ""

def extract(document:str,root:Path|None=None)->dict[str,str]:
    og,description=metadata(document)
    body_images=cover_candidates(document,root)
    main=body_images[0] if body_images else ""
    meta_image=media_url(og,root)
    image=meta_image or main or FALLBACK
    backup=next((url for url in body_images if url!=image),FALLBACK)
    return {"image":image,"image_fallback":backup,
            "snippet":lead_text(document),"body_image":main}

def from_file(file:Path,root:Path|None=None)->dict[str,str]:
    try:return extract(file.read_text(encoding="utf-8",errors="replace"),root)
    except OSError:return {"image":FALLBACK,"image_fallback":FALLBACK,"snippet":"","body_image":""}
