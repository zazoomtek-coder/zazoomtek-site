#!/usr/bin/env python3
"""Make identical paginated News archive descriptions page-specific.

Only existing, verified news-N.html archives; no body, menu, image or importer
changes. Does not rewrite nonstandard descriptions or indexability directives.
"""
import argparse,re,html
from pathlib import Path
from seo_head_safe import Metadata
from seo_paths_safe import canonical_candidates
ORIGINAL='<meta name="description" content="Le ultime News pubblicate da ZazoomTek, in ordine cronologico.">'
TITLE=re.compile(r'<title>\s*News - Pagina (\d+) \| ZazoomTek\s*</title>',re.I)
def transform(path,root,source):
    match=TITLE.search(source)
    if not match or not re.fullmatch(r'news-(\d+)\.html',path.name):return source
    page=int(match.group(1))
    if page<2 or f'news-{page}.html'!=path.name:return source
    head=source.split('</head>',1)
    if len(head)!=2 or head[0].count(ORIGINAL)!=1:return source
    meta=Metadata();meta.feed(head[0])
    if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,path):return source
    desc=f'Archivio News ZazoomTek, pagina {page}: notizie e aggiornamenti su tecnologia, gaming, recensioni, console, PC e mondo hi-tech.'
    return head[0].replace(ORIGINAL,'<meta name="description" content="'+html.escape(desc,quote=True)+'">')+'</head>'+head[1]
def build(root):
    root=Path(root).resolve()
    changes={}
    for page in root.glob('news-*.html'):
        before=page.read_text(encoding='utf-8',errors='replace')
        revised=transform(page,root,before)
        if revised!=before:
            assert revised.split('</head>',1)[1]==before.split('</head>',1)[1]
            changes[page]=revised
    return changes
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--check',action='store_true')
    a=p.parse_args();changes=build(a.root)
    print(f'Unique paginated News archive descriptions: {len(changes)}; dry_run={a.check}')
    if not a.check:
        for path,content in changes.items():path.write_text(content,encoding='utf-8')
if __name__=='__main__':main()
