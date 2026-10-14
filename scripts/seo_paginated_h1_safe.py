#!/usr/bin/env python3
"""Apply existing pixel-safe homepage semantic H1 repair to paginated archives.

Only the already-visible "News in evidenza" section heading changes from H2 to
H1, with corresponding original inline CSS selectors. No text, layout, article,
importer, video or navigation edits.
"""
import argparse,re
from pathlib import Path
from seo_home_h1_safe import transform

def build(root):
    root=Path(root)
    pages=sorted(root.glob('pagina-*.html'))
    changes={}
    for p in pages:
        if not re.fullmatch(r'pagina-[2-9]\d*\.html',p.name):continue
        before=p.read_text(encoding='utf-8',errors='replace')
        if not re.search(r'>(?:Articoli|News) - Pagina \d+ \| ZazoomTek</title>',before,re.I):continue
        revised=transform(before)
        assert transform(revised)==revised
        if before!=revised:changes[p]=revised
    return changes

def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path('.'));a.add_argument('--check',action='store_true')
    args=a.parse_args()
    changes=build(args.root)
    print(f'Archive pages semantic headings: {len(changes)} safe visual-equivalent H1 upgrades; dry_run={args.check}')
    if not args.check:
        for p,source in changes.items():p.write_text(source,encoding='utf-8')
if __name__=='__main__':main()
