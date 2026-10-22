#!/usr/bin/env python3
"""Rebuild the unified Cybercultura archive from the two existing public archives.
The legacy pages and article URLs are never deleted, redirected or noindexed.
Run inside the existing Cloudflare site build after the category generators.
"""
from __future__ import annotations
import html
import json
from pathlib import Path
import re
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
ARCHIVES=(("tech-today.html","Tech Impact"),("gaming-today.html","Gaming Inside"))
TARGET=ROOT/"cybercultura.html"
ROW=re.compile(r'<article\b[^>]*class="[^"]*\bnews-row\b[^"]*"[^>]*>.*?</article>', re.I|re.S)
URL=re.compile(r'<a\b[^>]*href="(/(?:news-|tech-impact-|gaming-inside-)[^"#?]+\.html)"',re.I)
LIST=re.compile(r'(<div\b[^>]*class="news-list"[^>]*>)(.*?</article>)(\s*</div>)',re.I|re.S)
DATE=re.compile(r'<div\b[^>]*class="news-meta"[^>]*>.*?(\d{4}-\d{2}-\d{2})',re.I|re.S)

def build() -> None:
    base=(ROOT/ARCHIVES[0][0]).read_text(encoding="utf-8")
    entries={}
    for filename,label in ARCHIVES:
        source=(ROOT/filename).read_text(encoding="utf-8")
        match=LIST.search(source)
        if not match:
            raise RuntimeError("Missing category archive news list: "+filename)
        for row in ROW.finditer(match.group(2)):
            item=row.group()
            link=URL.search(item)
            if not link:
                raise RuntimeError("Missing article URL in "+filename)
            url=link.group(1)
            if url in entries:
                continue
            date=DATE.search(item)
            published=date.group(1) if date else "1970-01-01"
            tag='<span class="zt-cyber-category">'+html.escape(label)+'</span>'
            item=item.replace('<div class="news-copy">','<div class="news-copy">'+tag,1)
            entries[url]=(published,item)
    if not entries:
        raise RuntimeError("Cybercultura cannot publish an empty combined archive")
    ordered=sorted(entries.values(),key=lambda item:item[0],reverse=True)
    # Preserve the existing accessible and responsive page shell, sidebar and footer.
    base=base.replace("<title>Tech Impact | ZazoomTek</title>","<title>Cybercultura | Tecnologia, Gaming, Società e Diritti - ZazoomTek</title>",1)
    base=base.replace('https://zazoomtek.it/tech-today.html','https://zazoomtek.it/cybercultura.html',1)
    base=re.sub(r'(<meta name="description" content=")[^"]+(")',r'\1Cybercultura: approfondimenti su tecnologia, videogiochi, politica, sicurezza, diritti digitali e società. Tutte le notizie Tech Impact e Gaming Inside.\2',base,count=1)
    base=base.replace('<strong>Tech Impact</strong>','<strong>Cybercultura</strong>',1)
    base=base.replace('<span>Notizie di tecnologia e innovazione</span>','<span>Tecnologia, videogiochi, politica, sicurezza e diritti digitali</span>',1)
    base=base.replace('<h1>Tech Impact</h1>','<h1>Cybercultura</h1>',1)
    opening=LIST.search(base)
    if not opening:
        raise RuntimeError("Cybercultura archive source structure changed")
    body='<div class="news-list" id="newsList" data-auto-articles="cybercultura">\n'+'\n'.join(item for _,item in ordered)+'\n</div>'
    base=base[:opening.start()]+body+base[opening.end():]
    base=base.replace('</head>','<style>.zt-cyber-category{display:inline-block;margin-bottom:8px;padding:5px 9px;background:#202020;color:#fff;font:800 11px Arial,Helvetica,sans-serif;text-transform:uppercase;border-left:3px solid #d51232}</style><meta property="og:type" content="website"><meta property="og:title" content="Cybercultura | ZazoomTek"><meta property="og:url" content="https://zazoomtek.it/cybercultura.html"></head>',1)
    preview_image=re.search(r'<img\\b[^>]*\\bsrc="([^"]+)"',ordered[0][1],re.I)
    image=html.unescape(preview_image.group(1)) if preview_image else "/ChatGPT.png"
    if image.startswith("/"):
        image="https://zazoomtek.it"+image
    description=("Cybercultura riunisce Tech Impact e Gaming Inside: "
                 "tecnologia, videogiochi, politica, cybersicurezza e diritti digitali.")
    social=(
        '<meta property="og:locale" content="it_IT">'
        '<meta property="og:site_name" content="ZazoomTek">'
        '<meta property="og:description" content="'+html.escape(description,quote=True)+'">'
        '<meta property="og:image" content="'+html.escape(image,quote=True)+'">'
        '<meta property="og:image:alt" content="Cybercultura: notizie e approfondimenti ZazoomTek">'
        '<meta name="twitter:card" content="summary_large_image">'
        '<meta name="twitter:title" content="Cybercultura | ZazoomTek">'
        '<meta name="twitter:description" content="'+html.escape(description,quote=True)+'">'
        '<meta name="twitter:image" content="'+html.escape(image,quote=True)+'">'
        '<meta name="robots" content="index,follow,max-image-preview:large">'
    )
    base=base.replace('</head>',social+'</head>',1)
    structured={
        "@context":"https://schema.org",
        "@type":"CollectionPage",
        "name":"Cybercultura | ZazoomTek",
        "url":"https://zazoomtek.it/cybercultura.html",
        "inLanguage":"it-IT",
        "mainEntity":{"@type":"ItemList","itemListElement":[
            {"@type":"ListItem","position":i,"url":"https://zazoomtek.it"+url}
            for i,url in enumerate(
                sorted(entries,key=lambda u:entries[u][0],reverse=True),start=1)
        ]}
    }
    block='<script type="application/ld+json">'+json.dumps(structured,ensure_ascii=False).replace('<','\\u003c')+'</script>'
    base=base.replace('</head>',block+'</head>',1)
    # Legacy archive links are kept for Google; site-wide navigation gets
    # its authoritative menu from the Home in apply-site-design.py.
    page_total=write_paged_archives(base,ordered,structured,block)
    sitemap=ROOT/"sitemap.xml"
    if sitemap.is_file():
        xml=sitemap.read_text(encoding="utf-8")
        locator="https://zazoomtek.it/cybercultura.html"
        if locator not in xml:
            if "</urlset>" not in xml:
                raise RuntimeError("Invalid sitemap")
            xml=xml.replace("</urlset>","  <url><loc>"+locator+"</loc></url>\n</urlset>",1)
            sitemap.write_text(xml,encoding="utf-8")
    print("CYBERCULTURA GENERATED:",len(ordered),"articles across",page_total,"pages; legacy category URLs preserved",flush=True)


