#!/usr/bin/env python3
"""Package the current ZazoomTek visual/content snapshot without a Master.

Only public HTML, CSS, JS, images, fonts, media metadata and selected public
site manifests enter dist/. Development scripts, caches and secrets never do.
The original files are not rewritten and their exact bytes are preserved.
"""
from __future__ import annotations
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"dist"
PUBLIC_EXT={".html",".css",".js",".png",".jpg",".jpeg",".webp",".gif",
            ".svg",".ico",".avif",".woff",".woff2",".ttf",".otf",
            ".webmanifest",".txt",".xml",".webm",".mp4",".vtt",".srt"}
PUBLIC_MANIFESTS={
    "featured-carousel.json","home-video-feed.json","notizie-dal-web.json",
    "robots.txt","sitemap.xml","manifest.json","site.webmanifest",
    "zt-release-status.json","_headers","_redirects","_routes.json"}
EXCLUDE_DIRS={".git",".github",".venv","venv","node_modules","dist",
    "scripts","services10","services10-data","master-staging","tests",
    "test","backup","backups","__pycache__","tmp",".pytest_cache"}
EXCLUDE_FILES={".env",".env.local",".gitignore",".gitattributes"}

def is_public(path:Path,root:Path=ROOT)->bool:
    relative=path.relative_to(root)
    if any(piece in EXCLUDE_DIRS or piece.startswith(".") for piece in relative.parts[:-1]):
        return False
    if path.name in EXCLUDE_FILES or path.name.startswith("."):
        return False
    if path.name in PUBLIC_MANIFESTS:
        return True
    if path.suffix.lower() not in PUBLIC_EXT:
        return False
    return True

def build(root:Path=ROOT,out:Path|None=None)->dict:
    root=root.resolve()
    destination=(out if out is not None else root/"dist").resolve()
    if destination==root or root not in destination.parents:
        # Keep output under this checkout so no arbitrary directory is cleared.
        raise ValueError("Output must be a child of the source checkout")
    destination.mkdir(parents=True,exist_ok=True)
    count=0
    for candidate in root.rglob("*"):
        if not candidate.is_file() or candidate.is_symlink():
            continue
        if destination in candidate.parents:
            continue
        if not is_public(candidate,root):
            continue
        target=destination/candidate.relative_to(root)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(candidate,target)
        count+=1
    return {"files":count,
            "home":(destination/"index.html").is_file(),
            "news":(destination/"news.html").is_file(),
            "studio":(destination/"studio"/"index.html").is_file(),
            "watch":(destination/"watch"/"index.html").is_file()}

if __name__=="__main__":
    result=build()
    print("Independent static site package:",result)
