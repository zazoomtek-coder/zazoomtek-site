#!/usr/bin/env python3
"""SEO watch-page generator for verified videos already imported from ZazoomTek.

Creates ONLY separate /watch/ pages: never edits existing pages, sync scripts,
the homepage, navigation, CSS, YouTube imports or editorials. Designed to run
within the ephemeral Firebase deployment checkout before site-wide styling.

The video itself is the page's primary content (a visible YouTube iframe);
source metadata comes from the publisher's imported channel feed only.
"""
import argparse
from datetime import datetime,timezone
from html import escape
from pathlib import Path
import json,re

from seo_media_safe import feed_videos,YT_ID
from seo_paths_safe import ORIGIN

MAX_ITEMS=2000
WATCH_DIR='watch'
CATEGORY={
    'recensioni':'Videorecensione', 'gaming':'Gaming', 'gameplay':'Gameplay',
    'test':'Test', 'unboxing':'Unboxing', 'video':'Video',
    'analogiktek':'Tecnologia',
}
def feed_items(root):
    src=root/'home-video-feed.json'
    obj=json.loads(src.read_text(encoding='utf-8'))
    archive=root/'video-watch-archive.json'
    if archive.is_file():
        prior=json.loads(archive.read_text(encoding='utf-8'))
        if isinstance(prior,list):
            seen_ids={x.get('id') for x in obj if isinstance(x,dict)}
            obj.extend(x for x in prior if isinstance(x,dict) and x.get('id') not in seen_ids)
    if not isinstance(obj,list) or len(obj)<10:
        raise ValueError('Video feed unexpectedly small; no watch pages generated')
    valid=feed_videos(root)
    # Archive entries were confirmed from the same imported public feed when
    # first recorded. Keep their original dates/titles without alterations.
    for item in obj:
        if not isinstance(item,dict):continue
        ident=item.get('id')
        if not isinstance(ident,str) or not YT_ID.fullmatch(ident) or ident in valid:continue
        title=item.get('title')
        when=item.get('publishedAt')
        if isinstance(title,str) and 6<=len(title.strip())<=230 and isinstance(when,str):
            valid[ident]={'name':title.strip(),'uploadDate':when}
    out=[]
    seen=set()
    for item in obj:
        if not isinstance(item,dict): continue
        ident=item.get('id')
        if not isinstance(ident,str) or not YT_ID.fullmatch(ident) or ident in seen or ident not in valid:
            continue
        if item.get('live') is True and item.get('completedLive') is not True:
            continue
        kind=str(item.get('category') or 'video')
        title=valid[ident]['name']
        if len(title)<6 or len(title)>230:
            continue
        try:
            published=datetime.fromisoformat(valid[ident]['uploadDate'].replace('Z','+00:00'))
            if published.tzinfo is None or published.astimezone(timezone.utc)>datetime.now(timezone.utc):
                continue
        except (ValueError,TypeError):continue
        seen.add(ident)
        out.append({'id':ident,'title':title,'publishedAt':valid[ident]['uploadDate'],
                    'category':CATEGORY.get(kind,'Video'),'short':item.get('short') is True})
    if len(out)<10 or len(out)>MAX_ITEMS:
        raise ValueError('Unexpected watch-page count: '+str(len(out)))
    return out

def page_parts(root):
    existing=(root/'news.html').read_text(encoding='utf-8')
    header=re.search(r'<header\b[^>]*>[\s\S]*?</header\s*>',existing,re.I)
    footer=re.search(r'<footer\b[^>]*>[\s\S]*?</footer\s*>',existing,re.I)
    if not header or not footer:
        raise RuntimeError('Approved site masthead/footer missing; refusing to publish watch pages')
    # Cloudflare already normalized news.html to the actual locked Home masthead.
    # Watch pages reuse both its exact header HTML and its scoped header CSS.
    if 'id="zt-site-home-header"' not in header.group(0):
        raise RuntimeError('Home-sourced ZazoomTek header missing')
    style=re.search(r'<style\b[^>]*id="zt-site-home-header-style"[^>]*>[\s\S]*?</style>',existing,re.I)
    if not style:
        raise RuntimeError('Home masthead stylesheet missing')
    return header.group(0),footer.group(0),style.group(0)

