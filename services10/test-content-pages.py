#!/usr/bin/env python3
"""Offline regression: incremental Community pages and independent review indexes."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parent
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,HERE/filename)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
home=load("zazoom_community_publisher","03-home.py")
reviews=load("zazoom_reviews_publisher","07-recensioni.py")

def post(i,section="tech"):
    return {"id":"UgkxABCDEF"+str(i),"text":"News "+section.title()+": Nuova notizia "+str(i)+
            "\n\nDettaglio completo con informazioni accurate.",
            "first_seen":"2026-10-23T16:00:00+00:00",
            "image":"https://example.org/cover.jpg"}

def test_community(folder):
    root=Path(folder)
    (root/"services10-data").mkdir(exist_ok=True)
    (root/"index.html").write_text(
        '<html><head><title>Original Home</title></head><body><p>KEEP HOME</p>'
        '<!-- ARTICLE_FEED_START --><article class="article-row">Existing</article>'
        '<!-- ARTICLE_FEED_END --></body></html>',encoding="utf-8")
    (root/"news.html").write_text(
        '<html><body><p>KEEP NEWS</p>'
        '<article class="news-row">Existing</article></body></html>',encoding="utf-8")
    path=root/"services10-data"/"community.json"
    path.write_text(json.dumps([post(1),post(2,"gaming")]),encoding="utf-8")
    (root/"home-video-feed.json").write_text(json.dumps([
        {"id":"existing0001","title":"Older horizontal video",
         "publishedAt":"2026-10-20T12:00:00Z","short":False},
        {"id":"short00001","title":"Old Shorts",
         "publishedAt":"2026-10-20T11:00:00Z","short":True}]),encoding="utf-8")
    (root/"services10-data"/"videos.json").write_text(json.dumps([
        {"id":"newvideo001","title":"New video 16:9",
         "published":"2026-10-23T16:30:00Z","type":"landscape_video"},
        {"id":"vertical001","title":"Vertical not permitted",
         "published":"2026-10-23T16:30:00Z","type":"vertical_video"}]),encoding="utf-8")

    result=home.update(root)
    assert result["created_pages"]==2
    assert result["new_videos"]==1
    assert (root/"watch"/"newvideo001.html").exists()
    assert (root/"watch"/"index.html").exists()
    assert not (root/"watch"/"vertical001.html").exists()
    assert not (root/"watch"/"short00001.html").exists()
    video_feed=json.loads((root/"home-video-feed.json").read_text())
    assert {"newvideo001","existing0001","short00001"} == {
        entry["id"] for entry in video_feed}
    assert len(list(root.glob("news-Ugkx*.html")))==2
    assert "<h1>" in (root/"news-UgkxABCDEF1.html").read_text()
    assert 'rel="canonical"' in (root/"news-UgkxABCDEF1.html").read_text()
    first=(root/"index.html").read_text()
    assert first.count('class="article-row"')==3
    assert "KEEP HOME" in first
    assert (root/"news.html").read_text().count('class="news-row"')==3
    assert home.update(root)["created_pages"]==0
    assert first==(root/"index.html").read_text()
    path.write_text(json.dumps([post(1),post(2,"gaming"),post(3)]),encoding="utf-8")
    assert home.update(root)["created_pages"]==1
    updated=(root/"index.html").read_text()
    assert updated.count('class="article-row"')==4
    assert updated.count('href="/news-UgkxABCDEF1.html"')>0
    assert updated.count('href="/news-UgkxABCDEF3.html"')>0
    assert "Existing" in updated and "KEEP HOME" in updated
    assert (root/"news.html").read_text().count('class="news-row"')==4
    assert home.update(root)["created_pages"]==0

def test_reviews(folder):
    root=Path(folder)
    layout='<html><body><div id="original">KEEP REVIEWS</div><div class="news-list" id="reviewList">'\
           '<article class="news-row">Existing</article></div></body></html>'
    for filename in reviews.ARCHIVES:
        (root/filename).write_text(layout,encoding="utf-8")
    (root/"dashcam-recensione.html").write_text(
        '<html><head><meta property="og:image" content="/assets/dashcam.webp"></head>'
        '<body><main><h1>Dashcam Recensione 4K</h1>Test prodotto tech</main></body></html>')
    (root/"esempio-recensione-pc.html").write_text(
        '<html><body><main><h1>Gioco Recensione PC</h1>Gameplay su PC</main></body></html>')
    result=reviews.update(root)
    assert result["recensioni-tech.html"]==1
    assert result["recensioni-gaming.html"]==1
    assert result["recensioni-scritte.html"]==2
    before=(root/"recensioni-tech.html").read_text()
    assert "KEEP REVIEWS" in before
    assert "Dashcam Recensione 4K" in before
    assert "Gioco Recensione PC" not in before
    assert "Gioco Recensione PC" in (root/"recensioni-gaming.html").read_text()
    assert reviews.update(root)==result
    assert before==(root/"recensioni-tech.html").read_text()
    assert (root/"dashcam-recensione.html").is_file()

def main():
    with TemporaryDirectory() as temp:
        test_community(temp)
    with TemporaryDirectory() as temp:
        test_reviews(temp)
    print("PASS: Home Community incrementally updates without duplicate/lost pages; review indexes stay intact")

if __name__=="__main__":
    main()
