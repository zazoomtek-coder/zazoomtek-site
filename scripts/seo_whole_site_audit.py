#!/usr/bin/env python3
"""Read-only audit of canonical SEO pages, headings and internal links."""
import json,re,argparse
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter,defaultdict
from seo_paths_safe import html_pages,canonical_candidates

class Parse(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title=[];self.descriptions=[];self.canonicals=[];self.robots=[]
        self.h1=0;self.links=[];self.in_title=False
    def handle_starttag(self,tag,attrs):
        a={k.lower():(v or '') for k,v in attrs if k}
        if tag=='title':self.in_title=True
        if tag=='h1':self.h1+=1
        if tag=='meta':
            if a.get('name','').lower()=='description':self.descriptions.append(a.get('content',''))
            if a.get('name','').lower() in ('robots','googlebot'):self.robots.append(a.get('content','').lower())
        if tag=='link' and 'canonical' in a.get('rel','').lower().split():self.canonicals.append(a.get('href',''))
        if tag=='a':self.links.append(a.get('href',''))
    def handle_data(self,data):
        if self.in_title:self.title.append(data)
    def handle_endtag(self,tag):
        if tag=='title':self.in_title=False

def target(href):
    if not href or href.startswith(('#','mailto:','tel:','javascript:','data:')):return None
    if href.startswith('//'):return None
    x=urlsplit(href)
    if x.netloc not in ('','zazoomtek.it','www.zazoomtek.it'):return None
    if x.scheme and x.scheme not in ('https','http'):return None
    p=unquote(x.path).lstrip('/')
    if not p:return 'index.html'
    if p.endswith('/'):return p+'index.html'
    if p.endswith('.html'):return p
    if '.' not in p.split('/')[-1]:return p+'.html'
    return None

def audit(root):
    root=Path(root).resolve()
    files=list(html_pages(root));names={x.relative_to(root).as_posix() for x in files}
    findings=[];types=Counter();inbound=Counter();unresolved=Counter();titles=defaultdict(list);descs=defaultdict(list)
    live={}
    for path in files:
        rel=path.relative_to(root).as_posix()
        source=path.read_text(encoding='utf-8',errors='replace')
        if not re.search(r'</head\s*>',source,re.I):continue
        p=Parse();p.feed(source)
        if any('noindex' in s for s in p.robots):continue
        if len(p.canonicals)!=1 or p.canonicals[0] not in canonical_candidates(root,path):
            findings.append((rel,'canonical','not unique or wrong'));continue
        title=' '.join(''.join(p.title).split())
        desc=' '.join(p.descriptions[0].split()) if len(p.descriptions)==1 else ''
        live[rel]={'title':title,'description':desc,'h1':p.h1}
        if not title:findings.append((rel,'title_missing',''))
        elif len(title)<18 or len(title)>75:findings.append((rel,'title_length',str(len(title))))
        if not desc:findings.append((rel,'description_missing',''))
        elif len(desc)<45 or len(desc)>170:findings.append((rel,'description_length',str(len(desc))))
        if p.h1!=1:findings.append((rel,'h1_count',str(p.h1)))
        if title:titles[title.casefold()].append(rel)
        if desc:descs[desc.casefold()].append(rel)
        for href in p.links:
            dest=target(href)
            if not dest:continue
            if dest in names:inbound[dest]+=1
            else:unresolved[dest]+=1
    for group,code in ((titles,'duplicate_title'),(descs,'duplicate_description')):
        for value,which in group.items():
            if len(which)>1:findings.append((', '.join(which[:4]),code,str(len(which))))
    for rel in live:
        if rel!='index.html' and inbound[rel]==0:
            findings.append((rel,'orphan_unlinked','No incoming local page links'))
    summary=Counter(item[1] for item in findings)
    return {'files_scanned':len(files),'canonical_pages':len(live),'finding_counts':dict(summary),
            'findings_sample':findings[:150],'missing_targets':unresolved.most_common(45),
            'by_page':live}
def main():
    a=argparse.ArgumentParser();a.add_argument('--root',type=Path,default=Path('.'));a.add_argument('--output',type=Path)
    args=a.parse_args();out=audit(args.root)
    if out['canonical_pages']<500:raise RuntimeError('Unexpected low page count')
    result=json.dumps(out,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(result,encoding='utf-8')
    print(result[:36000])
if __name__=='__main__':main()
