#!/usr/bin/env python3
"""Test Home highlights without publishing or touching the real Home."""
import importlib.util
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from tempfile import TemporaryDirectory

spec=importlib.util.spec_from_file_location("featured",Path(__file__).with_name("04-in-evidenza.py"))
featured=importlib.util.module_from_spec(spec)
spec.loader.exec_module(featured)

def article(category,index,date=None):
    title=f"Story {index}"
    date=date or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    return (f'<article class="news-row" data-post-category="{category}" '
            f'data-published-at="{date}T12:00:00Z">'
            f'<a href="/news-{index}.html"><img src="/assets/{index}.webp"></a>'
            f'<div class="news-copy"><h2><a href="/news-{index}.html">{title}</a></h2></div>'
            f'</article>')

def main():
    with TemporaryDirectory() as folder:
        root=Path(folder)
        before='<html><head><title>Unchanged</title></head><body><p>Keep design</p>'
        after='<div id="other-box">Keep content</div></body></html>'
        (root/"index.html").write_text(before+featured.START+'old cards'+featured.END+after)
        (root/"news.html").write_text(
            article("tech",1)+article("tech",2)+article("gaming",3)+
            article("tech",4)+article("tech",10,"2026-09-01")+article("news",9))
        old=[{"section":"tech","url":"/news-old.html","title":"Fallback Tech",
              "image":"/assets/old.webp"}]
        (root/"featured-carousel.json").write_text(json.dumps({"items":old}))
        assert featured.update(root)==4
        new=(root/"index.html").read_text()
        assert new.startswith(before) and new.endswith(after)
        assert new.count('class="zt-feature-card zt-feature-small"')==4
        assert new.count('data-feature-section="tech"')==3
        assert new.count('data-feature-section="gaming"')==1
        assert "Keep design" in new and "Keep content" in new
        manifest=json.loads((root/"featured-carousel.json").read_text())["items"]
        assert len(manifest)==4 and len({x["url"] for x in manifest})==4
        assert not any(x["url"] in ("/news-9.html","/news-10.html","/news-old.html") for x in manifest)
        assert featured.update(root)==4
    print("PASS: Featured recent unique Tech/Gaming without obsolete fallback")

if __name__=="__main__":
    main()
