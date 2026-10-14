#!/usr/bin/env python3
"""Replace factual generic "News" placeholders using their OWN first article line.

No invented facts. Strict conditions to avoid altering legitimate article
headings, video pages, original review text, unrelated metadata and styles.
"""
import argparse,html,re
from html.parser import HTMLParser
from pathlib import Path
from seo_paths_safe import html_pages,canonical_candidates
from seo_head_safe import Metadata
from seo_concise_metadata_safe import shorten
TITLE=re.compile(r'<title\s*>\s*News\s*\|\s*ZazoomTek\s*</title\s*>',re.I)
HEAD_END=re.compile(r'</head\s*>',re.I)
FIRST_PARAGRAPH=re.compile(r'<div\b[^>]*class=["\x27][^"\x27]*\barticle-body\b[^"\x27]*["\x27][^>]*>\s*<p\b[^>]*>(.*?)</p\s*>',re.I|re.S)
PLACEHOLDER_H1=re.compile(r'(<h1\b[^>]*>)\s*News\s*(</h1\s*>)',re.I)
DESCRIPTION=re.compile(r'(<meta\b[^>]*name=["\x27]description["\x27][^>]*\bcontent=["\x27])News(["\x27][^>]*>)',re.I)
TAG=re.compile(r'<[^>]*>')
def get_title(source):
    match=FIRST_PARAGRAPH.search(source)
    if not match:return None
    value=' '.join(html.unescape(TAG.sub('',match.group(1))).split())
    if not 34<=len(value)<=130:return None
    if re.match(r'(?i)^(news|web|preordini|trailer|iscriviti|subscribe)\s*[:.]?$',value):return None
    if re.search(r'https?://|www\.',value):return None
    return value

def transform(path,root,source):
    end=HEAD_END.search(source)
    if not end:return source
    head,body=source[:end.start()],source[end.start():]
    meta=Metadata();meta.feed(head)
    if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,path):return source
    if 'noindex' in (meta.meta.get('robots','')+' '+meta.meta.get('googlebot','')).lower():return source
    if not TITLE.search(head) or not DESCRIPTION.search(head):return source
    if 'application/ld+json' in head or 'og:title' in head.lower():return source
    if len(PLACEHOLDER_H1.findall(body))!=1:return source
    title=get_title(body)
    if not title:return source
    short=shorten(title+' | ZazoomTek',73,34)
    title_tag=short or (title+' | ZazoomTek' if len(title)+13<=73 else None)
    if not title_tag:return source
    original_body=body
    replacement_h1=html.escape(title,quote=False)
    body=PLACEHOLDER_H1.sub(lambda m:m.group(1)+replacement_h1+m.group(2),body,count=1)
    head=TITLE.sub('<title>'+html.escape(title_tag,quote=False)+'</title>',head,count=1)
    desc=shorten(title,158,34) or title
    head=DESCRIPTION.sub(lambda m:m.group(1)+html.escape(desc,quote=True)+m.group(2),head,count=1)
    # Original body preserved except generic H1 text; all other site markup intact.
    assert body.replace(replacement_h1,'News',1)==original_body
    return head+body

def build(root,minimum=500):
    root=Path(root).resolve()
    changes={}
    pages=list(html_pages(root))
    for page in pages:
        old=page.read_text(encoding='utf-8',errors='replace')
        new=transform(page,root,old)
        if new!=old:changes[page]=new
    if len(pages)<minimum:raise RuntimeError('Unexpected page count; refusing content update')
    return changes,len(pages)

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--root',type=Path,default=Path('.'))
    a.add_argument('--check',action='store_true')
    args=a.parse_args()
    changes,pages=build(args.root)
    print(f'Generic News headings corrected using verified article text: {len(changes)}/{pages}; dry_run={args.check}')
    if not args.check:
        for path,source in changes.items():path.write_text(source,encoding='utf-8')
if __name__=='__main__':main()
