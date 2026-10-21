#!/usr/bin/env python3
"""Purge Cloudflare cache after a verified production release.

Authentication is obtained solely from GitHub Actions secrets / environment.
Never persist or print the API token. This helper does not publish content.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.cloudflare.com/client/v4"


def purge() -> None:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    zone = os.environ.get("CLOUDFLARE_ZONE_ID", "").strip()
    if not token or not zone:
        raise RuntimeError("Missing CLOUDFLARE_API_TOKEN or CLOUDFLARE_ZONE_ID secret")
    if len(zone) != 32 or any(ch not in "0123456789abcdefABCDEF" for ch in zone):
        raise RuntimeError("Invalid CLOUDFLARE_ZONE_ID format")
    request = urllib.request.Request(
        f"{API}/zones/{zone}/purge_cache",
        data=json.dumps({"purge_everything": True}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # Do not output request headers or credentials.
        raise RuntimeError(f"Cloudflare purge HTTP {exc.code}") from None
    if result.get("success") is not True:
        errors = result.get("errors") or []
        codes = [str(err.get("code", "?")) for err in errors if isinstance(err, dict)]
        raise RuntimeError("Cloudflare purge rejected (error codes: " + ", ".join(codes) + ")")
    print("CLOUDFLARE_PURGE_SUCCESS: global cache purged after verified release")


if __name__ == "__main__":
    try:
        purge()
    except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"CLOUDFLARE_PURGE_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
