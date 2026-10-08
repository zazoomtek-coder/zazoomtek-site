#!/usr/bin/env python3
import html
import json
import re
from pathlib import Path

ROOT=Path(".")
OUT=ROOT/"search-index.json"

def clean_text(value):
    text=re.sub(r"<script\b[^>]*>[\s\S]*?</script>"," ",value,flags=re.I)
    text=re.sub(r"<style\b[^>]*>[\s\S]*?</style>"," ",text,flags=re.I)
    text=re.sub(r"<[^>]+>"," ",text)
    text=html.unescape(text)
    return re.sub(r"\s+"," ",text).strip()

def meta(content,name=None,prop=None):
    if name:
        patterns=[
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)',
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]
    else:
        patterns=[
            rf'<meta[^>]+property=["\']{re.escape(prop or "")}["\'][^>]+content=["\']([^"\']*)',
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']{re.escape(prop or "")}["\']',
        ]
    for p in patterns:
        m=re.search(p,content,re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""

def title_of(content):
    og=meta(content,prop="og:title")
    if og:
        return og
    m=re.search(r"<title[^>]*>(.*?)</title>",content,re.I|re.S)
    return clean_text(m.group(1)) if m else ""

def desc_of(content):
    d=meta(content,name="description") or meta(content,prop="og:description")
    if d:
        return clean_text(d)[:420]
    m=re.search(r'<(?:main|article)\b[^>]*>([\s\S]*?)</(?:main|article)>',content,re.I)
    return clean_text(m.group(1))[:420] if m else ""

def image_of(content):
    return meta(content,prop="og:image")

def editorial_type(path):
    n=path.name.lower()
    if n.startswith("news-"):
        return "News"
    if n.startswith("recensione-") or "recensione" in n:
        return "Recensione"
    return "Pagina"

def add_html(items,path,kind=None):
    try:
        content=path.read_text(encoding="utf-8",errors="replace")
    except Exception:
        return
    item_type=kind or editorial_type(path)
    title=title_of(content)

    # Legacy Community posts sometimes generated a generic "News" page title
    # while the real headline is the first paragraph of the article body.
    if item_type=="News" and clean_text(title).lower() in ("news","news | zazoomtek"):
        body=re.search(r'<div class="article-body">([\s\S]*?)</div>',content,re.I)
        if body:
            first_p=re.search(r'<p[^>]*>([\s\S]*?)</p>',body.group(1),re.I)
            if first_p:
                candidate=clean_text(first_p.group(1))
                if candidate:
                    title=candidate

    if not title:
        return
    items.append({
        "id":"page:"+path.name,
        "type":item_type,
        "title":title,
        "excerpt":desc_of(content),
        "url":"/"+path.name,
        "image":image_of(content),
        "category":"",
        "published":"",
    })

def main():
    items=[]
    seen=set()

    # Individual editorial pages are the highest-value site search results.
    for pattern in ("news-Ugkx*.html","recensione-Ugkx*.html"):
        for path in sorted(ROOT.glob(pattern)):
            if path.name in seen:
                continue
            seen.add(path.name)
            add_html(items,path)

    special=ROOT/"nba-2k27-recensione-ps5.html"
    if special.exists() and special.name not in seen:
        seen.add(special.name)
        add_html(items,special,"Recensione")

    # Important permanent site sections.
    main_pages={
        "news.html":"Sezione",
        "recensioni-scritte.html":"Sezione",
        "gaming.html":"Sezione",
        "recensioni.html":"Sezione",
        "test.html":"Sezione",
        "unboxing.html":"Sezione",
        "chi-sono.html":"Pagina",
        "contatti.html":"Pagina",
    }
    for filename,kind in main_pages.items():
        p=ROOT/filename
        if p.exists():
            add_html(items,p,kind)

    # All YouTube uploads are searchable too. They link to the most relevant
    # section of ZazoomTek when a category exists, otherwise to YouTube.
    state=ROOT/".youtube-latest.json"
    if state.exists():
        try:
            videos=json.loads(state.read_text(encoding="utf-8"))
        except Exception:
            videos=[]
        page_for={
            "gaming":"/gaming.html",
            "recensioni":"/recensioni.html",
            "test":"/test.html",
            "unboxing":"/unboxing.html",
            "analogiktek":"/",
        }
        label_for={
            "gaming":"Gaming",
            "recensioni":"Video Recensione",
            "test":"Video Test",
            "unboxing":"Unboxing",
            "analogiktek":"AnalogikTek",
        }
        for v in videos:
            if not isinstance(v,dict) or not v.get("id") or not v.get("title"):
                continue
            vid=v["id"]
            cat=v.get("category")
            url=page_for.get(cat) or f"https://www.youtube.com/watch?v={vid}"
            items.append({
                "id":"video:"+vid,
                "type":label_for.get(cat,"Video"),
                "title":v.get("title",""),
                "excerpt":"Video pubblicato sul canale YouTube ZazoomTek.",
                "url":url,
                "external":cat is None,
                "image":f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "category":cat or "",
                "published":v.get("publishedAt",""),
            })

    # Stable deduplication.
    unique=[]
    ids=set()
    for item in items:
        if item["id"] in ids:
            continue
        ids.add(item["id"])
        unique.append(item)

    if len(unique)<50:
        raise RuntimeError(f"Search index unexpectedly small: {len(unique)} entries")

    OUT.write_text(json.dumps(unique,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(f"Search index built: {len(unique)} entries")

if __name__=="__main__":
    main()
