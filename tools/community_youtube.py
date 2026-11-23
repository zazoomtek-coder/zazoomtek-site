#!/usr/bin/env python3
"""Read complete public YouTube Community posts, verifying each channel-feed card on its detail page."""
import json, re, urllib.request, urllib.parse, html, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

CHANNEL="https://www.youtube.com/@ZazoomTek/posts"
CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
HEADERS={"User-Agent":UA,"Accept-Language":"it-IT,it;q=0.9,en;q=0.8"}
# Emergency rollback: set False to restore the former cover-only Community import.
MULTI_IMAGE_IMPORT_ENABLED = True
def fetch(url, payload=None, timeout=9):
 headers=dict(HEADERS)
 if payload is not None:headers["Content-Type"]="application/json"
 req=urllib.request.Request(url, data=payload, headers=headers)
 with urllib.request.urlopen(req,timeout=timeout) as result:
  return result.read(4000000).decode("utf-8","replace")

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
 """Decode YouTube rich text without stringifying renderer dictionaries."""
 if isinstance(node,str):return html.unescape(node)
 if isinstance(node,list):return "".join(value(x) for x in node)
 if not isinstance(node,dict):return ""
 if isinstance(node.get("runs"),list):return "".join(value(run) for run in node["runs"])
 if isinstance(node.get("content"),str):return html.unescape(node["content"])
 if isinstance(node.get("text"),str):return html.unescape(node["text"])
 if isinstance(node.get("simpleText"),str):return html.unescape(node["simpleText"])
 return ""

def _clean_post_text(text):
 text=(text or "").replace("\r\n","\n").replace("\r","\n")
 text=re.sub(r"[ \t]+\n","\n",text)
 text=re.sub(r"\n{3,}","\n\n",text)
 return re.sub(r"</?escape>","",text,flags=re.I).strip()

def editorial_topic(title):
 """Return the explicit tech/gaming topic encoded in an editorial heading."""
 value_text=(title or "").strip()
 if re.match(r"^(?:NEWS|REVIEW|RECENSIONE)(?:\s+TECH)\s*:", value_text, re.I):
  return "tech"
 if re.match(r"^(?:NEWS|REVIEW|RECENSIONE)(?:\s+GAMING)\s*:", value_text, re.I):
  return "gaming"
 if re.match(r"^RECENSIONE/REVIEW\s+TECH\s*:", value_text, re.I):
  return "tech"
 if re.match(r"^RECENSIONE/REVIEW\s+GAMING\s*:", value_text, re.I):
  return "gaming"
 return None


def trim_youtube_promo_tail(text):
 """Remove channel-promo material after the editorial CTA, preserving article text."""
 value_text=(text or "").strip()
 markers=(
  r"\\n(?:Subscribe|Follow|YouTube|Patreon|Instagram|TikTok|X\s*:)",
  r"\n(?:Subscribe|Follow|YouTube|Patreon|Instagram|TikTok|X\s*:)",
 )
 positions=[match.start() for marker in markers
            for match in [re.search(marker,value_text,re.I)] if match]
 return value_text[:min(positions)].rstrip() if positions else value_text

def _renderer_text(node):
 """Select the fullest available text field from a Community renderer."""
 fields=("expandedText","expandedContentText","contentText","content","text")
 candidates=[]
 for key in fields:
  candidate=_clean_post_text(value(node.get(key)))
  if candidate and candidate not in candidates:candidates.append(candidate)
 if not candidates:return ""
 return max(candidates,key=len)

def fetch_post_detail(post_id, attempts=3):
 """Read the individual public post page, not just its abbreviated channel-feed card."""
 url="https://www.youtube.com/post/"+urllib.parse.quote(post_id,safe="")+"?hl=it&persist_hl=1"
 last_error=None
 for attempt in range(attempts):
  try:
   raw=fetch(url,timeout=18)
   root=webpage_json(raw)
   if not root:raise ValueError("YouTube post page has no ytInitialData")
   match=next((item for item in post_records(root) if item.get("id")==post_id),None)
   if not match or len(match.get("text",""))<1:
    raise ValueError("YouTube post renderer not found in individual post page")
   return match
  except Exception as exc:
   last_error=exc
   if attempt+1<attempts:time.sleep(attempt+1)
 raise RuntimeError("Cannot verify complete YouTube Community post "+post_id) from last_error

def merge_post_media(listing, detail):
 """Merge detail metadata without losing images already extracted from the feed."""
 listing=listing if isinstance(listing,dict) else {}
 detail=detail if isinstance(detail,dict) else {}
 merged=dict(listing)
 merged.update(detail)
 feed_cover=listing.get("image") or ""
 detail_cover=detail.get("image") or ""
 cover=feed_cover or detail_cover
 ordered=[]
 if detail_cover and detail_cover!=cover:
  ordered.append({"src":detail_cover,"caption":""})
 for source in (listing.get("images",[]),detail.get("images",[])):
  if isinstance(source,list):
   for image in source:
    if isinstance(image,dict) and image.get("src"):
     ordered.append(dict(image))
 unique=[]
 seen=set()
 for image in ordered:
  url=image.get("src","")
  if url and url!=cover and url not in seen:
   unique.append(image)
   seen.add(url)
 merged["image"]=cover
 merged["images"]=unique
 return merged


