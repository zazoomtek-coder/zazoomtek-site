#!/usr/bin/env python3
"""Ensure the site-wide CSS before Firebase deploy, including generated pages."""
from pathlib import Path
from zt_footer import unify_footer
import re

root=Path(__file__).resolve().parents[1]
css_tag='<link rel="stylesheet" href="/zt-design.css?v=20261010mastheadblue" data-zt-design="20261010">'
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
                    "/zt-design.css?v=20261010mastheadblue",html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:css_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    if 'src="/zt-visual.js' not in html:
        html=re.sub(r"</head>",lambda m:js_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    # Ensure the official ZazoomTek.it masthead is applied to every generated
    # article and static page, including pages rebuilt by YouTube sync.
    home_old='<span class="brand-copy"><strong>ZazoomTek</strong><small>TECH · GAMING · COMMUNITY</small></span>'
    brand_markup="<span class=\"zt-brand-copy\"><strong class=\"zt-wordmark\" aria-label=\"ZazoomTek.it\"><span class=\"zt-mark-blue\" aria-hidden=\"true\">ZAZOOM</span><span class=\"zt-mark-red\" aria-hidden=\"true\">TEK</span><span class=\"zt-mark-tld\" aria-hidden=\"true\">.it</span></strong><small class=\"zt-brand-tagline\">TECH · GAMING · COMMUNITY</small></span>"
    html=html.replace(home_old,brand_markup)
    html=re.sub(r'(?<=<img src="/ChatGPT.png" alt="ZazoomTek">)<strong>ZazoomTek</strong>(?=</a>)',brand_markup,html)
    html=unify_footer(html)
    if html!=original:
        path.write_text(html,encoding='utf-8')
        changed+=1
print(f"ZazoomTek: shared design ensured on {changed} HTML pages.")
