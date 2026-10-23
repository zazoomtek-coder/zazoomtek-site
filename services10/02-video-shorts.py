#!/usr/bin/env python3
"""Independent YouTube landscape-video collector using RSS and YouTube Data API.
Individual malformed entries are discarded; prior data are retained on failures.
"""
import json, os, tempfile, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"services10-data"/"videos.json"
CHANNEL=os.environ.get("ZT_YOUTUBE_CHANNEL_ID","UCJs0ZT10hUiPRD0UZtUpI1Q")
API_KEY=os.environ.get("YOUTUBE_API_KEY","")
NS={"a":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
def landscape_ids(ids):
    """Include only verified horizontal 16:9 videos; exclude Shorts and unknowns."""
    if not API_KEY or not ids:
        print("YouTube Data API key absent: cannot verify landscape; retaining archive")
        return set()
    result=set()
    for start in range(0,len(ids),50):
        batch=ids[start:start+50]
        params=urllib.parse.urlencode({"part":"player,snippet","id":",".join(batch),"key":API_KEY})
        req=urllib.request.Request("https://www.googleapis.com/youtube/v3/videos?"+params)
        with urllib.request.urlopen(req,timeout=35) as response:
            data=json.load(response)
        for item in data.get("items",[]):
            player=item.get("player",{})
            snippet=item.get("snippet",{})
            embed=player.get("embedHtml","")
            import re
            wh=re.search(r"width=[\\\"'](\\d+)[\\\"'][^>]*height=[\\\"'](\\d+)",embed)
            if not wh:
                wh=re.search(r"height=[\\\"'](\\d+)[\\\"'][^>]*width=[\\\"'](\\d+)",embed)
                if wh: w,h=int(wh.group(2)),int(wh.group(1))
                else: continue
            else:w,h=int(wh.group(1)),int(wh.group(2))
            if h and abs(w/h-16/9)<0.04 and snippet.get("liveBroadcastContent")!="upcoming":
                result.add(item["id"])
    return result
def collect(xml):
    root=ET.fromstring(xml)
    items=[]
    for entry in root.findall("a:entry",NS):
        try:
            vid=entry.findtext("yt:videoId",namespaces=NS)
            title=entry.findtext("a:title",namespaces=NS)
            published=entry.findtext("a:published",namespaces=NS)
            if not (vid and title and published):continue
            items.append({"id":vid,"title":title,"published":published,"url":"https://www.youtube.com/watch?v="+vid,"type":"landscape_video"})
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
        allowed=landscape_ids([x["id"] for x in new])
        new=[x for x in new if x["id"] in allowed]
        old=[x for x in old if x.get("type")=="landscape_video"]
        save(merge(old,new))
        print("Verified landscape videos:",len(new),"; total retained:",len(merge(old,new)))
    except Exception as exc:
        print("Video source temporarily unavailable; previous archive retained:",str(exc)[:160])
if __name__=="__main__":main()
