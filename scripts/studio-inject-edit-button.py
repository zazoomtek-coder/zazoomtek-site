#!/usr/bin/env python3
"""Show the opt-in Edit affordance on real detail pages, never on Home/archives."""
from __future__ import annotations
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
TAG='<script src="/studio/edit-button.js" defer></script>'
def inject(root:Path=ROOT):
    count=0
    for path in root.glob("*.html"):
        if path.name=="index.html" or path.name.startswith("preview-"):continue
        markup=path.read_text(encoding="utf-8")
        detail=(re.search(r'<article\b[^>]*class=["\'][^"\']*(?:article-main|story)\b',markup,re.I)
               and re.search(r'<h1\b',markup,re.I))
        if not detail or "</body>" not in markup.lower() or TAG in markup:continue
        markup=re.sub(r"</body>",lambda m:TAG+"\n"+m.group(),markup,count=1,flags=re.I)
        path.write_text(markup,encoding="utf-8")
        count+=1
    print("Administrator edit affordance included on editorial pages:",count)
    return count
def self_test():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        root=Path(t)
        (root/"index.html").write_text('<html><body><h1>Home</h1></body></html>',encoding="utf-8")
        f=root/"test.html";f.write_text('<html><body><article class="article-main"><h1>Test</h1></article></body></html>',encoding="utf-8")
        assert inject(root)==1 and inject(root)==0 and TAG in f.read_text()
        assert TAG not in (root/"index.html").read_text()
        print("PASS: protected homepage unchanged, idempotent article Edit button")
if __name__=="__main__":
    import sys
    self_test() if "--self-test" in sys.argv else inject()
