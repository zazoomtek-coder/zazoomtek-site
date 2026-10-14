#!/usr/bin/env python3
"""Conservatively reduce YouTube Community thumbnail download size.

Only touches the displayed URL of a lazy-loaded card image from the known
YouTube thumbnail CDN. No change to og:image, structured data, editorial body
text, CSS, geometry, navigation, thumbnail cropping, video or YouTube sync.
Runs only in optional temporary Firebase deployment checkout; never on source.
"""
import argparse
from pathlib import Path
import re
from seo_paths_safe import html_pages

IMG = re.compile(r'<img\b[^>]*>',re.I)
ATTR = re.compile(r'(?P<key>[\w:-]+)\s*=\s*(?P<quote>["\x27])(?P<value>.*?)(?P=quote)',re.I|re.S)
CDN = re.compile(r'^(?P<stem>https://yt3\.ggpht\.com/[A-Za-z0-9_-]{20,})=s1600-rw-nd-v1$',re.I)
# Small-screen cards are far narrower than 1200px. Keep 1200px for
# high-density phones and readable titles printed into Community covers.
THUMB_SIZE = 1200

def transform_tag(tag):
    props={m.group('key').lower():m.group('value') for m in ATTR.finditer(tag)}
    if props.get('loading','').lower()!='lazy':
        return tag
    if 'srcset' in props:
        return tag
    if any(word in props.get('class','').lower().split() for word in ('hero','article-hero','guide-hero','zt-home-guide-photo')):
        return tag
    m=CDN.fullmatch(props.get('src',''))
    if not m:
        return tag
    target=m.group('stem')+f'=s{THUMB_SIZE}-rw-nd-v1'
    # Change only the exact src attr; all sizing, alt, layout and JS remain.
    count=0
    def replace(attr):
        nonlocal count
        if attr.group('key').lower()=='src' and attr.group('value')==props['src']:
            count+=1
            return attr.group(0).replace(props['src'],target,1)
        return attr.group(0)
    result=ATTR.sub(replace,tag)
    assert count==1, 'Unexpected source structure'
    return result

def transform(source):
    revised=IMG.sub(lambda m:transform_tag(m.group(0)),source)
    return revised

def inspect(root,minimum=500):
    changes={}
    html_count=0
    altered_tags=0
    for path in html_pages(root):
        if path.name.startswith(('anteprima-','preview-','draft-')):
            continue
        html_count+=1
        src=path.read_text(encoding='utf-8',errors='replace')
        revised=transform(src)
        if revised!=src:
            new_tags=IMG.findall(revised)
            old_tags=IMG.findall(src)
            assert len(new_tags)==len(old_tags),(path.name,'img tag count changed')
            differences=[(old,new) for old,new in zip(old_tags,new_tags) if old!=new]
            for old,new in differences:
                assert 's1600-rw-nd-v1' in old and 's1200-rw-nd-v1' in new
                # Other image attributes and all non-IMG content unchanged.
                assert transform_tag(old)==new
            altered_tags+=len(differences)
            changes[path]=revised
    if html_count<minimum:
        raise RuntimeError(f'Too few pages seen: {html_count} < {minimum}. Refusing optimization')
    return changes,html_count,altered_tags

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--check',action='store_true')
    args=p.parse_args()
    root=args.root.resolve()
    changes,pages,images=inspect(root)
    print(f'Community thumbnail payload: {images} lazy images in {len(changes)} files; {pages} HTML scanned; dry_run={args.check}')
    if args.check:return
    for path,revised in changes.items():
        path.write_text(revised,encoding='utf-8')

if __name__=='__main__':
    main()
