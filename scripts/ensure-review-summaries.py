#!/usr/bin/env python3
"""Add one genuine 'Recensione in sintesi' to every published review page.

No LLM extraction, external media lookup, homepage editing or invented scores.
Descriptions and thumbnails come only from each review's own metadata/body.
Designed for repeatable Cloudflare builds and future YouTube-imported reviews.
"""
from __future__ import annotations

import argparse
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
CSS_LINK='<link rel="stylesheet" href="/zt-review-summary.css?v=20261017a">'
SIDEBAR=re.compile(r'<aside\b[^>]*\bclass=["\'][^"\']*\b(?:article-side|news-sidebar)\b[^"\']*["\'][^>]*>',re.I)
CARD=re.compile(r'<section\b[^>]*>\s*<h3\b[^>]*>\s*Recensione in sintesi\s*</h3>.*?</section>',re.I|re.S)
SUMMARY_CARD=re.compile(r'<section\b[^>]*\bzt-review-summary\b[^>]*>.*?</section>',re.I|re.S)
TITLE=re.compile(r'<h1\b[^>]*>(.*?)</h1>',re.I|re.S)
TAG=re.compile(r'<[^>]+>')
PARA=re.compile(r'<p\b[^>]*>(.*?)</p>',re.I|re.S)

class SummaryError(RuntimeError):
    pass

class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.description=''
        self.image=''
        self.heading=''
    def handle_starttag(self,tag,attrs):
        if tag!='meta':
            return
        info=dict(attrs)
        if info.get('name','').lower()=='description':
            self.description=info.get('content','')
        elif info.get('property','').lower()=='og:image':
            self.image=info.get('content','')

def plain(value:str)->str:
    return re.sub(r'\s+',' ',unescape(TAG.sub(' ',value))).strip()

def review_pages(root:Path)->list[Path]:
    pages={p for pattern in ("recensione-*.html","*-recensione-*.html")
           for p in root.glob(pattern) if p.is_file()
           and not p.name.startswith(("preview-","anteprima-","test-"))}
    return sorted(pages)

def first_image(markup:str,metadata:Metadata,root:Path)->str:
    hero=re.search(r'<img\b[^>]*class=["\'][^"\']*\bhero\b[^"\']*["\'][^>]*>',markup,re.I)
    article=re.search(r'<main\b[^>]*>(.*?)</main>',markup,re.I|re.S)
    candidates=[metadata.image]
    if hero:
        found=re.search(r'\bsrc=["\']([^"\']+)["\']',hero.group(),re.I)
        if found:
            candidates.append(unescape(found.group(1)))
    if article:
        for match in re.finditer(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']',article.group(1),re.I):
            candidates.append(unescape(match.group(1)))
    for value in candidates:
        value=value.strip()
        if value.startswith("//"):
            value="https:"+value
        parts=urlsplit(value)
        if value.startswith("/") and not value.startswith("//") and (root/value.lstrip("/").split("?")[0]).is_file():
            return value
        if parts.scheme=="https" and parts.hostname and not parts.username and not parts.password:
            return value
    return ''

def summary_text(markup:str,metadata:Metadata,title:str)->str:
    sentence=plain(metadata.description)
    if not sentence or sentence.lower().startswith(("pagina archivio", "archivio della recensione")):
        main=re.search(r'<main\b[^>]*>(.*?)</main>',markup,re.I|re.S)
        paragraphs=PARA.findall(main.group(1)) if main else []
        sentence=next((plain(p) for p in paragraphs if len(plain(p))>85),"")
    sentence=re.sub(r'^(?:Introduzione\s+)+','',sentence,flags=re.I)
    if not sentence:
        sentence=f"Recensione e approfondimento dedicati a {title}."
    # Keep the first well-formed sentence rather than an invented synopsis.
    sentence=re.sub(r'\s+',' ',sentence).strip()
    if len(sentence)>235:
        cut=sentence[:235].rfind(' ')
        sentence=sentence[:cut if cut>=155 else 235].rstrip(' ,;:-')+"…"
    return sentence

