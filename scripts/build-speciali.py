#!/usr/bin/env python3
"""Build the combined SPECIALI archive only from already approved Studio publications.

Never scrape, publish or generate an article here. No user/browser requests.
The marker-only update leaves approved shell, footer, sidebar and URLs intact.
"""
from __future__ import annotations
from datetime import datetime
import html
import json
from pathlib import Path
import re
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
START='<!-- ZT_SPECIALI_ITEMS_START -->'
END='<!-- ZT_SPECIALI_ITEMS_END -->'
CATEGORIES={'Speciali Tech':'TECH IMPACT','Speciali Gaming':'GAMING INSIDE'}
SENTINEL=('<div class="zt-specials-empty"><strong>Gli SPECIALI sono in preparazione.</strong>'
          '<p>I prossimi approfondimenti verificati appariranno qui dopo l’approvazione editoriale.</p></div>')
SAFE_ARTICLE=re.compile(r'[a-zA-Z0-9][a-zA-Z0-9_-]*\.html\Z')
SAFE_IMAGE=re.compile(r'/assets/[a-zA-Z0-9_./-]+\.(?:webp|png|jpg|jpeg|avif)\Z',re.I)

def approved_entries(root: Path=ROOT)->list[dict]:
    manifest=root/'studio/articoli.json'
    if not manifest.is_file():
        return []
    data=json.loads(manifest.read_text(encoding='utf-8'))
    if not isinstance(data,list):
        raise RuntimeError('Studio manifest invalid: refusing to rewrite SPECIALI')
    seen=set()
    items=[]
    for entry in data:
        if not isinstance(entry,dict) or entry.get('category') not in CATEGORIES:
            continue
        parsed=urlparse(str(entry.get('url') or ''))
        slug=parsed.path.lstrip('/')
        if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or not SAFE_ARTICLE.fullmatch(slug):
            raise RuntimeError('Unsafe Speciali URL in Studio manifest')
        if slug in seen:
            continue
        if not (root/slug).is_file():
            # Studio wrote manifest before article was replicated: no broken cards.
            print('SPECIALI deferred missing article:',slug)
            continue
        image=str(entry.get('image') or '')
        if not SAFE_IMAGE.fullmatch(image) or not (root/image.lstrip('/')).is_file():
            print('SPECIALI deferred missing local cover:',slug)
            continue
        title=str(entry.get('title') or '').strip()
        if not title:
            continue
        date=str(entry.get('published_at') or '')[:10]
        try:datetime.strptime(date,'%Y-%m-%d')
        except ValueError:
            print('SPECIALI deferred invalid publication date:',slug)
            continue
        desc=re.sub(r'\s+',' ',str(entry.get('description') or '')).strip()[:260] or title
        seen.add(slug)
        items.append({'slug':slug,'title':title,'desc':desc,'date':date,
                      'image':image,'label':CATEGORIES[entry['category']]})
    return sorted(items,key=lambda a:(a['date'],a['slug']),reverse=True)

def render_row(item:dict)->str:
    esc=lambda s:html.escape(s,quote=True)
    slug=esc(item['slug'])
    title=esc(item['title'])
    return ('<article class="news-row" data-zt-special="approved" data-news-search="'
            +esc((item['title']+' '+item['desc']+' '+item['label']).lower())+'">'
            +'<a href="/'+slug+'"><img src="'+esc(item['image'])+'" loading="lazy" alt="'+title+'"></a>'
            +'<div class="news-copy"><span class="zt-special-badge">'+esc(item['label'])+'</span>'
            +'<h2><a href="/'+slug+'">'+title+'</a></h2>'
            +'<div class="news-meta">ZazoomTek · '+esc(item['date'])+' · Speciale</div>'
            +'<p>'+esc(item['desc'])+'</p>'
            +'<a class="news-read" href="/'+slug+'">Leggi lo speciale ›</a></div></article>')


RELATED_START='<!-- ZT_SPECIALI_RELATED_START -->'
RELATED_END='<!-- ZT_SPECIALI_RELATED_END -->'

