#!/usr/bin/env python3
"""Mark all six genuinely above-the-fold featured News cover images as eager.

First image remains high priority. The other five use normal browser priority.
Only changes img loading and exact CDN resolution parameters within the protected
FEATURED_NEWS block in the ephemeral Firebase deployment checkout.
"""
import argparse
import re
from pathlib import Path

START='<!-- FEATURED_NEWS_START -->'
END='<!-- FEATURED_NEWS_END -->'
IMAGES=re.compile(r'<img\b[^>]*>',re.I)
CDN=re.compile(r'https://yt3\.ggpht\.com/[A-Za-z0-9_-]{20,}=s1600-rw-nd-v1',re.I)
SRC=re.compile(r'\bsrc\s*=\s*["\x27]([^"\x27]+)["\x27]',re.I)

def transform(src):
    if src.count(START)!=1 or src.count(END)!=1:
        raise RuntimeError('Featured News markers changed; no SEO changes')
    start=src.index(START)+len(START)
    stop=src.index(END,start)
    block=src[start:stop]
    images=IMAGES.findall(block)
    if len(images)!=6:
        raise RuntimeError(f'Expected exactly six featured cover images, got {len(images)}')
    if not (re.search(r'loading=["\x27]eager["\x27]',images[0],re.I) and
            'fetchpriority="high"' in images[0]):
        raise RuntimeError('Protected first LCP cover must remain eager/high')
    updates=[]
    for i,tag in enumerate(images):
        new=tag
        if i:
            new,count=re.subn(r'\bloading\s*=\s*["\x27]lazy["\x27]','loading="eager"',new,count=1,flags=re.I)
            if not count and not re.search(r'loading=["\x27]eager["\x27]',new,re.I):
                raise RuntimeError('Unexpected featured image loading attribute')
            # Never mark all images HIGH: reserve high priority for first cover.
            if re.search(r'\bfetchpriority\s*=\s*["\x27]high["\x27]',new,re.I):
                raise RuntimeError('Other featured images must not use high priority')
        match=SRC.search(new)
        if match and CDN.fullmatch(match.group(1)):
            replacement=match.group(1).replace('=s1600-rw-nd-v1','=s1200-rw-nd-v1')
            new=new[:match.start(1)]+replacement+new[match.end(1):]
        updates.append(new)
    iterator=iter(updates)
    revised=IMAGES.sub(lambda m:next(iterator),block)
    result=src[:start]+revised+src[stop:]
    if result[:start]!=src[:start] or result[result.index(END):]!=src[src.index(END):]:
        raise RuntimeError('Other site content changed')
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    path=args.root/'index.html'
    source=path.read_text(encoding='utf-8')
    revised=transform(source)
    assert transform(revised)==revised
    print(f'All 6 visible News covers eager (only first high priority); changes={source!=revised}; dry-run={args.check}')
    if not args.check and revised!=source:path.write_text(revised,encoding='utf-8')
if __name__=='__main__':main()
