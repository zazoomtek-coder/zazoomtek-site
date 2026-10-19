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
    if not all(key in updated for key in ('class="news-sidebar','zt-mix-feature','zt-mix-recent',
                                            'class="legal-footer','id="specialiList"')):
        raise RuntimeError('SPECIALI page lost editorial shell: refusing build')
    if updated!=page:
        target.write_text(updated,encoding='utf-8')
    print('Approved, unique SPECIALI indexed:',len(entries))
    return len(entries)

if __name__=='__main__':
    build()
