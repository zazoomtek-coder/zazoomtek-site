#!/usr/bin/env python3
"""Independent reviews catalog, preserving all existing articles and layouts.

Discovers existing review pages and appends only missing cards to Tech/Gaming
indexes. Never rewrites review bodies, pictures, scores or written copy.
"""
from __future__ import annotations
import html
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
START="<!-- SERVICES10_NEW_REVIEWS_START -->"
END="<!-- SERVICES10_NEW_REVIEWS_END -->"
ARCHIVES=("recensioni-tech.html","recensioni-gaming.html","recensioni-scritte.html")

def discover(root:Path=ROOT)->list[dict]:
    found=[]
    for path in root.glob("*.html"):
        name=path.name
        if ("recensione" not in name.lower() or
                name in ARCHIVES or name.startswith("recensioni-") or
                name.startswith("anteprima-")):
            continue
        try:page=path.read_text(encoding="utf-8")
        except UnicodeError:continue
        match=re.search(r'<h1\b[^>]*>([\s\S]*?)</h1>',page,re.I)
        title=html.unescape(re.sub(r'<[^>]+>','',match.group(1))).strip() if match else ""
        if not title:continue
        image=re.search(r'<meta\b[^>]*property=["\x27]og:image["\x27][^>]*content=["\x27]([^"\x27]+)',page,re.I)
        picture=html.unescape(image.group(1)) if image else ""
        sample=title+" "+page[page.find("<main"):page.find("<main")+1800]
        gaming=bool(re.search(r'\b(PS[45]|Xbox|Switch|Nintendo|Steam|PlayStation|videogiochi?|gameplay|PC)\b',sample,re.I))
        found.append({"url":"/"+name,"title":title,
                      "image":picture,"section":"gaming" if gaming else "tech"})
    return found

def card(item:dict)->str:
    link=html.escape(item["url"],quote=True)
    title=html.escape(item["title"],quote=True)
    image=('<a href="'+link+'"><img src="'+html.escape(item["image"],quote=True)+
           '" alt="'+title+'" loading="lazy"></a>' if item["image"] else "")
    return ('<article class="news-row">'+image+'<div class="news-copy"><h2><a href="'+
            link+'">'+title+'</a></h2><div class="news-meta">ZazoomTek · Recensioni '+
            item["section"].title()+'</div><a class="news-read" href="'+link+
            '">Leggi la recensione ›</a></div></article>')

def update(root:Path=ROOT)->dict:
    reviews=discover(root)
    additions={}
    for filename in ARCHIVES:
        path=root/filename
        if not path.is_file():continue
        section="gaming" if filename=="recensioni-gaming.html" else (
            "tech" if filename=="recensioni-tech.html" else None)
        page=path.read_text(encoding="utf-8")
        outside=page
        if START in outside and END in outside:
            a=outside.index(START)
            b=outside.index(END,a)+len(END)
            outside=outside[:a]+outside[b:]
        candidates=[r for r in reviews if (not section or r["section"]==section)
                    and 'href="'+r["url"]+'"' not in outside]
        fragment="\n".join(card(r) for r in candidates)
        if START in page and END in page:
            a=page.index(START);b=page.index(END,a)+len(END)
            rendered=page[:a]+START+"\n"+fragment+"\n"+END+page[b:]
        elif fragment:
            rendered=page.replace('<div class="news-list" id="reviewList">',
                     '<div class="news-list" id="reviewList">\n'+START+"\n"+fragment+
                     "\n"+END,1)
        else:rendered=page
        if rendered!=page:path.write_text(rendered,encoding="utf-8")
        additions[filename]=len(candidates)
    print("Review indexes synchronized:",additions)
    return additions

if __name__=="__main__":
    update()
