#!/usr/bin/env python3
"""Single entry point for the ZazoomTek six-slot featured editor.

Owns only the carousel selection. Reuses verified published articles, never
copies source content, never changes article publication dates or archives.
Special stories use the existing source-verification and licensed-cover desk,
and are requested only when a fresh replacement candidate exists.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
QUOTA=None  # Categories are computed from editor pins, not fixed slots.

def load_matcher():
    p=ROOT/"scripts/trending-crosscheck.py"
    spec=importlib.util.spec_from_file_location("zt_matcher",p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def validate():
    items=json.loads((ROOT/"featured-carousel.json").read_text(encoding="utf-8"))["items"]
    assert [x["section"] for x in items]==load_matcher().expected_featured_sections()
    assert len(set(x["url"] for x in items))==6
    for row in items:
        assert (ROOT/row["url"].lstrip("/")).is_file(),row["url"]
        if row["image"].startswith("/"):
            assert (ROOT/row["image"].lstrip("/")).is_file(),row["image"]
    return items

def candidate_specials(mod):
    """Automatic Tech Impact/Gaming Inside story research is disabled by policy."""
    return []

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--test",action="store_true")
    parser.add_argument("--apply",action="store_true")
    a=parser.parse_args()
    mod=load_matcher()
    if a.test:
        mod.selftest()
        validate()
        print("Featured editor: 5 technology, 1 gaming by default; manual pins only")
        return
    if a.apply:
        mod.apply()
        validate()
        candidates=candidate_specials(mod)
        print("Special replacements to investigate:",", ".join(candidates) or "none")
        out=__import__("os").environ.get("GITHUB_OUTPUT")
        if out:
            with open(out,"a",encoding="utf-8") as f:
                f.write("special_research="+str(bool(candidates)).lower()+"\n")
                f.write("special_sections="+",".join(candidates)+"\n")
        return
    parser.error("Choose --apply or --test")

if __name__=="__main__":main()
