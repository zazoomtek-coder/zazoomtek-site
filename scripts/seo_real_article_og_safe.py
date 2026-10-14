#!/usr/bin/env python3
"""Add OpenGraph image only when a verifiable main article cover exists.

Run ONLY on an ephemeral Firebase deploy checkout. No body, CSS, JS, YouTube
importer, sitemap, author, date or previously declared OG image is altered.
"""
import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit
from seo_paths_safe import html_pages,canonical_candidates
from seo_head_safe import Metadata
from seo_media_safe import primary_article_image

HEAD_END=re.compile(r'</head\s*>',re.I)
OG_IMAGE=re.compile(r'<meta\b(?=[^>]*\bproperty\s*=\s*["\x27]og:image["\x27])[^>]*>',re.I)
MARKER='<!-- ZT_VERIFIED_ARTICLE_OG_IMAGE_V1 -->'

def transform(path,root,html):
    end=HEAD_END.search(html)
    if not end:return html
    head=html[:end.start()]
    body=html[end.start():]
    if MARKER in head or OG_IMAGE.search(head):return html
    meta=Metadata()
    meta.feed(head)
    if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,path):return html
    if 'noindex' in (meta.meta.get('robots','')+' '+meta.meta.get('googlebot','')).lower():return html
    # Require primary visible editorial article, not a directory/listing or side rail.
    image=primary_article_image(body)
    if not image:return html
    url=urlsplit(image)
    if url.scheme!='https' or not url.netloc or url.username or url.password:return html
    # Do not produce OG images from generic images or known external service icons.
    if url.path.lower().endswith(('.svg','.gif')):return html
    escaped=image.replace('&','&amp;').replace('"','&quot;').replace('<','&lt;')
    modified=head+'\n'+MARKER+'\n<meta property="og:image" content="'+escaped+'">\n'+body
    assert modified.endswith(body)
    return modified

def scan(root):
    root=Path(root).resolve()
    changes={}
    count=0
    for path in html_pages(root):
        count+=1
        before=path.read_text(encoding='utf-8',errors='replace')
        after=transform(path,root,before)
        if before!=after:
            assert HEAD_END.split(before,maxsplit=1)[1]==HEAD_END.split(after,maxsplit=1)[1]
            changes[path]=after
    if count<500:raise RuntimeError('Unexpectedly small site; abort optional OG enhancement')
    return changes,count

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--check',action='store_true')
    args=ap.parse_args()
    changes,count=scan(args.root)
    print(f'Verified article OG cover: {len(changes)} pages eligible / {count} HTML pages; dry-run={args.check}')
    if args.check:return
    # All mutations happen only in temporary deploy checkout after validation.
    for path,after in changes.items():path.write_text(after,encoding='utf-8')

if __name__=='__main__':main()
