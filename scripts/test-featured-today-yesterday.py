#!/usr/bin/env python3
"""Featured stories survive idle days; only newer verified posts replace them."""
from __future__ import annotations
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("zt_news_persistent", ROOT/"scripts/trending-crosscheck.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def story(root,slug,day,kind,score=0,matched=False):
    url="/news-"+slug+".html"
    (root/url[1:]).write_text("<html>Verified published article</html>",encoding="utf-8")
    title=("Smartphone Tech "+slug if kind=="tech" else "Nintendo Switch gioco Zelda "+slug)
    return {"url":url,"title":title,"section":kind,
            "image":"https://images.example.com/thumb.jpg",
            "published_date":day,"trend_score":score,"freshness":score,
            "match_count":1 if matched else 0,"matched_sources":[],"summary":""}

def blocked(callback):
    try:
        callback()
    except RuntimeError:
        return
    raise AssertionError("Partial or invalid featured update must be rejected")

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
            assert len(selected)==5 and mod.valid_featured_sections(selected)
            assert [x["section"] for x in selected]==["tech"]*4+["gaming"]
            assert all(x["published_date"]=="2026-10-16" for x in selected)
            assert selected[-1]["url"]==today_g["url"]
            assert len({x["url"] for x in selected})==5

            # Publication ages are never a reason to erase the last five cards.
            # Future-dated test fixtures do NOT stand for a publication event.
            # When there are no new posts, the original eligible archive stays unchanged.
            idle_candidates=[x for x in candidates if x is not future]
            after_ten_days=mod.pick(idle_candidates,on_date=reference+dt.timedelta(days=10))
            assert [x["url"] for x in after_ten_days]==[x["url"] for x in selected]
            after_thirty_days=mod.pick(idle_candidates,on_date=reference+dt.timedelta(days=30))
            assert [x["url"] for x in after_thirty_days]==[x["url"] for x in selected]

            # Four Tech can span three days and still fill the approved mosaic.
            fallback=mod.pick([*yesterday,yesterday_g,old],on_date=reference)
            assert len(fallback)==5 and fallback[-1]["url"]==yesterday_g["url"]
            assert old["url"] in {x["url"] for x in fallback}
            assert mod.allowed_featured_date({"published_date":"2026-10-14"},reference)
            assert not mod.allowed_featured_date({"published_date":""},reference)
            assert not mod.allowed_featured_date({"published_date":"2026-10-17"},reference)
            assert mod.local_publication_date({"published_at":"2026-10-15T23:50:00Z"})==reference
            blocked(lambda: mod.pick([old,future,unknown],on_date=reference))

            # The actual timestamp of a published article overrides a stale
            # or misleading archive date, but age alone does not disqualify it.
            actual_old=story(root,"tech-real-date","2026-10-15","tech",1000)
            (root/actual_old["url"][1:]).write_text(
                '<meta property="article:published_time" content="2026-10-14T16:07:27Z">',encoding="utf-8")
            assert mod.allowed_featured_date(actual_old,reference)
            assert actual_old["url"] in {x["url"] for x in
                mod.pick([*yesterday,actual_old,yesterday_g],on_date=reference)}

            # Insufficient Tech stories MUST NOT replace old valid carousel with
            # fewer cards or fill missing Tech slots with additional Gaming.
            more_gaming=[story(root,"game-fill-"+str(i),"2026-10-16","gaming",i) for i in range(3)]
            blocked(lambda: mod.pick(yesterday[:2]+[today_g,yesterday_g,*more_gaming],on_date=reference))
            assert not mod.valid_featured_sections([{"section":"gaming"}]*2)

            # Among the newest publication day, verified matching coverage on
            # independent major sites takes priority over non-matching news.
            trend=story(root,"tech-viral","2026-10-16","tech",score=90,matched=True)
            unmatched=story(root,"tech-unmatched","2026-10-16","tech",score=0)
            same_day=mod.pick([*today[:3],unmatched,trend,today_g],on_date=reference)
            assert trend["url"] in {x["url"] for x in same_day}
            assert unmatched["url"] not in {x["url"] for x in same_day}
            assert same_day[0]["url"]==trend["url"]
            assert same_day[-1]["section"]=="gaming"
        finally:
            mod.ROOT=saved
    print("PASS: featured five persist for 10/30 days without new posts.")
    print("PASS: 4 Tech + 1 Gaming, no future dates, matching viral stories prioritized.")

if __name__=="__main__":
    main()
