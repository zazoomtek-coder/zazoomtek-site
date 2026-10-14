#!/usr/bin/env python3
"""Optional video sitemap ONLY for real, visible, owned YouTube watch-page embeds.

Never lists thumbnails, video grids, onclick players, trailer-only review links,
or guessed video data. Creates nothing when no trustworthy watch pages exist.
"""
import argparse
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
from seo_paths_safe import html_pages,canonical_candidates,ORIGIN
from seo_media_safe import feed_videos,verified_video,VisibleVideoParser
from seo_head_safe import Metadata

NS='http://www.sitemaps.org/schemas/sitemap/0.9'
VNS='http://www.google.com/schemas/sitemap-video/1.1'
ET.register_namespace('',NS)
ET.register_namespace('video',VNS)

class VisibleCopy(HTMLParser):
    def __init__(self):
        super().__init__()
        self.main=0;self.heading=False;self.header='';self.paragraph=False;self.paragraph_text=[];self.parts=[]
    def handle_starttag(self,tag,attrs):
        t=tag.lower()
        if t=='main':self.main+=1
        if not self.main:return
        if t=='h1':self.heading=True
        if t=='p' and len(self.parts)<3:self.paragraph=True
    def handle_data(self,data):
        if self.heading and self.main:self.header+=data
        if self.paragraph and self.main:self.paragraph_text.append(data)
    def handle_endtag(self,tag):
        t=tag.lower()
        if t=='h1':self.heading=False
        if t=='p' and self.paragraph:
            line=' '.join(' '.join(self.paragraph_text).split())
            if len(line)>=40:self.parts.append(line)
            self.paragraph=False;self.paragraph_text=[]
        if t=='main' and self.main:self.main-=1

def watch_candidate(path,root,known):
    html=path.read_text(encoding='utf-8',errors='replace')
    m=re.search(r'</head\s*>',html,re.I)
    if not m:return None
    head=html[:m.start()];body=html[m.end():]
    parsed=Metadata()
    parsed.feed(head)
    if len(parsed.canonicals)!=1 or parsed.canonicals[0] not in canonical_candidates(root,path):return None
    robots=' '.join(parsed.meta.get(x,'') for x in ('robots','googlebot')).lower()
    if re.search(r'(?<![a-z])(?:noindex|none)(?![a-z])',robots):return None
    video=verified_video(body,known)
    if not video:return None
    visible=VisibleCopy()
    visible.feed(body)
    if not visible.header.strip() or not visible.parts:return None
    title=video['name']
    # A watch page must be about the same video, not a sidebar aside link.
    title_normal=re.sub(r'\W+',' ',title,flags=re.UNICODE).strip().lower()
    header_normal=re.sub(r'\W+',' ',visible.header,flags=re.UNICODE).strip().lower()
    title_words=[word for word in title_normal.split() if len(word)>=4]
    if title_words and not any(w in header_normal for w in title_words):return None
    description=visible.parts[0][:2048]
    if len(description)<40:return None
    return parsed.canonicals[0],video,description

def entries(root):
    root=Path(root).resolve()
    known=feed_videos(root)
    result={}
    for page in html_pages(root):
        item=watch_candidate(page,root,known)
        if item:result[item[0]]=item
    if len(result)>4000:raise RuntimeError('Too many video watch pages, split video sitemap')
    return [result[k] for k in sorted(result)]

def build(entries_list):
    root=ET.Element(f'{{{NS}}}urlset')
    for url,v,description in entries_list:
        row=ET.SubElement(root,f'{{{NS}}}url')
        ET.SubElement(row,f'{{{NS}}}loc').text=url
        node=ET.SubElement(row,f'{{{VNS}}}video')
        for tag,value in (
            ('thumbnail_loc',v['thumbnailUrl']),
            ('title',v['name']),
            ('description',description),
            ('player_loc',v['embedUrl']),
            ('publication_date',v['uploadDate']),
        ):
            ET.SubElement(node,f'{{{VNS}}}{tag}').text=value
    xml=ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n'
    ET.fromstring(xml)
    return xml

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path('.'))
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    root=args.root.resolve()
    found=entries(root)
    print(f'Google video sitemap: {len(found)} verified prominent watch-page videos; dry-run={args.check}')
    if not found:
        print('No eligible video watch pages. Publishing no empty or inaccurate video sitemap.')
        return
    xml=build(found)
    if args.check:return
    (root/'video-sitemap.xml').write_bytes(xml)
    robots=root/'robots.txt'
    if robots.exists():
        old=robots.read_text(encoding='utf-8')
        ref='Sitemap: '+ORIGIN+'/video-sitemap.xml'
        if ref not in old.splitlines():
            robots.write_text(old.rstrip()+'\n'+ref+'\n',encoding='utf-8')
if __name__=='__main__':main()
