#!/usr/bin/env python3
"""Read-only production performance/indexability smoke test. No deploys or writes."""
import argparse
import json
import re
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

BASE = "https://zazoomtek.it"
PATHS = ("/", "/robots.txt", "/sitemap.xml", "/news.html", "/recensioni.html")
MAX_BYTES = 3_000_000

class Meta(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = []
        self.robots = []
        self.h1 = 0
    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs if k}
        if tag == "h1": self.h1 += 1
        if tag == "link" and "canonical" in a.get("rel","").lower().split():
            self.canonical.append(a.get("href",""))
        if tag == "meta" and a.get("name","").lower() in ("robots","googlebot"):
            self.robots.append(a.get("content",""))

def probe(path, timeout=18):
    req = urllib.request.Request(BASE + path, headers={
        "User-Agent": "ZazoomTek-SiteHealth/1.0 (+read-only)",
        "Accept": "text/html,application/xml,text/plain;q=0.9,*/*;q=0.5",
    })
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=timeout) as res:
        initial = res.read(MAX_BYTES + 1)
        ms = round((time.monotonic() - start) * 1000)
        if len(initial) > MAX_BYTES: raise ValueError("Response exceeds 3 MB probe limit")
        final = res.geturl()
        return {"path":path,"status":res.status,"elapsed_ms":ms,
                "bytes":len(initial),"final_url":final,
                "cache_control":res.headers.get("Cache-Control",""),
                "content_type":res.headers.get("Content-Type",""),
                "x_robots_tag":res.headers.get("X-Robots-Tag",""),
                "body":initial.decode("utf-8","replace")}

def audit():
    results = []
    failures = []
    for path in PATHS:
        try:
            result = probe(path)
            body = result.pop("body")
            if result["status"] != 200: failures.append(f"{path}: HTTP {result['status']}")
            if result["final_url"] != BASE + path:
                failures.append(f"{path}: unexpected redirect to {result['final_url']}")
            if "noindex" in result["x_robots_tag"].lower():
                failures.append(f"{path}: X-Robots-Tag noindex")
            if path.endswith(".html") or path == "/":
                parser = Meta()
                parser.feed(body.split("</head>",1)[0])
                if len(parser.canonical) != 1 or parser.canonical[0] != BASE + path:
                    failures.append(f"{path}: missing or incorrect canonical")
                if any("noindex" in x.lower() for x in parser.robots):
                    failures.append(f"{path}: robots meta noindex")
                if parser.h1 == 0 and not re.search(r"<h1\\b",body,re.I):
                    failures.append(f"{path}: H1 absent")
            if path == "/robots.txt" and "sitemap.xml" not in body.lower():
                failures.append("robots.txt: sitemap not advertised")
            if path == "/sitemap.xml" and "<loc>" not in body:
                failures.append("sitemap.xml: no URLs found")
            if result["elapsed_ms"] > 6000:
                failures.append(f"{path}: slow full response {result['elapsed_ms']}ms (monitor threshold)")
            results.append(result)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
            failures.append(f"{path}: request error: {e}")
    return {"probes":results,"findings":failures,"note":"Network elapsed time is not Core Web Vitals, crawl coverage or Google indexing status."}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--strict",action="store_true")
    args=parser.parse_args()
    report=audit()
    print(json.dumps(report,indent=2,ensure_ascii=False))
    if args.strict and report["findings"]:
        raise SystemExit(1)
if __name__=="__main__": main()
