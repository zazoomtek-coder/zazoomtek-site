#!/usr/bin/env python3
"""Independent best-effort YouTube Community reader; retains all prior posts.

Uses only official channel pages. Malformed posts are skipped individually.
"""
import html,json,os,re,tempfile,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"services10-data"/"community.json"
HANDLE=os.environ.get("ZT_YOUTUBE_HANDLE","ZazoomTek")
def walk(node):
    if isinstance(node,dict):
        yield node
        for value in node.values():yield from walk(value)
    elif isinstance(node,list):
        for value in node:yield from walk(value)
def text(node):
    if isinstance(node,dict):
        if "simpleText" in node:return str(node["simpleText"])
        if "runs" in node:return "".join(str(x.get("text","")) for x in node["runs"] if isinstance(x,dict))
    return ""
def image_from_attachment(post):
    attachment=post.get("backstageAttachment") or post.get("backstageImageRenderer") or {}
    if not isinstance(attachment,dict):
        return ""
    urls=[]
    for part in walk(attachment):
        images=part.get("thumbnails") if isinstance(part,dict) else None
        if not isinstance(images,list):continue
        for thumbnail in images:
            if isinstance(thumbnail,dict):
                value=str(thumbnail.get("url") or "")
                if value.startswith("https://"):
                    urls.append((int(thumbnail.get("width") or 0),value))
    return max(urls,default=(0,""))[1]

def extract(page):
    # Decode the complete nested JSON value. A non-greedy brace regex can
    # truncate an otherwise valid YouTube post collection.
    marker = re.search(
        r"(?:var\s+ytInitialData\s*=|window\[[\"']ytInitialData[\"']\]\s*=)\s*",
        page
    )
    if not marker:
        return []
    try:
        root, _ = json.JSONDecoder().raw_decode(page[marker.end():].lstrip())
    except (json.JSONDecodeError, ValueError):
        return []
    out=[]
    seen=set()
    for obj in walk(root):
        try:
            post=obj.get("backstagePostRenderer") or obj.get("postRenderer")
            if not isinstance(post,dict):continue
            pid=post.get("postId") or post.get("id")
            msg=text(post.get("contentText") or post.get("content") or {})
            if not pid or not msg or pid in seen:continue
            seen.add(pid)
            out.append({"id":pid,"title":msg[:160],"text":msg,
                        "url":"https://www.youtube.com/post/"+pid,
                        "image":image_from_attachment(post),
                        "first_seen":datetime.now(timezone.utc).isoformat()})
        except (TypeError,ValueError,KeyError,AttributeError):
            continue
    return out

def merge(old,new):
    posts={}
    for item in old+new:
        if not isinstance(item,dict) or not item.get("id"):continue
        before=posts.get(item["id"],{})
        merged={**before}
        merged.update({key:value for key,value in item.items() if value not in ("",None,[])})
        if before.get("first_seen"):
            merged["first_seen"]=before["first_seen"]
        posts[item["id"]]=merged
    return list(posts.values())

def main():
    old=json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else []
    try:
        url="https://www.youtube.com/@"+HANDLE.lstrip("@")+"/posts"
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"it-IT,it;q=0.9"})
        with urllib.request.urlopen(req,timeout=35) as response:page=response.read().decode("utf-8","replace")
        new=extract(page)
        if not new:
            print("Community page returned no parseable posts; retained previous archive")
            return
        result=merge(old,new)
        OUT.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8",dir=OUT.parent,delete=False) as f:
            json.dump(result,f,ensure_ascii=False,indent=2); name=f.name
        os.replace(name,OUT)
        print("Community posts observed:",len(new),"; retained total:",len(result))
    except Exception as exc:
        print("Community temporarily unavailable; archive retained:",str(exc)[:180])
if __name__=="__main__":main()
