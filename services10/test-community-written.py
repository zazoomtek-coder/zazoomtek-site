#!/usr/bin/env python3
"""Written Community regression: source metadata, photos, categories and uniqueness."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent

def importer(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/filename)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

source=importer("community_source","01-community.py")
pages=importer("community_pages","03-home.py")

def main():
    posts={"contents":{"group":[
        {"backstagePostRenderer":{
          "postId":"UgkxNewWritten001",
          "contentText":{"runs":[{"text":"News Tech: Nuovo smartphone Zazoom\n"},
                                  {"text":"Testo completo del nuovo prodotto.\n\n"},
                                  {"text":"Seconda sezione editoriale.\n"},
                                  {"text":"🌐 zazoomtek.it"}]},
          "publishedTimeText":{"simpleText":"2 ore fa"},
          "backstageAttachment":{"postMultiImageRenderer":{
             "images":[
                {"thumbnails":[{"url":"https://yt3.ggpht.com/img1=s320-c-fcrop64=abc","width":320,"height":180},
                                {"url":"https://yt3.ggpht.com/img1=s800-c-fcrop64=abc","width":800,"height":450}]},
                {"thumbnails":[{"url":"https://yt3.ggpht.com/img2=s360","width":360,"height":360}]}]}}}},
        {"backstagePostRenderer":{
          "postId":"UgkxNewsGaming002",
          "contentText":{"simpleText":"News Gaming: Avventura su PS5\nParagrafo originale."},
          "publishedTimeText":{"simpleText":"ieri"}}},
        {"backstagePostRenderer":{
          "postId":"UgkxPollNoText03","backstageAttachment":{"pollRenderer":{"choices":[]}}}}
    ]}}
    found=source.extract("var ytInitialData = "+json.dumps(posts)+";")
    assert len(found)==2
    article=next(p for p in found if p["id"]=="UgkxNewWritten001")
    assert len(article["images"])==2
    assert article["image"].endswith("=s1600-rw-nd-v1")
    assert article["published_iso"]
    assert article["text"].startswith("News Tech:")
    assert source.extract("var ytInitialData = {malformed")==[]
    previous=[{**article,"first_seen":"2026-10-20T09:00:00Z",
               "published_iso":"2026-10-20T07:00:00Z"}]
    merged=source.merge(previous,found)
    assert len(merged)==2
    same=next(x for x in merged if x["id"]=="UgkxNewWritten001")
    assert same["first_seen"]=="2026-10-20T09:00:00Z"
    assert same["published_iso"]=="2026-10-20T07:00:00Z"

    with TemporaryDirectory() as d:
        root=Path(d)
        data=root/"services10-data"
        data.mkdir()
        (data/"community.json").write_text(json.dumps(merged),encoding="utf-8")
        (root/"home-video-feed.json").write_text("[]",encoding="utf-8")
        (root/"index.html").write_text(
             "<!doctype html><html><body><!-- ARTICLE_FEED_START -->"
             "<article class=\"article-row\"></article>"
             "<!-- ARTICLE_FEED_END --></body></html>",encoding="utf-8")
        (root/"news.html").write_text(
             '<html><body><article class="news-row"></article></body></html>',
             encoding="utf-8")
        output=pages.update(root)
        assert output["posts"]==2
        generated=root/"news-UgkxNewWritten001.html"
        html=generated.read_text(encoding="utf-8")
        assert "<h1>Nuovo smartphone Zazoom</h1>" in html
        assert html.count('class="zt-community-gallery"')==1
        assert 'name="description"' in html
        assert 'article:published_time' in html
        assert "🌐 zazoomtek.it" not in html
        assert pages.classify({"text":"News Gaming: PS5"})=="gaming"
        assert pages.classify({"text":"News Tech: Smartphone"})=="tech"
        assert pages.classify({"text":"News Extra: Altro"})=="extra"
        assert (root/"news-UgkxNewsGaming002.html").is_file()
        before=generated.read_bytes()
        output=pages.update(root)
        assert output["created_pages"]==0
        assert generated.read_bytes()==before
        home=(root/"index.html").read_text(encoding="utf-8")
        assert home.count("/news-UgkxNewWritten001.html")>=1
    print("PASS: written YouTube Community preserves text, dates, photos, routing; no duplicate pages")

if __name__=="__main__":
    main()
