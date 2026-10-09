#!/usr/bin/env python3
"""Conservative source extraction for approved editorial research candidates.
Never treats Google News headlines as independent corroboration. Produces evidence
for review only; does not publish, approve, or alter the website.
"""
import datetime as dt
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

ROOT=Path(__file__).resolve().parent.parent
IN=ROOT/"special-drafts-review.json"
OUT=ROOT/"special-source-evidence.json"
USER_AGENT="ZazoomTekEditorialResearch/1.0 (+https://www.zazoomtek.it/contatti.html)"
class Extractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip=0
        self.stack=[]
        self.blocks=[]
        self.current=[]
        self.metadata={}
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag in ("script","style","nav","footer","header","noscript"):
            self.skip+=1
        if tag=="meta":
            name=attrs.get("property") or attrs.get("name")
            if name in ("og:title","og:description","article:published_time","description"):
                self.metadata[name]=attrs.get("content","")
        if not self.skip and tag in ("p","h1","h2"):
            self.stack.append(tag)
            self.current=[]
    def handle_endtag(self,tag):
        if not self.skip and self.stack and tag==self.stack[-1]:
            value=re.sub(r"\s+"," ","".join(self.current)).strip()
            if len(value)>=55:self.blocks.append(value[:900])
            self.stack.pop()
            self.current=[]
        if tag in ("script","style","nav","footer","header","noscript") and self.skip:
            self.skip-=1
    def handle_data(self,data):
        if self.stack and not self.skip:self.current.append(data)
def fetch(url):
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or not parsed.hostname:
        raise ValueError("Only public HTTPS sources accepted")
    if parsed.hostname.lower() in ("news.google.com","google.com","www.google.com"):
        raise ValueError("Aggregator link, not the original publisher. Requires direct source URL")
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req,timeout=16) as response:
        final=response.geturl()
        p=urllib.parse.urlsplit(final)
        if p.scheme!="https" or not p.hostname:raise ValueError("Untrusted redirect")
        if p.hostname.lower() in ("news.google.com","google.com","www.google.com"):
            raise ValueError("Redirect points to aggregator, not original source")
        size=response.read(650_001)
        if len(size)>650_000:raise ValueError("Source over size limit")
        content_type=response.headers.get("Content-Type","").lower()
        if "html" not in content_type:raise ValueError("Not an HTML source")
    parsed=Extractor()
    parsed.feed(size.decode("utf-8","replace"))
    return {"url":final,"metadata":parsed.metadata,"excerpts":parsed.blocks[:14]}
def main():
    drafts=json.loads(IN.read_text(encoding="utf-8")).get("drafts",[])
    results=[]
    for draft in drafts[:6]:
        evidence=[]
        for url in draft.get("source_urls",[])[:3]:
            try:evidence.append({"input_url":url,"result":"retrieved","data":fetch(url)})
            except (urllib.error.URLError,ValueError,TimeoutError,OSError) as exc:
                evidence.append({"input_url":url,"result":"unavailable","reason":str(exc)[:120]})
        # Never label an article as factually verified just because a web page
        # was retrieved. Independent corroboration and human approval required.
        results.append({"section":draft.get("section"),"title":draft.get("title"),
            "sources":evidence,"verified":False,"approved":False,
            "publication_allowed":False})
    out={"generated_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
         "published":False,"note":"Source excerpts are research only; copyrighted text must not be copied into published work.",
         "items":results}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Evidence reports:",len(results),"publication allowed: False")
if __name__=="__main__":main()
