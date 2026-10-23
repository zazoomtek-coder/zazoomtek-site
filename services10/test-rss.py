#!/usr/bin/env python3
"""RSS feed import isolation, daily cadence and data fallback (no network)."""
import importlib.util,json
from datetime import datetime,timezone,timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("zazoom_rss",HERE/"06-notizie-web.py")
web=importlib.util.module_from_spec(spec);spec.loader.exec_module(web)

def main():
    xml=b'''<?xml version="1.0"?><rss xmlns:media="http://search.yahoo.com/mrss/">
      <channel><item><title>News RSS nuova</title>
      <link>https://example.org/news/new</link>
      <pubDate>Fri, 23 Oct 2026 10:00:00 GMT</pubDate>
      <description>Nuovo prodotto tecnologico</description>
      <media:thumbnail url="https://example.org/new.jpg" /></item>
      <item><title>Elemento corrotto senza URL</title></item>
      </channel></rss>'''
    parsed=web.parse_feed(xml,"SmartWorld")
    assert len(parsed)==1 and parsed[0]["original_title"]=="News RSS nuova"
    assert parsed[0]["image"]=="https://example.org/new.jpg"
    now=datetime(2026,10,23,18,tzinfo=timezone.utc)
    with TemporaryDirectory() as tmp:
        root=Path(tmp)
        existing=[{"url":"https://example.org/old/"+str(i),"source":"HDblog",
             "image":"https://example.org/"+str(i)+".jpg",
             "original_title":"Old "+str(i)} for i in range(5)]
        path=root/"notizie-dal-web.json"
        path.write_text(json.dumps({"updated_at":(now-timedelta(days=2)).isoformat(),
                                    "items":existing}))
        def fetch(url):
            if "hdblog.it" in url:raise RuntimeError("Temporary RSS outage")
            return xml
        assert web.refresh_rss(root,fetch=fetch,now=now)==5
        result=json.loads(path.read_text())
        assert len(result["items"])==5
        assert result["items"][0]["original_title"]=="News RSS nuova"
        assert len({x["url"] for x in result["items"]})==5
        assert web.refresh_rss(root,fetch=lambda _:1/0,now=now+timedelta(hours=2))==0
        assert result==json.loads(path.read_text())
    print("PASS: daily web-news refresh, per-source outage isolation and previous-cover preservation")

if __name__=="__main__":
    main()
