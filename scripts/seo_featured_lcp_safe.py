#!/usr/bin/env python3
"""Conservative mobile LCP hint for the first static featured-news cover.

Only changes one existing <img> tag inside the protected FEATURED_NEWS markers
in the ephemeral Firebase checkout. Never touches JS, CSS, layout, importers,
editorial text, link targets, or other images. The first image is already eager.
"""
import argparse
from pathlib import Path
import re

START = '<!-- FEATURED_NEWS_START -->'
END = '<!-- FEATURED_NEWS_END -->'
FIRST_CARD = re.compile(r'<a\b[^>]*\bclass\s*=\s*["\x27][^"\x27]*\bzt-feature-card\b[^"\x27]*["\x27][^>]*>[\s\S]*?</a\s*>',re.I)
IMG = re.compile(r'<img\b[^>]*>',re.I)
CDN = re.compile(r'(?P<url>https://yt3\.ggpht\.com/[A-Za-z0-9_-]{20,})=s1600-rw-nd-v1',re.I)

def transform(source):
    a=source.find(START)
    b=source.find(END, a+len(START)) if a>=0 else -1
    if a<0 or b<0 or source.find(START,a+len(START))!=-1:
        return source
    section=source[a+len(START):b]
    first=FIRST_CARD.search(section)
    if not first:
        return source
    card=first.group(0)
    img=IMG.search(card)
    if not img:
        return source
    tag=img.group(0)
    if not re.search(r'\bloading\s*=\s*["\x27]eager["\x27]',tag,re.I):
        return source
    new=tag
    if not re.search(r'\bfetchpriority\s*=',new,re.I):
        new=new[:-1]+' fetchpriority="high">'
    if re.search(r'\bsrcset\s*=',new,re.I):
        # Do not override a pre-existing responsive image setup.
        return source
    # The same ratio and visual were checked against the live image CDN.
    # Keep 1200px for sharp 16:9 mobile/desktop card text.
    new=CDN.sub(lambda match:match.group('url')+'=s1200-rw-nd-v1',new,count=1)
    if new==tag:
        return source
    revised_card=card[:img.start()]+new+card[img.end():]
    revised_section=section[:first.start()]+revised_card+section[first.end():]
    result=source[:a+len(START)]+revised_section+source[b:]
    assert result.count(START)==1 and result.count(END)==1
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    page=args.root/'index.html'
    source=page.read_text(encoding='utf-8',errors='replace')
    result=transform(source)
    if result==source:
        raise RuntimeError('Expected first eager featured image missing or already optimized; refusing LCP changes')
    assert transform(result)==result, 'LCP hint not idempotent'
    print('Mobile featured LCP: first static image optimized safely; dry_run=',args.check)
    if not args.check:
        page.write_text(result,encoding='utf-8')

if __name__=='__main__': main()
