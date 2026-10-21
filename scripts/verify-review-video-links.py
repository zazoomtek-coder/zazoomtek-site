#!/usr/bin/env python3
"""Fail closed if a review banner links a non-review or the wrong YouTube video."""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VALID=json.loads((ROOT/"home-video-feed.json").read_text(encoding="utf-8"))
VIDEOS={str(v.get("id")) for v in VALID if
        v.get("category")=="recensioni" and v.get("short") is False
        and v.get("live") is False
        and (re.search(r"recension|review",str(v.get("title","")),re.I)
             or str(v.get("id"))=="XrXF0t5OPtU")}
EXPECTED={
 "thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html":"e7rAYQprXTM",
 "sesame-street-amici-e-risate-recensione-ps5.html":"WwGAaKGfoGY",
 "recensione-Ugkx1MzCpfD6F193kzdDtyqQU2ErUHi6FEu1.html":"fKiuvUW5eKI",
 "recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html":"by7Qm_XFO8c",
 "recensione-UgkxPQVLBegGEPWvHmDjVq-rA5b8EwFeFrtk.html":"RtHYQ7o5Gws",
 "recensione-Ugkxq4wPsbAKxSo1aB0OptleaGIR5iyfIuyz.html":"hp6JW2xqa9Y",
 "recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html":"XrXF0t5OPtU",
 "recensione-UgkxUyzI3zn3urxvkpRPcd349swqkNqHFXEK.html":"X5qvA6u5lvo",
}
NO_VIDEO=("poly-fighter-recensione-pc.html",
          "recensione-Ugkxvpi4bKV_hiuDy7XJQb0-qw7CTJc5Is33.html")
def main():
    total=0
    for path in sorted(ROOT.glob("*.html")):
        if "recensione" not in path.name or path.name.startswith("recensioni-scritte"):
            continue
        doc=path.read_text(encoding="utf-8")
        # Support the existing link card and the official lazy YouTube embed.
        # Marker counts, video identity and duplicate detection remain strict.
        blocks=re.findall(
            r'<!-- ZT_REVIEW_VIDEO_START -->(.*?)<!-- ZT_REVIEW_VIDEO_END -->',
            doc, re.S)
        if (len(blocks)>1 or doc.count("ZT_REVIEW_VIDEO_START")!=len(blocks)
                or doc.count("ZT_REVIEW_VIDEO_END")!=len(blocks)):
            raise RuntimeError("Invalid or duplicate video banner: "+path.name)
        ids=[]
        for block in blocks:
            embed_ids=re.findall(
                r'https://www[.]youtube-nocookie[.]com/embed/([A-Za-z0-9_-]{11})',
                block)
            link_ids=re.findall(
                r'https://www[.]youtube[.]com/watch[?]v=([A-Za-z0-9_-]{11})',
                block)
            references=embed_ids+link_ids
            if (not references or len(set(references))!=1
                    or len(embed_ids)>1 or len(link_ids)>1
                    or 'zt-review-video-banner' not in block):
                raise RuntimeError("Mismatched or incomplete YouTube review player: "+path.name)
            ids.append(references[0])
        if any(vid not in VIDEOS for vid in ids):
            raise RuntimeError("Video is not a verified ZazoomTek REVIEW: "+path.name)
        if path.name in EXPECTED and EXPECTED[path.name] in VIDEOS:
            if ids!=[EXPECTED[path.name]]:
                raise RuntimeError("Review page has wrong YouTube video: "+path.name)
        if path.name in NO_VIDEO and ids:
            raise RuntimeError("Unverified video added to article: "+path.name)
        total+=len(ids)
    expected_available=sum(vid in VIDEOS for vid in EXPECTED.values())
    if total < expected_available:
        raise RuntimeError("Previously verified ZazoomTek video reviews missing")
    css=(ROOT/"zt-design.css").read_text(encoding="utf-8")
    if ".zt-review-video-banner" not in css:
        raise RuntimeError("Review video banner styling missing")
    print(f"PASS: {total} video-review banners, exclusively verified ZazoomTek reviews")
if __name__=="__main__":
    main()
