#!/usr/bin/env python3
"""No stale featured coverage: strictly today, then yesterday, then stop."""
from __future__ import annotations
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("zt_news_fresh", ROOT/"scripts/trending-crosscheck.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def story(root,slug,day,kind,score=0):
    url="/news-"+slug+".html"
    (root/url[1:]).write_text("<html>Verified published article</html>",encoding="utf-8")
    title=("Smartphone Tech "+slug if kind=="tech" else "Nintendo Switch gioco Zelda "+slug)
    return {"url":url,"title":title,"section":kind,
            "image":"https://images.example.com/thumb.jpg",
            "published_date":day,"trend_score":score,"freshness":score,
            "matched_sources":[],"summary":""}

def main():
    reference=dt.date(2026,10,16)
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        (root/"featured-editorial-pins.json").write_text('{"items":[]}',encoding="utf-8")
        (root/"manual-news.json").write_text('{"items":[]}',encoding="utf-8")
        (root/"standard-news.json").write_text('{"articles":[]}',encoding="utf-8")
        saved=mod.ROOT
        mod.ROOT=root
        try:
            today=[story(root,"tech-today-"+str(i),"2026-10-16","tech",i) for i in range(4)]
            yesterday=[story(root,"tech-yesterday-"+str(i),"2026-10-15","tech",100+i) for i in range(3)]
            yesterday_g=story(root,"game-yesterday","2026-10-15","gaming",100)
            today_g=story(root,"game-today","2026-10-16","gaming",1)
            old=story(root,"tech-old","2026-10-14","tech",1000)
            future=story(root,"tech-future","2026-10-17","tech",1000)
            unknown=story(root,"tech-undated","not-a-date","tech",1000)
            candidates=[old,future,unknown,*yesterday,today_g,*today,yesterday_g]
            selected=mod.pick(candidates,on_date=reference)
            assert len(selected)==6,selected
            assert [x["section"] for x in selected]==["tech"]*5+["gaming"]
            assert [x["published_date"] for x in selected[:5]]==["2026-10-16"]*4+["2026-10-15"]
            assert selected[5]["url"]==today_g["url"]
            assert mod.valid_featured_sections(selected)
            assert len({x["url"] for x in selected})==6

            only_yesterday=mod.pick(yesterday[:2]+[yesterday_g,old],on_date=reference)
            assert len(only_yesterday)==3,only_yesterday
            assert [x["section"] for x in only_yesterday]==["tech","tech","gaming"]
            assert all(x["published_date"]=="2026-10-15" for x in only_yesterday)

            assert mod.pick([old,future,unknown],on_date=reference)==[]
            assert mod.allowed_featured_date({"published_date":"2026-10-16"},reference)
            assert mod.allowed_featured_date({"published_date":"2026-10-15"},reference)
            assert not mod.allowed_featured_date({"published_date":"2026-10-14"},reference)
            assert not mod.allowed_featured_date({"published_date":""},reference)
            assert not mod.allowed_featured_date({"published_date":"2026-10-17"},reference)
            assert mod.local_publication_date({"published_at":"2026-10-15T23:50:00Z"})==reference
            assert not mod.valid_featured_sections([{"section":"gaming"}]*2)
        finally:
            mod.ROOT=saved
    print("PASS: Today's dates beat yesterday's even against higher trend score; no earlier fallback.")
    print("PASS: Fewer cards remain empty; unavailable, unknown and future dates are never promoted.")

if __name__=="__main__":
    main()