def context_articles(root:Path=ROOT)->str:
    """Published contextual NEWS in a separate 'Articoli correlati' area.

    Never labels these cards as Speciali. Their own category archives
    remain the source of truth and their original article URLs are preserved.
    """
    selected=[]
    seen=set()
    for label,source in (('TECH IMPACT','tech-today.html'),('GAMING INSIDE','gaming-today.html')):
        page=root/source
        if not page.is_file():
            continue
        text=page.read_text(encoding='utf-8',errors='replace')
        count=0
        for match in re.finditer(r'<article class="news-row"[^>]*>.*?</article>',text,re.S|re.I):
            card=match.group()
            link=re.search(r'<h2>\s*<a[^>]*href="(/[^"]+)"[^>]*>(.*?)</a>',card,re.S|re.I)
            image=re.search(r'<img\b[^>]*src="([^"]+)"',card,re.I)
            if not link or not image:
                continue
            slug=link.group(1).lstrip('/')
            if not SAFE_ARTICLE.fullmatch(slug) or slug in seen or not (root/slug).is_file():
                continue
            pic=html.unescape(image.group(1))
            if not (pic.startswith('https://') or SAFE_IMAGE.fullmatch(pic)):
                continue
            title=html.unescape(re.sub(r'<[^>]+>','',link.group(2))).strip()
            if not title:
                continue
            esc=lambda t:html.escape(t,quote=True)
            selected.append('<a class="zt-specials-related-card" href="/'+esc(slug)+'">'
                            +'<img loading="lazy" src="'+esc(pic)+'" alt="'+esc(title)+'">'
                            +'<span class="zt-specials-related-copy"><small>'+label+'</small>'
                            +'<strong>'+esc(title)+'</strong></span></a>')
            seen.add(slug)
            count+=1
            if count>=3:
                break
    if not selected:
        return ('<a class="zt-specials-related-category" href="/tech-today.html">'
                'Scopri le news Tech Impact →</a>'
                '<a class="zt-specials-related-category" href="/gaming-today.html">'
                'Scopri le news Gaming Inside →</a>')
    return '\n'.join(selected)


def build(root:Path=ROOT)->int:
    target=root/'speciali.html'
    page=target.read_text(encoding='utf-8')
    if page.count(START)!=1 or page.count(END)!=1:
        raise RuntimeError('SPECIALI markers missing/duplicated; original unchanged')
    head,remain=page.split(START,1)
    _,tail=remain.split(END,1)
    entries=approved_entries(root)
    body='\n'.join(map(render_row,entries)) if entries else SENTINEL
    updated=head+START+'\n'+body+'\n'+END+tail
    if updated.count(RELATED_START)!=1 or updated.count(RELATED_END)!=1:
        raise RuntimeError("SPECIALI contextual articles markers missing; refusing build")
    prefix,rest=updated.split(RELATED_START,1)
    _,suffix=rest.split(RELATED_END,1)
    updated=prefix+RELATED_START+'\n'+context_articles(root)+'\n'+RELATED_END+suffix
    # Refresh schema.org ItemList only after verified, approved pages are known.
    graph={
        "@context":"https://schema.org",
        "@graph":[
            {"@type":"CollectionPage","name":"Speciali Tech e Gaming",
             "description":"Approfondimenti originali su tecnologia, gaming, società, politica, diritti, economia e industria digitale.",
             "url":"https://zazoomtek.it/speciali.html",
             "isPartOf":{"@type":"WebSite","name":"ZazoomTek","url":"https://zazoomtek.it/"},
             "mainEntity":{"@type":"ItemList","itemListElement":[
                {"@type":"ListItem","position":idx+1,"name":entry["title"],
                 "url":"https://zazoomtek.it/"+entry["slug"]}
                for idx,entry in enumerate(entries)]}},
            {"@type":"BreadcrumbList","itemListElement":[
                {"@type":"ListItem","position":1,"name":"Home","item":"https://zazoomtek.it/"},
                {"@type":"ListItem","position":2,"name":"TG Inside","item":"https://zazoomtek.it/speciali.html"},
                {"@type":"ListItem","position":3,"name":"Speciali","item":"https://zazoomtek.it/speciali.html"}
            ]}
        ]}
    ld=json.dumps(graph,ensure_ascii=False).replace('<','\\u003c')
    updated,count=re.subn(
        r'(<script id="zt-specials-ld"[^>]*>).*?(</script>)',
        lambda m:m.group(1)+ld+m.group(2),
        updated,count=1,flags=re.S)
    if count!=1:
        raise RuntimeError("Speciali SEO JSON-LD missing; refusing incomplete build")
    if not all(key in updated for key in ('class="news-sidebar','zt-mix-feature','zt-mix-recent',
                                            'class="legal-footer','id="specialiList"')):
        raise RuntimeError('SPECIALI page lost editorial shell: refusing build')
    if updated!=page:
        target.write_text(updated,encoding='utf-8')
    # Keep the canonical archive discoverable from Google sitemap.
    sitemap=root/"sitemap.xml"
    if sitemap.is_file():
        xml=sitemap.read_text(encoding="utf-8")
        url="https://zazoomtek.it/speciali.html"
        if url not in xml:
            if "</urlset>" not in xml:
                raise RuntimeError("Invalid sitemap: SPECIALI cannot be indexed safely")
            xml=xml.replace("</urlset>","  <url><loc>"+url+"</loc></url>\n</urlset>",1)
            sitemap.write_text(xml,encoding="utf-8")
    print('Approved, unique SPECIALI indexed:',len(entries))
    return len(entries)

if __name__=='__main__':
    build()
