#!/usr/bin/env python3
"""Build a canonical sitemap without changing article HTML or import workflows.

Run from repository root (or pass --root). Build and validate in memory, then
atomically replace changed files. Dates come only from verified article metadata.
No YouTube API or Firebase access needed.
"""
import argparse
import json
from datetime import datetime, timezone, date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from seo_paths_safe import html_pages, canonical_candidates

ORIGIN = 'https://zazoomtek.it'
SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9'
MAX_URLS = 45000
MAX_BYTES = 45 * 1024 * 1024
OMIT = {'404.html', 'googlea3c594e14c6f832d.html', 'nba-2k27-recensione-ps5.html'}

class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.robots = []
        self.dates = {}
        self.jsonld = []
        self._json = None

    def handle_starttag(self, tag, pairs):
        props = {k.lower(): (v or '') for k, v in pairs if k}
        if tag.lower() == 'link' and 'canonical' in props.get('rel', '').lower().split():
            self.canonicals.append(props.get('href', '').strip())
        if tag.lower() == 'meta':
            kind = props.get('name', '').lower()
            prop = props.get('property', '').lower()
            if kind in ('robots', 'googlebot'):
                self.robots.append(props.get('content', ''))
            if prop in ('article:modified_time', 'article:published_time'):
                self.dates[prop] = props.get('content', '')
        if tag.lower() == 'script' and props.get('type','').lower() == 'application/ld+json':
            self._json = ''

    def handle_data(self, data):
        if self._json is not None:
            self._json += data

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._json is not None:
            self.jsonld.append(self._json)
            self._json = None

def date_from_meta(value):
    if not value:
        return None
    try:
        value = value.strip()
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            day = date.fromisoformat(value)
            return day.isoformat() if day <= datetime.now(timezone.utc).date() else None
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None or dt.astimezone(timezone.utc) > datetime.now(timezone.utc):
            return None
        return dt.date().isoformat()
    except ValueError:
        return None

def schema_article_lastmod(head, url):
    """Only trust dateModified for the SAME canonical article, never related items."""
    for raw in head.jsonld:
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            continue
        stack = [data]
        while stack:
            node = stack.pop()
            if isinstance(node, list):
                stack.extend(node)
                continue
            if not isinstance(node, dict):
                continue
            if isinstance(node.get('@graph'), list):
                stack.extend(node['@graph'])
            kinds = node.get('@type', [])
            kinds = [kinds] if isinstance(kinds, str) else kinds if isinstance(kinds, list) else []
            if not any(t in kinds for t in ('Article', 'NewsArticle', 'BlogPosting')):
                continue
            page = node.get('mainEntityOfPage')
            target = page if isinstance(page, str) else page.get('@id') if isinstance(page, dict) else None
            if target != url and node.get('url') != url:
                continue
            value = node.get('dateModified')
            if isinstance(value, str):
                validated = date_from_meta(value)
                if validated:
                    return validated
    return None

def entries(root):
    found = {}
    for path in html_pages(root):
        if path.name in OMIT or path.name.startswith('preview-'):
            continue
        try:
            with path.open(encoding='utf-8', errors='replace') as handle:
                source = handle.read(120000)
        except OSError:
            continue
        before_head = re.split(r'</head\s*>', source, maxsplit=1, flags=re.I)[0]
        if len(before_head) == len(source) and len(source) >= 120000:
            continue
        parsed = Head()
        parsed.feed(before_head)
        if any('noindex' in re.split(r'[;,\s]+', rule.lower()) for rule in parsed.robots):
            continue
        if len(parsed.canonicals) != 1 or parsed.canonicals[0] not in canonical_candidates(root, path):
            continue
        expected = parsed.canonicals[0]
        parts = urlsplit(expected)
        if parts.scheme != 'https' or parts.netloc != 'zazoomtek.it':
            continue
        lastmod = (date_from_meta(parsed.dates.get('article:modified_time'))
                   or schema_article_lastmod(parsed, expected)
                   or date_from_meta(parsed.dates.get('article:published_time')))
        found[expected] = lastmod
    if ORIGIN + '/' not in found:
        raise ValueError('Homepage canonical missing: refusing sitemap changes')
    return sorted(found.items(), key=lambda pair: (pair[0] != ORIGIN + '/', pair[0]))

def url_node(url, lastmod):
    row = f'  <url><loc>{escape(url)}</loc>'
    if lastmod:
        row += f'<lastmod>{lastmod}</lastmod>'
    return row + '</url>\n'

def wrap_urlset(rows):
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="{SITEMAP_NS}">\n' + ''.join(rows) + '</urlset>\n').encode('utf-8')

def build(root):
    items = entries(root)
    files, blocks, current, current_size = {}, [], [], 150
    for item in items:
        row = url_node(*item)
        size = len(row.encode('utf-8'))
        if current and (len(current) >= MAX_URLS or current_size + size >= MAX_BYTES):
            blocks.append(wrap_urlset(current))
            current, current_size = [], 150
        current.append(row)
        current_size += size
    if current:
        blocks.append(wrap_urlset(current))
    if len(blocks) == 1:
        files['sitemap.xml'] = blocks[0]
        files['google-sitemap.xml'] = blocks[0]
    else:
        names = []
        for i, content in enumerate(blocks, 1):
            name = f'sitemap-part-{i:04d}.xml'
            names.append(name)
            files[name] = content
        nodes = ''.join(f'  <sitemap><loc>{ORIGIN}/{name}</loc></sitemap>\n' for name in names)
        index = (f'<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="{SITEMAP_NS}">\n' + nodes + '</sitemapindex>\n').encode('utf-8')
        files['sitemap.xml'] = index
        files['google-sitemap.xml'] = index
    files['sitemap.txt'] = ('\n'.join(url for url, _ in items) + '\n').encode('utf-8')
    for name, content in files.items():
        if name.endswith('.xml'):
            ET.fromstring(content)
            if len(content) > MAX_BYTES:
                raise ValueError(f'{name} exceeds sitemap size safety limit')
    return files, len(items)

def publish(root, outputs, check=False):
    changed = [name for name, value in outputs.items() if not (root / name).exists() or (root / name).read_bytes() != value]
    if check:
        return changed
    for name in changed:
        fd, temporary = tempfile.mkstemp(prefix='.zt-sitemap-', dir=str(root))
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(outputs[name])
            os.replace(temporary, root / name)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return changed

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--check', action='store_true', help='read-only dry run')
    args = parser.parse_args()
    root = args.root.resolve()
    outputs, count = build(root)
    changed = publish(root, outputs, check=args.check)
    print(f'SEO sitemap: {count} canonical URLs; {len(changed)} files {"would change" if args.check else "updated"}: {", ".join(changed) or "none"}')

if __name__ == '__main__':
    main()
