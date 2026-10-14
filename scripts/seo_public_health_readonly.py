#!/usr/bin/env python3
"""Read-only public SEO health monitor, independent of import/deploy jobs.

No authenticated APIs, no writes to production and no crawl of 700+ pages.
Designed to remain safe as future categories and video watch pages are added.
"""
import argparse
import json
import re
import urllib.request
from xml.etree import ElementTree as ET

BASE='https://zazoomtek.it'
NS={'s':'http://www.sitemaps.org/schemas/sitemap/0.9','v':'http://www.google.com/schemas/sitemap-video/1.1','n':'http://www.google.com/schemas/sitemap-news/0.9'}

def load(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'ZazoomTek-ReadOnly-SEO-Health/1.0'})
    with urllib.request.urlopen(req,timeout=20) as response:
        if response.status!=200:raise RuntimeError(f'{path} returned {response.status}')
        return response.read().decode('utf-8','replace')

def check(get=load):
    findings=[]
    report={}
    robots=get('/robots.txt')
    for path in ('/sitemap.xml','/news-sitemap.xml','/video-sitemap.xml'):
        if f'Sitemap: {BASE+path}' not in robots:
            findings.append(f'robots.txt missing {path}')
    for path,key,lower in (('/sitemap.xml','canonical',500),('/news-sitemap.xml','news',0),('/video-sitemap.xml','videos',1)):
        try:
            root=ET.fromstring(get(path))
            locs=[x.text for x in root.findall('.//s:loc',NS)]
            report[key]=len(locs)
            if len(locs)<lower:findings.append(f'{path}: unusually few URLs ({len(locs)})')
            if len(locs)!=len(set(locs)):findings.append(f'{path}: duplicate canonical URLs')
            if not all(isinstance(x,str) and x.startswith(BASE+'/') for x in locs):
                findings.append(f'{path}: invalid URL origin')
            if key=='videos':
                entries=root.findall('.//s:url',NS)
                if not all(entry.find('v:video',NS) is not None for entry in entries):
                    findings.append('Video sitemap: missing video:video entry')
            if key=='news':
                entries=root.findall('.//s:url',NS)
                if not all(entry.find('n:news',NS) is not None for entry in entries):
                    findings.append('News sitemap: missing news:news entry')
        except (ET.ParseError,ValueError,RuntimeError) as e:
            findings.append(f'{path}: {e}')
    for path in ('/','/watch/tEkXOj7XOwA.html'):
        try:
            html=get(path)
            head=html.split('</head>',1)[0]
            if '</head>' not in html:findings.append(f'{path}: missing closing head')
            if not re.search(r'<link[^>]+rel=["\x27]canonical["\x27]',head,re.I):
                findings.append(f'{path}: missing canonical')
            if not re.search(r'<h1\b',html,re.I):findings.append(f'{path}: missing H1')
            if path.startswith('/watch/') and 'VideoObject' not in head:
                findings.append(f'{path}: missing VideoObject')
        except (ValueError,RuntimeError) as e:
            findings.append(f'{path}: {e}')
    report['findings']=findings
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--strict',action='store_true')
    args=ap.parse_args()
    result=check()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if args.strict and result['findings']:
        raise SystemExit(1)

if __name__=='__main__':main()
