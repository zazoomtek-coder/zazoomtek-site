#!/usr/bin/env python3
"""Test Home highlights without publishing or touching the real Home."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

spec=importlib.util.spec_from_file_location("featured",Path(__file__).with_name("04-in-evidenza.py"))
featured=importlib.util.module_from_spec(spec)
spec.loader.exec_module(featured)

def article(category,index):
    title=f"Story {index}"
    return (f'<article class="news-row" data-post-category="{category}" '
            f'data-published-at="2026-10-23T12:00:00Z">'
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
            article("tech",4)+article("news",9))
        old=[{"section":"tech","url":"/news-old.html","title":"Fallback Tech",
              "image":"/assets/old.webp"}]
        (root/"featured-carousel.json").write_text(json.dumps({"items":old}))
        assert featured.update(root)==5
        new=(root/"index.html").read_text()
        assert new.startswith(before) and new.endswith(after)
        assert new.count('class="zt-feature-card zt-feature-small"')==5
        assert new.count('data-feature-section="tech"')==4
        assert new.count('data-feature-section="gaming"')==1
        assert "Keep design" in new and "Keep content" in new
        manifest=json.loads((root/"featured-carousel.json").read_text())["items"]
        assert len(manifest)==5 and len({x["url"] for x in manifest})==5
        assert not any(x["url"]=="/news-9.html" for x in manifest)
        assert featured.update(root)==5
    print("PASS: Featured 4 Tech + 1 Gaming without altering adjacent Home layout")

if __name__=="__main__":
    main()
