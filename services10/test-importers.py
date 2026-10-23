#!/usr/bin/env python3
"""Offline regressions: both >180s AND source 16:9, no media downloads."""
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
def load(name,file):
    spec=importlib.util.spec_from_file_location(name, ROOT/file)
    result=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

community=load("community_check","01-community.py")
videos=load("video_check","02-video-16x9.py")

def item(vid,seconds,channel=videos.CHANNEL,visibility="public"):
    return {"id":vid, "snippet":{"channelId":channel,"title":"Video "+vid,
            "publishedAt":"2026-10-23T15:00:00Z","liveBroadcastContent":"none"},
            "contentDetails":{"duration":"PT"+str(seconds)+"S"},
            "status":{"privacyStatus":visibility,"embeddable":True}}

def source(w,h,rotation="none",ratio=None):
    stream={"widthPixels":w,"heightPixels":h,"rotation":rotation}
    if ratio is not None:stream["aspectRatio"]=ratio
    return {"videoStreams":[stream]}

def main():
    assert videos.duration_seconds("PT3M")==180
    assert videos.duration_seconds("PT3M1S")==181
    assert videos.duration_seconds("PT59S")==59
    assert videos.duration_seconds("PT1H1M1S")==3661
    assert videos.duration_seconds("not-time") is None
    rss=b'''<feed xmlns="http://www.w3.org/2005/Atom"
       xmlns:yt="http://www.youtube.com/xml/schemas/2015">
    <entry><yt:videoId>widevideo01</yt:videoId><title>Video</title>
    <published>2026-10-23T15:00:00Z</published></entry>
    <entry><yt:videoId>bad</yt:videoId><title>Invalid</title>
    <published>2026-10-23T15:00:00Z</published></entry>
    </feed>'''
    assert [v["id"] for v in videos.collect(rss)]==["widevideo01"]

    horizontal=source(1920,1080,ratio=16/9)
    vertical=source(1080,1920,ratio=9/16)
    square=source(1080,1080,ratio=1)
    four_three=source(1440,1080,ratio=4/3)
    assert videos.verified_16x9(horizontal)
    assert videos.verified_16x9(source(1280,720))
    assert videos.verified_16x9(source(1080,1920,rotation="clockwise"))
    assert not videos.verified_16x9(vertical)
    assert not videos.verified_16x9(square)
    assert not videos.verified_16x9(four_three)
    assert not videos.verified_16x9({"videoStreams":[]})
    assert not videos.verified_16x9(source(1920,1080,rotation="clockwise"))
    assert not videos.verified_16x9({"videoStreams":[{"widthPixels":0,"heightPixels":1080}]})
    assert not videos.verified_16x9({"videoStreams":[
        {"aspectRatio":16/9},{"aspectRatio":9/16}]})

    # No video can pass on duration alone, including >3 minutes.
    for seconds in (0,59,179,180):
        assert videos.classify(item("widevideo01",seconds),set(),
             geometry={"widevideo01":horizontal})[0]!="landscape"
    assert videos.classify(item("widevideo01",181),set())[0]=="pending"
    assert videos.classify(item("widevideo01",360),set())[0]=="pending"
    cls,row=videos.classify(item("widevideo01",181),set(),
                           geometry={"widevideo01":horizontal})
    assert cls=="landscape" and row["verification"]=="owner_file_details_16x9"
    cls,row=videos.classify(item("widevideo01",360),set(),
                           geometry={"widevideo01":vertical})
    assert cls=="non_16x9" and row is None
    assert videos.classify(item("widevideo01",181),set(),
                geometry={"widevideo01":square})[0]=="non_16x9"
    assert videos.classify(item("widevideo01",181),set(),
                geometry={"widevideo01":four_three})[0]=="non_16x9"
    # Owner-provided vertical geometry must override a stale manual registry.
    assert videos.classify(item("widevideo01",360),{"widevideo01"},
                geometry={"widevideo01":vertical})[0]=="non_16x9"
    assert videos.classify(item("widevideo01",181),{"widevideo01"})[0]=="landscape"
    assert videos.classify(item("widevideo01",180),{"widevideo01"})[0]=="short_or_unknown"
    assert videos.classify(item("widevideo01",240,channel="another"),{"widevideo01"})[0]=="other"
    assert videos.classify(item("widevideo01",240,visibility="private"),
                           {"widevideo01"})[0]=="other"

    with patch.object(videos,"request_api") as get:
        get.side_effect=[
            {"items":[{"contentDetails":{"relatedPlaylists":{"uploads":"UU_SAMPLE"}}}]},
            {"items":[{"contentDetails":{"videoId":"widevideo01"},
                        "snippet":{"title":"Video"}}]}]
        assert videos.upload_candidates()[0]["id"]=="widevideo01"
        assert get.call_count==2
    with patch.object(videos,"request_api",return_value={"items":[item("widevideo01",240)]}):
        assert videos.metadata([{"id":"widevideo01"}])[0]["id"]=="widevideo01"

    with TemporaryDirectory() as folder:
        root=Path(folder)
        with patch.object(videos,"OUT",root/"videos.json"),\
             patch.object(videos,"PENDING",root/"pending.json"),\
             patch.object(videos,"API_KEY","mock_api_key"),\
             patch.object(videos,"confirmed_ids",return_value=set()),\
             patch.object(videos,"upload_candidates",return_value=[
                 {"id":"widevideo01"},{"id":"vertical001"},{"id":"squarevid01"},
                 {"id":"shortvid001"},{"id":"unknown0001"}]),\
             patch.object(videos,"rss_candidates",return_value=[]),\
             patch.object(videos,"metadata",return_value=[
                 item("widevideo01",181),item("vertical001",360),
                 item("squarevid01",400),item("shortvid001",180),
                 item("unknown0001",500)]),\
             patch.object(videos,"owner_geometry",return_value={
                 "widevideo01":horizontal,"vertical001":vertical,
                 "squarevid01":square}):
            videos.save([{"id":"oldvalid001","title":"Existing confirmed",
                "type":"landscape_video","verification":"owner_file_details_16x9"}])
            videos.save([{"id":"legacyvid01","title":"Old duration-only",
                "duration_seconds":500,"type":"landscape_video",
                "verification":"duration_over_3m_not_short","orientation":"unverified"}],
                videos.PENDING)
            result=videos.run()
            assert result["verified_new"]==1
            approved=videos.load(videos.OUT)
            pending=videos.load(videos.PENDING)
            assert {v["id"] for v in approved}=={"oldvalid001","widevideo01"}
            assert {v["id"] for v in pending}=={"unknown0001"}
            assert not any(v["id"] in {"vertical001","squarevid01","shortvid001"}
                           for v in approved)
            with patch.object(videos,"upload_candidates",side_effect=RuntimeError("quota")),\
                 patch.object(videos,"rss_candidates",side_effect=RuntimeError("offline")):
                result=videos.run()
                assert result["source"]=="no_candidates"
                assert videos.load(videos.OUT)==approved

    # Previous duration-only publications must be quarantined, not auto-approved.
    with TemporaryDirectory() as folder:
        root=Path(folder)
        with patch.object(videos,"OUT",root/"videos.json"),\
             patch.object(videos,"PENDING",root/"pending.json"),\
             patch.object(videos,"API_KEY",""),\
             patch.object(videos,"rss_candidates",return_value=[]):
            videos.save([{"id":"priorlong01","title":"Was duration-only",
                         "published":"2026-10-23T15:00:00Z","duration_seconds":400,
                         "type":"landscape_video","verification":"duration_over_3m_not_short",
                         "orientation":"unverified"}])
            assert videos.run()["source"]=="no_candidates"
            assert videos.load(videos.OUT)==[]
            assert [v["id"] for v in videos.load(videos.PENDING)]==["priorlong01"]

    posts={"a":{"backstagePostRenderer":{"postId":"Ugkx123",
       "contentText":{"runs":[{"text":"Text with }; embedded delimiters"}]}}},
       "b":{"backstagePostRenderer":{"postId":"broken"}}}
    page="var ytInitialData = "+json.dumps(posts)+";"
    assert [v["id"] for v in community.extract(page)]==["Ugkx123"]
    print("PASS: 180s rejected, 181s+16:9 accepted, 9:16/square/4:3 rejected; unknowns quarantined")

if __name__=="__main__":
    main()