def verify_post_details(items, workers=4):
 """Enrich every feed record from its own post page; fail closed rather than import excerpts."""
 if not items:return items
 results={}
 errors=[]
 with ThreadPoolExecutor(max_workers=max(1,min(int(workers),6))) as pool:
  pending={pool.submit(fetch_post_detail,item["id"]):item for item in items}
  for future in as_completed(pending):
   feed_item=pending[future]
   try:results[feed_item["id"]]=future.result()
   except Exception as exc:errors.append((feed_item["id"],exc))
 if errors:
  sample=", ".join(post_id+":"+type(exc).__name__ for post_id,exc in errors[:5])
  print("YOUTUBE COMMUNITY DETAIL RETRY:",len(errors),"of",len(items),
        "posts could not be verified; they remain eligible for the next cycle:",sample,flush=True)
 if not results:
  raise RuntimeError("No individual YouTube Community post could be verified; retry next cycle")
 verified=[]
 for feed_item in items:
  detail=results.get(feed_item["id"])
  if not detail:continue
  feed_text=_clean_post_text(feed_item.get("text",""))
  detail_text=_clean_post_text(detail.get("text",""))
  full_text=max((feed_text,detail_text),key=len)
  if not full_text:
   raise ValueError("Empty Community text after detail verification: "+feed_item["id"])
  merged=merge_post_media(feed_item, detail)
  merged["text"]=full_text
  merged["verified_detail"]=True
  # A detail page that still exposes an ellipsis or fewer characters than the
  # feed cannot certify that the entire post was recovered.
  detail_is_full=(len(detail_text)>=len(feed_text) and
                  not re.search(r"(?:\.\.\.|…|\b(?:mostra altro|read more)\s*)$",detail_text,re.I))
  merged["text_complete"]=bool(detail_is_full)
  merged["text_source"]="youtube-post-detail"
  if not detail_is_full:
   print("YOUTUBE COMMUNITY DETAIL INCOMPLETE; retry next cycle:",
         feed_item["id"],"feed chars",len(feed_text),"detail chars",len(detail_text),flush=True)
   continue
  verified.append(merged)
 return verified

def post_records(root):
 found={}
 for container in walk(root):
  for typ in ("backstagePostRenderer","postRenderer"):
   node=container.get(typ)
   if not isinstance(node,dict):continue
   post_id=node.get("postId") or node.get("id")
   if not isinstance(post_id,str) or not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}",post_id):continue
   content=_renderer_text(node)
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
   previous=found.get(post_id)
   if previous:
    if len(previous.get("text",""))>len(content):content=previous["text"]
    image_urls=list(dict.fromkeys(([previous.get("image","")] if previous.get("image") else [])+
                                  [x.get("src","") for x in previous.get("images",[]) if x.get("src")]+
                                  image_urls))
    thumb=image_urls[0] if image_urls else ""
    extra_images=[{"src":url,"caption":""} for url in image_urls[1:]]
   found[post_id]={"id":post_id,"text":content,"when":when or (previous or {}).get("when",""),"image":thumb,
                   "images":extra_images,"url":"https://www.youtube.com/post/"+post_id}
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
 # Preserve the editorial category instead of collapsing every "News ..." post
 # into generic news. These values are consumed by the site importer.
 if mark.startswith(("news tech:","news gaming:")):kind="news"
 elif mark.startswith(("news guide:","news guides:","guida:","guide:")):kind="guide"
 elif mark.startswith(("news extra:","extra:")):kind="extra"
 elif mark.startswith(("news speciali:","news special:","speciale:","special:")):kind="speciali"
 elif mark.startswith(("review:","recensione:","recensioni:","recensione/review:","review tech:","review gaming:","recensione tech:","recensione gaming:","recensioni tech:","recensioni gaming:","recensione/review tech:","recensione/review gaming:")):kind="review"
 elif mark.startswith("news:"):kind="news"
 else:
  # Accept known editorial headings even when punctuation or line breaks vary.
  first=" ".join((text or "").split()[:22]).lower()
  if first.startswith(("news tech","news gaming")):kind="news"
  elif first.startswith(("news guide","guida","guide")):kind="guide"
  elif first.startswith(("news extra","extra")):kind="extra"
  elif first.startswith(("news speciali","news special","speciale","special")):kind="speciali"
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
 # Verify every discovered ID before applying title/type/length filters: the feed
 # excerpt may be too short even to classify, while the detail page has the full post.
 # Only detail-fetch editorial posts (plus empty-text renderers that may still
 # contain a recoverable detail page). This avoids unnecessary requests for
 # unrelated or non-editorial channel entries.
 candidates=[]
 for item in collected:
  text=item.get("text","")
  if not text or title_type(text)[1]:
   candidates.append(item)
 collected=verify_post_details(candidates)
 output=[]
 for ix,item in enumerate(collected):
  text=item["text"].strip()
  title,kind=title_type(text)
  if not kind or len(text)<60:continue
  date=date_from_relative(item.get("when",""),reference)
  # YouTube relative dates are estimates, not a guaranteed precise published timestamp.
  heading=title.lower()
  explicit_topic="gaming" if heading.startswith(("news gaming","review gaming","recensione gaming","recensioni gaming")) else ("tech" if heading.startswith(("news tech","review tech","recensione tech","recensioni tech")) else "")
  item.update(title=title,type=kind,date=date[:10] if date else None,
    published_at=date or "",rank=ix,channel_id=CHANNEL_ID,
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
