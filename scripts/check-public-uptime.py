#!/usr/bin/env python3
"""Read-only public uptime checker. Never modifies DNS or performs a deploy."""
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin

BASE = "https://zazoomtek.it/"
PATHS = ("", "news.html", "recensioni.html", "gaming.html", "robots.txt", "sitemap.xml")
UA = "ZazoomTek-ReadOnly-Uptime/1.0"

def check(path):
    url = urljoin(BASE, path)
    reason = ""
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=15) as response:
                data = response.read(2048)
                if response.status == 200 and data:
                    print(f"PASS {response.status} {url}")
                    return True
                reason = f"unexpected status/empty response: {response.status}"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = str(exc)
        if attempt < 2:
            time.sleep(3 * (attempt + 1))
    print(f"FAIL {url}: {reason}", file=sys.stderr)
    return False

if __name__ == "__main__":
    sys.exit(0 if all(check(p) for p in PATHS) else 1)
