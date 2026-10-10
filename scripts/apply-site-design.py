#!/usr/bin/env python3
"""Ensure the site-wide CSS before Firebase deploy, including generated pages."""
from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
css_tag='<link rel="stylesheet" href="/zt-design.css?v=20261010navfix" data-zt-design="20261010">'
js_tag='<script src="/zt-visual.js?v=20261010" defer></script>'
changed=0
for path in root.rglob('*.html'):
    if any(p in {'.git','node_modules','functions'} for p in path.relative_to(root).parts):
        continue
    html=path.read_text(encoding='utf-8')
    if '</head>' not in html.lower():
        continue
    original=html
    if 'href="/zt-design.css' in html:
        html=re.sub(r'(?<=href=")/zt-design[.]css(?:[?][^"]*)?',
                    "/zt-design.css?v=20261010navfix",html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:css_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    if 'src="/zt-visual.js' not in html:
        html=re.sub(r"</head>",lambda m:js_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    if html!=original:
        path.write_text(html,encoding='utf-8')
        changed+=1
print(f"ZazoomTek: shared design ensured on {changed} HTML pages.")
