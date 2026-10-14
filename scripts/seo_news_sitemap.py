#!/usr/bin/env python3
"""Google News sitemap from verified, genuinely recent published NewsArticle data.

Safe release-time XML only: never changes HTML, media, CSS, GitHub source or
YouTube sync. Excludes old articles, drafts, noindex, invalid canonicals and
any item without reliable original publication date.
"""
import argparse
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from seo_paths_safe import html_pages, canonical_candidates, ORIGIN

SITEMAP_NS='http://www.sitemaps.org/schemas/sitemap/0.9'
NEWS_NS='http://www.google.com/schemas/sitemap-news/0.9'
NEWS_SITEMAP=ORIGIN+'/news-sitemap.xml'
ET.register_namespace('',SITEMAP_NS)
ET.register_namespace('news',NEWS_NS)

class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals=[]
        self.robots=[]
        self.scripts=[]
        self._json=None
    def handle_starttag(self,tag,attrs):
        props={k.lower():(v or '') for k,v in attrs if k}
        if tag.lower()=='link' and 'canonical' in props.get('rel','').lower().split():
            self.canonicals.append(props.get('href','').strip())
        if tag.lower()=='meta' and props.get('name','').lower() in ('robots','googlebot'):
            self.robots.append(props.get('content','').strip().lower())
        if tag.lower()=='script' and props.get('type','').lower()=='application/ld+json':
            self._json=''
    def handle_data(self,data):
        if self._json is not None:self._json+=data
    def handle_endtag(self,tag):
        if tag.lower()=='script' and self._json is not None:
            self.scripts.append(self._json)
            self._json=None

def nodes(data):
    if isinstance(data,list):
        for x in data:yield from nodes(x)
    elif isinstance(data,dict):
        yield data
        if isinstance(data.get('@graph'),list):
            for x in data['@graph']:yield from nodes(x)

def news_candidate(path,root,now):
    try:
        html=path.read_text(encoding='utf-8',errors='replace')
    except OSError:
        return None
    match=re.search(r'</head\s*>',html,re.I)
    if not match:
        return None
    head=HeadParser()
    head.feed(html[:match.start()])
    if len(head.canonicals)!=1 or head.canonicals[0] not in canonical_candidates(root,path):
        return None
    url=head.canonicals[0]
    if any(re.search(r'(?<![a-z])(?:noindex|none)(?![a-z])',s) for s in head.robots):
        return None
    for raw in head.scripts:
        try: data=json.loads(raw)
        except (ValueError, TypeError): continue
        for node in nodes(data):
            types=node.get('@type',[])
            types=[types] if isinstance(types,str) else types if isinstance(types,list) else []
            if 'NewsArticle' not in types:
                continue
            page=node.get('mainEntityOfPage')
            entity=page if isinstance(page,str) else page.get('@id') if isinstance(page,dict) else None
            if entity!=url:
                continue
            title=node.get('headline')
            raw_date=node.get('datePublished')
            if not isinstance(title,str) or not title.strip() or len(title)>600:
                continue
            if not isinstance(raw_date,str) or not re.fullmatch(
                    r'\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?',raw_date):
                continue
            try:
                if 'T' in raw_date:
                    date=datetime.fromisoformat(raw_date.replace('Z','+00:00'))
                else:
                    date=datetime.fromisoformat(raw_date).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if date.tzinfo is None or not (now-timedelta(hours=48) <= date.astimezone(timezone.utc) <= now):
                continue
            return url,date,title.strip(),raw_date
    return None

def entries(root,now=None):
    root=Path(root).resolve()
    now=now or datetime.now(timezone.utc)
    result={}
    for path in html_pages(root):
        item=news_candidate(path,root,now)
        if item: result[item[0]]=item
    if len(result)>1000:
        raise RuntimeError('Google News sitemap exceeds 1000 current news; split required before deployment')
    return sorted(result.values(),key=lambda x:(x[1],x[0]),reverse=True)

def make_xml(items):
    root=ET.Element(f'{{{SITEMAP_NS}}}urlset')
    for url,_,headline,published in items:
        item=ET.SubElement(root,f'{{{SITEMAP_NS}}}url')
        ET.SubElement(item,f'{{{SITEMAP_NS}}}loc').text=url
        news=ET.SubElement(item,f'{{{NEWS_NS}}}news')
        publication=ET.SubElement(news,f'{{{NEWS_NS}}}publication')
        ET.SubElement(publication,f'{{{NEWS_NS}}}name').text='ZazoomTek'
        ET.SubElement(publication,f'{{{NEWS_NS}}}language').text='it'
        ET.SubElement(news,f'{{{NEWS_NS}}}publication_date').text=published
        ET.SubElement(news,f'{{{NEWS_NS}}}title').text=headline
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)
    ET.fromstring(xml) # Validate before any writes.
    return xml+b'\n'

def run(root,check=False):
    root=Path(root).resolve()
    items=entries(root)
    xml=make_xml(items)
    print(f'Google News sitemap: {len(items)} verified news from last 48 hours; check={check}')
    for item in items[:6]:
        print('Recent:',item[0],item[3])
    if check:return len(items)
    # Replacing a standalone XML and an extra robots pointer never modifies
    # site pages or protected YouTube/Community workflows.
    (root/'news-sitemap.xml').write_bytes(xml)
    robots=root/'robots.txt'
    if robots.is_file():
        content=robots.read_text(encoding='utf-8')
        line=f'Sitemap: {NEWS_SITEMAP}'
        if line not in content.splitlines():
            robots.write_text(content.rstrip()+'\n'+line+'\n',encoding='utf-8')
    return len(items)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    run(args.root,args.check)

if __name__=='__main__':main()
