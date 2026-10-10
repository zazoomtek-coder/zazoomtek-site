#!/usr/bin/env python3
"""Apply one shared stylesheet and optional progressive enhancements to every published HTML.
Runs in Firebase's deploy checkout. Does not change titles, content or URLs.
Also covers automatically generated future pages.
"""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
css_tag='<link rel="stylesheet" href="/zt-design.css?v=20261010" data-zt-design="20261010">'
js_tag='<script src="/zt-visual.js?v=20261010" defer></script>'
changed=0
for path in root.rglob('*.html'):
    if any(p in {'.git', 'node_modules', 'functions'} for p in path.relative_to(root).parts):
        continue
    html=path.read_text(encoding='utf-8')
    if '</head>' not in html.lower():
        continue
    if 'data-zt-design="20261010"' in html:
        continue
    # Put the stylesheet last so it gently refines each page's existing inline styles.
    html,n=re.subn(r'</head>',css_tag+js_tag+'</head>',html,count=1,flags=re.I)
    if n:
        path.write_text(html,encoding='utf-8')
        changed+=1
print(f'ZazoomTek: applied shared design to {changed} HTML pages.')
