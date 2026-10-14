#!/usr/bin/env python3
"""Prioritize only the verified mobile LCP cover in the sixth featured card.

No preloading, no remote-image changes, and no CSS/layout/content changes.
The normal first card remains unchanged. Abort if the featured layout changes.
"""
import re
from pathlib import Path

START = '<!-- FEATURED_NEWS_START -->'
END = '<!-- FEATURED_NEWS_END -->'
IMAGE = re.compile(r'<img\\b[^>]*>', re.I)

def transform(source):
    if source.count(START) != 1 or source.count(END) != 1:
        raise RuntimeError('Featured markers changed')
    a = source.index(START) + len(START)
    b = source.index(END, a)
    block = source[a:b]
    tags = IMAGE.findall(block)
    if len(tags) != 6:
        raise RuntimeError('Expected six featured cards')
    old = tags[-1]
    if not re.search(r'src="/assets/special/gaming-inside-[^"]+\\.webp"', old):
        raise RuntimeError('Unexpected mobile LCP image: no changes')
    new = re.sub(r'loading="(?:lazy|eager)"', 'loading="eager"', old, count=1)
    if not re.search(r'loading="eager"', new):
        raise RuntimeError('Missing loading attribute')
    if 'fetchpriority="high"' not in new:
        new = new[:-1] + ' fetchpriority="high">'
    if old == new:
        return source
    newblock = block.replace(old, new, 1)
    return source[:a] + newblock + source[b:]

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=Path('index.html')
    before=path.read_text(encoding='utf-8')
    after=transform(before)
    assert transform(after) == after
    print('Gaming Inside mobile LCP priority applied:',before!=after,'dryrun:',args.check)
    if not args.check and before!=after:
        path.write_text(after,encoding='utf-8')
