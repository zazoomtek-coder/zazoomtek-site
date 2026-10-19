#!/usr/bin/env python3
"""Build the lightweight TECH/GAMING written-review archives from published pages.

Run at build time only; nothing is filtered or rescanned in readers' browsers.
Preserves the original card URLs, the approved page shell, and full editorial rail.
Uncertain classification leaves a review in the legacy all-reviews archive.
"""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CARD = re.compile(r'<article\s+class="news-row"[^>]*>[\s\S]*?</article>', re.I)
LINK = re.compile(r'<h2>\s*<a\s+href="(/[^"#?]+\.html)"', re.I)
TITLE = re.compile(r'<h2>\s*<a[^>]*>([\s\S]*?)</a>', re.I)
BEG = '<div class="news-list" id="reviewList">'
END_BANNER = '<!-- ZT_COMMUNITY_BANNER_START -->'


def list_boundary(text: str, start: int) -> int:
    """Generated archives may not yet include a Community banner."""
    ends = [i for token in (END_BANNER, '</section><aside', '<aside')
            if (i := text.find(token, start)) >= 0]
    return min(ends) if ends else -1
PAGES = {'tech': 'recensioni-tech.html', 'gaming': 'recensioni-gaming.html'}
# Immutable editorially approved covers (19 October 2026). The YouTube
# source may still carry an older thumbnail; do not restore it at rebuild time.
REVIEW_COVER_OVERRIDES = {
    "recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html":
        "/assets/recensioni/70mai-a900-cover-20261019.webp",
    "recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html":
        "/assets/recensioni/iifactor-m08e-cover-20261019.webp",
}


# The title of a game need not contain "PS5" or "PC"; product-specific
# indicators take precedence over generic mentions of gaming.
HARDWARE = re.compile(
    r'\b(?:thermomate|70mai|iifactor|dash\s?cam|smart\s?glasses|smartphone|'
    r'router|fritz.?box|notebook|laptop|mini\s?pc|pc\s?desktop|'
    r'cuffie|headset|tastier[ae]|mouse|monitor|auricolari|buds|'
    r'riscaldatore|stufa|telecamer[ae]|webcam|powerbank|caricatore|'
    r'proiettore|microfono|ssd|soundbar|aspirapolvere|stampante|'
    r'dispositivo|hardware|gadget|computer|tablet|speaker)\b', re.I)
GAMES = re.compile(
    r'\b(?:videogioch[io]|video\s?game|gameplay|game\s?review|'
    r'playstation|ps[45]|xbox|nintendo|switch|steam|'
    r'gioco\s+di\s+ruolo|roguelike|metroidvania|boss\s?rush|'
    r'picchiaduro|sparatutto|gestionale|simulatore|avventura\s+grafica|'
    r'platform|rpg)\b', re.I)
SECTION_GAMES = re.compile(r'\b(?:Gameplay|Storia|Il gameplay|Meccaniche di gioco)\b', re.I)
SECTION_TECH = re.compile(r'\b(?:Materiali e design|Hardware e prestazioni|Uso quotidiano|Autonomia)\b', re.I)


