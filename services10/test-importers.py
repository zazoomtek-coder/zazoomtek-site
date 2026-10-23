#!/usr/bin/env python3
"""Offline regression tests for official YouTube Data API import + Community.

No live access, API keys, secrets, cookies, Cloudflare deploys or downloads.
"""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

community=load("community_offline","01-community.py")
videos=load("videos_official","02-video-16x9.py")

def video(vid,seconds,channel=videos.CHANNEL):
    return {"id":vid,"snippet":{"channelId":channel,"title":"Review "+vid,
        "publishedAt":"2026-10-23T15:00:00Z","liveBroadcastContent":"none"},
        "contentDetails":{"duration":"PT"+str(seconds)+"S"},
        "status":{"privacyStatus":"public","embeddable":True}}

def main():
    assert videos.duration_seconds("PT3M") == 180
    assert videos.duration_seconds("PT3M1S") == 181
    assert videos.duration_seconds("PT1H1M1S") == 3661
    assert videos.duration_seconds("P1DT2H") == 93600
    assert videos.duration_seconds("not-time") is None
    xml=b'''<feed xmlns="http://www.w3.org/2005/Atom"
    xmlns:yt="http://www.youtube.com/xml/schemas/2015">
     <entry><yt:videoId>abcdef12345</yt:videoId><title>Full</title><published>2026-10-23T15:00:00Z</published></entry>
     <entry><yt:videoId>bad</yt:videoId><title>Ignore</title><published>2026-10-23T15:00:00Z</published></entry>
    </feed>'''
    assert [x["id"] for x in videos.collect(xml)]==["abcdef12345"]
    known={"abcdef12345"}
    status,row=videos.classify(video("abcdef12345",30),known)
    assert status=="short_or_unknown" and row is None
    status,row=videos.classify(video("shortvid001",40),set())
    assert status=="short_or_unknown" and row is None
    status,row=videos.classify(video("longvid0001",360),set())
    assert status=="landscape" and row["type"]=="landscape_video"
    assert row["verification"]=="duration_over_3m_not_short"
    assert row["orientation"]=="unverified"  # duration is not 16:9 metadata
    assert videos.classify(video("exact180001",180),set())[0]=="short_or_unknown"
    assert videos.classify(video("exact180001",180),{"exact180001"})[0]=="short_or_unknown"
    assert videos.classify(video("exact181001",181),set())[0]=="landscape"
    assert videos.classify(video("exact181001",181),{"exact181001"})[0]=="landscape"
    assert videos.classify(video("longvid0001",360,"another-channel"),known)[0]=="other"
    future=video("abcdef12345",600)
    future["snippet"]["liveBroadcastContent"]="upcoming"
    assert videos.classify(future,known)[0]=="other"
    blocked=video("abcdef12345",600)
    blocked["status"]["embeddable"]=False
    assert videos.classify(blocked,known)[0]=="other"
    old=[{"id":"priorvid001","title":"Old verified","type":"landscape_video",
          "published":"2026-10-22T00:00:00Z"}]
    approved=[{"id":"abcdef12345","title":"Confirmed","type":"landscape_video",
               "published":"2026-10-23T15:00:00Z"}]
    assert len(videos.merge(old,approved))==2
    assert len(videos.merge(videos.merge(old,approved),approved))==2

    with patch.object(videos,"request_api") as get:
        get.side_effect=[
           {"items":[{"contentDetails":{"relatedPlaylists":{"uploads":"UU_TEST"}}}]},
           {"items":[
             {"contentDetails":{"videoId":"abcdef12345","videoPublishedAt":"2026-10-23T15:00:00Z"},
              "snippet":{"title":"Review"}}],
            "nextPageToken":""}
        ]
        uploads=videos.upload_candidates()
        assert uploads[0]["id"]=="abcdef12345"
        assert get.call_count==2
        assert get.call_args_list[1].args[0]=="playlistItems"
    with patch.object(videos,"request_api") as get:
        get.return_value={"items":[video("abcdef12345",120)]}
        assert len(videos.metadata([{"id":"abcdef12345"}]))==1
        assert get.call_args.args[0]=="videos"

    with TemporaryDirectory() as tmp:
        directory=Path(tmp)
        with patch.object(videos,"OUT",directory/"videos.json"), \
             patch.object(videos,"PENDING",directory/"pending.json"), \
             patch.object(videos,"API_KEY","test-key"), \
             patch.object(videos,"confirmed_ids",return_value={"abcdef12345"}), \
             patch.object(videos,"upload_candidates",return_value=[
                 {"id":"abcdef12345"},{"id":"longvid0001"},{"id":"shortvid001"}]), \
             patch.object(videos,"rss_candidates",return_value=[]), \
             patch.object(videos,"metadata",return_value=[
                 video("abcdef12345",181),video("longvid0001",450),video("shortvid001",45)]):
            videos.save(old)
            videos.save([
                {"id":"legacyvid01","title":"Previous pending (now auto)",
                 "published":"2026-10-20T12:00:00Z",
                 "type":"pending_landscape",
                 "verification":"duration_over_3m_only","duration_seconds":420},
                {"id":"shortvid001","title":"Short (never approve)",
                 "type":"pending_landscape","duration_seconds":45}
            ],videos.PENDING)
            result=videos.run()
            assert result["verified_new"]==2 and result["auto_duration"]==1
            verified=videos.load(videos.OUT)
            waiting=videos.load(videos.PENDING)
            assert {x["id"] for x in verified}=={
                "priorvid001","abcdef12345","longvid0001","legacyvid01"}
            assert waiting==[]
            assert "shortvid001" not in {x["id"] for x in verified}
            with patch.object(videos,"upload_candidates",side_effect=RuntimeError("quotaExceeded")), \
                 patch.object(videos,"rss_candidates",side_effect=RuntimeError("RSS failed")):
                assert videos.run()["source"]=="no_candidates"
                assert videos.load(videos.OUT)==verified
                assert videos.load(videos.PENDING)==waiting

    # RSS omits duration: even manually approved IDs cannot bypass
    # the strict >180 seconds rule without verified API metadata.
    with TemporaryDirectory() as tmp:
        folder=Path(tmp)
        with patch.object(videos,"OUT",folder/"videos.json"), \
             patch.object(videos,"PENDING",folder/"pending.json"), \
             patch.object(videos,"API_KEY",""), \
             patch.object(videos,"confirmed_ids",return_value={"abcdef12345"}), \
             patch.object(videos,"rss_candidates",return_value=[
                 {"id":"abcdef12345","title":"Short but confirmed horizontal",
                  "published":"2026-10-23T15:00:00Z","url":"https://www.youtube.com/watch?v=abcdef12345"},
                 {"id":"shortvid001","title":"Unknown Short",
                  "published":"2026-10-23T15:00:00Z","url":"https://www.youtube.com/watch?v=shortvid001"}]):
            stats=videos.run()
            assert stats["source"]=="rss_without_duration"
            assert videos.load(videos.OUT)==[]

    # Braces inside post text and malformed neighbours never break Community.
    posts={"contents":{
        "a":{"backstagePostRenderer":{"postId":"Ugkx123",
             "contentText":{"runs":[{"text":"Tech news }; safe"}]}}},
        "b":{"backstagePostRenderer":{"postId":"broken"}},
        "c":{"backstagePostRenderer":{"postId":"Ugkx456",
             "contentText":{"simpleText":"Gaming update"}}}}}
    parsed=community.extract("var ytInitialData = "+json.dumps(posts)+";")
    assert {x["id"] for x in parsed}=={"Ugkx123","Ugkx456"}
    assert len(community.merge(parsed,parsed))==2
    assert community.extract("var ytInitialData = {corrupt;")==[]
    print("PASS: strict >180s import, 180s rejected even when approved, RSS without duration blocked, archive preserved")

if __name__=="__main__":
    main()
