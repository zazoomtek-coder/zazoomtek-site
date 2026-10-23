#!/usr/bin/env python3
"""Independent YouTube video/Shorts collector. RSS + official Data API if configured.
Individual malformed entries are discarded; prior data are retained on failures.
"""
import json, os, tempfile, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"services10-data"/"videos.json"
CHANNEL=os.environ.get("ZT_YOUTUBE_CHANNEL_ID","")
NS={"a":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
def collect(xml):
    root=ET.fromstring(xml)
    items=[]
    for entry in root.findall("a:entry",NS):
        try:
            vid=entry.findtext("yt:videoId",namespaces=NS)
            title=entry.findtext("a:title",namespaces=NS)
            published=entry.findtext("a:published",namespaces=NS)
            if not (vid and title and published):continue
            items.append({"id":vid,"title":title,"published":published,"url":"https://www.youtube.com/watch?v="+vid,"type":"video_or_short"})
        except (TypeError,ValueError,AttributeError):continue
    return items
def merge(previous,news):
    result={}
    for row in previous+news:
        if isinstance(row,dict) and row.get("id") and row.get("title"):
            result[row["id"]]=row
    return sorted(result.values(),key=lambda r:r.get("published",""),reverse=True)
def save(rows):
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=OUT.parent,delete=False) as f:
        json.dump(rows,f,ensure_ascii=False,indent=2)
        name=f.name
    os.replace(name,OUT)
def main():
    old=json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
    if not CHANNEL:
        print("No ZT_YOUTUBE_CHANNEL_ID; preserving previous video data")
        return
    try:
        req=urllib.request.Request("https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL,headers={"User-Agent":"Mozilla/5.0 (compatible; ZazoomTek/1.0)"})
        with urllib.request.urlopen(req,timeout=35) as response:new=collect(response.read())
        save(merge(old,new))
        print("Video RSS collected:",len(new),"; total retained:",len(merge(old,new)))
    except Exception as exc:
        print("Video source temporarily unavailable; previous archive retained:",str(exc)[:160])
if __name__=="__main__":main()