def description(item):
    kind=item['category'].lower()
    return ('Guarda il video '+item['title']+'. '
            'Contenuto '+kind+' pubblicato sul canale ufficiale ZazoomTek il '+
            datetime.fromisoformat(item['publishedAt'].replace('Z','+00:00')).strftime('%d/%m/%Y')+
            '. Il player integrato riproduce il video originale di YouTube.')

def make_video(root,item,header,footer,header_style):
    ident=item['id']
    title=item['title']
    url=ORIGIN+'/watch/'+ident+'.html'
    thumb='https://i.ytimg.com/vi/'+ident+'/hqdefault.jpg'
    player='https://www.youtube-nocookie.com/embed/'+ident
    desc=description(item)
    data={'@context':'https://schema.org','@type':'VideoObject','name':title,
          'description':desc,'thumbnailUrl':thumb,'uploadDate':item['publishedAt'],
          'embedUrl':player,'url':url,'inLanguage':'it',
          'publisher':{'@type':'Organization','name':'ZazoomTek','url':ORIGIN+'/'},
          'mainEntityOfPage':url}
    safe_title=escape(title,quote=True)
    name=escape(item.get('seo_title') or title,quote=True)+' | ZazoomTek'
    e= lambda value:escape(str(value),quote=True)
    seo_desc=f"Video ZazoomTek: {title}. {item['category']} del {item['publishedAt'][:10]}. ID YouTube {ident}."
    if len(seo_desc)>158:
        seo_desc=seo_desc[:130].rsplit(' ',1)[0].rstrip(' ,.;')+'… Video '+ident+'.'

    ratio='9/16' if item['short'] else '16/9'
    width='min(460px,100%)' if item['short'] else '100%'
    return f'''<!doctype html>
<html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name}</title>
<meta name="description" content="{e(seo_desc)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-video-preview:-1">
<link rel="canonical" href="{e(url)}">
<meta name="author" content="ZazoomTek">\n<link rel="stylesheet" href="/zt-design.css?v=20261012sidebarFix5">\n<link rel="stylesheet" href="/zt-thumbnails.css?v=20261013textPriorityCover5">
<meta property="og:type" content="video.other">
<meta property="og:site_name" content="ZazoomTek">
<meta property="og:title" content="{safe_title}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{e(thumb)}">
<meta property="og:video" content="{e(player)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')}</script>
<style>.zt-watch-shell{{max-width:1100px;width:min(94%,1100px);margin:24px auto 40px;background:#fff;padding:clamp(16px,3vw,28px);border-top:5px solid #d51232;box-shadow:0 3px 14px #00000012;color:#222}}.zt-watch-shell h1{{font:800 clamp(23px,3.3vw,36px)/1.25 Arial,Helvetica,sans-serif;overflow-wrap:anywhere;margin:10px 0 18px;color:#181818}}.zt-watch-frame{{margin:0 auto 16px;width:{width};aspect-ratio:{ratio};background:#111;overflow:hidden;position:relative}}.zt-watch-frame iframe{{border:0;position:absolute;inset:0;width:100%;height:100%}}.zt-watch-shell p{{font:16px/1.65 Arial,sans-serif;margin:14px 0}}.zt-watch-back{{font:700 14px Arial,sans-serif;display:inline-block;margin-bottom:10px;color:#a91029}}@media(max-width:640px){{.zt-watch-shell{{margin:12px auto;padding:14px}}}}</style>
{header_style}
</head><body>
{header}
<main class="zt-watch-shell">
<a class="zt-watch-back" href="/watch/">← Tutti i video ZazoomTek</a>
<article class="zt-watch-article">
<h1>{safe_title}</h1>
<div class="zt-watch-frame"><iframe src="{e(player)}" title="{safe_title}" loading="eager" referrerpolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe></div>
<p>{e(desc)}</p>
<p>Categoria: <strong>{e(item['category'])}</strong>. Video pubblicato il <time datetime="{e(item['publishedAt'][:10])}">{e(item['publishedAt'][:10])}</time>.</p>
<p><a href="https://www.youtube.com/watch?v={e(ident)}" target="_blank" rel="noopener noreferrer">Apri il video originale su YouTube</a> · <a href="/watch/">Esplora altri video ZazoomTek</a></p>
</article></main>
{footer}
</body></html>'''

