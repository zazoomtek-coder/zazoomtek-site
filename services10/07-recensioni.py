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
    image=('<a href="'+link+'"><img src="'+html.escape(item["image"] or "/ChatGPT.png",quote=True)+
           '" alt="'+title+'" loading="lazy" decoding="async"></a>')
    return ('<article class="news-row">'+image+'<div class="news-copy"><h2><a href="'+
            link+'">'+title+'</a></h2><div class="news-meta">ZazoomTek · Recensioni '+
            item["section"].title()+'</div><a class="news-read" href="'+link+
            '">Leggi la recensione ›</a></div></article>')

# Conservative, content-local de-duplication. Do not change review bodies.
ROWS=re.compile(r'<article\b(?=[^>]*\bclass=["\'][^"\']*\bnews-row\b)[^>]*>[\s\S]*?</article>',re.I)
HEAD=re.compile(r'<h2[^>]*>\s*<a[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>\s*</h2>',re.I)
IMG=re.compile(r'<img\b[^>]*>',re.I)
SRC=re.compile(r'\bsrc=["\']([^"\']*)["\']',re.I)

def normalized(value:str)->str:
    return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]*>','',value))).strip().casefold()

def valid_art(value:str,root:Path)->bool:
    src=html.unescape(value or '').strip()
    return (src.startswith(('https://','http://','data:image/'))
            or (src.startswith('/') and (root/src.lstrip('/')).is_file()))

def review_scope(page:str)->tuple[int,int]:
    head=re.search(r'<div\b[^>]*\bid=["\']reviewList["\'][^>]*>',page,re.I)
    if not head:return 0,0
    end=page.find('<!-- ZT_COMMUNITY_BANNER_START -->',head.end())
    if end<0:end=page.find('</section>',head.end())
    return head.end(),end if end>=head.end() else head.end()

def repair_rows(page:str,root:Path,all_reviews:list[dict])->tuple[str,int,int]:
    begin,end=review_scope(page)
    if end<=begin:return page,0,0
    known={item['url'].casefold():item for item in all_reviews}
    seen_url=set();seen_title=set()
    duplicates=0;covers=0
    def repair(match):
        nonlocal duplicates,covers
        row=match.group(0)
        h=HEAD.search(row)
        if not h:return row
        link=h.group(1).split('?',1)[0].split('#',1)[0]
        title=normalized(h.group(2))
        if link.casefold() in seen_url or (title and title in seen_title):
            duplicates+=1
            return ''
        seen_url.add(link.casefold())
        if title:seen_title.add(title)
        cover=IMG.search(row)
        src=SRC.search(cover.group(0)) if cover else None
        image=html.unescape(src.group(1)) if src else ''
        if not valid_art(image,root):
            item=known.get(link.casefold())
            photo=item['image'] if item and valid_art(item.get('image',''),root) else '/ChatGPT.png'
            safe=html.escape(photo,quote=True)
            if cover:
                tag=cover.group(0)
                updated=SRC.sub('src="'+safe+'"',tag,count=1) if src else tag[:-1]+' src="'+safe+'">'
                row=row[:cover.start()]+updated+row[cover.end():]
            else:
                img='<a href="'+html.escape(link,quote=True)+'"><img src="'+safe+'" alt="'+html.escape(html.unescape(re.sub(r"<[^>]+>","",h.group(2))),quote=True)+'" loading="lazy" decoding="async"></a>'
                i=row.find('>')+1
                row=row[:i]+img+row[i:]
            covers+=1
        cover=IMG.search(row)
        if cover and not re.search(r'\balt=["\'][^"\']+["\']',cover.group(0),re.I):
            tag=cover.group(0)
            alt=html.escape(html.unescape(re.sub(r'<[^>]+>','',h.group(2))),quote=True)
            row=row[:cover.start()]+tag[:-1]+' alt="'+alt+'">'+row[cover.end():]
        return row
    cleaned=ROWS.sub(repair,page[begin:end])
    return page[:begin]+cleaned+page[end:],duplicates,covers

def update(root:Path=ROOT)->dict:
    reviews=discover(root)
    additions={};removed=0;restored=0
    for filename in ARCHIVES:
        path=root/filename
        if not path.is_file():continue
        section="gaming" if filename=="recensioni-gaming.html" else (
            "tech" if filename=="recensioni-tech.html" else None)
        page=path.read_text(encoding="utf-8")
        page,dupes,covers=repair_rows(page,root,reviews)
        removed+=dupes;restored+=covers
        outside=page
        if START in outside and END in outside:
            a=outside.index(START)
            b=outside.index(END,a)+len(END)
            outside=outside[:a]+outside[b:]
        a,b=review_scope(outside)
        scoped=outside[a:b]
        seen_urls={x.group(1).split('?',1)[0].casefold() for x in HEAD.finditer(scoped)}
        seen_names={normalized(x.group(2)) for x in HEAD.finditer(scoped)}
        candidates=[]
        for r in reviews:
            if section and r["section"]!=section:continue
            u=r["url"].casefold();t=normalized(r["title"])
            if u in seen_urls or not t or t in seen_names:continue
            candidates.append(r)
            seen_urls.add(u);seen_names.add(t)
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
    print("Review indexes synchronized:",additions,"duplicates removed:",removed,"covers recovered:",restored)
    return additions

if __name__=="__main__":
    update()
