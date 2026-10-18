#!/usr/bin/env python3
"""Release gate for Git-connected Cloudflare Pages Free.

Only the trigger file causes a Pages build. You MUST configure Pages Build
watch paths -> Includes: cloudflare-release-trigger.txt, Excludes: (none).
Public changes are batched with a 50-minute rolling cooldown and a 450/31-day cap.
If nothing public changed, the hourly check starts zero Cloudflare builds.
Scheduled releases stop after 450 trigger changes in the previous 31 days,
preserving a separate urgent reserve to 475 (and another 25 as contingency).

This is a conservative Git-history backstop, NOT Cloudflare's actual billable
build counter. Check the Cloudflare dashboard for any deployments outside
this Git integration (such as manual redeployments or branch builds).
"""
from __future__ import annotations
import argparse
import datetime as dt
import fnmatch
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
TRIGGER=ROOT/"cloudflare-release-trigger.txt"
HORIZON="31 days ago"
COOLDOWN_MINUTES=50
RESERVE_SCHEDULED=450
RESERVE_URGENT=475
# If 350 builds or more are used, skip changes solely to homepage boxes;
# if 400 or more, skip changes solely to the featured carousel.
EDITORIAL_STOP=350
FEATURED_STOP=400
CONTENT_EXT={".html",".css",".js",".json",".xml",".txt",".png",".jpg",".jpeg",".webp",".svg",".avif",".gif",".woff",".woff2",".ico"}
OMIT={"cloudflare-release-trigger.txt"}
NONPUBLIC_DIR={".github","scripts","functions","editorial","includes","node_modules","dist"}
NONPUBLIC_SUFFIX=("-report.json","-manifest.json","-state.json")
LOW_EDITORIAL={"index.html","zt-home-live.js"}
LOW_FEATURED={"featured-carousel.json","trending-sources.json","trending-match-report.json"}
# Build-time generators are real production inputs even when they have not
# changed an .html/.js file in the repository yet. Without this list, a fix to
# the build pipeline could remain unpublished forever while the gate says
# "no changed public content". Never include the release workflow itself.
BUILD_INPUTS={
    "scripts/cloudflare-build-site.py",
    "scripts/build-cloudflare-pages.py",
    "scripts/apply-site-design.py",
    "scripts/trending-crosscheck.py",
    "scripts/cloudflare-sync-featured-home.py",
    "scripts/refresh-home-latest-reviews.py",
    "scripts/zt_sidebar_mix.py",
    "scripts/build-related-content.py",
    "scripts/link-review-videos.py",
    "scripts/ensure-review-summaries.py",
    "scripts/seo_watch_pages_safe.py",
    "scripts/validate-sync-output.py",
    "scripts/verify-packaged-home.py",
}
class ReleaseError(RuntimeError): pass

def git(*args: str) -> str:
    p=subprocess.run(["git",*args],cwd=ROOT,check=True,text=True,capture_output=True)
    return p.stdout.strip()

def build_count() -> int:
    # Count *all* commits that changed the watched release-trigger file, not
    # only commits with a particular subject prefix. Each changed trigger may
    # create a Pages build, including manual urgent deployments. Counting
    # unknown message subjects is safer than silently undercounting.
    commits=git("log","--since="+HORIZON,"--format=%H",
                "--","cloudflare-release-trigger.txt").splitlines()
    return len(set(commits))

def public(path: str) -> bool:
    p=Path(path)
    if not p.parts or p.parts[0].startswith("."):
        return False
    if path in BUILD_INPUTS:
        return True
    if p.parts[0] in NONPUBLIC_DIR or p.name in OMIT:
        return False
    if p.name.startswith(("preview-","anteprima-","audit-","test-","check-")):
        return False
    if p.name.endswith(NONPUBLIC_SUFFIX):
        return False
    if len(p.parts)>1 and p.parts[0]=="studio":
        return len(p.parts)==2 and p.name in {"index.html","publisher.js"}
    if len(p.parts)>1 and p.parts[0] not in ("assets","watch"):
        return False
    return p.suffix.lower() in CONTENT_EXT

def changed_since(previous: str) -> list[str]:
    if not previous:
        return ["index.html"]  # First release is intentional.
    try:
        git("cat-file","-e",previous+"^{commit}")
    except subprocess.CalledProcessError as exc:
        raise ReleaseError("Previous release source SHA is unknown; do not guess") from exc
    return [f for f in git("diff","--name-only",previous,"HEAD").splitlines() if public(f)]

