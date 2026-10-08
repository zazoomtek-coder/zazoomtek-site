#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(".")
TAG='<script src="/zt-analytics.js" defer></script>'
SKIP={"googlea3c594e14c6f832d.html"}

def inject(path: Path):
    if path.name in SKIP:
        return False
    text=path.read_text(encoding="utf-8",errors="replace")
    if TAG in text:
        return False
    marker="</head>"
    pos=text.lower().find(marker)
    if pos<0:
        return False
    text=text[:pos]+TAG+"\n"+text[pos:]
    path.write_text(text,encoding="utf-8")
    return True

def main():
    changed=0
    skipped=0
    for path in ROOT.glob("*.html"):
        if inject(path):
            changed+=1
        else:
            skipped+=1
    print(f"GA4 tag ensured on {changed} HTML files; {skipped} already tagged/skipped.")

if __name__=="__main__":
    main()
