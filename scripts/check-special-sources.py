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

def direct_source(url):
    """Decode the Google News RSS wrapper to a publisher URL; never use RSS as evidence.
    If Google's nonpublic resolver changes, skip that story rather than invent a URL.
    """
    from urllib.parse import urlsplit, quote
    import html as htm
    parts=urlsplit(url)
    if parts.hostname not in ("news.google.com","www.news.google.com"):
        return url
    ident=parts.path.rstrip("/").split("/")[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,2000}", ident):
        raise ValueError("Invalid Google News ID")
    req=urllib.request.Request(
        "https://news.google.com/rss/articles/"+ident,
        headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                 "Accept-Language":"en-US,en;q=0.9","Cookie":"CONSENT=PENDING+987"})
    with urllib.request.urlopen(req,timeout=15) as r:
        document=r.read(950_000).decode("utf-8","replace")
    sg=re.search(r'data-n-a-sg="([^"]+)"',document)
    ts=re.search(r'data-n-a-ts="([0-9]+)"',document)
    if not sg or not ts:
        raise ValueError("Google News resolver unavailable (consent or rate limit)")
    from json import dumps, loads
    inner=["garturlreq",
       [["X","X",["X","X"],None,None,1,1,"US:en",None,1,None,None,None,None,None,0,1],
        "X","X",1,[1,1,1],1,1,None,0,0,None,0],
       ident,int(ts.group(1)),htm.unescape(sg.group(1))]
    payload=dumps([[["Fbv4je",dumps(inner)]]],separators=(",",":"))
    data=urllib.parse.urlencode({"f.req":payload}).encode("utf-8")
    req=urllib.request.Request(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute",
        data=data,method="POST",
        headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
                 "Content-Type":"application/x-www-form-urlencoded;charset=UTF-8",
                 "Origin":"https://news.google.com","Referer":"https://news.google.com/",
                 "X-Same-Domain":"1"})
    with urllib.request.urlopen(req,timeout=15) as r:
        raw=r.read(130_000).decode("utf-8","replace")
    payload=raw.split("\n\n",1)[-1]
    try:frames=loads(payload)
    except ValueError:raise ValueError("Google resolver returned invalid JSON")
    urls=[]
    for frame in frames:
        if isinstance(frame,list) and len(frame)>2 and frame[0]=="wrb.fr" and frame[1]=="Fbv4je" and frame[2]:
            decoded=loads(frame[2])
            if isinstance(decoded,list) and len(decoded)>1 and decoded[0]=="garturlres":
                urls.append(decoded[1])
    if len(urls)!=1:
        raise ValueError("Google News original article URL not available")
    return urls[0]

def allowed_public_source(url):
    """No local endpoints, private IP literals, credentials, or Google News wrappers."""
    import ipaddress
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or not p.hostname or p.username or p.password:
        return False
    host=p.hostname.lower().rstrip(".")
    if host in ("localhost","news.google.com","www.news.google.com") or host.endswith((".local",".internal")):
        return False
    try:return ipaddress.ip_address(host).is_global
    except ValueError:return len(host)<245 and "." in host and not host.endswith(".localhost")

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
    url=direct_source(url)
    parsed=urllib.parse.urlsplit(url)
    if not allowed_public_source(url):
        raise ValueError("Original source did not resolve to public HTTPS")
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/html,application/xhtml+xml"})
    with urllib.request.urlopen(req,timeout=16) as response:
        final=response.geturl()
        p=urllib.parse.urlsplit(final)
        if not allowed_public_source(final):raise ValueError("Unsafe source redirect")
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
