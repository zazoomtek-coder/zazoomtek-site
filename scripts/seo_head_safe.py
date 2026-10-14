#!/usr/bin/env python3
"""Optional, head-only SEO enrichment. Never changes article bodies, CSS or scripts.

Only adds an image preview permission when no preview restriction exists.
Only adds Article/NewsArticle JSON-LD when the page already declares itself an
article and does not already supply JSON-LD. Never fabricates dates or ratings.
"""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import json
import html
import os
import re
import tempfile
from seo_paths_safe import html_pages, canonical_candidates
from seo_media_safe import verified_video, feed_videos, primary_article_image

ORIGIN = 'https://zazoomtek.it'
MARKER = '<!-- ZT_SEO_HEAD_SAFE_V1 -->'

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.canonicals = []
        self.jsonld = False

    def handle_starttag(self, tag, pairs):
        tag = tag.lower()
        a = {k.lower(): (v or '') for k, v in pairs if k}
        if tag == 'meta':
            key = (a.get('property') or a.get('name') or '').lower()
            if key and key not in self.meta:
                self.meta[key] = a.get('content', '').strip()
        elif tag == 'link' and 'canonical' in a.get('rel', '').lower().split():
            self.canonicals.append(a.get('href', '').strip())
        elif tag == 'script' and a.get('type', '').lower() == 'application/ld+json':
            self.jsonld = True

def valid_url(url):
    try:
        parts = urlsplit(url)
        return parts.scheme == 'https' and bool(parts.netloc) and not parts.username and not parts.password
    except ValueError:
        return False

def transform(name, text, canonical_urls=None, known_videos=None):
    if MARKER in text or name.startswith('preview-') or name == '404.html':
        return text
    end = re.search(r'</head\s*>', text, re.I)
    if not end:
        return text
    head, remainder = text[:end.start()], text[end.start():]
    meta = Metadata()
    meta.feed(head)
    expected = canonical_urls or {ORIGIN + ('/' if name == 'index.html' else '/' + name)}
    if len(meta.canonicals) != 1 or meta.canonicals[0] not in expected:
        return text
    canonical = meta.canonicals[0]
    robots = ' '.join(meta.meta.get(k, '') for k in ('robots', 'googlebot')).lower()
    if re.search(r'(?<![a-z])(?:noindex|none|noimageindex)(?![a-z])', robots):
        return text

    insert = []
    # Select an image ALREADY displayed as the main article's cover.
    # Never guess from related-news thumbnails, site logos or category lists.
    hero = None
    if 'og:image' not in meta.meta and '<article' in remainder.lower():
        hero = primary_article_image(remainder)
        if hero:
            insert.append('<meta property="og:image" content="' + html.escape(hero, quote=True) + '">')
            if 'twitter:image' not in meta.meta:
                insert.append('<meta name="twitter:image" content="' + html.escape(hero, quote=True) + '">')
    if not re.search(r'max-image-preview\s*:', robots):
        insert.append('<meta name="robots" content="max-image-preview:large">')

    if meta.meta.get('og:type', '').lower() == 'article' and not meta.jsonld:
        title = meta.meta.get('og:title', '').strip()
        description = meta.meta.get('description', '').strip()
        if title and description:
            article = {
                '@context': 'https://schema.org',
                '@type': 'NewsArticle' if name.startswith('news-') else 'Article',
                'headline': title,
                'description': description,
                'mainEntityOfPage': canonical,
                'inLanguage': 'it-IT',
                'publisher': {'@type': 'Organization', 'name': 'ZazoomTek', 'url': ORIGIN + '/'},
            }
            author = meta.meta.get('author', '').strip()
            if author:
                article['author'] = {'@type': 'Organization', 'name': author} if author == 'ZazoomTek' else {'@type': 'Person', 'name': author}
            image = meta.meta.get('og:image', '').strip() or hero
            if valid_url(image):
                article['image'] = [image]
            for field, key in [('article:published_time', 'datePublished'), ('article:modified_time', 'dateModified')]:
                value = meta.meta.get(field, '').strip()
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
                    article[key] = value
            payload = json.dumps(article, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
            insert.append('<script type="application/ld+json">' + payload + '</script>')

    # Only verified, directly embedded main-content videos. No sidebar thumbnails,
    # scripted embeds, guessed publication dates or unrelated YouTube links.
    if known_videos and '<iframe' in remainder.lower() and not re.search(
            r'["\x27]@type["\x27]\s*:\s*["\x27]VideoObject["\x27]', head, re.I):
        video = verified_video(remainder, known_videos)
        if video:
            payload = json.dumps(video, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
            insert.append('<script type="application/ld+json">' + payload + '</script>')

    if not insert:
        return text
    out = head + '\n' + MARKER + '\n' + '\n'.join(insert) + '\n' + remainder
    # Defensive contract: never change any bytes from </head> onward.
    assert out.endswith(remainder)
    assert out.count(MARKER) == 1
    return out

def build(root):
    changes = {}
    count = 0
    known_videos = feed_videos(root)
    for path in html_pages(root):
        source = path.read_text(encoding='utf-8', errors='replace')
        revised = transform(path.name, source, canonical_candidates(root, path), known_videos)
        if revised != source:
            before = re.split(r'</head\s*>', source, maxsplit=1, flags=re.I)
            after = re.split(r'</head\s*>', revised, maxsplit=1, flags=re.I)
            if len(before) != 2 or len(after) != 2 or before[1] != after[1]:
                raise RuntimeError(f'Body changed in {path.name}: abort SEO')
            changes[path] = revised
        count += 1
    if count < 500:
        raise RuntimeError(f'Only {count} HTML files seen: SEO safeguard')
    return changes

def apply(changes):
    for path, content in changes.items():
        fd, temporary = tempfile.mkstemp(prefix='.zt-seo-head-', dir=str(path.parent))
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write(content)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, default=Path('.'))
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    changes = build(args.root)
    if not args.check:
        apply(changes)
    print(f'Optional SEO head: {len(changes)} pages {"would gain" if args.check else "gained"} safe metadata; article bodies unchanged')

if __name__ == '__main__':
    main()
