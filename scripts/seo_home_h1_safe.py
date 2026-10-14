#!/usr/bin/env python3
"""Replace visible homepage section heading H2 with a semantic H1, pixel-safe.

Only the homepage in the temporary Firebase checkout. No article, CSS file,
YouTube import, page structure or site content rewriting.
"""
from pathlib import Path
import argparse
import re

BEFORE='<div class="module-head"><h2>News in evidenza</h2></div>'
AFTER='<div class="module-head"><h1 style="letter-spacing:.025em">News in evidenza</h1></div>'
INLINE_STYLE=re.compile(r'<style\b[^>]*>[\s\S]*?</style\s*>',re.I)
RULE='.module-head h2'
REPLACEMENT='.module-head :is(h2,h1)'

def transform(src):
    if src.count(BEFORE)!=1:
        if AFTER in src and '<h2>News in evidenza</h2>' not in src:
            return src
        raise RuntimeError('Homepage featured heading changed; refusing automatic SEO rewrite')
    if re.search(r'<h1\b',src,re.I):
        raise RuntimeError('Homepage already contains H1: refusing to add another')
    replaced=0
    def amend(match):
        nonlocal replaced
        block=match.group(0)
        found=block.count(RULE)
        if found:
            replaced+=found
            return block.replace(RULE,REPLACEMENT)
        return block
    out=INLINE_STYLE.sub(amend,src)
    if not 3<=replaced<=20:
        raise RuntimeError(f'Unexpected inline CSS heading selector count: {replaced}')
    out=out.replace(BEFORE,AFTER,1)
    if out.count('<h1 ')!=1:
        raise RuntimeError('Exactly one homepage H1 expected')
    # Sanity: all external JS and regular article content stay exactly the same
    if out[out.index('<!-- FEATURED_NEWS_START -->'):]!=src[src.index('<!-- FEATURED_NEWS_START -->'):]:
        raise RuntimeError('Editorial content changed unexpectedly')
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=args.root/'index.html'
    source=path.read_text(encoding='utf-8')
    out=transform(source)
    assert transform(out)==out
    print('Homepage: semantic H1 matches original visible heading styling; changed=',source!=out,'check=',args.check)
    if not args.check and source!=out:path.write_text(out,encoding='utf-8')

if __name__=='__main__':main()
