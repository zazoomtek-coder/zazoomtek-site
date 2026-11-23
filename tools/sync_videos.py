#!/usr/bin/env python3
"""Lettura incrementale degli upload YouTube tramite RSS e pagine canale paginate."""
from pathlib import Path
import json,re,urllib.request,urllib.parse,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"data/videos.json"
CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
NS={"atom":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
def is_short_title(title):
 low=title.casefold()
 return bool(re.search(r"(?:#|\b)shorts?\b|/shorts/",low))
def is_short_entry(entry):
 return any("/shorts/" in (link.get("href") or "").casefold()
            for link in entry.findall("atom:link",NS))
def classify(title):
 low=title.casefold()
 if is_short_title(title) or "gameplay" in low or "trailer" in low:return None
 if "unboxing" in low:kind="unboxing"
 elif re.search(r"\btest\b",low):kind="test"
 elif "recensione" in low or "review" in low:kind="review"
 else:return None
 gaming=any(x in low for x in ("ps5","ps4","xbox","switch","nintendo","gameplay","call of duty","modern warfare","gta ","ace combat","sesame street","wolverine","walto","serious sam","nba 2k","lou's lagoon","princess of the water lilies"))
 tech=any(x in low for x in ("70mai","thermomate","smart glasses","dash cam","smartphone","notebook","ryzen","realme","laptop","iifactor","dtno"))
 if gaming==tech:return None
 return kind,"gaming" if gaming else "tech"
def main():
 current=json.loads(PATH.read_text(encoding="utf8"))
 previous={v["id"]:v for v in current["videos"]}
 uri="https://www.youtube.com/feeds/videos.xml?channel_id="+CHANNEL_ID
 req=urllib.request.Request(uri,headers={"User-Agent":"ZazoomTek Feed Sync/1.0"})
 with urllib.request.urlopen(req,timeout=20) as reply:root=ET.fromstring(reply.read())
 added=0
 for entry in root.findall("atom:entry",NS):
  vid=entry.findtext("yt:videoId",default="",namespaces=NS)
  title=entry.findtext("atom:title",default="",namespaces=NS)
  day=entry.findtext("atom:published",default="",namespaces=NS)
  if not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid) or not title or not day or vid in previous:continue
  if is_short_entry(entry):continue
  kindtopic=classify(title)
  if not kindtopic:continue
  kind,topic=kindtopic
  previous[vid]={"id":vid,"title":title,"date":day,"topic":topic,"kind":kind}
  added+=1
 current["videos"]=sorted(previous.values(),key=lambda x:x.get("date",""),reverse=True)
 if added:
  PATH.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("New valid videos:",added,"total:",len(current["videos"]))


def _fetch_channel_page(url, payload=None, timeout=22, extra_headers=None):
 headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36",
          "Accept-Language":"it-IT,it;q=0.9,en;q=0.8"}
 if payload is not None:headers["Content-Type"]="application/json"
 if isinstance(extra_headers,dict):headers.update(extra_headers)
 request=urllib.request.Request(url,data=payload,headers=headers)
 with urllib.request.urlopen(request,timeout=timeout) as response:
  return response.read(5000000).decode("utf-8","replace")


def _walk_youtube(value):
 stack=[value]
 while stack:
  item=stack.pop()
  if isinstance(item,dict):
   yield item
   stack.extend(reversed(list(item.values())))
  elif isinstance(item,list):
   stack.extend(reversed(item))


def _youtube_text(value):
 if isinstance(value,str):return value
 if isinstance(value,list):return "".join(_youtube_text(item) for item in value)
 if not isinstance(value,dict):return ""
 if isinstance(value.get("runs"),list):return "".join(_youtube_text(item) for item in value["runs"])
 for key in ("text","simpleText","content"):
  if isinstance(value.get(key),str):return value[key]
 return ""


def _youtube_initial_data(source):
 for pattern in (r'(?:var\s+)?ytInitialData\s*=\s*',
                 r'window\["ytInitialData"\]\s*=\s*',
                 r'"ytInitialData"\s*:\s*'):
  match=re.search(pattern,source)
  if match:
   try:return json.JSONDecoder().raw_decode(source[match.end():])[0]
   except (ValueError,TypeError):pass
 return {}


def _youtube_continuations(root):
 found=[]
 for item in _walk_youtube(root):
  for key in ("continuationCommand","nextContinuationData","reloadContinuationData"):
   value=item.get(key)
   if isinstance(value,dict) and isinstance(value.get("token"),str):
    token=value["token"]
    if token and token not in found:found.append(token)
 return found


def _is_short_renderer(renderer):
 for item in _walk_youtube(renderer):
  status=item.get("thumbnailOverlayTimeStatusRenderer")
  if isinstance(status,dict) and str(status.get("style","")).upper()=="SHORTS":
   return True
  badge=item.get("metadataBadgeRenderer")
  if isinstance(badge,dict) and "short" in _youtube_text(badge.get("label")).casefold():
   return True
 return False


