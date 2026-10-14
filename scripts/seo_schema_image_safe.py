#!/usr/bin/env python3
"""Add verified primary article cover to existing JSON-LD, head only.

This is an optional release-time enrichment. It never touches article bodies,
importers, styles, existing image fields, ratings, authors, or dates.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from seo_head_safe import Metadata
from seo_media_safe import primary_article_image
from seo_paths_safe import html_pages, canonical_candidates

LD_SCRIPT = re.compile(
    r'<script\b(?=[^>]*\btype\s*=\s*["\x27]application/ld\+json["\x27])[^>]*>'
    r'(?P<json>[\s\S]*?)</script\s*>', re.I
)
END_HEAD = re.compile(r'</head\s*>', re.I)
ARTICLE_TYPES = {'Article', 'NewsArticle', 'BlogPosting'}

def article_type(value):
    if isinstance(value, str):
        return value in ARTICLE_TYPES
    return isinstance(value, list) and any(isinstance(v, str) and v in ARTICLE_TYPES for v in value)

def matches_entity(entity, canonical):
    if isinstance(entity, str):
        return entity == canonical
    if isinstance(entity, dict):
        return entity.get('@id') == canonical
    return False

def add_image_to_graph(data, canonical, url):
    """Only change a NewsArticle/Article specifically tied to THIS URL."""
    edited = 0
    if isinstance(data, dict):
        nodes = data.get('@graph')
        if isinstance(nodes, list):
            for node in nodes:
                edited += add_image_to_graph(node, canonical, url)
        if article_type(data.get('@type')) and matches_entity(data.get('mainEntityOfPage'), canonical) and 'image' not in data:
            data['image'] = [url]
            edited += 1
    elif isinstance(data, list):
        for node in data:
            edited += add_image_to_graph(node, canonical, url)
    return edited

def transform(path, root, source):
    """Returns original HTML on any uncertainty. Body must be byte-identical."""
    rel = path.relative_to(root)
    if path.name.startswith(('preview-', 'anteprima-', 'draft-')):
        return source
    end = END_HEAD.search(source)
    if not end:
        return source
    head, rest = source[:end.start()], source[end.start():]
    metadata = Metadata()
    metadata.feed(head)
    if len(metadata.canonicals) != 1 or metadata.canonicals[0] not in canonical_candidates(root, path):
        return source
    canonical = metadata.canonicals[0]
    robots = ' '.join(metadata.meta.get(k,'') for k in ('robots','googlebot')).lower()
    if re.search(r'(?<![a-z])(?:noindex|none|noimageindex)(?![a-z])', robots):
        return source
    image = primary_article_image(rest)
    if not image:
        return source
    parts = urlsplit(image)
    if parts.scheme != 'https' or not parts.netloc or parts.username or parts.password:
        return source

    def augment(match):
        raw = match.group('json')
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return match.group(0)
        added = add_image_to_graph(parsed, canonical, image)
        if added != 1:
            return match.group(0)
        revised = json.dumps(parsed, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
        return match.group(0)[:match.start('json')-match.start()] + revised + match.group(0)[match.end('json')-match.start():]

    revised_head = LD_SCRIPT.sub(augment, head)
    if revised_head == head:
        return source
    result = revised_head + rest
    assert result.endswith(rest), 'Article body changed: abort SEO'
    return result

def build(root):
    root=root.resolve()
    modified={}
    examined=0
    for p in html_pages(root):
        examined += 1
        original=p.read_text(encoding='utf-8',errors='replace')
        revised=transform(p,root,original)
        if revised != original:
            a=END_HEAD.search(original)
            b=END_HEAD.search(revised)
            assert a and b and original[a.start():] == revised[b.start():], p.name
            modified[p]=revised
    if examined < 500:
        raise RuntimeError(f'SEO safety: unexpected page count {examined}')
    return modified, examined

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true',help='read-only test mode')
    args=parser.parse_args()
    changes, examined=build(args.root)
    print(f'Article image schema: {len(changes)} verified pages / {examined} inspected; check={args.check}')
    if args.check:
        for path in list(changes)[:15]:
            print('Eligible:',path)
        return
    # Build all changes before writing; no article body or existing structured data is removed.
    for path, revised in changes.items():
        path.write_text(revised,encoding='utf-8')

if __name__ == '__main__':
    main()
