#!/usr/bin/env python3
"""Use a small faithful PNG for header logos, retain the full original elsewhere.

All HTML edits occur only in the ephemeral Firebase deploy checkout. The
small optimized header asset is committed and fingerprinted once, so future
deploys don't need Pillow unless the source logo actually changes.
"""
import argparse
import hashlib
import io
import os
import re
import tempfile
from pathlib import Path
from seo_paths_safe import html_pages

OLD = 'ChatGPT.png'
NEW = '/assets/zt-header-logo-128.png'
HASH_FILE = 'assets/zt-header-logo-128.sha256'
IMG = re.compile(r'<img\b[^>]*>',re.I)
HEADER = re.compile(r'<header\b[^>]*>[\s\S]*?</header\s*>',re.I)
ATTR = re.compile(r'(?P<name>[\w:-]+)\s*=\s*(?P<quote>["\x27])(?P<value>.*?)(?P=quote)',re.I|re.S)

def rewrite_tag(tag):
    d={x.group('name').lower():x.group('value') for x in ATTR.finditer(tag)}
    old=d.get('src','')
    if old not in ('/ChatGPT.png','ChatGPT.png'):
        return tag
    if d.get('alt','').strip().lower()!='zazoomtek':
        return tag
    return ATTR.sub(lambda m: m.group(0).replace(old,NEW,1) if m.group('name').lower()=='src' else m.group(0),tag,count=0)

def rewrite_html(source):
    def transform_header(m):
        return IMG.sub(lambda z:rewrite_tag(z.group(0)),m.group(0))
    out=HEADER.sub(transform_header,source)
    # No metadata, JSON-LD, text, thumbnails, or CSS changed.
    return out

def logo_hash(root):
    return hashlib.sha256((root/OLD).read_bytes()).hexdigest()

def asset_current(root):
    output=root/NEW.lstrip('/')
    fingerprint=root/HASH_FILE
    return output.is_file() and fingerprint.is_file() and fingerprint.read_text(encoding='ascii').strip()==logo_hash(root)

def render_png(root):
    from PIL import Image,ImageOps,ImageChops,ImageStat
    origin=root/OLD
    raw=origin.read_bytes()
    img=Image.open(io.BytesIO(raw))
    img=ImageOps.exif_transpose(img).convert('RGBA')
    if img.width<128 or img.height<128:
        raise RuntimeError('Original logo too small for a 128px retina header; refusing to upscale')
    small=img.copy()
    small.thumbnail((128,128),Image.Resampling.LANCZOS)
    # Maintain natural aspect; let existing CSS decide any crop.
    buf=io.BytesIO()
    small.save(buf,format='PNG',optimize=True,compress_level=9)
    optimized=buf.getvalue()
    if len(optimized)>=len(raw)*.6:
        raise RuntimeError(f'Logo not sufficiently smaller ({len(optimized)} vs {len(raw)})')
    baseline=img.resize((54,54),Image.Resampling.LANCZOS)
    sample=small.resize((54,54),Image.Resampling.LANCZOS)
    bands=ImageStat.Stat(ImageChops.difference(baseline,sample)).mean
    if max(bands)>4:
        raise RuntimeError(f'Logo pixel divergence exceeded safety threshold: {bands}')
    return optimized,(img.width,img.height),small.size,len(raw)

def write_atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=str(path.parent),prefix='.zt-logo-')
    try:
        with os.fdopen(fd,'wb') as f:f.write(data)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def prepare_logo(root,check=False):
    if asset_current(root):
        output=root/NEW.lstrip('/')
        print(f'Header logo unchanged: {output.stat().st_size}B; no regeneration')
        return
    optimized,original,resized,oldsize=render_png(root)
    print(f'Header logo source {original} / {oldsize} B; optimized {resized} / {len(optimized)} B')
    if not check:
        write_atomic(root/NEW.lstrip('/'),optimized)
        write_atomic(root/HASH_FILE,(logo_hash(root)+'\n').encode('ascii'))

def run(root,check=False,build_only=False):
    root=Path(root).resolve()
    prepare_logo(root,check=check)
    if build_only:return
    changed={}
    seen=0
    for p in html_pages(root):
        seen+=1
        src=p.read_text(encoding='utf-8',errors='replace')
        new=rewrite_html(src)
        if new!=src:
            changes=src.count('src="/ChatGPT.png"')+src.count('src="ChatGPT.png"')
            if NEW not in new or changes==0:
                raise RuntimeError(f'Unexpected header structure: {p.name}')
            changed[p]=new
    if seen<500 or len(changed)<20:
        raise RuntimeError(f'Unexpected site cardinality {seen} pages {len(changed)} with header logos')
    print(f'Header logo: {len(changed)} published HTML pages update only header img/src; read-only={check}')
    if not check:
        if not asset_current(root):
            raise RuntimeError('Logo asset missing or out of sync; refusing any HTML changes')
        for path,content in changed.items():write_atomic(path,content.encode('utf-8'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--check',action='store_true')
    ap.add_argument('--build-only',action='store_true')
    args=ap.parse_args()
    run(args.root,args.check,args.build_only)
if __name__=='__main__':main()
