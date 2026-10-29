#!/usr/bin/env python3
"""Read original public YouTube channel Community text, including per-post detail pages.
No API key, browser credentials, or fabricated content. Fail softly if YouTube blocks access.
Only posts with an actual /post/ identifier and recoverable text are returned.
"""
import json, re, urllib.request, urllib.parse, html
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

CHANNEL="https://www.youtube.com/@ZazoomTek/posts"
CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
HEADERS={"User-Agent":UA,"Accept-Language":"it-IT,it;q=0.9,en;q=0.8"}
def fetch(url, payload=None, timeout=9):
 headers=dict(HEADERS)
 if payload is not None:headers["Content-Type"]="application/json"
 req=urllib.request.Request(url, data=payload, headers=headers)
 with urllib.request.urlopen(req,timeout=timeout) as result:
  return result.read(4000000).decode("utf-8","replace")

def webpage_json(source):
 for pattern in (r'(?:var\s+)?ytInitialData\s*=\s*',r'window\["ytInitialData"\]\s*=\s*'):
  match=re.search(pattern,source)
  if match:
   try:return json.JSONDecoder().raw_decode(source[match.end():])[0]
   except (ValueError,TypeError):pass
 return {}

def walk(root):
 stack=[root]
 while stack:
  x=stack.pop()
  if isinstance(x,dict):
   yield x
   stack.extend(reversed(list(x.values())))
  elif isinstance(x,list):stack.extend(reversed(x))

def value(node):
 if isinstance(node,str):return html.unescape(node)
 if isinstance(node,list):return "".join(value(x) for x in node)
 if not isinstance(node,dict):return ""
 if "runs" in node:return "".join(value(run) for run in node["runs"])
 if "content" in node and isinstance(node["content"],str):return html.unescape(node["content"])
 return html.unescape(str(node.get("text") or node.get("simpleText") or ""))

def post_records(root):
 found={}
 for container in walk(root):
  for typ in ("backstagePostRenderer","postRenderer"):
   node=container.get(typ)
   if not isinstance(node,dict):continue
   post_id=node.get("postId") or node.get("id")
   if not isinstance(post_id,str) or not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}",post_id):continue
   content=value(node.get("contentText") or node.get("content") or node.get("text"))
   content=content.replace("\r\n","\n").strip()
   if not content:continue
   when=value(node.get("publishedTimeText") or node.get("publishedTime"))
   thumb=""
   for p in walk(node.get("backstageAttachment") or node.get("attachment") or {}):
    if "thumbnails" in p and isinstance(p["thumbnails"],list):
     candidates=[x for x in p["thumbnails"] if isinstance(x,dict) and x.get("url","").startswith("https://")]
     if candidates:
      thumb=candidates[-1]["url"].replace("&amp;","&");break
   found[post_id]={"id":post_id,"text":content,"when":when,"image":thumb,"url":"https://www.youtube.com/post/"+post_id}
 return list(found.values())

def continuation_tokens(root):
 tokens=[]
 for item in walk(root):
  for key in ("continuationCommand","nextContinuationData","reloadContinuationData"):
   o=item.get(key)
   if isinstance(o,dict) and o.get("token") and isinstance(o["token"],str):
    token=o["token"]
    if token not in tokens:tokens.append(token)
 return tokens

def date_from_relative(label,reference):
 raw=(label or "").lower().strip().replace("'", "")
 if any(x in raw for x in ("oggi","today","just now","adesso","ora fa","seconds","secondi")):
  return reference.isoformat(timespec="seconds")
 matches=re.search(r"(\d+)\s*(second|secondi|minute|minut|minuti|hour|ore|ora|giorn|day|settiman|week|mes|month|ann|year)",raw)
 if not matches:return ""
 n=int(matches.group(1)); unit=matches.group(2)
 if unit.startswith(("second","minut")):delta=timedelta(minutes=n if unit.startswith("minut") else n/60)
 elif unit.startswith(("hour","ore","ora")):delta=timedelta(hours=n)
 elif unit.startswith(("giorn","day")):delta=timedelta(days=n)
 elif unit.startswith(("settiman","week")):delta=timedelta(weeks=n)
 elif unit.startswith(("mes","month")):delta=timedelta(days=30*n)
 else:delta=timedelta(days=365*n)
 return (reference-delta).isoformat(timespec="seconds")

