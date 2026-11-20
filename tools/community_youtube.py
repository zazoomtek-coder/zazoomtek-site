#!/usr/bin/env python3
"""Read original public YouTube channel Community text, including per-post detail pages.
No API key, browser credentials, or fabricated content. Fail softly if YouTube blocks access.
Only posts with an actual /post/ identifier and recoverable text are returned.
"""
import json, re, urllib.request, urllib.parse, html, time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

CHANNEL="https://www.youtube.com/@ZazoomTek/posts"
CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
HEADERS={"User-Agent":UA,"Accept-Language":"it-IT,it;q=0.9,en;q=0.8"}
# Emergency rollback: set False to restore the former cover-only Community import.
MULTI_IMAGE_IMPORT_ENABLED = True
def fetch(url, payload=None, timeout=9, attempts=3):
 """Fetch YouTube data with bounded retries; never turn a transient error into an empty feed."""
 headers=dict(HEADERS)
 if payload is not None:headers["Content-Type"]="application/json"
 last_error=None
 for attempt in range(attempts):
  try:
   req=urllib.request.Request(url, data=payload, headers=headers)
   with urllib.request.urlopen(req,timeout=timeout) as result:
    return result.read(4000000).decode("utf-8","replace")
  except Exception as error:
   last_error=error
   if attempt+1<attempts:time.sleep(1+attempt)
 raise RuntimeError("YouTube request failed after "+str(attempts)+" attempts: "+url) from last_error

def webpage_json(source):
 for pattern in (r'(?:var\s+)?ytInitialData\s*=\s*',r'window\["ytInitialData"\]\s*=\s*',r'"ytInitialData"\s*:\s*'):
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

def trim_youtube_promo_tail(text):
 """Stop imported Community text immediately after the required closing sentence."""
 if not isinstance(text, str):
  return text
 pattern=re.compile(re.escape("Se ti piacciono tecnologia, gaming, unboxing e recensioni, segui ZazoomTek.").replace(r"\ ",r"\s+"),re.IGNORECASE)
 match=pattern.search(text)
 return text[:match.end()].rstrip() if match else text

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
   # Remove chat-rendering escape wrappers if they were pasted into a public Community post.
   content=re.sub(r"</?escape>","",content,flags=re.I)
   if not content:continue
   when=value(node.get("publishedTimeText") or node.get("publishedTime"))
   image_urls=[]
   attachment=node.get("backstageAttachment") or node.get("attachment") or {}
   for p in walk(attachment):
    thumbnails=p.get("thumbnails")
    if not isinstance(thumbnails,list):continue
    candidates=[x for x in thumbnails if isinstance(x,dict) and isinstance(x.get("url"),str) and x["url"].startswith("https://")]
    if not candidates:continue
    chosen=candidates[-1]["url"].replace("&amp;","&")
    if chosen not in image_urls:image_urls.append(chosen)
   if not MULTI_IMAGE_IMPORT_ENABLED:
    image_urls=image_urls[:1]
   thumb=image_urls[0] if image_urls else ""
   extra_images=[{"src":url,"caption":""} for url in image_urls[1:]]
   found[post_id]={"id":post_id,"text":content,"when":when,"image":thumb,
                   "images":extra_images,"url":"https://www.youtube.com/post/"+post_id}
 return list(found.values())

def merge_post_media(listing, detail):
 """Keep media found on the feed when the detail page omits or changes attachments."""
 merged=dict(detail)
 listing_cover=listing.get("image") or ""
 detail_cover=detail.get("image") or ""
 cover=listing_cover or detail_cover
 extras=[]
 seen={cover} if cover else set()
 # The feed and detail page can expose different portions of a multi-image post.
 # Preserve every unique extra image from both responses.
 for source in (listing.get("images"),detail.get("images")):
  if not isinstance(source,list):continue
  for image in source:
   if not isinstance(image,dict):continue
   src=image.get("src")
   if not isinstance(src,str) or not src.strip() or src in seen:continue
   seen.add(src)
   extras.append(dict(image))
 # If the detail page exposes a different lead image, retain it as an extra
 # instead of silently discarding either version of the post's media.
 if listing_cover and detail_cover and detail_cover not in seen and detail_cover!=listing_cover:
  extras.insert(0,{"src":detail_cover,"caption":detail.get("image_caption","")})
 merged["image"]=cover
 merged["images"]=extras
 return merged


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
 # Normalize case and common editorial separators while retaining the visible title.
 mark=re.sub(r"\s+"," ",title.casefold()).strip()
 compact=re.sub(r"\s*[:：–—-]\s*",": ",mark)
 if re.match(r"^news\s+tech(?:\s*[:：–—-]|\s+)",mark):kind="news";topic="tech"
 elif re.match(r"^news\s+gaming(?:\s*[:：–—-]|\s+)",mark):kind="news";topic="gaming"
 elif re.match(r"^news\s+extra(?:\s*[:：–—-]|\s+)",mark):kind="extra";topic=""
 elif re.match(r"^news\s+(?:speciali|special)(?:\s*[:：–—-]|\s+)",mark):kind="speciali";topic=""
 elif re.match(r"^news\s+(?:guide|guida)(?:s)?(?:\s*[:：–—-]|\s+)",mark):kind="guide";topic=""
 elif re.match(r"^(?:review|reviews|recensione|recensioni)(?:\s*/\s*(?:review|recensione))?(?:\s+(?:tech|gaming))?(?:\s*[:：–—-]|\s+)",mark):kind="review";topic="gaming" if re.match(r"^(?:review|reviews|recensione|recensioni)(?:\s*/\s*(?:review|recensione))?\s+gaming",mark) else ("tech" if re.match(r"^(?:review|reviews|recensione|recensioni)(?:\s*/\s*(?:review|recensione))?\s+tech",mark) else "")
 elif re.match(r"^(?:guida|guide|guides)(?:\s*[:：–—-]|\s+)",mark):kind="guide";topic=""
 elif re.match(r"^(?:speciale|speciali|special)(?:\s*[:：–—-]|\s+)",mark):kind="speciali";topic=""
 elif re.match(r"^extra(?:\s*[:：–—-]|\s+)",mark):kind="extra";topic=""
 elif re.match(r"^news(?:\s*[:：–—-]|\s+)",mark):kind="news";topic=""
 else:return title,None
 return title,kind

