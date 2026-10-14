#!/usr/bin/env python3
"""Read-only SEO media audit for current and future sections.

Never downloads third-party images, changes content, calls YouTube, or deploys.
Local image dimensions are validated using Pillow when available.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
from seo_paths_safe import html_pages, ORIGIN
from seo_head_safe import Metadata
from seo_media_safe import feed_videos, verified_video

def local_image_size(root, url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or parts.netloc != urlsplit(ORIGIN).netloc:
        return 'external', None
    path = (root / unquote(parts.path).lstrip('/')).resolve()
    if not path.is_relative_to(root.resolve()) or not path.exists():
        return 'missing', None
    try:
        from PIL import Image
        with Image.open(path) as im:
            return 'local', im.size
    except ImportError:
        return 'unverified', None
    except (OSError, ValueError):
        return 'invalid', None

def inspect(root):
    known=feed_videos(root)
    counted=Counter()
    samples={'missing_og_image': [], 'undersized_local': [], 'invalid_local': [], 'remote_unverified': [], 'verified_video_markup_candidates': []}
    for path in html_pages(root):
        counted['html_pages']+=1
        source=path.read_text(encoding='utf-8',errors='replace')
        head=source.split('</head>',1)[0]
        if head==source:
            counted['missing_head_end']+=1
            continue
        data=Metadata()
        data.feed(head)
        if data.meta.get('robots','').lower().find('noindex')>=0:
            counted['noindex_pages']+=1
            continue
        if len(data.canonicals)!=1:
            counted['noncanonical']+=1
            continue
        image=data.meta.get('og:image','').strip()
        if not image:
            counted['missing_og_image']+=1
            if len(samples['missing_og_image'])<15:
                samples['missing_og_image'].append(path.as_posix())
        else:
            status,dims=local_image_size(root,image)
            counted['image_'+status]+=1
            if dims:
                width,height=dims
                if width>=1200 and width*height>300000:
                    counted['local_1200plus']+=1
                else:
                    counted['undersized_local']+=1
                    if len(samples['undersized_local'])<20:
                        samples['undersized_local'].append({'path':path.as_posix(),'size':[width,height]})
            elif status in ('invalid','missing','external'):
                key='remote_unverified' if status=='external' else 'invalid_local'
                if len(samples[key])<10:
                    samples[key].append({'path':path.as_posix(),'image':image[:180]})
        if '<iframe' in source.lower():
            counted['iframe_mention']+=1
            obj=verified_video(source,known)
            if obj:
                counted['verified_video_markup_candidates']+=1
                if len(samples['verified_video_markup_candidates'])<15:
                    samples['verified_video_markup_candidates'].append({'path':path.as_posix(),'name':obj['name'],'embedUrl':obj['embedUrl']})
    return {'summary':dict(counted),'samples':samples,'notes':[
       'Images served by third parties are not downloaded or dimension-verified.',
       'A qualifying image does not guarantee Google Discover placement.',
       'VideoObject is only proposed for literal main-content embeds with a matching published video record.',
       'All reported values are diagnostic; this command changes no site content.'
    ]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--output',type=Path,help='write only an audit report (never site files)')
    args=ap.parse_args()
    report=inspect(args.root.resolve())
    if report['summary'].get('html_pages',0)<500:
        raise RuntimeError('SEO audit stopped: unexpected repository size')
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
if __name__=='__main__':
    main()
