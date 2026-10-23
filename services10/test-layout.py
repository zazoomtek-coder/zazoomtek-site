#!/usr/bin/env python3
"""Offline Home graphic regression: popular eight cards, web news as screenshot hero plus four."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

popular=load("popular","05-da-non-perdere.py")
web=load("web","06-notizie-web.py")

def main():
    with TemporaryDirectory() as folder:
        directory=Path(folder)
        homepage=directory/"index.html"
        rows=[]
        for n in range(10):
            rows.append(f'<article class="article-row" data-post-category="tech">'
                f'<a href="news-{n}.html"><img class="article-image" src="/assets/{n}.webp"></a>'
                f'<div class="article-copy"><h3><a href="news-{n}.html">Tech {n}</a></h3></div></article>')
        homepage.write_text(
            '<html><head><title>ZazoomTek</title></head><body>'
            '<div id="unchanged">KEEP THIS</div>'
            '<!-- ARTICLE_FEED_START -->'+''.join(rows)+'<!-- ARTICLE_FEED_END -->'
            '<!-- POPULAR_NEWS_ITEMS_START --><a class="zt-popular-article" href="/old.html">'
            'old</a><!-- POPULAR_NEWS_ITEMS_END -->'
            '<section id="zt-webnews-home"><p>Previous 2-column layout</p></section>'
            '</body></html>',encoding="utf-8")
        assert popular.update(directory)==8
        result=homepage.read_text(encoding="utf-8")
        box=result.split(popular.START,1)[1].split(popular.END,1)[0]
        assert box.count('class="zt-popular-article"')==8
        assert 'id="zt-services10-popular-eight"' in result
        assert ':nth-of-type(-n+8)' in result and ':nth-of-type(n+9)' in result
        assert 'KEEP THIS' in result
        assert popular.update(directory)==8
        result=homepage.read_text(encoding="utf-8")
        assert result.count('id="zt-services10-popular-eight"')==1

        stories=[{"url":f"https://example.org/news-{n}",
                  "image":f"/assets/notizie-dal-web/{n}.webp",
                  "original_title":f"News {n}","source":"SmartWorld",
                  "excerpt":f"Description {n}"} for n in range(5)]
        (directory/"notizie-dal-web.json").write_text(
            json.dumps({"items":stories}),encoding="utf-8")
        assert web.update(directory)==5
        updated=homepage.read_text(encoding="utf-8")
        section=updated.split('<section id="zt-webnews-home"',1)[1].split('</section>',1)[0]
        assert section.count('class="zt-webnews-item"')==5
        assert 'Description 0' in section
        assert 'VEDI TUTTE' in section
        assert (directory/"notizie-dal-web.html").is_file()
        assert 'grid-row:1 / span 4' in updated
        assert 'getElementById("zt-home-shelves")' in updated
        assert updated.count('id="zt-services10-webnews-layout"')==1
        assert updated.count('id="zt-services10-webnews-place"')==1
        assert 'KEEP THIS' in updated
        assert web.update(directory)==5
        updated=homepage.read_text(encoding="utf-8")
        assert updated.count('id="zt-services10-webnews-layout"')==1
        assert updated.count('id="zt-services10-webnews-place"')==1
    print("PASS: Home layout remains intact; eight Tech cards and web news 1+4 with editorial archive")

if __name__=="__main__":
    main()
