#!/usr/bin/env python3
"""Aggiornamento incrementale dei soli video YouTube recensione/test/unboxing dal RSS ufficiale."""
from pathlib import Path
import json,re,urllib.request,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"data/videos.json"
CHANNEL_ID="UCJs0ZT10hUiPRD0UZtUpI1Q"
NS={"atom":"http://www.w3.org/2005/Atom","yt":"http://www.youtube.com/xml/schemas/2015"}
def classify(title):
 low=title.casefold()
 if "gameplay" in low or "trailer" in low or "shorts" in low:return None
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
  kindtopic=classify(title)
  if not kindtopic:continue
  kind,topic=kindtopic
  previous[vid]={"id":vid,"title":title,"date":day,"topic":topic,"kind":kind}
  added+=1
 current["videos"]=sorted(previous.values(),key=lambda x:x.get("date",""),reverse=True)
 if added:
  PATH.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("New valid videos:",added,"total:",len(current["videos"]))
if __name__=="__main__":main()
