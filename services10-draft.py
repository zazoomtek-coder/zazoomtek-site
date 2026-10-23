#!/usr/bin/env python3
"""ZazoomTek 10 independent services — draft-only, never publishes or mutates main.

Each independent task keeps using its established implementation until the
replacement is validated against a full offline Cloudflare snapshot.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = [
  [
    "01-community",
    "update-youtube-posts.py"
  ],
  [
    "02-video-shorts",
    "update-youtube.py"
  ],
  [
    "03-home",
    "cloudflare-sync-featured-home.py"
  ],
  [
    "04-in-evidenza",
    "trending-crosscheck.py"
  ],
  [
    "05-da-non-perdere",
    "cloudflare-build-site.py"
  ],
  [
    "06-notizie-web",
    "cloudflare-build-site.py"
  ],
  [
    "07-recensioni",
    "refresh-home-latest-reviews.py"
  ],
  [
    "08-studio",
    "studio-inject-edit-button.py"
  ],
  [
    "09-layout",
    "apply-site-design.py"
  ],
  [
    "10-cloudflare-publish",
    "build-cloudflare-pages.py"
  ]
]
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("component", choices=[k for k,_ in COMPONENTS])
    parser.add_argument("--execute", action="store_true", help="Run component on this checkout only; never deploy")
    args = parser.parse_args()
    script = dict(COMPONENTS)[args.component]
    if not args.execute:
        print(json.dumps({"component":args.component,"existing_implementation":script,"mode":"draft","cloudflare_deploy":False},ensure_ascii=False))
        return
    cmd = [sys.executable, str(ROOT / "scripts" / script)]
    if args.component == "04-in-evidenza":
        cmd.append("--apply")
    if args.component == "10-cloudflare-publish":
        raise SystemExit("Draft release requires review; no Cloudflare deployment from this runner")
    subprocess.run(cmd, cwd=ROOT, check=True)
if __name__ == "__main__":
    main()
