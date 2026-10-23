#!/usr/bin/env python3
"""Install the already-approved Studio editing UI on interior site pages.

No Master / legacy Python script. Does not alter the Home or Studio itself.
Studio session is checked in the client-side UI; actual writes require Studio.
"""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TAG='<script src="/studio/edit-button.js" defer></script>'

def inject(root:Path=ROOT)->int:
    count=0
    if not (root/"studio"/"edit-button.js").is_file():
        print("Studio editing asset not found; retaining existing pages")
        return 0
    for page in root.rglob("*.html"):
        relative=page.relative_to(root).as_posix()
        if (relative=="index.html" or relative.startswith(("dist/","studio/",".github/"))
                or "node_modules/" in relative or "/dist/" in relative):
            continue
        if "watch/" in relative and relative=="watch/index.html":
            continue
        try:source=page.read_text(encoding="utf-8")
        except UnicodeError:continue
        if TAG in source or "/studio/edit-button.js" in source or "</body>" not in source:
            continue
        if not ("<main" in source or "<article" in source):
            continue
        page.write_text(source.replace("</body>",TAG+"\n</body>",1),encoding="utf-8")
        count+=1
    print("Studio edit UI enabled in",count,"interior pages; Home unchanged")
    return count

if __name__=="__main__":inject()