def write_paged_archives(base: str, ordered: list, structured: dict, original_block: str) -> int:
    """Write 20 distinct approved Cybercultura stories per accessible static page."""
    per_page=20
    total=max(1,(len(ordered)+per_page-1)//per_page)
    for number in range(1,total+1):
        part=ordered[(number-1)*per_page:number*per_page]
        path="cybercultura.html" if number==1 else "cybercultura-"+str(number)+".html"
        page_url="https://zazoomtek.it/"+path
        selected=LIST.search(base)
        if not selected:
            raise RuntimeError("Cybercultura list markup changed; pagination aborted")
        navigation=""
        if total>1:
            controls=[]
            for index in range(1,total+1):
                caption=str(index)
                target="/cybercultura.html" if index==1 else "/cybercultura-"+caption+".html"
                controls.append('<span class="active" aria-current="page">'+caption+'</span>'
                                if index==number else '<a href="'+target+'">'+caption+'</a>')
            if number<total:
                controls.append('<a class="next" href="/cybercultura-'+str(number+1)+'.html">NEXT</a>')
            navigation='<nav class="archive-pagination" aria-label="Pagine Cyber Cultura">'+''.join(controls)+'</nav>'
        markup='<div class="news-list" id="newsList" data-auto-articles="cybercultura">\n'+''.join(
            item+'\n' for _,item in part)+'</div>'+navigation
        scoped=base[:selected.start()]+markup+base[selected.end():]
        current_schema=json.loads(json.dumps(structured))
        current_schema["url"]=page_url
        records=[]
        for idx,(_,item) in enumerate(part):
            link=URL.search(item)
            if not link:
                raise RuntimeError("Cybercultura article missing URL during pagination")
            records.append({"@type":"ListItem","position":(number-1)*per_page+idx+1,
                            "url":"https://zazoomtek.it"+link.group(1)})
        current_schema["mainEntity"]["itemListElement"]=records
        replacement='<script type="application/ld+json">'+json.dumps(
            current_schema,ensure_ascii=False).replace('<',r'\u003c')+'</script>'
        if original_block not in scoped:
            raise RuntimeError("Cybercultura JSON-LD marker unavailable")
        scoped=scoped.replace(original_block,replacement,1)
        if number>1:
            scoped=scoped.replace("Cybercultura | Tecnologia, Gaming, Società e Diritti - ZazoomTek",
                                  "Cybercultura - Pagina "+str(number)+" | ZazoomTek",1)
            scoped=scoped.replace("https://zazoomtek.it/cybercultura.html",page_url)
            scoped=scoped.replace("<h1>Cybercultura</h1>",
                                  "<h1>Cybercultura - Pagina "+str(number)+"</h1>",1)
        rel=[]
        if number>1:
            previous="cybercultura.html" if number==2 else "cybercultura-"+str(number-1)+".html"
            rel.append('<link rel="prev" href="https://zazoomtek.it/'+previous+'">')
        if number<total:
            rel.append('<link rel="next" href="https://zazoomtek.it/cybercultura-'+str(number+1)+'.html">')
        scoped=scoped.replace("</head>","".join(rel)+"</head>",1)
        (ROOT/path).write_text(scoped,encoding="utf-8")
    return total


if __name__=="__main__":
    build()
