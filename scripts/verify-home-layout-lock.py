#!/usr/bin/env python3
"""Fail closed when an automatic update changes the approved Home layout.

Editorial data in index.html, featured news, video feeds, article text and
images may keep updating. Structural Home CSS/JS and the foundational inline
Home stylesheet are locked. To change design later, an editor must intentionally
review and update this file and the multi-viewport browser checks together.
Runs both before and after the Cloudflare production build; no deployment.
"""
from __future__ import annotations
import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
LOCKED_BLOBS={
    "zt-home-live.js":"4fa8b5e8dfd87964b8d791cad6c771bff635f1c5",
    "zt-home-graphic-layout-20261016.css":"81d674a512a6074e3942049f3e5fad2413ad748e",
    "zt-home-graphic-layout-20261016.js":"d2f224d8eedf75b0ed711f5ba2ab106b5af6ed8f",
    "zt-home-gap-fix-20261014.css":"8db90af3c1bfb273b53f81c0ad7f1631cd82aacf",
}
# The daily editorial job may refresh this one JSON list in an otherwise locked JS file.
# Its structure is verified and the entire rest of the JS must retain the approved digest.
LOCKED_HOME_LIVE_TEMPLATE_SHA="c4d51afb4ae5139084d2d3c5fe97d670d7645b19"
INLINE_STYLE_FNV64="df1fab8ffc145811"
HOME_ASSET_REVISION="20261017stableColumnsRollback4"

class HomeLockError(RuntimeError):
    pass

def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def fnv64(text:str)->str:
    value=0xcbf29ce484222325
    for ch in text:
        value=((value^ord(ch))*0x100000001b3)&0xffffffffffffffff
    return f"{value:016x}"

def safe_editorial_js_sha(data: bytes) -> str | None:
    """Ignore *only* the valid sidebar article JSON, never executable JS changes."""
    import json
    try:
        source=data.decode("utf-8")
        matches=list(re.finditer(
            r"const sidebarEditorials=(\[[^\r\n]*\]);(?=\s*const editorialBox=)",
            source))
        if len(matches)!=1 or source.count("const sidebarEditorials=")!=1:
            return None
        items=json.loads(matches[0].group(1))
        if not isinstance(items,list) or not 1<=len(items)<=12:
            return None
        urls=set()
        for item in items:
            if not isinstance(item,dict) or set(item)!={"title","url","image"}:
                return None
            if not isinstance(item["title"],str) or not item["title"].strip():
                return None
            url=item["url"]
            img=item["image"]
            if not isinstance(url,str) or not re.fullmatch(r"/[a-zA-Z0-9_.-]+\.html",url) or url in urls:
                return None
            if not isinstance(img,str) or not (
                img.startswith("https://") or
                re.fullmatch(r"/assets/[a-zA-Z0-9_./-]+",img)
            ):
                return None
            urls.add(url)
        # Replacing exactly the data list also protects the layout, handlers and code
        # surrounding it. This fingerprint is fixed to the last approved Home script.
        cleaned=source[:matches[0].start(1)]+"__EDITORIAL_DATA_ONLY__"+source[matches[0].end(1):]
        return blob_sha(cleaned.encode("utf-8"))
    except (UnicodeError,ValueError,TypeError,KeyError):
        return None

class HomeElements(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids={}
        self.classes=set()
        self.js=[]
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if data.get("id"):
            key=data["id"]
            self.ids[key]=self.ids.get(key,0)+1
        self.classes.update((data.get("class") or "").split())
        if tag=="script" and data.get("src"):
            self.js.append(data["src"])

def verify(root:Path=ROOT, packaged:bool=False)->None:
    errors=[]
    for name,expected in LOCKED_BLOBS.items():
        path=root/name
        if not path.is_file():
            errors.append("Missing locked Home asset: "+name)
        elif name=="zt-home-live.js":
            if safe_editorial_js_sha(path.read_bytes())!=LOCKED_HOME_LIVE_TEMPLATE_SHA:
                errors.append("Unauthorized Home layout/code change: "+name)
        elif blob_sha(path.read_bytes())!=expected:
            errors.append("Unauthorized Home layout change: "+name)
    source=root/"index.html"
    if not source.is_file():
        errors.append("Missing canonical Home index.html")
    else:
        home=source.read_text(encoding="utf-8")
        style=re.search(r"<style\b[^>]*>(.*?)</style>",home,re.I|re.S)
        if not style or fnv64(style.group(1))!=INLINE_STYLE_FNV64:
            errors.append("Canonical Home inline layout CSS was modified")
        parser=HomeElements()
        parser.feed(home)
        for name in ("ztFeaturedGrid","articleList"):
            if parser.ids.get(name)!=1:
                errors.append(f"Home must contain exactly one #{name} (found {parser.ids.get(name,0)})")
        for marker in ("ARTICLE_FEED_START","ARTICLE_FEED_END",
                       "FEATURED_NEWS_START","FEATURED_NEWS_END",
                       "HOME_LATEST_REVIEWS_MAIN_START","HOME_LATEST_REVIEWS_MAIN_END"):
            if home.count("<!-- "+marker+" -->")!=1:
                errors.append("Home import/layout marker missing or duplicated: "+marker)
        for key in ("ztp-three-columns","ztp-news-tech","ztp-news-gaming",
                    "ztp-news-rail","ztp-two-news-columns"):
            if key not in home and key not in (root/"zt-home-live.js").read_text(encoding="utf-8"):
                errors.append("Critical Home column structure missing: "+key)
        if not any("/zt-home-live.js?v="+HOME_ASSET_REVISION in s for s in parser.js):
            errors.append("Wrong Home layout script cache revision")
        if not any("/zt-home-graphic-layout-20261016.js" in s for s in parser.js):
            errors.append("Approved Home magazine graphics not linked")
    if errors:
        raise HomeLockError("HOME LAYOUT LOCK FAILED:\n"+ "\n".join("- "+x for x in errors))
    label="packaged production snapshot" if packaged else "repository and generated source"
    print(f"HOME LAYOUT LOCK PASS ({label}): approved Home columns, CSS and JS unchanged; editorial news may refresh.")

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--packaged",action="store_true")
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    if args.self_test:
        assert blob_sha(b"a")=="2e65efe2a145dda7ee51d1741299f848e5bf752e"
        assert fnv64("")=="cbf29ce484222325"
        assert blob_sha(b"a")!=blob_sha(b"b")
        assert fnv64("x")!=fnv64("y")
        print("HOME LOCK SELF TEST PASS")
    else:
        verify(ROOT/"dist" if args.packaged else ROOT, packaged=args.packaged)

if __name__=="__main__":
    main()
