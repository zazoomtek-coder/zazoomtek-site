#!/usr/bin/env python3
"""Offline tests for channel-wide uploads and safe independent fallback."""
import importlib.util, json, os, tempfile
from pathlib import Path
from unittest.mock import patch
from io import BytesIO

os.environ.setdefault("YOUTUBE_API_KEY", "test-key-not-used")
spec=importlib.util.spec_from_file_location("yt_videos",Path(__file__).with_name("update-youtube.py"))
yt=importlib.util.module_from_spec(spec)
spec.loader.exec_module(yt)

ids=[f"V{i:010d}" for i in range(31)]
channel=yt.CHANNEL_ID
def item(vid,n,channel_id=channel):
    return {"id":vid,"snippet":{"title":f"Video {n}","channelId":channel_id,
            "publishedAt":f"2026-10-{(n % 28)+1:02d}T10:00:00Z","liveBroadcastContent":"none"},
            "contentDetails":{"duration":"PT3M"}}

# The official Atom feed catches a brand-new video missing from uploads playlist.
atom=f"""<feed xmlns="http://www.w3.org/2005/Atom" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
<yt:channelId>{channel}</yt:channelId>
<entry><yt:videoId>{ids[30]}</yt:videoId></entry>
<entry><yt:videoId>{ids[29]}</yt:videoId></entry>
</feed>""".encode()
class Response:
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,limit): return atom[:limit]
with patch.object(yt.urllib.request,"urlopen",return_value=Response()):
    assert yt.official_rss_recent_ids({ids[29]},{ids[0]})==[ids[30]]

def fake_get(endpoint,**kw):
    if endpoint=="channels":
        return {"items":[{"contentDetails":{"relatedPlaylists":{"uploads":"official"}}}]}
    if endpoint=="playlistItems":
        return {"items":[{"contentDetails":{"videoId":ids[29]}}]}
    if endpoint=="videos":
        # Ignore a fraudulent video from another channel.
        return {"items":[item(v,int(v[1:])) for v in kw["id"].split(",")]+
                        [item("FOREIGN0001",0,"wrong-channel")]}
    raise AssertionError(endpoint)
with patch.object(yt,"get",side_effect=fake_get), \
     patch.object(yt,"official_rss_recent_ids",return_value=[ids[30]]):
    result=yt.uploads([{"id":ids[29],"title":"old","publishedAt":"2026-10-01T10:00:00Z"}])
    assert ids[30] in {v["id"] for v in result}
    assert "FOREIGN0001" not in {v["id"] for v in result}

# A failed category playlist never prevents discovery of an otherwise unclassified upload.
old=[{"id":ids[0],"category":"gaming"}]
with patch.object(yt,"playlist_video_ids",side_effect=RuntimeError("HTTP 503")):
    assert yt.safe_playlist_ids("playlist","gaming",old)=={ids[0]}
with patch.object(yt,"playlist_video_ids",return_value={ids[1]}):
    assert yt.safe_playlist_ids("playlist","gaming",old)=={ids[1]}

# The compact public feed covers all new channel uploads, not just curated playlists.
previous=[{"id":ids[i],"title":f"Video {i}","publishedAt":item(ids[i],i)["snippet"]["publishedAt"],
           "category":None,"short":False,"live":False,"completedLive":False} for i in range(30)]
fresh=[item(ids[i],i) for i in range(31)]
fresh.sort(key=lambda x:x["snippet"]["publishedAt"],reverse=True)
with tempfile.TemporaryDirectory() as tmp:
    cwd=os.getcwd()
    try:
        os.chdir(tmp)
        Path(".youtube-latest.json").write_text(json.dumps(previous),encoding="utf-8")
        with patch.object(yt,"uploads",return_value=fresh), \
             patch.object(yt,"playlist_video_ids",return_value=set()), \
             patch.object(yt,"youtube_short_ids",return_value=set()), \
             patch.object(yt,"update_home",return_value=None), \
             patch.object(yt,"update_category",return_value=None):
            yt.main()
            feed=json.loads(Path("home-video-feed.json").read_text())
            state=json.loads(Path(".youtube-latest.json").read_text())
            assert len(feed)==31 and len(state)==31,(len(feed),len(state))
            assert {v["id"] for v in feed}==set(ids)
            assert all(v["category"]=="video" for v in feed)
            # Unchanged subsequent scans do not touch either output.
            before=(Path(".youtube-latest.json").read_bytes(),Path("home-video-feed.json").read_bytes())
            yt.main()
            after=(Path(".youtube-latest.json").read_bytes(),Path("home-video-feed.json").read_bytes())
            assert before==after
    finally:
        os.chdir(cwd)

print("PASS: channel RSS fallback, channel-verified IDs, playlist failures, every video visible, unchanged no-op")
