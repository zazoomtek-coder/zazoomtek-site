#!/usr/bin/env python3
"""Keep analytics and shared design on all current/new HTML pages at each sync."""
from pathlib import Path
import re

ROOT=Path(".")
TAG='<script src="/zt-analytics.js" defer></script>'
STYLE='<link rel="stylesheet" href="/zt-design.css?v=20261010compactvideo" data-zt-design="20261010">'
SKIP={"googlea3c594e14c6f832d.html"}

def inject(path: Path):
    if path.name in SKIP:
        return False
    content=path.read_text(encoding="utf-8",errors="replace")
    if "</head>" not in content.lower():
        return False
    updated=content
    if 'href="/zt-design.css' in updated:
        updated=re.sub(r'(?<=href=")/zt-design[.]css(?:[?][^"]*)?',
                       "/zt-design.css?v=20261010compactvideo",updated,count=1)
    else:
        updated=re.sub(r"</head>",lambda m:STYLE+"\n"+m.group(0),updated,count=1,flags=re.I)
    if TAG not in updated:
        updated=re.sub(r"</head>",lambda m:TAG+"\n"+m.group(0),updated,count=1,flags=re.I)
    if updated==content:
        return False
    path.write_text(updated,encoding="utf-8")
    return True

def main():
    changed=0
    for path in ROOT.glob("*.html"):
        changed+=bool(inject(path))
    print(f"Shared design and analytics ensured on {changed} HTML pages.")

if __name__=="__main__":
    main()
