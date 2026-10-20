#!/usr/bin/env python3
"""Prepare a Home design approval draft; never self-approve or deploy."""
import argparse
import json
import re
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location("zt_home_lock",ROOT/"scripts/verify-home-layout-lock.py")
mod=module_from_spec(spec)
spec.loader.exec_module(mod)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reason",required=True,help="Editorially requested improvement")
    ap.add_argument("--output",default="artifacts/home-layout-approval-draft.json")
    args=ap.parse_args()
    if len(args.reason.strip())<12:
        ap.error("Explain the requested layout improvement")
    html=(ROOT/"index.html").read_text(encoding="utf-8")
    style=re.search(r"<style\b[^>]*>(.*?)</style>",html,re.I|re.S)
    if not style:
        raise RuntimeError("Home has no inline styles")
    script=(ROOT/"zt-home-live.js").read_bytes()
    digest=mod.safe_editorial_js_sha(script)
    if not digest:
        raise RuntimeError("Home runtime changed beyond approved editorial data pattern; manual review required")
    # Verify invariants independently of the proposed new fingerprints.
    parser=mod.HomeElements()
    parser.feed(html)
    for key in ("ztFeaturedGrid","articleList"):
        if parser.ids.get(key)!=1:
            raise RuntimeError("Missing or duplicated critical Home ID: "+key)
    for marker in ("ARTICLE_FEED_START","ARTICLE_FEED_END","FEATURED_NEWS_START","FEATURED_NEWS_END",
                   "HOME_LATEST_REVIEWS_MAIN_START","HOME_LATEST_REVIEWS_MAIN_END"):
        if html.count("<!-- "+marker+" -->")!=1:
            raise RuntimeError("Home update broke an importer anchor: "+marker)
    result={"approved":False,"reason":args.reason.strip(),
            "blobs":{name:mod.blob_sha((ROOT/name).read_bytes()) for name in mod.LOCKED_BLOBS},
            "home_live_template_sha":digest,
            "inline_style_fnv64":mod.fnv64(style.group(1))}
    out=ROOT/args.output
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("DRAFT ONLY:",out,"Review screenshots and tests; set approved=true only after explicit human approval.")

if __name__=="__main__":
    main()
