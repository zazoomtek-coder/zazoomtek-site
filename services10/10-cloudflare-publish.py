#!/usr/bin/env python3
"""Independent Cloudflare Pages publisher.

A preview uses a *non-production* Cloudflare branch by default.
Explicit --production is required to target main; this component is not
connected to a live workflow in the migration branch.
"""
import argparse
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

def publish(dist: Path, *, project: str, branch: str, dry_run: bool = False):
    if not (dist / "index.html").is_file():
        raise RuntimeError("No built Home found at " + str(dist))
    env = os.environ.copy()
    args = ["npx", "--yes", "wrangler@3", "pages", "deploy", str(dist),
            "--project-name=" + project, "--branch=" + branch]
    if dry_run:
        print("Preview command validated; no upload made:", " ".join(args))
        return
    if not env.get("CLOUDFLARE_API_TOKEN") or not env.get("CLOUDFLARE_ACCOUNT_ID"):
        raise RuntimeError("Cloudflare test credentials missing")
    subprocess.run(args, cwd=ROOT, env=env, check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist", type=Path, default=DIST)
    parser.add_argument("--project", default=os.environ.get("CLOUDFLARE_PAGES_PROJECT_NAME"))
    parser.add_argument("--branch", default="zt-services10-review")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.project:
        parser.error("Cloudflare Pages project name required")
    if args.branch == "main" and not args.production:
        parser.error("Publishing on main requires --production")
    if args.production and args.branch != "main":
        parser.error("--production requires --branch main")
    publish(args.dist, project=args.project, branch=args.branch, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