def updated_review(path:Path,root:Path)->str:
    source=path.read_text(encoding='utf-8')
    side=SIDEBAR.search(source)
    if side is None:
        raise SummaryError(f'{path.name}: no verified article sidebar to safely attach the summary')
    title_match=TITLE.search(source)
    if not title_match:
        raise SummaryError(f'{path.name}: article heading missing')
    title=plain(title_match.group(1))
    metadata=Metadata()
    metadata.feed(source.split('</head>',1)[0])
    card=SUMMARY_CARD.search(source)
    if card:
        # Already normalized: preserve the existing content and cover.
        if source.count('zt-review-summary"')!=1:
            raise SummaryError(f'{path.name}: duplicated review summary')
        if CSS_LINK not in source:
            raise SummaryError(f'{path.name}: normalized card without mandatory 16:9 stylesheet')
        return source

    old=CARD.search(source)
    if old:
        # Preserve ThermoMate's manually fact-checked power/IP65/vote details.
        block=old.group(0)
        block=re.sub(r'<section\b[^>]*>',
                     '<section class="side-box zt-review-summary" aria-label="Recensione in sintesi">',
                     block,count=1,flags=re.I)
        block=block.replace('<div>','<div class="zt-review-summary-body">',1)
        if not re.search(r'<img\b[^>]*\bsrc=',block,re.I):
            raise SummaryError(f'{path.name}: existing summary has no product image')
        # Remove the old position to keep the summary next to the first
        # sidebar section. Do not delete any other editorial sidebar boxes.
        source=source[:old.start()]+source[old.end():]
    else:
        image=first_image(source,metadata,root)
        if not image:
            raise SummaryError(f'{path.name}: no actual cover or review image; refusing a fake thumbnail')
        synopsis=summary_text(source,metadata,title)
        block=(
            '<section class="side-box zt-review-summary" aria-label="Recensione in sintesi">'
            '<h3>Recensione in sintesi</h3>'
            '<div class="zt-review-summary-body">'
            f'<img src="{escape(image,quote=True)}" alt="{escape(title,quote=True)}"'
            ' loading="lazy" decoding="async" width="640" height="360">'
            f'<p>{escape(synopsis)}</p>'
            '</div></section>'
        )
    side=SIDEBAR.search(source)
    if not side:
        raise SummaryError(f'{path.name}: sidebar disappeared')
    source=source[:side.end()]+block+source[side.end():]
    if CSS_LINK not in source:
        source=source.replace('</head>',CSS_LINK+'</head>',1)
    return source

def validate(root:Path)->int:
    pages=review_pages(root)
    if not pages:
        raise SummaryError("No review pages found")
    if not (root/"zt-review-summary.css").is_file():
        raise SummaryError("Shared summary CSS missing")
    css=(root/"zt-review-summary.css").read_text(encoding="utf-8")
    if "aspect-ratio:16/9" not in css or "object-fit:contain" not in css:
        raise SummaryError("Summary thumbnails must be 16:9 without stretching or clipping")
    for path in pages:
        content=path.read_text(encoding="utf-8")
        if len(SUMMARY_CARD.findall(content))!=1 or len(CARD.findall(content))!=1:
            raise SummaryError(f'{path.name}: expected exactly one Recensione in sintesi box')
        if CSS_LINK not in content:
            raise SummaryError(f'{path.name}: missing 16:9 CSS')
        card=SUMMARY_CARD.search(content).group()
        image=re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)["\']',card,re.I)
        if not image:
            raise SummaryError(f'{path.name}: summary miniature missing')
        if not re.search(r'<h3\b[^>]*>\s*Recensione in sintesi\s*</h3>',card,re.I):
            raise SummaryError(f'{path.name}: summary title missing')
    print(f"PASS: {len(pages)} review summaries, each one using a real thumbnail fitted 16:9")
    return len(pages)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        assert plain('<p>L&#x27;articolo <b>vero</b></p>')=="L'articolo vero"
        assert first_image('<main><img src="https://example.org/photo.jpg"></main>',Metadata(),ROOT)
        assert summary_text('',Metadata(),'Un prodotto').startswith('Recensione e approfondimento')
        print("REVIEW SUMMARY SELF TEST PASS")
        return
    if args.check:
        validate(ROOT)
        return
    pages=review_pages(ROOT)
    count=0
    for path in pages:
        updated=updated_review(path,ROOT)
        original=path.read_text(encoding="utf-8")
        if updated!=original:
            path.write_text(updated,encoding="utf-8")
            count+=1
    print(f"REVIEW SUMMARY GENERATED: {count} pages updated of {len(pages)}")
    validate(ROOT)

if __name__=="__main__":
    main()
