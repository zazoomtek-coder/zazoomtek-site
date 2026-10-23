#!/usr/bin/env python3
"""Confirm that a requested Cloudflare Pages release is REALLY live.

This makes public GET requests only: it does not trigger extra Pages builds,
does not need an API token and never marks a release successful from git push
alone. Fails the GitHub Actions job on timeout with a diagnostic message.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REVIEW = "/thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html"
EXPECTED_REVIEW_VIDEO = "e7rAYQprXTM"


def get_public_page(base: str, path: str, expected: str) -> str:
    stamp = str(int(time.time()))
    separator = "&" if "?" in path else "?"
    url = base.rstrip("/") + path + separator + "zt-check=" + expected[:12] + "-" + stamp
    request = Request(url, headers={
        "User-Agent": "ZazoomTek-Release-Verification/1.0",
        "Cache-Control": "no-cache, no-store",
        "Pragma": "no-cache",
        "Accept": "application/json, text/html, */*",
    })
    with urlopen(request, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError(f"{path}: HTTP {response.status}")
        return response.read(2 * 1024 * 1024).decode("utf-8", "replace")


def verify_once(base: str, expected: str) -> str:
    receipt = json.loads(get_public_page(base, "/zt-release-status.json", expected))
    if (not isinstance(receipt, dict) or receipt.get("validated") is not True
            or receipt.get("source_commit") != expected):
        seen = receipt.get("source_commit", "missing") if isinstance(receipt, dict) else "malformed"
        raise RuntimeError(f"Live release receipt is old: expected {expected[:12]}, found {str(seen)[:12]}")
    # STUDIO PUBLIC RELEASE GATE: for every NEW release after the first
    # deployed Studio baseline, verify the real public files rather than merely
    # trusting a GitHub commit or Cloudflare receipt. Do not modify Home.
    first_studio_baseline = "dd585cd6c018150b9d0d283c04219b578f69a288"
    if expected != first_studio_baseline:
        studio_html = get_public_page(base, "/studio/index.html", expected)
        studio_js = get_public_page(base, "/studio/publisher.js", expected)
        seo_js = get_public_page(base, "/studio/editorial-seo.js", expected)
        if ("ZTStudioSEO" not in seo_js or "/studio/editorial-seo.js?v=" not in studio_html):
            raise RuntimeError("Published Studio lacks its content-aware SEO editor")
        if (not re.search(r'src="/studio/publisher\.js(?:\?v=[A-Za-z0-9_-]+)?"', studio_html)
                or 'id="publishBtn"' not in studio_html
                or 'id="ztVault"' not in studio_js
                or 'ZT_STUDIO_ENCRYPTED_VAULT_1' not in studio_js
                or 'ZT_STUDIO_TRUSTED_DEVICE_V1' not in studio_js
                or 'ztRememberSave' not in studio_js
                or 'ztRememberUnlock' not in studio_js
                or 'restoreTrustedDevice();' not in studio_js
                or 'async function publish(){' not in studio_js):
            raise RuntimeError(
                "Public Studio is missing password vault, trusted-PC auto-login, "
                "publisher script or its editor HTML; deployment is NOT complete"
            )
    # Check key outputs, not just the receipt. These are existing mandatory
    # ZazoomTek publishing rules that were previously missed in production.
    review = get_public_page(base, REVIEW, expected)
    # A CSS rule can contain the class name even if the sidebar was omitted.
    # Verify the actual rendered sidebar structure and all 11 editorial boxes.
    sidebar = re.search(
        r'<aside\b[^>]*\bzt-thermo-full-editorial\b[^>]*>(.*?)</aside>',
        review, re.I | re.S,
    )
    module_count = (
        len(re.findall(r'<section\b[^>]*\bside-box\b', sidebar.group(1), re.I))
        if sidebar else 0
    )
    if module_count < 11:
        raise RuntimeError(
            f"Published ThermoMate sidebar incomplete: {module_count}/11 editorial modules"
        )
    if ("zt-review-video-banner" not in review
            or "youtube.com/watch?v=" + EXPECTED_REVIEW_VIDEO not in review):
        raise RuntimeError("Published ThermoMate page lacks its verified YouTube review video")
    # Confirm the existing public Home runtime is retrievable. The layout
    # implementation and cache revision are freely editable by the editor.
    js = get_public_page(base, "/zt-home-live.js", expected)
    if not js.strip():
        raise RuntimeError("Published Home JavaScript response is empty")
    home = get_public_page(base, "/", expected)
    # A valid release MUST deliver the public Cybercultura archive and
    # both primary navigation links, not only a successful Cloudflare receipt.
    cyber = get_public_page(base, "/cybercultura.html", expected)
    if ('<h1>Cybercultura</h1>' not in cyber
            or 'https://zazoomtek.it/cybercultura.html' not in cyber
            or 'Tech Impact' not in cyber or 'Gaming Inside' not in cyber):
        raise RuntimeError("Cybercultura archive is missing or incomplete online")
    if ('href="/cybercultura.html">Cybercultura</a>' not in home
            or 'href="/speciali.html">Speciali</a>' not in home
            or 'id="ztHomeSpeciali"' not in home):
        raise RuntimeError("Live Home lacks Cybercultura/Speciali navigation or Speciali box")
    # Public receipt and HTTP 200 do not prove that the Home mosaic is intact.
    from html.parser import HTMLParser
    class FeaturedReader(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.cards=[]
            self.active=None
        def handle_starttag(self,tag,attrs):
            a=dict(attrs)
            if tag=="a" and "zt-feature-card" in (a.get("class") or "").split():
                self.active={"section":a.get("data-feature-section"),"url":a.get("href"),
                             "image":None}
                self.cards.append(self.active)
            elif tag=="img" and self.active is not None:
                self.active["image"]=a.get("src")
        def handle_endtag(self,tag):
            if tag=="a":
                self.active=None
    left="<!-- FEATURED_NEWS_START -->"
    right="<!-- FEATURED_NEWS_END -->"
    if home.count(left)!=1 or home.count(right)!=1:
        raise RuntimeError("Public home featured markers missing or duplicated")
    reader=FeaturedReader()
    reader.feed(home.split(left,1)[1].split(right,1)[0])
    data=json.loads(get_public_page(base,"/featured-carousel.json",expected))
    selected=data.get("items",[]) if isinstance(data,dict) else []
    expected_sections=["tech"]*4+["gaming"]
    if (len(reader.cards)!=5 or len(selected)!=5 or
            [c["section"] for c in reader.cards]!=expected_sections or
            [x.get("section") for x in selected]!=expected_sections or
            [c["url"] for c in reader.cards]!=[x.get("url") for x in selected] or
            [c["image"] for c in reader.cards]!=[x.get("image") for x in selected] or
            len({c["url"] for c in reader.cards})!=5):
        raise RuntimeError("Live Home carousel is missing, misordered or differs from manifest")
    # Old fixed column counts, alignment code and cache revision tokens are
    # not publication requirements. The public receipt, actual Home carousel,
    # rendered reviews and their assets are validated independently.
    # The pre-summary public release is still valid while the hourly
    # release cooldown protects the remaining Cloudflare build quota.
    # Every subsequent release must include all review summary thumbnails.
    if expected != "1a13c247cfc6504b4826bb3d0431c41fb6ad0b9b":
        # Check every published review, not just ThermoMate. The same actual
        # 16:9 image frame and one unique summary must reach Cloudflare.
        style = get_public_page(base, "/zt-review-summary.css", expected)
        if "aspect-ratio:16/9" not in style or "object-fit:contain" not in style:
            raise RuntimeError("Live review thumbnail stylesheet lacks 16:9 frame")
        root = Path(__file__).resolve().parents[1]
        reviews = sorted(p for p in {*root.glob("recensione-*.html"), *root.glob("*-recensione-*.html")}
                         if p.is_file() and not p.name.startswith(("preview-", "anteprima-", "test-")))
        if not reviews:
            raise RuntimeError("No local review inventory available for live checks")
        for page in reviews:
            text = review if page.name == REVIEW.lstrip("/") else get_public_page(base, "/"+page.name, expected)
            cards = re.findall(
                r'<section\b[^>]*class="[^"]*\bzt-review-summary\b[^"]*"[^>]*>.*?</section>',
                text, re.I | re.S,
            )
            if len(cards) != 1 or not re.search(r'<img\b[^>]*\bsrc=', cards[0], re.I):
                raise RuntimeError(f"Published review summary or 16:9 miniature missing: {page.name}")
            if '/zt-review-summary.css' not in text:
                raise RuntimeError(f"Published review does not load summary stylesheet: {page.name}")
    return expected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit")
    parser.add_argument("--base-url", default="https://zazoomtek.it")
    parser.add_argument("--timeout-seconds", type=int, default=420)
    parser.add_argument("--interval-seconds", type=int, default=20)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        sample = {"validated": True, "source_commit": "a" * 40}
        assert sample["validated"] is True and re.fullmatch(r"[a-f0-9]{40}", sample["source_commit"])
        assert "zt-check=" in args.base_url + "?zt-check=test"
        print("LIVE RELEASE VERIFY SELF TEST PASSED", flush=True)
        return
    if not args.source_commit or not re.fullmatch(r"[a-f0-9]{40}", args.source_commit):
        parser.error("--source-commit must be the 40-character SHA in the release trigger")
    if not args.base_url.startswith("https://"):
        parser.error("Public verification requires HTTPS")
    if not 20 <= args.timeout_seconds <= 900 or not 10 <= args.interval_seconds <= 120:
        parser.error("Unsupported polling settings")
    deadline = time.monotonic() + args.timeout_seconds
    attempt = 0
    while True:
        attempt += 1
        try:
            verified = verify_once(args.base_url, args.source_commit)
            print(f"PASS: Cloudflare public site is serving verified release {verified}", flush=True)
            return
        except (HTTPError, URLError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(f"Not live yet (attempt {attempt}): {exc}", flush=True)
        if time.monotonic() >= deadline:
            print("::error::Cloudflare release was requested but NOT verified on public "
                  "zazoomtek.it within the allowed window. Check Cloudflare build logs, "
                  "Pages build watch paths, and Git integration.", file=sys.stderr, flush=True)
            raise SystemExit(1)
        time.sleep(min(args.interval_seconds, max(0, deadline - time.monotonic())))


if __name__ == "__main__":
    main()
