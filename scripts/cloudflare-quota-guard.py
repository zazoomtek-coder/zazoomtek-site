#!/usr/bin/env python3
"""Conservative, fail-closed Cloudflare Pages release-budget gate.

Runs in GitHub Actions *before* a Cloudflare publication. Never runs on
visitors' browsers and is not shipped in the Pages static dist.

Count recent Pages deployment attempts across the entire Cloudflare account,
including previews and failures. This is a conservative proxy, not an official
billing meter: the actual Pages build usage in Cloudflare must be reconciled
when connecting the account. API failure blocks deployment rather than risk
eating the entire month's remaining allowance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LIMIT = 500
# Stop nonessential services first; preserve news and urgent corrections.
THRESHOLDS = {
    "editorial": 350,  # daily Home/editorial-box rotation
    "featured": 400,   # News in evidenza carousel
    "news": 485,       # YouTube Community, videos, manually edited articles
    "urgent": 495,     # urgent editorial correction only
}
SAFE_WINDOW_DAYS = 31  # avoids assuming the reset happens on the 1st of a month
MAX_API_PAGES = 100

class QuotaError(RuntimeError):
    pass

def permitted(kind: str, used: int) -> bool:
    if kind not in THRESHOLDS:
        raise QuotaError("Unknown publication priority")
    if used < 0:
        raise QuotaError("Negative build count")
    return used < THRESHOLDS[kind]

def api_get(path: str, params: dict | None = None) -> dict:
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        raise QuotaError("Missing CLOUDFLARE_API_TOKEN")
    url = "https://api.cloudflare.com/client/v4" + path
    if params:
        url += "?" + urlencode(params)
    with urlopen(Request(url, headers={"Authorization": "Bearer " + token,
                                       "Accept": "application/json",
                                       "User-Agent": "ZazoomTek-QuotaGuard/1.0"}),
                 timeout=25) as response:
        data = json.load(response)
    if not data.get("success") or not isinstance(data.get("result"), list):
        raise QuotaError("Cloudflare API did not return a valid result list")
    return data

def paged(path: str):
    for page in range(1, MAX_API_PAGES + 1):
        data = api_get(path, {"per_page": 100, "page": page})
        for entry in data["result"]:
            yield entry
        info = data.get("result_info") or {}
        pages = int(info.get("total_pages") or page)
        if page >= pages:
            return
    raise QuotaError("Cloudflare API results too large to count safely")

def parse_date(value: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise QuotaError("Cloudflare deployment missing creation timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise QuotaError("Invalid Cloudflare deployment timestamp") from exc
    if stamp.tzinfo is None:
        raise QuotaError("Cloudflare deployment timestamp has no timezone")
    return stamp.astimezone(timezone.utc)

def count_recent_attempts() -> int:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    if not account or not account.isalnum():
        raise QuotaError("Missing or invalid CLOUDFLARE_ACCOUNT_ID")
    cutoff = datetime.now(timezone.utc) - timedelta(days=SAFE_WINDOW_DAYS)
    projects = list(paged(f"/accounts/{account}/pages/projects"))
    total = 0
    unique = set()
    for project in projects:
        name = project.get("name")
        if not isinstance(name, str) or not name:
            raise QuotaError("Cloudflare Pages project missing name")
        for deployment in paged(f"/accounts/{account}/pages/projects/{name}/deployments"):
            ident = (name, deployment.get("id"))
            if not ident[1]:
                raise QuotaError("Cloudflare deployment has no ID")
            if ident in unique:
                continue
            unique.add(ident)
            if parse_date(deployment.get("created_on")) >= cutoff:
                # Even aborted/failed and preview builds conservatively count.
                # Skip reasons explicitly identified as no-build do not count.
                if not deployment.get("skip_reason"):
                    total += 1
    return total

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=sorted(THRESHOLDS), required=True)
    parser.add_argument("--simulate-used", type=int,
                        help="Offline regression test only; never use to authorize production")
    args = parser.parse_args()
    try:
        if args.simulate_used is not None:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                raise QuotaError("Simulation is forbidden in GitHub Actions")
            used = args.simulate_used
            print("SIMULATION: not real Cloudflare usage", file=sys.stderr)
        else:
            used = count_recent_attempts()
        remaining = max(0, LIMIT - used)
        print(f"PAGES ESTIMATED 31-DAY USAGE: {used}/{LIMIT}; "
              f"remaining at most {remaining}; publication={args.kind}; "
              f"stop threshold={THRESHOLDS[args.kind]}")
        if not permitted(args.kind, used):
            print(f"BLOCK: {args.kind} publication deferred to protect news budget",
                  file=sys.stderr)
            return 2
        if used >= 300:
            print("WARNING: release budget is nearing its reserve band")
        return 0
    except (QuotaError, OSError, ValueError, KeyError, TimeoutError) as exc:
        print(f"BLOCK: cannot verify Pages release budget: {exc}", file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