def title_type(text):
 title=(text or "").split("\n",1)[0].strip().lstrip("#").strip()
 if not title:return "",None
 if len(title)>210:title=title[:210].rsplit(" ",1)[0].strip()
 mark=title.lower()
 if mark.startswith(("news tech:","news gaming:","news:")):kind="news"
 elif mark.startswith(("review:","recensione:","review tech:","review gaming:")):kind="review"
 elif mark.startswith(("guida:","guide:")):kind="guide"
 elif mark.startswith(("speciale:","special:")):kind="speciali"
 elif mark.startswith("extra:"):kind="extra"
 else:
  # Public channel sometimes begins with an editorial heading followed by a colon.
  first=" ".join((text or "").split()[:22]).lower()
  if first.startswith(("news tech","news gaming")):kind="news"
  elif first.startswith(("review","recensione")):kind="review"
  else:return title,None
 return title,kind

def discover(limit=160,max_pages=12):
 reference=datetime.now(timezone.utc)
 raw=fetch(CHANNEL+"?hl=it&persist_hl=1")
 root=webpage_json(raw)
 if not root:raise ValueError("YouTube did not return public post data")
 collected=[];ids=set()
 api=re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"',raw)
 client=re.search(r'"INNERTUBE_CLIENT_VERSION"\s*:\s*"([^"]+)"',raw)
 visitor=re.search(r'"VISITOR_DATA"\s*:\s*"([^"]+)"',raw)
 key=api.group(1) if api else ""
 version=client.group(1) if client else "2.20261001.00.00"
 ctx={"client":{"clientName":"WEB","clientVersion":version,"hl":"it","gl":"IT"}}
 if visitor:ctx["client"]["visitorData"]=visitor.group(1)
 token_seen=set()
 for page in range(max_pages):
  for item in post_records(root):
   if item["id"] in ids:continue
   ids.add(item["id"]);collected.append(item)
   if len(collected)>=limit:break
  if len(collected)>=limit or not key:break
  tokens=[token for token in continuation_tokens(root) if token not in token_seen]
  if not tokens:break
  token=tokens[0];token_seen.add(token)
  body=json.dumps({"context":ctx,"continuation":token}).encode("utf-8")
  try:root=json.loads(fetch("https://www.youtube.com/youtubei/v1/browse?key="+urllib.parse.quote(key),body))
  except Exception:break
 # Each detail page is opened to recover the *entire* text rather than teaser text.
 def complete(item):
  try:
   detail=post_records(webpage_json(fetch(item["url"]+"?hl=it",timeout=7)))
   matched=next((x for x in detail if x["id"]==item["id"]),None)
   if matched and len(matched["text"])>=len(item["text"]):
    item.update(matched)
    item["verified_detail"]=True
  except Exception:pass
  return item
 with ThreadPoolExecutor(max_workers=6) as executor:
  collected=list(executor.map(complete,collected))
 output=[]
 for ix,item in enumerate(collected):
  text=item["text"].strip()
  title,kind=title_type(text)
  if not kind or len(text)<60 or not item.get("verified_detail"):continue
  date=date_from_relative(item.get("when",""),reference)
  # YouTube relative dates are estimates, not a guaranteed precise published timestamp.
  heading=title.lower()
  explicit_topic="gaming" if heading.startswith(("news gaming","review gaming")) else ("tech" if heading.startswith(("news tech","review tech")) else "")
  item.update(title=title,type=kind,date=date[:10] if date else None,
    published_at=date or "",rank=ix,channel_id=CHANNEL_ID,text_complete=True,
    **({"topic":explicit_topic} if explicit_topic else {}))
  if kind=="review":
   from review_pros_cons import attach
   attach(item)
  output.append(item)
 return output

if __name__=="__main__":
 try:
  data=discover()
  print(json.dumps({"post_count":len(data),"posts":data},ensure_ascii=False,indent=2))
 except Exception as err:
  print(json.dumps({"error":str(err),"post_count":0,"posts":[]},ensure_ascii=False))
