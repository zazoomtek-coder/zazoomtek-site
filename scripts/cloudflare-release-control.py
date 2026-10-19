#!/usr/bin/env python3
"""Release gate for Git-connected Cloudflare Pages Free.

Only the trigger file causes a Pages build. You MUST configure Pages Build
watch paths -> Includes: cloudflare-release-trigger.txt, Excludes: (none).
Validated public changes are published in fixed two-hour UTC release windows
(opening at even hours :17), with :47 and odd-hour checks as recovery opportunities.
One triggered release per window, no rolling 50-minute delay and no arbitrary
editorial/carousel hold. The 450/31-day budget leaves an urgent reserve to 475
(and another 25 as contingency). External GitHub/Cloudflare delays remain possible.
No public changes means no Pages build.

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
RESERVE_SCHEDULED=450
RESERVE_URGENT=475
SLOT_HOURS=2
SLOT_START_MINUTE=17
CONTENT_EXT={".html",".css",".js",".json",".xml",".txt",".png",".jpg",".jpeg",".webp",".svg",".avif",".gif",".woff",".woff2",".ico"}
OMIT={"cloudflare-release-trigger.txt"}
NONPUBLIC_DIR={".github","scripts","functions","editorial","includes","node_modules","dist"}
NONPUBLIC_SUFFIX=("-report.json","-manifest.json","-state.json")
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
    # All editorial updates, including Home modules, menus and the carousel,
    # are valid publication inputs. The separate Home safety gate decides
    # whether a change is destructive; this gate must not postpone safe content.
    return "publish"


def release_slot(now: dt.datetime) -> dt.datetime:
    """Latest fixed two-hour window start, UTC (00:17, 02:17, ...)."""
    if now.tzinfo is None:
        raise ReleaseError("A timezone-aware clock is required")
    now=now.astimezone(dt.timezone.utc)
    shifted=now-dt.timedelta(minutes=SLOT_START_MINUTE)
    even_hour=shifted.hour-(shifted.hour%SLOT_HOURS)
    return shifted.replace(hour=even_hour,minute=SLOT_START_MINUTE,
                           second=0,microsecond=0)


def release_metadata() -> dict[str,str]:
    if not TRIGGER.is_file():
        return {}
    lines=TRIGGER.read_text(encoding="utf-8").splitlines()
    return dict(line.split("=",1) for line in lines if "=" in line)


def already_released_in_slot(meta: dict[str,str],slot: dt.datetime) -> bool:
    """Prevent duplicate Cloudflare builds, including pre-migration receipts."""
    recorded=meta.get("slot_utc","")
    if recorded:
        try:
            stamp=dt.datetime.fromisoformat(recorded.replace("Z","+00:00"))
        except ValueError as exc:
            raise ReleaseError("Invalid existing release slot") from exc
        if stamp.tzinfo is None:
            raise ReleaseError("Existing release slot lacks timezone")
        return stamp.astimezone(dt.timezone.utc)>=slot
    created=meta.get("created_utc","")
    if not created:
        return False
    try:
        at=dt.datetime.fromisoformat(created.replace("Z","+00:00"))
    except ValueError as exc:
        raise ReleaseError("Invalid last release timestamp") from exc
    if at.tzinfo is None:
        raise ReleaseError("Last release timestamp lacks timezone")
    return at.astimezone(dt.timezone.utc)>=slot


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--urgent",action="store_true")
    parser.add_argument("--self-test",action="store_true")
    parser.add_argument("--scheduled-slot",action="store_true",
                        help="Publish once per fixed two-hour UTC window, recover on later checks")
    args=parser.parse_args()
    if args.self_test:
        assert decide(["news-X.html"],350)=="publish"
        assert decide(["index.html","zt-home-live.js"],350)=="publish"
        assert decide(["featured-carousel.json"],400)=="publish"
        assert decide(["news-X.html"],450)=="block-budget"
        assert decide(["news-X.html"],450,True)=="publish"
        assert decide(["news-X.html"],475,True)=="block-budget"
        assert decide(["news-X.html"],449)=="publish"
        assert decide(["news-X.html"],449,True)=="publish"
        assert decide(["news-X.html"],0)=="publish"
        assert decide([],0)=="unchanged"
        assert decide([],0,True)=="unchanged"
        assert not public("scripts/editorial-only.py")
        assert public("assets/special/example.webp") and public("news-example.html")
        assert public("studio/index.html") and public("studio/publisher.js")
        assert not public("studio/drafts.json")
        assert not public(".github/workflows/main.yml")
        assert not public("scripts/private.py")
        assert public("scripts/link-review-videos.py")
        assert public("scripts/cloudflare-build-site.py")
        assert not public("cloudflare-release-trigger.txt")
        utc=dt.timezone.utc
        assert release_slot(dt.datetime(2026,10,19,10,16,tzinfo=utc))==dt.datetime(2026,10,19,8,17,tzinfo=utc)
        assert release_slot(dt.datetime(2026,10,19,10,17,tzinfo=utc))==dt.datetime(2026,10,19,10,17,tzinfo=utc)
        assert release_slot(dt.datetime(2026,10,19,11,47,tzinfo=utc))==dt.datetime(2026,10,19,10,17,tzinfo=utc)
        assert release_slot(dt.datetime(2026,10,19,12,17,tzinfo=utc))==dt.datetime(2026,10,19,12,17,tzinfo=utc)
        assert release_slot(dt.datetime(2026,10,20,0,5,tzinfo=utc))==dt.datetime(2026,10,19,22,17,tzinfo=utc)
        slot=dt.datetime(2026,10,19,10,17,tzinfo=utc)
        assert already_released_in_slot({"slot_utc":"2026-10-19T10:17:00Z"},slot)
        assert not already_released_in_slot({"slot_utc":"2026-10-19T08:17:00Z"},slot)
        assert already_released_in_slot({"created_utc":"2026-10-19T10:28:00+00:00"},slot)
        assert not already_released_in_slot({"created_utc":"2026-10-19T10:10:00+00:00"},slot)
        print("RELEASE SELF TEST PASSED")
        return
    meta=release_metadata()
    previous=meta.get("source_commit","")
    slot=release_slot(dt.datetime.now(dt.timezone.utc))
    if args.scheduled_slot and not args.urgent and already_released_in_slot(meta,slot):
        print("RELEASE CONTROL: window "+slot.isoformat()+" already published; "
              "keep new updates queued for next fixed window")
        return
    changed=changed_since(previous)
    used=build_count()
    outcome=decide(changed,used,args.urgent)
    print(f"RELEASE CONTROL: {outcome}, last 31 days Git-triggered releases={used}, "
          f"changed public files={len(changed)}, urgent={args.urgent}")
    if outcome=="block-budget":
        raise ReleaseError("Cloudflare release budget exhausted: content remains queued; "
                           "scheduled publication needs quota or plan adjustment")
    if outcome!="publish":
        return
    source=git("rev-parse","HEAD")
    stamp=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    TRIGGER.write_text(
        "ZazoomTek verified scheduled release\n"+
        "source_commit="+source+"\n"+
        "created_utc="+stamp+"\n"+
        "priority="+("urgent" if args.urgent else "news") +"\n"+
        "slot_utc="+slot.isoformat().replace("+00:00","Z")+"\n",
        encoding="utf-8")
    print("TRIGGER CREATED: Cloudflare Pages Git integration must watch only this file")

if __name__=="__main__":
    main()
