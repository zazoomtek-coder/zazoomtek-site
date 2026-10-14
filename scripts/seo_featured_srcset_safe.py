#!/usr/bin/env python3
"""Responsive remote featured thumbnails, preserving original desktop source.

Only add srcset/sizes to four remote featured image tags. No source URL,
layout, graphic, links, local editorial images or external JS modifications.
"""
from pathlib import Path
import re

START='<!-- FEATURED_NEWS_START -->'
END='<!-- FEATURED_NEWS_END -->'
IMG=re.compile(r'<img\b[^>]*>', re.I)
SRC=re.compile(r'\bsrc="(https://yt3\.ggpht\.com/([A-Za-z0-9_-]{20,})=s(?:1200|1600)-rw-nd-v1)"',re.I)

def transform(html):
    if html.count(START)!=1 or html.count(END)!=1:
        raise RuntimeError('Featured section changed')
    a=html.index(START)+len(START)
    b=html.index(END,a)
    section=html[a:b]
    tags=IMG.findall(section)
    if len(tags)!=6:
        raise RuntimeError('Expected six featured cards')
    changed=[]
    for index,tag in enumerate(tags):
        if index >=4:
            changed.append(tag)
            continue
        m=SRC.search(tag)
        if not m:
            raise RuntimeError('Unknown remote featured thumbnail')
        if 'srcset=' in tag or 'sizes=' in tag:
            changed.append(tag)
            continue
        base='https://yt3.ggpht.com/'+m.group(2)
        size='(max-width: 600px) 100vw, (max-width: 1100px) 50vw, 480px'
        variants=', '.join(f'{base}=s{n}-rw-nd-v1 {n}w' for n in (480,720,960,1200,1600))
        tag=tag[:-1]+' srcset="'+variants+'" sizes="'+size+'">'
        changed.append(tag)
    it=iter(changed)
    new=IMG.sub(lambda m:next(it),section)
    return html[:a]+new+html[b:]

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--check',action='store_true')
    opts=p.parse_args()
    file=Path('index.html')
    before=file.read_text(encoding='utf-8')
    after=transform(before)
    assert transform(after)==after
    print('Responsive featured URLs: changed=', before!=after, 'dry_run=',opts.check)
    if not opts.check and after!=before:
        file.write_text(after,encoding='utf-8')
