#!/usr/bin/env python3
"""One-time restoration of bright, licensed featured-cover photos.

Rebuild the four standard and two selected special cover WebPs from the exact
Wikimedia Commons source files recorded in the existing provenance manifests.
Only the image bytes change: the homepage carousel, URLs and article copy stay
untouched. Skip later runs after a verified successful refresh.
"""
import importlib.util
import io
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = ROOT / ".featured-covers-original-light-v1.json"
STANDARD = json.loads((ROOT / "standard-news.json").read_text(encoding="utf-8"))["articles"]
SPECIAL = json.loads((ROOT / "approved-special-articles.json").read_text(encoding="utf-8"))["articles"]
STANDARD_MANIFEST = json.loads((ROOT / "standard-cover-manifest.json").read_text(encoding="utf-8"))["articles"]
SPECIAL_MANIFEST = json.loads((ROOT / "special-cover-manifest.json").read_text(encoding="utf-8"))["articles"]
spec = importlib.util.spec_from_file_location("zt_cover_builder", ROOT / "scripts/build-special-covers.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

# These were displayed with the black curtain baked into the picture.
SPECIAL_SLUGS = (
    ("tech", "ue-bulgaria-digital-services-act-controlli-piattaforme"),
    ("gaming", "eu-kids-act-giochi-online-minori-proposta-europea"),
)

def prepare(article, section, key, metadata):
    if metadata.get("origin", {}).get("origin") != "Wikimedia Commons":
        raise RuntimeError("Cannot recreate without original provenance: " + key)
    file_name = str(metadata["origin"].get("file") or "")
    if not file_name.startswith("File:"):
        raise RuntimeError("No verified Commons file for: " + key)
    target = ROOT / metadata["path"].lstrip("/")
    if not target.is_file():
        raise RuntimeError("Existing cover missing; refusing unexpected new files: " + str(target))
    # Explicit filename ensures the same photographic subject, not a new search result.
    item = {**article, "section": section, "cover_file": file_name[5:]}
    photo, rights = builder.commons_cc0(item)
    if photo is None or not rights:
        raise RuntimeError("Could not retrieve licensed original photo: " + key)
    if rights.get("file", "").removeprefix("File:") != file_name[5:]:
        raise RuntimeError("Unexpected Wikimedia file returned for: " + key)
    encoded = builder.encode(builder.render(item, photo))
    image = Image.open(io.BytesIO(encoded))
    if image.size != builder.SIZE or image.format != "WEBP" or len(encoded) > builder.MAX_BYTES:
        raise RuntimeError("Cover validation failed: " + key)
    return target, encoded, key

def main():
    standard_items = [x for x in STANDARD if x.get("kind") in ("tech", "gaming")]
    if len(standard_items) != 4:
        raise RuntimeError("Expected exactly four approved general news.")
    picked = []
    for article in standard_items:
        key = "standard/" + article["slug"]
        picked.append(prepare(article, article["kind"], key, STANDARD_MANIFEST[key]))
    for section, slug in SPECIAL_SLUGS:
        matches = [x for x in SPECIAL if x.get("section") == section and x.get("slug") == slug]
        if len(matches) != 1:
            raise RuntimeError("Missing unique approved special: " + slug)
        key = section + "/" + slug
        picked.append(prepare(matches[0], section, key, SPECIAL_MANIFEST[key]))
    if len(picked) != 6 or len({str(row[0]) for row in picked}) != 6:
        raise RuntimeError("Only six distinct covers may be modified.")
    if SENTINEL.exists():
        stamp = json.loads(SENTINEL.read_text(encoding="utf-8"))
        if stamp.get("version") == 1 and all(target.read_bytes() == data for target, data, _ in picked):
            print("All six featured covers are already restored.")
            return
    # Do not write anything until every cover has been successfully validated.
    for target, encoded, key in picked:
        target.write_bytes(encoded)
        print("Restored undarkened photograph:", key, len(encoded), "bytes")
    SENTINEL.write_text(json.dumps({
        "version": 1,
        "purpose": "Original-luminosity editorial photos; original lettering retained",
        "files": [str(target.relative_to(ROOT)) for target, _, _ in picked],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
