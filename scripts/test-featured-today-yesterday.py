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
            assert len(selected)==5,selected
            assert sorted(x["section"] for x in selected)==["gaming"]+["tech"]*4
            assert [x["published_date"] for x in selected[:5]]==["2026-10-16"]*5
            assert today_g["url"] in {x["url"] for x in selected}
            assert selected[-1]["published_date"]=="2026-10-16"
            assert mod.valid_featured_sections(selected)
            assert len({x["url"] for x in selected})==5

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
            # Reject stale articles even if an archive card falsely says "yesterday".
            stale_page=story(root,"tech-false-yesterday","2026-10-15","tech",1000)
            (root/stale_page["url"][1:]).write_text(
                '<meta property="article:published_time" content="2026-10-14T16:07:27Z">',encoding="utf-8")
            assert not mod.allowed_featured_date(stale_page,reference)
            assert stale_page["url"] not in {x["url"] for x in mod.pick([stale_page],on_date=reference)}

            # When fewer true Tech are available, real Gaming posts fill gaps.
            more_gaming=[story(root,"game-fill-"+str(i),"2026-10-16","gaming",i) for i in range(3)]
            selection=mod.pick(yesterday[:2]+[today_g,yesterday_g,*more_gaming],on_date=reference)
            assert len(selection)==5,selection
            assert [x["section"] for x in selection].count("tech")==2
            assert [x["section"] for x in selection].count("gaming")==3
            assert all(x["published_date"]=="2026-10-16" for x in selection[:3])
            assert all(x["published_date"]=="2026-10-15" for x in selection[-2:])
            assert mod.valid_featured_sections(selection)
            assert not mod.valid_featured_sections([{"section":"gaming"}]*6)

            # Chronological publication time within the same day, not trend score.
            timed_new=story(root,"tech-later","2026-10-16","tech",score=0)
            timed_old=story(root,"tech-earlier","2026-10-16","tech",score=120)
            (root/timed_new["url"][1:]).write_text(
                '<meta property="article:published_time" content="2026-10-16T11:30:00Z">',encoding="utf-8")
            (root/timed_old["url"][1:]).write_text(
                '<meta property="article:published_time" content="2026-10-16T09:00:00Z">',encoding="utf-8")
            ordered=mod.pick([timed_old,timed_new],on_date=reference)
            assert [x["url"] for x in ordered]==[timed_new["url"],timed_old["url"]],ordered
        finally:
            mod.ROOT=saved
    print("PASS: Today's dates beat yesterday's even against higher trend score; no earlier fallback.")
    print("PASS: Gaming fallback fills at most five when fresh Technology news are scarce; correct publication-hour order.")

if __name__=="__main__":
    main()
