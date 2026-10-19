#!/usr/bin/env python3
"""Offline safety gate for ZazoomTek review split; never touches the Home."""
from __future__ import annotations
import hashlib
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / 'scripts/build-review-categories.py'
spec = importlib.util.spec_from_file_location('zt_review_categories', MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def check() -> None:
    home = ROOT / 'index.html'
    original_home = hashlib.sha256(home.read_bytes()).hexdigest()
    original_archive = hashlib.sha256((ROOT / 'recensioni-scritte.html').read_bytes()).hexdigest()
    counts = mod.build(ROOT)
    assert all(counts.get(k, 0) >= 1 for k in ('tech', 'gaming')), counts
    combined: set[str] = set()
    for name in ('tech', 'gaming'):
        page = (ROOT / ('recensioni-' + name + '.html')).read_text(encoding='utf-8')
        assert ('<h1>Recensioni ' + name.title() + '</h1>') in page
        assert '<aside class="news-sidebar' in page
        assert 'zt-mix-feature' in page and 'zt-mix-recent' in page
        assert 'class="legal-footer' in page
        assert '<nav class="zt-nav"' in page or '<nav class="nav"' in page
        assert ('https://zazoomtek.it/recensioni-' + name + '.html') in page
        cards = mod.CARD.findall(page)
        assert len(cards) == counts[name], (name, len(cards), counts)
        for card in cards:
            slug = mod.slug_from_card(card)
            assert slug not in combined, ('duplicated review across categories', slug)
            assert (ROOT / slug).is_file(), ('broken review target', slug)
            combined.add(slug)
            assert mod.review_category(card, ROOT) == name, (name, slug)
    assert hashlib.sha256(home.read_bytes()).hexdigest() == original_home
    assert hashlib.sha256((ROOT / 'recensioni-scritte.html').read_bytes()).hexdigest() == original_archive
    print('PASS review categories:', counts, ', no duplicates or Home/archive rewriting')


if __name__ == '__main__':
    check()
