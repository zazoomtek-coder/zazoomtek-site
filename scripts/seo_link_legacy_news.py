#!/usr/bin/env python3
"""Restore discoverability of unlinked legacy Community news on the News archive.
Does not change individual articles, importers, CSS or site navigation.
"""
import argparse
import html
import re
from pathlib import Path
from seo_whole_site_audit import audit

START='<!-- ZT_SEO_ARCHIVE_LINKS_START -->'
END='<!-- ZT_SEO_ARCHIVE_LINKS_END -->'
AREA=re.compile(re.escape(START)+r'[\s\S]*?'+re.escape(END), re.I)
MAIN_END=re.compile(r'</main\s*>',re.I)

def transform(root, content, findings):
    orphan_news=sorted({
        name for name, kind, _ in findings
        if kind=='orphan_unlinked' and
        re.fullmatch(r'news-Ugkx[A-Za-z0-9_-]+\.html',name)
        and (root/name).is_file()
    })
    links=[]
    for name in orphan_news:
        source=(root/name).read_text(encoding='utf-8',errors='replace')
        hit=re.search(r'<title\b[^>]*>(.*?)</title\s*>',source,re.I|re.S)
        title=html.unescape(re.sub(r'<[^>]+>',' ',hit.group(1))) if hit else ''
        title=' '.join(title.split())
        title=re.sub(r'\s*\|\s*ZazoomTek\s*$','',title,flags=re.I).strip()
        if not title: continue
        links.append('<li><a href="/'+html.escape(name,quote=True)+'">'+html.escape(title)+'</a></li>')
    if any(name=='chi-sono.html' and kind=='orphan_unlinked' for name,kind,_ in findings):
        links.append('<li><a href="/chi-sono.html">Informazioni su ZazoomTek</a></li>')
    existing=AREA.search(content)
    if not links:
        return AREA.sub('',content) if existing else content,len(links)
    block=START+'\n<section class="zt-legacy-news-links" aria-label="Archivio notizie precedenti" style="max-width:1050px;margin:28px auto;padding:16px 20px;background:#fff;border:1px solid #ddd"><h2 style="font-size:18px;margin:0 0 10px">Dall’archivio della Community</h2><ul style="margin:0;padding-left:20px;line-height:1.7">'+''.join(links)+'</ul></section>\n'+END
    if existing: return AREA.sub(lambda _:block,content),len(links)
    matches=list(MAIN_END.finditer(content))
    if len(matches)!=1: raise RuntimeError('Expected one News main container; no changes')
    at=matches[0].start()
    return content[:at]+block+'\n'+content[at:],len(links)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--check',action='store_true')
    args=p.parse_args()
    root=args.root.resolve()
    page=root/'news.html'
    before=page.read_text(encoding='utf-8')
    report=audit(root)
    after,count=transform(root,before,report['priority_findings'])
    print(f'Archived Community news linked: {count}; changed={after!=before}; check={args.check}')
    if not args.check and after!=before: page.write_text(after,encoding='utf-8')

if __name__=='__main__': main()