def editorial_topic(title):
 """Return an explicit topic only when the editorial prefix defines one."""
 heading=re.sub(r"\s+"," ",str(title or "").casefold()).strip()
 if re.match(r"^(?:news\s+gaming|(?:review|reviews|recensione|recensioni)(?:\s*/\s*(?:review|recensione))?\s+gaming)(?:\s*[:：–—-]|\s+)",heading):
  return "gaming"
 if re.match(r"^(?:news\s+tech|(?:review|reviews|recensione|recensioni)(?:\s*/\s*(?:review|recensione))?\s+tech)(?:\s*[:：–—-]|\s+)",heading):
  return "tech"
 return None

def discover(limit=160,max_pages=12):
 reference=datetime.now(timezone.utc)
 raw=""
 root={}
 initial_posts=[]
 last_error=None
 page_sources=(
  CHANNEL+"?hl=it&persist_hl=1",
  "https://www.youtube.com/channel/"+CHANNEL_ID+"/posts?hl=it&persist_hl=1",
  "https://www.youtube.com/channel/"+CHANNEL_ID+"/community?hl=it&persist_hl=1",
 )
 for source_url in page_sources:
  for attempt in range(3):
   try:
    raw=fetch(source_url,timeout=12,attempts=1)
    root=webpage_json(raw)
    initial_posts=post_records(root) if root else []
    if initial_posts:break
    last_error=RuntimeError("YouTube HTML did not contain Community post renderers")
   except Exception as error:
    last_error=error
   if attempt<2:time.sleep(1+attempt)
  if initial_posts:break
 if not initial_posts:
  raise RuntimeError("YouTube did not return Community post data after retries and fallback URLs") from last_error
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
  if len(collected)>=limit:break
  tokens=[token for token in continuation_tokens(root) if token not in token_seen]
  if not tokens:break
  if not key:raise RuntimeError("YouTube returned Community continuation data without an API key; pagination incomplete")
  token=tokens[0];token_seen.add(token)
  body=json.dumps({"context":ctx,"continuation":token}).encode("utf-8")
  root=json.loads(fetch("https://www.youtube.com/youtubei/v1/browse?key="+urllib.parse.quote(key),body))
 # Each detail page is opened to recover the *entire* text rather than teaser text.
 failed_details=[]
 def complete(item):
  title,kind=title_type(item.get("text",""))
  needs_detail=bool(kind and len(item.get("text",""))>=60)
  try:
   detail=post_records(webpage_json(fetch(item["url"]+"?hl=it",timeout=7)))
   matched=next((x for x in detail if x["id"]==item["id"]),None)
   if matched and len(matched["text"])>=len(item["text"]):
    item.update(merge_post_media(item,matched))
    item["verified_detail"]=True
   elif needs_detail:
    failed_details.append(item["id"])
  except Exception as error:
   if needs_detail:failed_details.append(item["id"])
  return item
 with ThreadPoolExecutor(max_workers=6) as executor:
  collected=list(executor.map(complete,collected))
 if failed_details:
  # A transient failure on a small number of detail pages must not discard
  # the other fully verified posts in this batch. Unverified IDs are not
  # returned, so they remain absent from the imported queue and are retried
  # automatically by the next scheduled collection.
  print("COMMUNITY DETAIL RETRY: "+str(len(failed_details))+
        " editorial post(s) could not be verified; skipped for this run: "+
        ", ".join(failed_details),flush=True)
 output=[]
 for ix,item in enumerate(collected):
  text=trim_youtube_promo_tail(item["text"].strip())
  item["text"]=text
  title,kind=title_type(text)
  if not kind or len(text)<60 or not item.get("verified_detail"):continue
  date=date_from_relative(item.get("when",""),reference)
  # YouTube relative dates are estimates, not a guaranteed precise published timestamp.
  heading=title.lower()
  explicit_topic=editorial_topic(title) or ""
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