def text_only(value: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', ' ', value)).strip()


def slug_from_card(card: str) -> str:
    match = LINK.search(card)
    return match.group(1).lstrip('/') if match else ''


def review_category(card: str, root: Path = ROOT) -> str | None:
    title_match = TITLE.search(card)
    title = text_only(title_match.group(1)) if title_match else ''
    link = slug_from_card(card)
    if not title or not link or not (root / link).is_file():
        return None
    if HARDWARE.search(title):
        return 'tech'
    if GAMES.search(title):
        return 'gaming'
    # Secondary inspection is only needed for titles without strong indicators.
    p = (root / link).read_text(encoding='utf-8', errors='replace')
    section = re.search(r'<(?:div|section)\b[^>]*class="[^"]*(?:article-body|review-body|article-content)[^"]*"[^>]*>([\s\S]*?)</(?:div|section)>', p, re.I)
    body = text_only(section.group(1)) if section else text_only(p[:18000])
    excerpt = text_only(card)
    if SECTION_GAMES.search(body[:8000]) and not HARDWARE.search(title):
        return 'gaming'
    if SECTION_TECH.search(body[:8000]):
        return 'tech'
    if GAMES.search(excerpt[:750]):
        return 'gaming'
    if HARDWARE.search(excerpt[:750]):
        return 'tech'
    return None


def studio_cards(root: Path, seen: set[str]) -> list[tuple[str, str]]:
    """Studio's manifest is the source of truth for unpublished-to-archive reviews."""
    path = root / 'studio/articoli.json'
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('Studio article registry must be a list')
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        category = str(item.get('category') or '')
        if category not in ('Recensioni Gaming', 'Recensioni Hi-Tech'):
            continue
        target = 'gaming' if category == 'Recensioni Gaming' else 'tech'
        href = str(item.get('url') or '')
        parsed = urlparse(href)
        slug = parsed.path.lstrip('/')
        if (parsed.scheme or parsed.netloc or not re.fullmatch(r'[a-z0-9-]+\.html', slug)
                or slug in seen or not (root / slug).is_file()):
            continue
        title = str(item.get('title') or '').strip()
        if not title:
            continue
        seen.add(slug)
        pic = str(item.get('image') or '/ChatGPT.png')
        if not (pic.startswith('/') or pic.startswith('https://')):
            pic = '/ChatGPT.png'
        desc = re.sub(r'\s+', ' ', str(item.get('description') or title)).strip()[:260]
        date = str(item.get('published_at') or '')[:10]
        safe = lambda t: html.escape(t, quote=True)
        card = ('<article class="news-row" data-news-search="' + safe((title + ' ' + desc).lower()) + '">'
                '<a href="/' + safe(slug) + '"><img src="' + safe(pic) + '" alt="' + safe(title)
                + '" loading="lazy"></a><div class="news-copy"><h2><a href="/' + safe(slug) + '">'
                + safe(title) + '</a></h2><div class="news-meta">ZazoomTek · ' + safe(date)
                + ' · ' + ('Gaming' if target == 'gaming' else 'Tech')
                + '</div><p>' + safe(desc) + '</p><a class="news-read" href="/' + safe(slug)
                + '">Leggi la recensione ›</a></div></article>')
        result.append((target, card))
    return result


def archive_pages(root: Path) -> list[Path]:
    pages = [root / 'recensioni-scritte.html']
    pages += sorted(root.glob('recensioni-scritte-[0-9]*.html'))
    return pages


def build(root: Path = ROOT) -> dict[str, int]:
    main = root / 'recensioni-scritte.html'
    if not main.is_file():
        raise FileNotFoundError('Official written-review archive is absent')
    base = main.read_text(encoding='utf-8')
    marker = base.find(BEG)
    banner = list_boundary(base, marker)
    if marker < 0 or banner < 0:
        raise RuntimeError('Official archive list or full editorial shell changed: safe stop')
    list_start = marker + len(BEG)
    matches = list(CARD.finditer(base, list_start, banner))
    if not matches:
        raise RuntimeError('Official archive contains no review cards: safe stop')
    after_cards = base[matches[-1].end():banner]
    if not after_cards.lstrip().startswith('</div>'):
        raise RuntimeError('Review-list boundary changed: safe stop')
    cards: dict[str, list[str]] = {'tech': [], 'gaming': []}
    seen: set[str] = set()
    for archive in archive_pages(root):
        source = archive.read_text(encoding='utf-8')
        s = source.find(BEG)
        e = list_boundary(source, s)
        if s < 0:
            raise RuntimeError('Review archive missing list: ' + archive.name)
        if e < 0:
            e = len(source)
        for match in CARD.finditer(source, s + len(BEG), e):
            card = match.group()
            slug = slug_from_card(card)
            if not slug or slug in seen:
                continue
            seen.add(slug)
            override = REVIEW_COVER_OVERRIDES.get(slug)
            if override:
                if not (root / override.lstrip('/')).is_file():
                    raise RuntimeError('Missing approved review cover: ' + override)
                card, replaced = re.subn(
                    r'(<img\\b[^>]*\\bsrc=")[^"]+(")',
                    lambda match: match.group(1) + override + match.group(2),
                    card, count=1, flags=re.I)
                if replaced != 1:
                    raise RuntimeError('Approved review card image missing: ' + slug)
            cat = review_category(card, root)
            if cat:
                cards[cat].append(card)
            else:
                print('REVIEW CATEGORY NEEDS EDITORIAL CHECK:', slug)
    for category, card in studio_cards(root, seen):
        cards[category].insert(0, card)

    for category, filename in PAGES.items():
        title = 'Recensioni Tech' if category == 'tech' else 'Recensioni Gaming'
        description = ('Recensioni di prodotti tecnologici, hardware e accessori ZazoomTek.'
                       if category == 'tech' else
                       'Recensioni di videogiochi per PC, PlayStation, Xbox e Nintendo ZazoomTek.')
        canonical = 'https://zazoomtek.it/' + filename
        page = base[:list_start] + ''.join(cards[category]) + base[matches[-1].end():]
        page = page.replace('<title>Recensioni | ZazoomTek</title>',
                            '<title>' + title + ' | ZazoomTek</title>', 1)
        page = page.replace('Archivio delle recensioni scritte di ZazoomTek, ordinate dalla più recente alla più vecchia.',
                            description, 1)
        page = page.replace('https://zazoomtek.it/recensioni-scritte.html', canonical, 1)
        page = re.sub(r'(<div class="news-main-head"><h1>)(.*?)(</h1>)',
                      lambda m: m.group(1) + title + m.group(3), page, count=1, flags=re.S)
        page = re.sub(r'<div class="news-filter"><span>Tutte</span>.*?</div>',
                      '<div class="news-filter"><span>' + title + '</span></div>',
                      page, count=1, flags=re.S)
        page = page.replace('Recensioni scritte di tecnologia e gaming pubblicate da ZazoomTek',
                            description, 1)
        # The complete original right rail, ticker, header and footer are reused.
        if (not all(k in page for k in ('class="news-sidebar', 'class="legal-footer'))
                or len(CARD.findall(page[(page.index(BEG) + len(BEG)):list_boundary(page, page.index(BEG))])) != len(cards[category])):
            raise RuntimeError('Incomplete editorial sidebar or category cards: ' + filename)
        (root / filename).write_text(page, encoding='utf-8')
    return {key: len(rows) for key, rows in cards.items()}


if __name__ == '__main__':
    print('Written-review categories updated:', build())
