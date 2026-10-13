#!/usr/bin/env python3
"""Approved editorial review queue: Rome timestamps, atomic staging and idempotent retries."""
import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
QUEUE = "editorial/review-publication-queue.json"
HOME_A = "<!-- HOME_LATEST_REVIEWS_MAIN_START -->"
HOME_B = "<!-- HOME_LATEST_REVIEWS_MAIN_END -->"
ARCHIVE = '<div class="news-list" id="reviewList">'
SAFE = re.compile(r"^[a-z0-9][a-z0-9-]*\.html$")


def manifest(root):
    data = json.loads((root / QUEUE).read_text(encoding="utf-8"))
    if data.get("version") != 1 or data.get("timezone") != "Europe/Rome":
        raise ValueError("Invalid approval queue or timezone")
    seen = set()
    for item in data["items"]:
        for key in ("id", "status", "publish_at", "source", "target", "title",
                    "platform", "date_label", "description", "image"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise ValueError(f"Missing field {key} in review queue")
        if item["status"] not in ("draft", "approved", "cancelled"):
            raise ValueError("Unknown approval state")
        if item["id"] in seen or item["target"] in seen:
            raise ValueError("Duplicate queue entry")
        seen.update((item["id"], item["target"]))
        if (not SAFE.fullmatch(item["source"]) or not item["source"].startswith("anteprima-")
                or not SAFE.fullmatch(item["target"]) or item["target"].startswith("anteprima-")):
            raise ValueError("Unsafe public/preview path")
        when = datetime.fromisoformat(item["publish_at"])
        if when.tzinfo is None or when.astimezone(ZoneInfo("Europe/Rome")).utcoffset() != when.utcoffset():
            raise ValueError("Timestamp must carry the correct Europe/Rome UTC offset")
    return data["items"]


def release_html(text, target):
    url = "https://zazoomtek.it/" + target
    if not all(x in text.lower() for x in ("<title>", "<h1", "<article", "</html>")):
        raise ValueError("Approved preview is not a full article: " + target)
    text = re.sub(r'<meta\s+name="robots"\s+content="[^"]*"\s*/?>', "", text, flags=re.I)
    text = re.sub(r'<link\s+rel="canonical"[^>]*>', "", text, flags=re.I)
    text = re.sub(r'<div class="previewbar">[\s\S]*?</div>', "", text, count=1)
    text = re.sub(r'(<meta property="og:url" content=")[^"]*(")', lambda m: m[1]+url+m[2], text, count=1)
    if "<head>" not in text:
        raise ValueError("Head tag missing")
    return text.replace("<head>", '<head><meta name="robots" content="index,follow,max-image-preview:large">'
                        '<link rel="canonical" href="'+url+'">', 1)


def review_archive_card(item):
    esc=lambda v: html.escape(v,quote=True)
    title,link,pic=esc(item["title"]),esc(item["target"]),esc(item["image"])
    terms=esc((item["title"]+" "+item["description"]+" "+item["platform"]).lower())
    info=esc("ZazoomTek · "+item["date_label"]+" · "+item["platform"])
    desc=esc(item["description"])
    return (f'<article class="news-row" data-news-search="{terms}"><a href="/{link}">'
            f'<img src="{pic}" alt="{title}" loading="lazy"></a><div class="news-copy">'
            f'<h2><a href="/{link}">{title}</a></h2><div class="news-meta">{info}</div>'
            f'<p>{desc}</p><a class="news-read" href="/{link}">Leggi la recensione ›</a>'
            '</div></article>')


def home_review_card(item):
    esc=lambda v: html.escape(v,quote=True)
    title,link,pic=esc(item["title"]),esc(item["target"]),esc(item["image"])
    return (f'<article class="video-card zt-review-card"><a class="video-thumb zt-review-thumb"'
            f' href="/{link}" aria-label="{title}"><img src="{pic}" alt="{title}" loading="lazy"></a>'
            f'<h3><a href="/{link}">{title}</a></h3><small>{item["publish_at"][:10]}</small></article>')


def publish(root=ROOT, now=None, dry_run=False):
    now=now or datetime.now(timezone.utc)
    changes={}
    def read(name):
        return changes.get(name, (root/name).read_text(encoding="utf-8"))
    due_items=[]
    for item in sorted(manifest(root),key=lambda i:i["publish_at"]):
        if item["status"]!="approved" or datetime.fromisoformat(item["publish_at"])>now:
            continue
        target=item["target"]
        src=root/item["source"]
        if not src.is_file():
            raise ValueError("Approved preview not found: "+item["source"])
        new_public = not (root/target).is_file()
        if new_public:
            changes[target]=release_html(src.read_text(encoding="utf-8"),target)
        elif re.search(r'<meta[^>]+name="robots"[^>]+noindex',read(target),re.I):
            raise ValueError("Published file incorrectly marked noindex: "+target)
        archive=read("recensioni-scritte.html")
        if f'href="/{target}"' not in archive:
            if archive.count(ARCHIVE)!=1:
                raise ValueError("Review archive structure changed")
            changes["recensioni-scritte.html"]=archive.replace(ARCHIVE,ARCHIVE+review_archive_card(item),1)
        home=read("index.html")
        if home.count(HOME_A)!=1 or home.count(HOME_B)!=1:
            raise ValueError("Home review markers missing")
        start,end=home.index(HOME_A)+len(HOME_A),home.index(HOME_B)
        block=home[start:end]
        # Never re-pin an older review after newer reviews replace it in Home.
        # Newly released reviews alone are eligible for a Home insertion.
        if new_public and f'href="/{target}"' not in block:
            cards=re.findall(r'<article class="video-card zt-review-card">[\s\S]*?</article>',block)
            if len(cards)!=5:
                raise ValueError("Home review count changed; safe stop")
            changes["index.html"]=home[:start]+"\n"+"\n".join([home_review_card(item)]+cards[:4])+"\n"+home[end:]
        for name in ("sitemap.xml","google-sitemap.xml"):
            site=read(name)
            url="https://zazoomtek.it/"+target
            if "<loc>"+url+"</loc>" not in site:
                if site.count("</urlset>")!=1:
                    raise ValueError("Sitemap is malformed")
                entry=f'<url><loc>{url}</loc><lastmod>{item["publish_at"][:10]}</lastmod></url>\n'
                changes[name]=site.replace("</urlset>",entry+"</urlset>",1)
        due_items.append(item["id"])
    changed=[n for n,c in changes.items() if not (root/n).is_file() or (root/n).read_text(encoding="utf-8")!=c]
    if not dry_run:
        for n in changed:
            (root/n).write_text(changes[n],encoding="utf-8")
    print(json.dumps({"due":due_items,"changed":changed,"dry_run":dry_run},ensure_ascii=False))
    return changed


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    publish(dry_run=args.dry_run)
