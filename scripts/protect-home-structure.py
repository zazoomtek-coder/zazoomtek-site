#!/usr/bin/env python3
"""Fail a production release only when the protected Home structure is damaged.

Content is intentionally NOT frozen: headlines, article cards, reviews, videos,
editorial items and other data may change normally. This guard protects only
the structural anchors that define the approved ZazoomTek Home layout.
"""
from pathlib import Path
import sys

REQUIRED = {
    'main navigation': 'class="nav"',
    'news carousel': 'id="newsSlider"',
    'three-column home shell': 'ztp-three-home',
    'three-column news grid': 'ztp-three-columns',
    'tech column': 'ztp-news-tech',
    'gaming column': 'ztp-news-gaming',
    'right editorial rail': 'ztp-news-rail',
    'guides module': 'id="ztHomeGuide"',
    'latest reviews module': 'latest-reviews-module',
    'latest videos module': 'zt-video-stack',
    'popular articles box': 'id="zt-popular-box"',
    'amazon module': 'zt-amazon-box',
    'editorial box': 'zt-special-box',
    'ticker video links': 'ticker-video-links',
}

FORBIDDEN = (
    '<body></body>',
    'display:none!important}/* HOME DISABLED',
)

def check(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f'HOME GUARD: missing {path}')
    text = path.read_text(encoding='utf-8')
    missing = [label for label, token in REQUIRED.items() if token not in text]
    if missing:
        raise SystemExit('HOME GUARD: protected structure missing: ' + ', '.join(missing))
    for token in FORBIDDEN:
        if token in text:
            raise SystemExit(f'HOME GUARD: destructive marker found: {token}')
    if len(text) < 25000:
        raise SystemExit(f'HOME GUARD: index unexpectedly small ({len(text)} bytes)')
    print(f'HOME GUARD OK: {path} — structure protected, content updates allowed.')

def main():
    targets = [Path(p) for p in (sys.argv[1:] or ['index.html'])]
    for target in targets:
        check(target)

if __name__ == '__main__':
    main()
