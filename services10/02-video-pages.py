#!/usr/bin/env python3
"""Independent verified-video page renderer; does not access Community posts."""
from __future__ import annotations
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load_list(path:Path)->list[dict]:
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data,list) else []
    except (ValueError,OSError):
        return []

def sync_video_catalog(root:Path=ROOT)->dict:
    """Publish only new confirmed 16:9 videos; preserve the old video archive."""
    new=load_list(root/"services10-data"/"videos.json")
    original=load_list(root/"home-video-feed.json")
    entries={x["id"]:x for x in original if isinstance(x,dict) and x.get("id")}
    added=0
    for video in new:
        if not isinstance(video,dict) or video.get("type")!="landscape_video":
            continue
        vid=str(video.get("id") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):continue
        if vid not in entries:
            entries[vid]={"id":vid,"title":str(video.get("title") or "Video ZazoomTek"),
                "publishedAt":str(video.get("published") or ""),
                "category":"video","short":False,"live":False,"completedLive":False}
            added+=1
    if added:
        catalog=sorted(entries.values(),key=lambda e:e.get("publishedAt",""),reverse=True)
        (root/"home-video-feed.json").write_text(
            json.dumps(catalog,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    horizontal=[v for v in entries.values()
                if not v.get("short") and re.fullmatch(
                    r"[A-Za-z0-9_-]{11}",str(v.get("id") or ""))]
    folder=root/"watch";folder.mkdir(parents=True,exist_ok=True)
    created=0
    for video in horizontal:
        vid=video["id"]
        page=folder/(vid+".html")
        if page.exists():continue
        title=html.escape(str(video.get("title") or "Video ZazoomTek"))
        page.write_text(
          '<!-- SERVICES10_GENERATED -->\\n<!doctype html><html lang="it"><head><meta charset="utf-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>'+title+' | ZazoomTek</title><link rel="stylesheet" href="/zt-design.css">'
          '<link rel="canonical" href="https://zazoomtek.it/watch/'+vid+'.html">'
          '<style>body{background:#eee;font:16px Arial}main{max-width:1100px;margin:30px auto;'
          'background:white;padding:25px}iframe{width:100%;aspect-ratio:16/9;border:0}'
          '</style></head><body><header><a href="/">ZazoomTek</a></header><main>'
          '<article class="zt-watch-article"><h1>'+title+'</h1>'
          '<iframe title="'+title+'" loading="lazy" allowfullscreen '
          'src="https://www.youtube-nocookie.com/embed/'+vid+'"></iframe>'
          '<p><a href="https://www.youtube.com/watch?v='+vid+'">Guarda su YouTube</a></p>'
          '</article></main><script src="/studio/edit-button.js" defer></script>'
          '</body></html>',encoding="utf-8")
        created+=1
    listing=folder/"index.html"
    if not listing.exists() or "SERVICES10_GENERATED" in listing.read_text(encoding="utf-8"):
        cards="\n".join('<article><a href="/watch/'+v["id"]+'.html">'
          '<img loading="lazy" width="240" '
          'src="https://i.ytimg.com/vi/'+v["id"]+'/hqdefault.jpg" alt="">'
          '<h2>'+html.escape(str(v.get("title") or "Video"))+'</h2></a></article>'
          for v in sorted(horizontal,
             key=lambda v:str(v.get("publishedAt") or ""),reverse=True))
        listing.write_text('<!-- SERVICES10_GENERATED -->\\n<!doctype html><html lang="it"><head><meta charset="utf-8">'
          '<title>Video ZazoomTek</title><link rel="stylesheet" href="/zt-design.css">'
          '</head><body><main><h1>Video orizzontali ZazoomTek</h1>'+cards+
          '</main></body></html>',encoding="utf-8")
    print("Landscape video catalog:",added,"new videos,",created,"Watch pages")
    return {"new_videos":added,"watch_pages":created}


if __name__=="__main__":
    sync_video_catalog()
