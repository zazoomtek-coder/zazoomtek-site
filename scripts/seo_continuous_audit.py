#!/usr/bin/env python3
"""Read-only continuous SEO audit, including future categories and nested pages.

NEVER writes HTML, sitemap, or deploy configuration. No network/API calls.
"""
import argparse
import json
import re
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from seo_paths_safe import html_pages, canonical_candidates

class Head(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical=[]
        self.robots=[]
        self.title=[]
        self.description=[]
        self.structured=[]
        self._title=False
        self._script=False
        self._script_content=''

    def handle_starttag(self, tag, attrs):
        props={k.lower():(v or '') for k,v in attrs if k}
        tag=tag.lower()
        if tag=='title': self._title=True
        elif tag=='link' and 'canonical' in props.get('rel','').lower().split():
            self.canonical.append(props.get('href','').strip())
        elif tag=='meta':
            key=props.get('name','').lower()
            if key in ('robots','googlebot'): self.robots.append(props.get('content',''))
            if key=='description': self.description.append(props.get('content',''))
        elif tag=='script' and props.get('type','').lower()=='application/ld+json':
            self._script=True
            self._script_content=''

    def handle_data(self, data):
        if self._title: self.title.append(data)
        if self._script: self._script_content+=data

    def handle_endtag(self, tag):
        if tag.lower()=='title': self._title=False
        if tag.lower()=='script' and self._script:
            self.structured.append(self._script_content)
            self._script=False

def audit(root):
    issues=[]
    count=0
    seen={}
    for page in html_pages(root):
        count+=1
        rel=str(page.relative_to(root))
        try:
            source=page.read_text(encoding='utf-8',errors='replace')
        except OSError as e:
            issues.append((rel,'read_error',str(e)));continue
        match=re.search(r'</head\s*>',source,re.I)
        if not match:
            issues.append((rel,'missing_head','No closing head tag'));continue
        parser=Head()
        try: parser.feed(source[:match.start()])
        except Exception as e:
            issues.append((rel,'malformed_head',str(e)));continue
        if len(parser.canonical)!=1 or parser.canonical[0] not in canonical_candidates(root,page):
            issues.append((rel,'canonical','Missing, duplicate or mismatched canonical'))
        else:
            url=parser.canonical[0]
            if url in seen:
                issues.append((rel,'duplicate_canonical',f'Also declared in {seen[url]}'))
            seen[url]=rel
        if any(re.search(r'(?<!\w)noindex(?!\w)',r,re.I) for r in parser.robots):
            issues.append((rel,'noindex','Published-looking page has noindex; verify intent'))
        if not ''.join(parser.title).strip():
            issues.append((rel,'title','Missing title'))
        if len(parser.description)!=1 or not parser.description[0].strip():
            issues.append((rel,'description','Missing or duplicated meta description'))
        for i,payload in enumerate(parser.structured,1):
            try:
                data=json.loads(payload)
                if not isinstance(data,(dict,list)):
                    raise ValueError('JSON-LD root must be object or list')
            except (ValueError,TypeError) as e:
                issues.append((rel,'jsonld',f'JSON-LD #{i}: {e}'))
    return count,issues

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,default=Path('.'))
    ap.add_argument('--strict',action='store_true',help='fail on any detected issue')
    args=ap.parse_args()
    count,issues=audit(args.root)
    print(f'SEO audit (read-only): {count} pages, {len(issues)} findings')
    for page,kind,detail in issues[:150]:
        print(f'{kind}: {page}: {detail}')
    if len(issues)>150: print(f'... {len(issues)-150} additional findings')
    if count<1 or (args.strict and issues):
        raise SystemExit(1)

if __name__=='__main__': main()
