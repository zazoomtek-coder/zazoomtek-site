#!/usr/bin/env python3
"""Add review-video banners ONLY when an official ZazoomTek review video exists.

Runs offline from the verified YouTube video import. Safe for repeated imports,
review edits, and every Cloudflare build. Never links trailers/gameplay/Shorts.
"""
from __future__ import annotations
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/"home-video-feed.json"
START="<!-- ZT_REVIEW_VIDEO_START -->"
END="<!-- ZT_REVIEW_VIDEO_END -->"
# Editorially checked alternative-language titles and one-word series.
# The referenced video MUST still exist in the official categorized video feed.
EXPLICIT={
  "70mai-a900-ultra-recensione-dual-4k.html":("3biZz45pUJs",("70mai","a900","ultra")),
  # Official ThermoMate 2500W review; never infer this link from a fuzzy title match.
  "thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html":("e7rAYQprXTM",("thermomate","2500w")),
  "sesame-street-amici-e-risate-recensione-ps5.html":("WwGAaKGfoGY",("sesame","street")),
  "recensione-Ugkx1MzCpfD6F193kzdDtyqQU2ErUHi6FEu1.html":("fKiuvUW5eKI",("walto",)),
}
IGNORE={"recensione","review","pc","ps5","ps4","xbox","playstation",
        "switch","console","test","italiano","ita","video","gaming",
        "il","lo","la","le","gli","di","da","del","della","per","con","una",
        "the","and","for","with","on","of","ed","in","su","edition"}
def normalize(value):
    value=unicodedata.normalize("NFKD",html.unescape(str(value))).casefold()
    value="".join(c for c in value if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+",value)
def keywords(value):
    return [w for w in normalize(value) if len(w)>=3 and w not in IGNORE]
def verified_videos():
    entries=json.loads(FEED.read_text(encoding="utf-8"))
    if not isinstance(entries,list):
        raise RuntimeError("Invalid official YouTube catalog")
    approved={}
    for video in entries:
        vid=str(video.get("id",""))
        if (video.get("category")=="recensioni" and video.get("short") is False
                and video.get("live") is False
                and re.fullmatch(r"[A-Za-z0-9_-]{11}",vid)):
            title=str(video.get("title",""))
            # A playlist category alone is not proof the upload is a review:
            # exclude previews, gameplay, trailers and unboxings.
            if re.search(r"recension|review",title,re.I) or vid=="XrXF0t5OPtU":
                approved[vid]=title
    return approved
def match_video(path,title,videos):
    if path.name in EXPLICIT:
        vid,required=EXPLICIT[path.name]
        title_words=set(normalize(videos.get(vid,"")))
        return vid if videos.get(vid) and set(required)<=title_words else None
    # Use the product/game title, not the review's subtitle or prose.
    identity=title.split("|",1)[0].split(" – ",1)[0].split(" — ",1)[0]
    tokens=set(keywords(identity))
    if len(tokens)<2:
        return None  # One vague word is not safe for automatic matching.
    matches=[vid for vid,video_title in videos.items()
             if tokens<=set(keywords(video_title))]
    return matches[0] if len(matches)==1 else None
def insert_banner(document,vid):
    pos=re.search(r'<img\b[^>]*\bclass="(?:hero|article-hero)"[^>]*>',document,re.I)
    if not pos:
        raise RuntimeError("Review lacks approved hero image placement")
    offset=pos.end()
    # Captions are part of the cover; put the CTA immediately below them.
    caption=re.match(r'\s*<(?:small|p)\b[^>]*class="(?:hero-caption|hero-cap)"[^>]*>.*?</(?:small|p)>',
                     document[offset:],re.S|re.I)
    if caption: offset+=caption.end()
    # Native, privacy-enhanced embed for an independently verified review video.
    # Lazy iframe loading avoids competing with the article's LCP image.
    banner=(f'\n{START}\n'
            '<section class="zt-review-video-banner" data-zt-review-video="1" '
            'aria-label="Videorecensione ufficiale ZazoomTek" '
            'style="max-width:960px;margin:18px auto 22px">'
            '<h2 style="margin:0 0 10px;font-size:1.15rem">Guarda la videorecensione</h2>'
            '<div style="width:100%;aspect-ratio:16/9;background:#101827">'
            f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
            'title="Videorecensione ufficiale ZazoomTek" '
            'loading="lazy" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin" '
            'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'style="display:block;width:100%;height:100%;border:0"></iframe></div>'
            f'<p><a href="https://www.youtube.com/watch?v={vid}" '
            'target="_blank" rel="noopener noreferrer">'
            'Apri la videorecensione su YouTube</a></p></section>\n'
            f'{END}\n')
    return document[:offset]+banner+document[offset:].lstrip()
def main():
    videos=verified_videos()
    changed=linked=unchanged=0
    for path in sorted(ROOT.glob("*.html")):
        if "recensione" not in path.name or path.name.startswith("recensioni-scritte"):
            continue
        source=path.read_text(encoding="utf-8")
        match=re.search(r'<h1\b[^>]*>(.*?)</h1>',source,re.S|re.I)
        if not match or not re.search(r'(?:Recensioni|recensioni-scritte\.html)',source,re.I):
            continue
        title=re.sub(r'<[^>]+>'," ",match.group(1))
        vid=match_video(path,html.unescape(title),videos)
        original=source
        # Remove only banners previously managed by this generator.
        source=re.sub(r'\s*'+re.escape(START)+r'.*?'+re.escape(END)+r'\s*',
                      "",source,flags=re.S)
        if vid:
            source=insert_banner(source,vid)
            linked+=1
        if source!=original:
            path.write_text(source,encoding="utf-8")
            changed+=1
        else:
            unchanged+=1
    print(f"REVIEW VIDEO LINKS: {linked} verified review videos; "
          f"{changed} pages updated; {unchanged} pages unchanged")
if __name__=="__main__":
    main()
