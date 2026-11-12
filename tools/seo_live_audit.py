#!/usr/bin/env python3
"""Read-only live SEO checks; never deploys or changes production."""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

BASE = "https://zazoomtek.it"
UA = "ZazoomTek-SEO-Health/1.0 (read-only)"
SECTIONS = ("/", "/news", "/news-tech", "/news-gaming",
            "/recensioni-tech", "/recensioni-gaming", "/guide",
            "/speciali", "/extra", "/cybercultura")
LEGACY_ARTICLE_PATHS = ("/community-ugkxhw4e98tezptpdc7opr4e9dcs53bsioey",)
SM = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


class PageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.robots = []
        self.h1 = 0
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        if tag == "meta" and attrs.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(attrs.get("content", ""))


def request(url):
    req = Request(url, headers={"User-Agent": UA})
    try:
        with urlopen(req, timeout=20) as response:
            return response.status, response.url, response.read(8_000_000), response.headers
    except HTTPError as exc:
        return exc.code, exc.url, exc.read(1000), exc.headers


def audit(base=BASE, sample=10):
    base = base.rstrip("/")
    errors, warnings, checks = [], [], []
    try:
        status, _, robots_body, _ = request(base + "/robots.txt")
        robots = robots_body.decode("utf-8", "replace")
        if status != 200:
            errors.append("robots.txt: HTTP " + str(status))
        if any(line.strip().casefold() == "disallow: /" for line in robots.splitlines()):
            errors.append("robots.txt appears to disallow the entire site")
        if base + "/sitemap.xml" not in robots:
            errors.append("robots.txt missing canonical sitemap declaration")
        checks.append({"url": base + "/robots.txt", "status": status})

        status, _, sitemap_body, _ = request(base + "/sitemap.xml")
        if status != 200:
            errors.append("sitemap.xml: HTTP " + str(status))
            paths = []
        else:
            root = ET.fromstring(sitemap_body)
            paths = [node.text for node in root.iter(SM + "loc") if node.text]
            if not paths:
                errors.append("sitemap.xml contains no URLs")
            if len(paths) != len(set(paths)):
                errors.append("sitemap.xml has repeated URLs")
            if any(not p.startswith(base + "/") for p in paths):
                errors.append("sitemap.xml has URLs outside the expected domain")
            for path in LEGACY_ARTICLE_PATHS:
                if base + path not in paths:
                    errors.append("Known Google article URL is missing from sitemap: " + path)
        checks.append({"url": base + "/sitemap.xml", "status": status, "entries": len(paths)})

        known = set(paths)
        urls = list(dict.fromkeys([base + p for p in SECTIONS] + paths[:sample] +
                                  [base + p for p in LEGACY_ARTICLE_PATHS]))
        def inspect(url):
            status, final_url, body, headers = request(url)
            return url, status, final_url, body, headers

        # Check all sitemap routes concurrently so a full 400+ URL audit stays
        # comfortably within the read-only workflow timeout.
        with ThreadPoolExecutor(max_workers=16) as pool:
            for url, status, final_url, body, headers in pool.map(inspect, urls):
                entry = {"url": url, "status": status, "final_url": final_url}
                if final_url.rstrip("/") != url.rstrip("/"):
                    errors.append(url + ": redirected to a different destination " + final_url)
                if status != 200:
                    errors.append(url + ": HTTP " + str(status))
                    checks.append(entry)
                    continue
                meta = PageMeta()
                meta.feed(body.decode("utf-8", "replace"))
                entry["canonical"] = meta.canonicals
                entry["robots"] = meta.robots
                if len(meta.canonicals) != 1:
                    errors.append(url + ": expected exactly one canonical")
                elif meta.canonicals[0] != url:
                    errors.append(url + ": canonical mismatch " + meta.canonicals[0])
                if any("noindex" in r.casefold() for r in meta.robots):
                    errors.append(url + ": noindex on a public, expected indexable page")
                if "noindex" in headers.get("X-Robots-Tag", "").casefold():
                    errors.append(url + ": noindex from X-Robots-Tag")
                if url not in known:
                    warnings.append(url + ": section absent from sitemap (inspect if intentional)")
                checks.append(entry)

        # The two URL forms should not introduce competing canonical documents.
        for path in ("/extra", "/speciali", "/news"):
            clean = base + path
            html = clean + ".html"
            status, final_url, body, _ = request(html)
            if status == 200:
                meta = PageMeta()
                meta.feed(body.decode("utf-8", "replace"))
                if meta.canonicals != [clean]:
                    errors.append(html + ": extension alias has incorrect canonical")
                else:
                    warnings.append(html + ": HTTP 200 alias with correct canonical; 301 may be preferable")
            elif status not in (301, 308):
                # urllib follows redirects, so 200 after a 301 usually reaches this branch above.
                warnings.append(html + ": unexpected HTTP " + str(status))
            checks.append({"url": html, "status": status, "final_url": final_url})
    except (URLError, TimeoutError, ET.ParseError, UnicodeError, ValueError) as exc:
        errors.append("Audit could not complete: " + type(exc).__name__ + ": " + str(exc))

    return {"site": base, "pages_checked": len(checks), "errors": errors,
            "warnings": warnings, "checks": checks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--sample", type=int, default=10)
    ap.add_argument("--json", default="seo-live-audit.json")
    args = ap.parse_args()
    result = audit(args.base, max(0, min(args.sample, 1000)))
    with open(args.json, "w", encoding="utf-8") as out:
        json.dump(result, out, indent=2, ensure_ascii=False)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"},
                     indent=2, ensure_ascii=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
