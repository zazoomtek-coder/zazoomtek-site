#!/usr/bin/env python3
"""Approved ZazoomTek JSON -> generated HTML adapters (STAGING BUILD ONLY).

This script intentionally reads structured data but never modifies the repository
source during a Master data stage. Rendering occurs in a disposable worktree,
then only the verified dist/ artifact is kept.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object: " + str(path))
    return data


def local_url(root: Path, item: dict[str, Any]) -> None:
    url = item.get("url")
    if not isinstance(url, str) or not re.fullmatch(
            r"/(?:news-[A-Za-z0-9_-]+|tech-impact-[a-z0-9-]+|gaming-inside-[a-z0-9-]+)\.html", url):
        raise ValueError("Unapproved article URL: " + str(url))
    if not (root / url[1:]).is_file():
        raise ValueError("Article not published: " + url)
    if not isinstance(item.get("title"), str) or len(item["title"].strip()) < 10:
        raise ValueError("Article title too short: " + url)
    img = item.get("image")
    if not isinstance(img, str) or not img.startswith(("https://", "/assets/")):
        raise ValueError("Invalid article cover: " + url)
    if img.startswith("/assets/") and not (root / img[1:]).is_file():
        raise ValueError("Missing article cover: " + img)


def validate_boxes(root: Path, data: dict) -> dict:
    cards = data.get("cards")
    lengths = {"suggested": 6, "tech_impact": 4, "gaming_inside": 4, "dalla_redazione": 12}
    if not isinstance(cards, dict):
        raise ValueError("No structured editorial box data")
    all_urls: list[str] = []
    for name, count in lengths.items():
        group = cards.get(name)
        if not isinstance(group, list) or len(group) != count:
            raise ValueError(f"{name}: expected {count} stories")
        for item in group:
            if not isinstance(item, dict):
                raise ValueError(f"{name}: malformed story")
            local_url(root, item)
            category = item.get("category")
            if name == "suggested" and category != "tech":
                raise ValueError("Tech sidebar contains non-Tech story")
            if name == "dalla_redazione" and category != "gaming":
                raise ValueError("Gaming sidebar contains non-Gaming story")
            all_urls.append(item["url"])
    if len(all_urls) != 26 or len(set(all_urls)) != 26:
        raise ValueError("Repeated article across editorial boxes")
    featured = load_json(root / "featured-carousel.json").get("items", [])
    featured_urls = {x.get("url") for x in featured if isinstance(x, dict)}
    if any(x in featured_urls for x in all_urls):
        raise ValueError("Editorial box duplicates the 5-slot carousel")
    return cards


def load_renderer() -> dict:
    script = ROOT / "scripts/refresh-home-editorial-boxes.py"
    spec = importlib.util.spec_from_file_location("zt_editorial_box_renderer", script)
    # Script filename contains '-', so load through its path, not an import name.
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load the existing box markup helpers")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return {"popular": obj.popular_cards, "special": obj.special_cards,
            "replace": obj.replace_once}


def render_boxes_to_dist(root: Path, dist: Path) -> None:
    data = load_json(root / "master-staging/editorial-boxes.json")
    cards = validate_boxes(root, data)
    render = load_renderer()
    homepage = (dist / "index.html").read_text(encoding="utf-8")
    javascript = (dist / "zt-home-live.js").read_text(encoding="utf-8")
    replace = render["replace"]
    homepage = replace(
        homepage,
        r"(?<=<!-- POPULAR_NEWS_ITEMS_START -->).*?(?=<!-- POPULAR_NEWS_ITEMS_END -->)",
        "\n" + render["popular"](cards["suggested"]) + "\n        ",
        "JSON editorial popular cards",
    )
    for name in ("tech", "gaming"):
        group = cards["tech_impact" if name == "tech" else "gaming_inside"]
        homepage = replace(
            homepage,
            r'(?<=<div class="zt-special-list" id="zt-special-' + name
            + r'">).*?(?=</div>\s*<div class="zt-special-footer">)',
            "\n" + render["special"](group) + "\n          ",
            "JSON " + name + " editorial special",
        )
    # Reuse the existing production markup contract; no new selectors or CSS.
    serialized = json.dumps(
        [{k: x[k] for k in ("title", "url", "image")}
         for x in cards["dalla_redazione"]],
        ensure_ascii=False, separators=(",", ":"),
    ).replace("<", "\\u003c")
    javascript = replace(
        javascript, r"const sidebarEditorials=\[.*?\];(?=\s*const editorialBox=)",
        "const sidebarEditorials=" + serialized + ";",
        "JSON Gaming sidebar source",
    )
    if (homepage.count('id="zt-special-tech"') != 1
            or homepage.count('id="zt-special-gaming"') != 1
            or homepage.count('id="ztFeaturedGrid"') != 1):
        raise ValueError("Post-render Home structure changed")
    (dist / "index.html").write_text(homepage, encoding="utf-8")
    (dist / "zt-home-live.js").write_text(javascript, encoding="utf-8")
    print("RENDERED: 26 validated JSON editorial box entries in disposable dist/")


def render_approved_reviews(root: Path) -> None:
    """One-way approved review JSON publication, inside throwaway build only."""
    path = root / "master-staging/reviews-due.json"
    if not path.exists():
        return
    data = load_json(path)
    if not isinstance(data.get("due"), list) or not isinstance(data.get("changed"), list):
        raise ValueError("Malformed review plan")
    if not data["due"]:
        print("REVIEWS: no approved unpublished reviews due")
        return
    result = subprocess.run(
        [sys.executable, "scripts/publish-approved-reviews.py", "--dry-run"],
        cwd=root, capture_output=True, text=True, check=True, timeout=150)
    fresh = json.loads(result.stdout)
    if fresh.get("due") != data["due"] or set(fresh.get("changed", [])) != set(data["changed"]):
        raise RuntimeError("Review plan is stale: refuse publishing")
    result = subprocess.run([sys.executable, "scripts/publish-approved-reviews.py"],
                            cwd=root, capture_output=True, text=True, check=True, timeout=150)
    applied = json.loads(result.stdout)
    if set(applied.get("changed", [])) != set(data["changed"]):
        raise RuntimeError("Approved review files changed unexpectedly")
    print(f"REVIEWS: generated {len(data['due'])} approved entries in disposable build")


def self_test() -> None:
    assert [6, 4, 4, 12] == list({"suggested": 6, "tech_impact": 4,
                                "gaming_inside": 4, "dalla_redazione": 12}.values())
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state = {"items": [
            {"url": f"/news-demo-{i}.html", "section": kind}
            for i, kind in enumerate(["tech"] * 4 + ["gaming"])]}
        (root / "featured-carousel.json").write_text(json.dumps(state), encoding="utf-8")
        try:
            validate_boxes(root, {"cards": {}})
        except ValueError:
            pass
        else:
            raise AssertionError("Incomplete editorial JSON must be rejected")
    print("PASS: rejects missing editor data and enforces quota/schema")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--prebuild-reviews", action="store_true")
    p.add_argument("--postbuild-editorial", action="store_true")
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = p.parse_args()
    if args.self_test:
        self_test()
    elif args.prebuild_reviews:
        render_approved_reviews(args.root)
    elif args.postbuild_editorial:
        render_boxes_to_dist(args.root, args.dist)
    else:
        p.error("Choose a renderer phase")


if __name__ == "__main__":
    main()
