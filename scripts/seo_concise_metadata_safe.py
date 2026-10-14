#!/usr/bin/env python3
"""Conservative, head-only title/description SEO normalization.

No generated editorial content, no changes to H1, body, JS, CSS, images,
canonical URLs, reviews, video or Community imports.
"""
import argparse,html,re
from pathlib import Path
from collections import Counter
from seo_paths_safe import html_pages,canonical_candidates
from seo_head_safe import Metadata
HEAD=re.compile(r'</head\s*>',re.I)
TITLE=re.compile(r'(<title\b[^>]*>)([^<]*)(</title\s*>)',re.I)
META=re.compile(r'<meta\b[^>]*>',re.I)
DESCRIPTION=re.compile(r'\bname\s*=\s*(["\x27])description\1',re.I)
CONTENT=re.compile(r'(\bcontent\s*=\s*)(["\x27])(?P<text>.*?)(\2)',re.I|re.S)

def shorten(value,limit,minimum):
    value=' '.join(html.unescape(value).split())
    if len(value)<=limit:return None
    # Keep as much of the existing editorial content as possible.
    if limit==73:
        base=re.sub(r'\s*[|–—-]\s*ZazoomTek\s*$','',value,flags=re.I).strip()
        suffix=' | ZazoomTek' if base!=value else ''
        allowed=limit-len(suffix)
        cutoff=base[:allowed+1].rfind(' ')
        if cutoff<minimum:cutoff=allowed
        result=base[:cutoff].rstrip(' ,;:–—-.')+suffix
    else:
        window=value[:limit+1]
        stops=[m.end() for m in re.finditer(r'[.!?](?:\s|$)',window)]
        stop=max((s for s in stops if minimum<=s<=limit),default=None)
        if stop is None:
            stop=window.rfind(' ')
            if stop<minimum:stop=limit-1
            result=value[:stop].rstrip(' ,;:–—-.')+'…'
        else:result=value[:stop].strip()
    if len(result)>limit or len(result)<minimum:return None
    return result

def propose(path,root,source):
    end=HEAD.search(source)
    if not end:return None
    head=source[:end.start()];tail=source[end.start():]
    meta=Metadata();meta.feed(head)
    if len(meta.canonicals)!=1 or meta.canonicals[0] not in canonical_candidates(root,path):return None
    robots=' '.join(meta.meta.get(k,'') for k in ('robots','googlebot')).lower()
    if 'noindex' in robots or 'none' in robots:return None
    m=TITLE.search(head)
    title=shorten(m.group(2),73,34) if m else None
    descriptions=[tag for tag in META.finditer(head) if DESCRIPTION.search(tag.group(0))]
    description=None
    if len(descriptions)==1:
        content=CONTENT.search(descriptions[0].group(0))
        if content:
            description=shorten(content.group('text'),158,85)
    return (head,tail,m,title,descriptions,description)

def build(root,minimum=500):
    root=Path(root).resolve()
    changes={}
    pages=list(html_pages(root))
    existing_titles=[]
    existing_desc=[]
    candidates=[]
    for page in pages:
        source=page.read_text(encoding='utf-8',errors='replace')
        p=propose(page,root,source)
        if not p:continue
        head,tail,m,title,ds,desc=p
        if m:existing_titles.append(' '.join(html.unescape(m.group(2)).split()).casefold())
        if len(ds)==1:
            old=CONTENT.search(ds[0].group(0))
            if old:existing_desc.append(' '.join(html.unescape(old.group('text')).split()).casefold())
        candidates.append((page,source,p))
    titles=Counter(existing_titles)
    descs=Counter(existing_desc)
    target_titles=Counter(p[3].casefold() for _,_,p in candidates if p[3])
    target_descs=Counter(p[5].casefold() for _,_,p in candidates if p[5])
    title_updates=description_updates=0
    for page,source,(head,tail,m,title,ds,desc) in candidates:
        if title and target_titles[title.casefold()]==1 and titles[title.casefold()]==0:
            before=m.group(0)
            updated=m.group(1)+html.escape(title,quote=False)+m.group(3)
            head=head.replace(before,updated,1)
            title_updates+=1
        if desc and target_descs[desc.casefold()]==1 and descs[desc.casefold()]==0:
            # Find description META again after title replacement.
            tag=next((t for t in META.finditer(head) if DESCRIPTION.search(t.group(0))),None)
            if tag:
                match=CONTENT.search(tag.group(0))
                if match:
                    encoded=html.escape(desc,quote=True)
                    newtag=tag.group(0)[:match.start('text')]+encoded+tag.group(0)[match.end('text'):]
                    head=head[:tag.start()]+newtag+head[tag.end():]
                    description_updates+=1
        new=head+tail
        if new!=source:
            assert new.split('</head>',1)[-1]==source.split('</head>',1)[-1]
            changes[page]=new
    if len(pages)<minimum:raise RuntimeError('Unexpected repository size, refusing metadata edits')
    return changes,{'pages':len(pages),'changed_pages':len(changes),
                    'shorter_titles':title_updates,'shorter_descriptions':description_updates}

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--root',type=Path,default=Path('.'))
    a.add_argument('--check',action='store_true')
    args=a.parse_args()
    changes,stats=build(args.root)
    print('Whole-site metadata, conservative and head-only:',stats,'dry_run=',args.check)
    if not args.check:
        for p,source in changes.items():p.write_text(source,encoding='utf-8')
if __name__=='__main__':main()