def _has_standard_video_renderer(root):
 for parent in _walk_youtube(root):
  for renderer_key in ("videoRenderer","gridVideoRenderer"):
   renderer=parent.get(renderer_key)
   if not isinstance(renderer,dict):
    continue
   video_id=renderer.get("videoId")
   title=_youtube_text(renderer.get("title")).strip()
   if (isinstance(video_id,str) and re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id)
       and title and not is_short_title(title) and not _is_short_renderer(renderer)):
    return True
 return False


def discover_uploads(limit=180,max_pages=12):
 """Read standard channel uploads with YouTube's Innertube Videos tab and continuation API."""
 urls=(
  "https://www.youtube.com/channel/"+CHANNEL_ID+"/videos?hl=it&persist_hl=1",
  "https://www.youtube.com/channel/"+CHANNEL_ID+"/videos?view=0&sort=dd&flow=grid&hl=en&gl=US",
  "https://www.youtube.com/@ZazoomTek/videos?hl=en&gl=US",
  "https://www.youtube.com/@ZazoomTek/videos?app=desktop&hl=it",
  "https://m.youtube.com/@ZazoomTek/videos?hl=en",
 )
 raw=""
 root={}
 fallback_raw=""
 fallback_root={}
 failures=[]
 for url in urls:
  try:
   candidate=_fetch_channel_page(url)
   parsed=_youtube_initial_data(candidate)
   if parsed and _has_standard_video_renderer(parsed):
    raw=candidate
    root=parsed
    break
   if parsed and not fallback_raw:
    fallback_raw=candidate
    fallback_root=parsed
   failures.append(url+(": ytInitialData has no standard video renderers" if parsed else ": no ytInitialData"))
  except Exception as exc:
   failures.append(url+": "+type(exc).__name__)

 # Some YouTube channel pages return only a shell. Keep its client metadata
 # and ask the channel Videos tab directly through the same Innertube browse
 # endpoint used by YouTube's own web client.
 if not root:
  raw=fallback_raw or raw
  root=fallback_root or {}
 api=re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"',raw)
 client=re.search(r'"INNERTUBE_CLIENT_VERSION"\s*:\s*"([^"]+)"',raw)
 visitor=re.search(r'"VISITOR_DATA"\s*:\s*"([^"]+)"',raw)
 key=api.group(1) if api else "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
 version=client.group(1) if client else "2.20260114.08.00"
 context={"client":{"clientName":"WEB","clientVersion":version,"hl":"it","gl":"IT"}}
 if visitor:context["client"]["visitorData"]=visitor.group(1)
 browse_url="https://www.youtube.com/youtubei/v1/browse?key="+urllib.parse.quote(key)+"&prettyPrint=false"
 headers={
  "X-YouTube-Client-Name":"1",
  "X-YouTube-Client-Version":version,
  "Origin":"https://www.youtube.com",
  "Referer":"https://www.youtube.com/",
 }
 if not _has_standard_video_renderer(root):
  payload=json.dumps({
   "context":context,
   "browseId":CHANNEL_ID,
   "params":"EgZ2aWRlb3PyBgQKAjoA",
  }).encode("utf-8")
  try:
   response=_fetch_channel_page(browse_url,payload,extra_headers=headers)
   parsed=json.loads(response)
   if _has_standard_video_renderer(parsed):
    root=parsed
   else:
    failures.append("Innertube channel Videos tab returned no standard video renderers")
  except Exception as exc:
   failures.append("Innertube channel Videos tab: "+type(exc).__name__+": "+str(exc)[:180])

 if not _has_standard_video_renderer(root):
  raise ValueError("YouTube channel videos endpoints unavailable: "+"; ".join(failures))

 records={}
 seen_tokens=set()
 for page in range(max(1,int(max_pages))):
  for parent in _walk_youtube(root):
   for renderer_key in ("videoRenderer","gridVideoRenderer"):
    renderer=parent.get(renderer_key)
    if not isinstance(renderer,dict):continue
    video_id=renderer.get("videoId")
    title=_youtube_text(renderer.get("title")).strip()
    published_label=_youtube_text(renderer.get("publishedTimeText")).strip()
    if (not isinstance(video_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",video_id)
        or not title or is_short_title(title) or _is_short_renderer(renderer)):
     continue
    records[video_id]={"id":video_id,"title":title,"published_label":published_label}
  if len(records)>=limit:break
  token=next((value for value in _youtube_continuations(root) if value not in seen_tokens),None)
  if not token:break
  seen_tokens.add(token)
  body=json.dumps({"context":context,"continuation":token}).encode("utf-8")
  response=_fetch_channel_page(browse_url,body,extra_headers=headers)
  try:root=json.loads(response)
  except (ValueError,TypeError):root=_youtube_initial_data(response)
  if not root:break
  if len(records)>=limit:break
 if not records:raise ValueError("YouTube channel page returned no standard video renderers")
 return list(records.values())[:limit]


if __name__=="__main__":main()
