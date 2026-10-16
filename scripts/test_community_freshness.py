#!/usr/bin/env python3
"""No-network regression tests: never import duplicates, and recover missing fresh posts."""
import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
spec=importlib.util.spec_from_file_location("community_import",Path(__file__).with_name("update-youtube-posts.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

a={"id":"UgkxAlreadyPublishedExample123456","text":"News: already published"}
fresh={"id":"UgkxFreshNewsExample123456789","text":"News: new post"}

with patch.object(mod,"fetch_recent_alternate",return_value=[fresh]) as alt, \
     patch.object(mod,"fetch_recent_invidious",return_value=[]) as mirror:
    posts,complete=mod.augment_recent_posts([dict(a)],[dict(a)],False)
    assert [p["id"] for p in posts]==[fresh["id"],a["id"]]
    assert complete is False
    alt.assert_called_once()
    mirror.assert_not_called()

with patch.object(mod,"fetch_recent_alternate",return_value=[]) as alt, \
     patch.object(mod,"fetch_recent_invidious",return_value=[fresh]) as mirror:
    posts,complete=mod.augment_recent_posts([dict(a)],[dict(a)],False)
    assert posts[0]["id"]==fresh["id"]
    assert not complete
    alt.assert_called_once()
    mirror.assert_called_once()

# Regression for the real outage: the first tab had newly published
# Gaming, so the importer skipped other URLs containing new Tech news.
gaming={"id":"UgkxNewGamingPost1234567890","text":"News Gaming: Nuovo gioco"}
tech={"id":"UgkxNewTechArticle1234567890","text":"News Tech: Nuovo router Wi-Fi"}
with patch.object(mod,"fetch_recent_alternate",return_value=[tech]) as alt, \
     patch.object(mod,"fetch_recent_invidious",return_value=[]) as mirror:
    posts,complete=mod.augment_recent_posts([dict(gaming),dict(a)],[dict(a)],False)
    assert complete is False and len(posts)==3,posts
    assert [p["id"] for p in posts]==[tech["id"],gaming["id"],a["id"]]
    alt.assert_called_once_with({a["id"]},{a["id"],gaming["id"]})
    mirror.assert_not_called()

with patch.object(mod,"fetch_recent_alternate",return_value=[]) as alt, \
     patch.object(mod,"fetch_recent_invidious",return_value=[]) as mirror:
    posts,complete=mod.augment_recent_posts([dict(gaming),dict(a)],[dict(a)],False)
    assert complete is False and len(posts)==2
    alt.assert_called_once()
    mirror.assert_called_once()

with patch.object(mod,"fetch_recent_alternate") as alt, \
     patch.object(mod,"fetch_recent_invidious") as mirror:
    posts,complete=mod.augment_recent_posts([dict(a)],[dict(a)],True,force_full_scan=True)
    assert complete
    alt.assert_not_called()
    mirror.assert_not_called()

# Reject stale, missing timestamp, duplicate, and malformed IDs from a mirror.
now=int(mod.time.time())
def item(pid,seconds_ago,text="News: sample"):
    return {"commentId":pid,"published":now-seconds_ago,"content":text}
sample={"comments":[
    item("UgkxFreshNewsExample123456789",120),
    item("UgkxAlreadyPublishedExample123456",120),
    item("UgkxOldPostExample12345678901",30*86400),
    item("invalid-id",120),
    item("UgkxEmptyPostExample123456789",120,""),
]}
with patch.object(mod,"open_with_retry",return_value=sample):
    rows=mod.fetch_recent_invidious({a["id"]},set())
    assert [x["id"] for x in rows]==[fresh["id"]],rows
    assert rows[0]["published_iso"] and rows[0]["url"].endswith(fresh["id"])

# A cached/old first Community page must not hide a newer post available
# through another official YouTube URL. Reject repeated IDs from later pages.
def official_page(pid, headline):
    data={"contents":{"postRenderer":{
        "postId":pid,
        "contentText":{"runs":[{"text":headline}]},
        "publishedTimeText":{"simpleText":"1 minuto fa"}
    }}}
    return "var ytInitialData = "+mod.json.dumps(data)+";</script>"

with patch.object(mod,"open_with_retry",side_effect=[
    official_page(a["id"],a["text"]),
    official_page(fresh["id"],fresh["text"]),
    official_page(fresh["id"],fresh["text"]),
    mod.urllib.error.URLError("one mobile source offline"),
]):
    actual=mod.fetch_recent_alternate({a["id"]},set())
    assert [x["id"] for x in actual]==[fresh["id"]],actual

# The first public mirror can be down; the next healthy mirror must still
# recover the missing post, without generating duplicates.
with patch.object(mod,"invidious_instances",return_value=[
    "https://first-mirror.example","https://second-mirror.example"
]),patch.object(mod,"open_with_retry",side_effect=[
    mod.urllib.error.URLError("first mirror unavailable"),sample
]):
    actual=mod.fetch_recent_invidious({a["id"]},set())
    assert [x["id"] for x in actual]==[fresh["id"]],actual

print("PASS: new Gaming post never masks fresh Tech on alternate YouTube tabs; no duplicates; history safe")
