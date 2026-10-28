"""Audit all real Web news landing pages against source and first-party matches."""
from pathlib import Path
from html.parser import HTMLParser
from html import escape as esc
from web_editorial import gateway_path,relevant,topic_similarity
import re

class Links(HTMLParser):
 def __init__(self):
  super().__init__()
  self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="a":
   data=dict(attrs)
   self.links.append(data.get("href",""))

def check_web_gateways(root,web_items,rows):
 root=Path(root)
 issues=[]
 expected=set()
 for entry in web_items:
  url=str(entry.get("url") or "")
  if entry.get("source_only"):
   if entry.get("internal_path"):issues.append("Source-only placeholder cannot have a gateway")
   continue
  path=gateway_path(entry)
  if not path:continue
  expected.add(path)
  if path!=entry.get("internal_path"):issues.append("Missing canonical Web gateway for "+url)
  dest=root/(path[1:]+".html")
  if not dest.is_file():
   issues.append("Missing gateway "+path)
   continue
  html=dest.read_text(encoding="utf-8")
  parser=Links()
  parser.feed(html)
  if 'data-web-gateway="1"' not in html:
   issues.append(path+": incorrect internal landing template")
  if url not in parser.links:
   issues.append(path+": original external source unavailable")
  computed=relevant(entry.get("title",""),rows)
  expected_match=computed[0] if computed else None
  if expected_match:
   if parser.links.count("/"+expected_match["slug"])!=1:
    issues.append(path+": first-party match absent or repeated")
   if "Approfondimento originale ZazoomTek" not in html:
    issues.append(path+": original first-party headline not prioritized")
  else:
   if "non risulta un approfondimento originale" not in html:
    issues.append(path+": fallback explanatory introduction missing")
   if "Scopri altri contenuti ZazoomTek" not in html and "sull'argomento" not in html:
    issues.append(path+": internal discovery fallback missing")
  if "<h1>" not in html or 'class="web-gateway-primary"' not in html:
   issues.append(path+": missing gateway main structure")
  if 'name="robots" content="noindex' not in html:
   issues.append(path+": thin page must not be indexed")
 index=(root/"notizie-web.html").read_text(encoding="utf-8")
 home=(root/"index.html").read_text(encoding="utf-8")
 for path in expected:
  if 'href="'+path+'"' not in index and 'href="'+path+'"' not in home:
   issues.append(path+": Web news card still points only to the external URL")
 # Matching must be conservative: sharing a generic word or a brand is not proof.
 samples=[
  ("MacBook Pro con schermo touch: tutti i dettagli",
   {"title":"Apple MacBook Pro schermo touch: cosa cambia","category":"news-tech"},True),
  ("Prezzi e novità della tecnologia",
   {"title":"Novità Sony PlayStation per il gaming","category":"news-tech"},False),
  ("Samsung lancia un nuovo prodotto",
   {"title":"Samsung Galaxy Tab S11 presenta un display","category":"news-tech"},False)
 ]
 for headline,article,should_match in samples:
  found=bool(topic_similarity(headline,article))
  if found!=should_match:issues.append("Topic matcher regression: "+headline)
 if issues:raise AssertionError("WEB GATEWAY AUDIT FAILED: "+"; ".join(issues[:18]))
 print("WEB GATEWAY AUDIT PASS:",len(expected),
       "real imported article pages, original-source links and first-party match verification",flush=True)
