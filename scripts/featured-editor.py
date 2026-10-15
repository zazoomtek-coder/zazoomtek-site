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
QUOTA=("tech","tech","tech","gaming","tech-impact","gaming-inside")

def load_matcher():
    p=ROOT/"scripts/trending-crosscheck.py"
    spec=importlib.util.spec_from_file_location("zt_matcher",p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def validate():
    items=json.loads((ROOT/"featured-carousel.json").read_text(encoding="utf-8"))["items"]
    assert tuple(x["section"] for x in items)==QUOTA
    assert len(set(x["url"] for x in items))==6
    for row in items:
        assert (ROOT/row["url"].lstrip("/")).is_file(),row["url"]
        if row["image"].startswith("/"):
            assert (ROOT/row["image"].lstrip("/")).is_file(),row["image"]
    return items

def candidate_specials(mod):
    """Only request replacement reporting for timely, distinct policy leads.

    An existing special article remains in place if no stronger lead is
    available; the downstream special desk checks original sources and dates.
    """
    now=dt.datetime.now(dt.timezone.utc)
    cache=ROOT/"trending-sources.json"
    if not cache.is_file():return []
    source=json.loads(cache.read_text(encoding="utf-8")).get("items",[])
    current=validate()
    candidate_sections=set()
    for s in source:
        if not s.get("homepage") or int(s.get("rank",99))>10:continue
        section=mod.classify(s.get("title",""),s.get("kind",""))
        if section not in ("tech-impact","gaming-inside"):continue
        last=s.get("last_seen")
        try:seen=dt.datetime.fromisoformat(last)
        except (ValueError,TypeError):continue
        if seen.tzinfo is None:continue
        if not dt.timedelta(0)<=now-seen<=dt.timedelta(hours=5):continue
        incumbent=next(x for x in current if x["section"]==section)
        if mod.similarity(s.get("title",""),incumbent["title"])>.50:continue
        candidate_sections.add(section)
    return sorted(candidate_sections)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--test",action="store_true")
    parser.add_argument("--apply",action="store_true")
    a=parser.parse_args()
    mod=load_matcher()
    if a.test:
        mod.selftest()
        validate()
        print("Featured editor: 3 technology, 1 gaming, 1 Impact, 1 Inside; six unique valid destinations")
        return
    if a.apply:
        mod.apply()
        validate()
        candidates=candidate_specials(mod)
        print("Special replacements to investigate:",", ".join(candidates) or "none")
        out=__import__("os").environ.get("GITHUB_OUTPUT")
        if out:
            with open(out,"a",encoding="utf-8") as f:f.write("special_research="+str(bool(candidates)).lower()+"\n")
                f.write("special_sections="+",".join(candidates)+"\n")
        return
    parser.error("Choose --apply or --test")

if __name__=="__main__":main()