def make_directory(items,header,footer,header_style):
    url=ORIGIN+'/watch/'
    links=[]
    for item in items:
        e=escape
        ident=item['id']
        links.append(f'<li><a href="/watch/{ident}.html">{e(item["title"])}</a> <small>({e(item["category"])}, {e(item["publishedAt"][:10])})</small></li>')
    rows='\n'.join(links)
    desc='Archivio dei video originali ZazoomTek: recensioni, unboxing, test, gaming, gameplay e Shorts pubblicati su YouTube.'
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video ZazoomTek: recensioni, test, gaming e gameplay</title>
<meta name="description" content="{escape(desc,quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{url}">\n<link rel="stylesheet" href="/zt-design.css?v=20261012sidebarFix5">\n<link rel="stylesheet" href="/zt-thumbnails.css?v=20261013textPriorityCover5">
<meta property="og:title" content="Archivio video ZazoomTek">
<meta property="og:description" content="{escape(desc,quote=True)}">
<meta property="og:type" content="website"><meta property="og:url" content="{url}">
<style>.zt-watch-list{{max-width:1100px;width:min(94%,1100px);margin:24px auto 40px;padding:26px;background:#fff;color:#222;border-top:5px solid #d51232}}.zt-watch-list h1{{font:800 clamp(23px,4vw,34px)/1.3 Arial,sans-serif}}.zt-watch-list li{{margin:0 0 9px;line-height:1.55}}.zt-watch-list small{{color:#666}}@media(max-width:640px){{.zt-watch-list{{padding:14px}}}}</style>
{header_style}
</head><body>{header}<main class="zt-watch-list"><h1>Video ZazoomTek</h1>
<p>{desc} Ogni collegamento apre una pagina dedicata con il video originale in primo piano.</p>
<ul>{rows}</ul></main>{footer}</body></html>'''

def build(root):
    root=Path(root).resolve()
    items=feed_items(root)
    header,footer,header_style=page_parts(root)
    output={}
    from collections import Counter
    name_counts=Counter(x['title'].casefold() for x in items)
    for item in items:
        item=dict(item)
        if name_counts[item['title'].casefold()]>1:
            item['seo_title']=item['title']+' ('+item['category']+', '+item['publishedAt'][:10]+', '+item['id'][-4:]+')'
        else:
            item['seo_title']=item['title']
        # Always use the verified video ID to keep final titles unique even
        # when unrelated originals share identical shortened title prefixes.
        suffix=' ['+item['id']+']'
        available=75-len(' | ZazoomTek')-len(suffix)
        if len(item['seo_title'])>available:
            prefix=item['seo_title'][:available-1].rsplit(' ',1)[0].rstrip(' ,.;')
            item['seo_title']=prefix+'…'
        item['seo_title']+=suffix
        name=WATCH_DIR+'/'+item['id']+'.html'
        output[name]=make_video(root,item,header,footer,header_style)
    output[WATCH_DIR+'/index.html']=make_directory(items,header,footer,header_style)
    for name,html in output.items():
        assert html.count('<h1')==1,(name,'heading')
        assert html.count('</head>')==1
        assert html.count('<link rel="canonical"')==1
        assert html.count('<iframe')==(0 if name.endswith('/index.html') else 1)
    return output,len(items)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    root=args.root.resolve()
    output,count=build(root)
    print(f'WATCH SEO: {count} verified YouTube videos; {len(output)} new video pages; check={args.check}')
    if args.check:return
    destination=root/WATCH_DIR
    destination.mkdir(exist_ok=True)
    for name,content in output.items():
        file=root/name
        assert file.is_relative_to(destination) and file.name.endswith('.html')
        if file.exists() and file.read_text(encoding='utf-8')==content:continue
        file.write_text(content,encoding='utf-8')

if __name__=='__main__':main()
