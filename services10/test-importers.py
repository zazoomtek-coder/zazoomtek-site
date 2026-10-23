#!/usr/bin/env python3
"""Regression tests for independently running YouTube collectors; no network."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

community=load("community", "01-community.py")
videos=load("videos", "02-video-shorts.py")

def main():
    xml=b'''<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
    <entry><yt:videoId>good1</yt:videoId><title>Recensione completa</title><published>2026-10-23T12:00:00Z</published></entry>
    <entry><yt:videoId>bad</yt:videoId><title>Corrotto</title></entry>
    <entry><yt:videoId>good2</yt:videoId><title>Test video</title><published>2026-10-23T13:00:00Z</published></entry>
    </feed>'''
    assert [x["id"] for x in videos.collect(xml)]==["good1","good2"]
    old=[{"id":"prior","title":"Old","published":"2026-10-22T00:00:00Z"}]
    combined=videos.merge(old,videos.collect(xml))
    assert len(combined)==3
    assert combined[0]["id"]=="good2"
    post_page='var ytInitialData = {"contents":{"a":{"backstagePostRenderer":{"postId":"Ugkx123","contentText":{"runs":[{"text":"Notizia tech"}]}}},"b":{"backstagePostRenderer":{"postId":"bad"}}}};'
    parsed=community.extract(post_page)
    assert len(parsed)==1 and parsed[0]["id"]=="Ugkx123"
    assert len(community.merge(parsed,parsed))==1
    with TemporaryDirectory() as folder:
        videos.OUT=Path(folder)/"videos.json"
        videos.save(combined)
        assert videos.OUT.is_file()
        assert len(__import__("json").loads(videos.OUT.read_text()))==3
    print("PASS: faulty item ignored, other items imported, previous archive retained and deduplicated")
if __name__=="__main__":
    main()
