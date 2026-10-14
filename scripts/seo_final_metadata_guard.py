#!/usr/bin/env python3
"""Patch only verified SEO metadata after other build steps have regenerated pages."""
import argparse
import re
from pathlib import Path
from seo_head_safe import Metadata
from seo_paths_safe import canonical_candidates

CORRECTIONS = {
 'news.html': (
   '<title>News | ZazoomTek</title>',
   '<title>Ultime News Tech e Gaming | ZazoomTek</title>'
 ),
 'news-UgkxRIkkCOSKmYs0Irjj3gONuRScFsor9-qu.html': (
   '<meta name="description" content="Avete già prenotato GT6?">',
   '<meta name="description" content="La Community ZazoomTek discute delle prenotazioni di GT6: scopri la domanda rivolta ai giocatori e partecipa al confronto sul nuovo capitolo.">'
 ),
}

def build(root):
    edits={}
    for filename,(original,replacement) in CORRECTIONS.items():
        path=root/filename
        source=path.read_text(encoding="utf-8")
        m=re.search(r"</head\s*>",source,re.I)
        if not m: raise RuntimeError(filename+" lacks closing head")
        head,tail=source[:m.start()],source[m.start():]
        meta=Metadata(); meta.feed(head)
        if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,path):
            raise RuntimeError(filename+" canonical mismatch")
        if original in head:
            assert head.count(original)==1,filename
            revised=head.replace(original,replacement)+tail
            assert revised.endswith(tail)
            edits[path]=revised
        elif replacement not in head:
            raise RuntimeError(filename+" unexpected metadata, requires review")
    return edits

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path,default=Path("."))
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    edits=build(args.root.resolve())
    if not args.check:
        for path,content in edits.items():
            path.write_text(content,encoding="utf-8")
    print("Verified final SEO metadata: "+str(len(edits))+" updates; dry-run="+str(args.check))
if __name__=="__main__": main()
