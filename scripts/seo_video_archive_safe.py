#!/usr/bin/env python3
"""Keep the URLs of older verified ZazoomTek videos available to Google.

Merges the trusted public YouTube feed into a small, permanent local archive;
no YouTube API call, no edit to synchronization, Firebase, or HTML. Scheduled
independently once daily. Never delete archived videos merely because a video
falls out of the newest 200-item feed.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,re,argparse
ARCHIVE='video-watch-archive.json'
ID=re.compile(r'^[A-Za-z0-9_-]{11}$')
LIMIT=2000
def valid(item):
    if not isinstance(item,dict):return None
    ident,title,date=item.get('id'),item.get('title'),item.get('publishedAt')
    if not isinstance(ident,str) or not ID.fullmatch(ident) or not isinstance(title,str) or len(title.strip())<6 or len(title.strip())>230 or not isinstance(date,str):return None
    try:
        dt=datetime.fromisoformat(date.replace('Z','+00:00'))
        if dt.tzinfo is None or dt.astimezone(timezone.utc)>datetime.now(timezone.utc):return None
    except ValueError:return None
    return {'id':ident,'title':title.strip(),'publishedAt':date,'category':str(item.get('category') or 'video')[:36],
            'short':item.get('short') is True,'live':item.get('live') is True,
            'completedLive':item.get('completedLive') is True}
def build(root):
    feed=json.loads((root/'home-video-feed.json').read_text(encoding='utf-8'))
    if not isinstance(feed,list) or len(feed)<10:raise RuntimeError('Feed unexpectedly small')
    existing_path=root/ARCHIVE
    previous=json.loads(existing_path.read_text(encoding='utf-8')) if existing_path.exists() else []
    if not isinstance(previous,list):raise RuntimeError('Archive is not a JSON list')
    merged={}
    for x in previous:
        v=valid(x)
        if v:merged[v['id']]=v
    preserved=len(merged)
    for x in feed:
        v=valid(x)
        if v:
            # Live feeds are authoritative over previously archived metadata.
            merged[v['id']]=v
    if len(merged)<max(10,preserved) or len(merged)>LIMIT:raise RuntimeError(f'Archive safety count {len(merged)}')
    result=sorted(merged.values(),key=lambda x:(x['publishedAt'],x['id']),reverse=True)
    return result,len(result)-preserved
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--check',action='store_true')
    args=p.parse_args()
    root=args.root.resolve()
    items,new=build(root)
    new_content=json.dumps(items,ensure_ascii=False,indent=2)+'\n'
    path=root/ARCHIVE
    changed=not path.exists() or path.read_text(encoding='utf-8')!=new_content
    print(f'Watch archive: {len(items)} public feed records, new IDs {new}, changed={changed}, check={args.check}')
    if not args.check and changed:path.write_text(new_content,encoding='utf-8')
if __name__=='__main__':main()