def decide(changed: list[str],used: int,urgent: bool=False) -> str:
    if used >= (RESERVE_URGENT if urgent else RESERVE_SCHEDULED):
        return "block-budget"
    if not changed:
        return "unchanged"
    if not urgent and used>=EDITORIAL_STOP and set(changed)<=LOW_EDITORIAL:
        return "defer-editorial"
    if not urgent and used>=FEATURED_STOP and set(changed)<=LOW_FEATURED:
        return "defer-featured"
    return "publish"

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--urgent",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--dedupe-hour",action="store_true",
                        help="Suppress ordinary releases within 50 minutes of last trigger")
    args=parser.parse_args()
    if args.self_test:
        assert decide(["news-X.html"],350)=="publish"
        assert decide(["index.html","zt-home-live.js"],350)=="defer-editorial"
        assert decide(["featured-carousel.json"],400)=="defer-featured"
        assert decide(["news-X.html"],450)=="block-budget"
        assert decide(["news-X.html"],450,True)=="publish"
        assert decide(["news-X.html"],475,True)=="block-budget"
        assert decide(["news-X.html"],449)=="publish"
        assert decide(["news-X.html"],449,True)=="publish"
        assert decide(["news-X.html"],475)=="block-budget"
        assert decide(["news-X.html"],0)=="publish"
        assert decide([],0)=="unchanged"
        assert decide([],0,True)=="unchanged"
        assert decide(["scripts/editorial-only.py"],0)=="publish"  # Only direct public diffs may be passed to decide().
        assert not public("scripts/editorial-only.py")
        assert public("assets/special/example.webp") and public("news-example.html")
        assert public("studio/index.html") and public("studio/publisher.js")
        assert not public("studio/drafts.json")
        assert not public(".github/workflows/main.yml")
        assert not public("scripts/private.py")
        assert public("scripts/link-review-videos.py")
        assert public("scripts/cloudflare-build-site.py")
        assert not public("cloudflare-release-trigger.txt")
        print("RELEASE SELF TEST PASSED")
        return
    previous=""
    # GitHub Actions may deliver the prior :44 run at :04 of the NEXT hour.
    # Blocking by the local hour then silently drops this hour’s new articles:
    # e.g. a delayed release at 16:04 blocked the scheduled 16:44.
    # Instead use a 50-minute rolling cooldown so the :17 and :47 runs
    # check every hour but create at most one normal release per hour.
    # The independent rolling 31-day 450-build budget cap remains authoritative.
    if args.dedupe_hour and not args.urgent and TRIGGER.is_file():
        for row in TRIGGER.read_text(encoding="utf-8").splitlines():
            if not row.startswith("created_utc="):
                continue
            try:
                last=dt.datetime.fromisoformat(row.split("=",1)[1].replace("Z","+00:00"))
                if last.tzinfo is None:
                    raise ReleaseError("Release timestamp lacks timezone; refusing uncounted build")
                elapsed=(dt.datetime.now(dt.timezone.utc)-
                         last.astimezone(dt.timezone.utc)).total_seconds()
                if elapsed < 0:
                    raise ReleaseError("Release timestamp is in the future")
                if elapsed < COOLDOWN_MINUTES*60:
                    print(f"RELEASE CONTROL: last release was {elapsed/60:.1f}m ago; "
                          f"defer within {COOLDOWN_MINUTES}m cooldown to avoid duplicate Pages builds")
                    return
            except ValueError as exc:
                raise ReleaseError("Invalid release timestamp; refusing uncounted duplicate") from exc
    if TRIGGER.is_file():
        for line in TRIGGER.read_text(encoding="utf-8").splitlines():
            if line.startswith("source_commit="):
                previous=line.split("=",1)[1].strip()
    changed=changed_since(previous)
    used=build_count()
    outcome=decide(changed,used,args.urgent)
    print(f"RELEASE CONTROL: {outcome}, last 31 days Git-triggered releases={used}, "
          f"changed public files={len(changed)}, urgent={args.urgent}")
    if outcome!="publish":
        return
    source=git("rev-parse","HEAD")
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    TRIGGER.write_text(
        "ZazoomTek verified scheduled release\n"+
        "source_commit="+source+"\n"+
        "created_utc="+stamp+"\n"+
        "priority="+("urgent" if args.urgent else "news") +"\n",
        encoding="utf-8")
    print("TRIGGER CREATED: Cloudflare Pages Git integration must watch only this file")

if __name__=="__main__":
    main()
