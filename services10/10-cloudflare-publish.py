#!/usr/bin/env python3
"""Direct Cloudflare Pages deployment of a prepared static site.

Each publication invokes this independently; no central Master gateway.
Required environment: CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,
CLOUDFLARE_PAGES_PROJECT_NAME. Never delete existing content.
"""
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
def main():
    if not (DIST/"index.html").is_file():
        raise RuntimeError("No generated index.html in dist; refusing empty upload")
    project=os.environ["CLOUDFLARE_PAGES_PROJECT_NAME"]
    env=os.environ.copy()
    env["CLOUDFLARE_ACCOUNT_ID"]=os.environ["CLOUDFLARE_ACCOUNT_ID"]
    subprocess.run(["npx","--yes","wrangler@3","pages","deploy",str(DIST),
        "--project-name="+project,"--branch=main"],cwd=ROOT,env=env,check=True)
    if env.get("CLOUDFLARE_ZONE_ID"):
        subprocess.run(["python3",str(ROOT/"scripts/cloudflare-purge-after-release.py")],
            cwd=ROOT,env=env,check=False)
if __name__=="__main__":
    main()
