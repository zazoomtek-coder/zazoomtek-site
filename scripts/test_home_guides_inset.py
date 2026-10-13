#!/usr/bin/env python3
"""Regression: Guides box remains after ten Home NEWS across both news publishers."""
from pathlib import Path
from importlib.util import spec_from_file_location,module_from_spec
import re,json,sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"scripts"))
mod=spec_from_file_location("standard",ROOT/"scripts/apply-standard-news-featured.py")
m=module_from_spec(mod);mod.loader.exec_module(m)
u=spec_from_file_location("community",ROOT/"scripts/update-youtube-posts.py")
community=module_from_spec(u);u.loader.exec_module(community)
page=(ROOT/"index.html").read_text(encoding="utf-8")
body=page.split(m.FEED_START,1)[1].split(m.FEED_END,1)[0]
templ=(ROOT/"includes/home-guides-inset.html").read_text(encoding="utf-8").strip()
rows=list(re.finditer(r'<article\b[^>]*class="article-row"',body))
assert len(rows)==15,len(rows)
assert body.count(templ)==1
start=body.index("<!-- HOME_GUIDES_INSET_START -->")
assert sum(x.start()<start for x in rows)==10
standard,special=m.load()
result=m.chronological_home_feed(body,standard)
assert result.count(templ)==1
offset=result.index("<!-- HOME_GUIDES_INSET_START -->")
assert sum(x.start()<offset for x in re.finditer(r'<article\b[^>]*class="article-row"',result))==10
assert m.chronological_home_feed(result,standard)==result
posts=json.loads((ROOT/".youtube-posts.json").read_text(encoding="utf-8"))
recent=[x for x in posts if (x.get("text") or "").lower().lstrip().startswith("news:")][:15]
feed=community.render_article_feed(recent,templ)
assert feed.count(templ)==1
assert sum(x.start()<feed.index("<!-- HOME_GUIDES_INSET_START -->") for x in re.finditer(r'<article\b[^>]*class="article-row"',feed))==10
assert all("recensione-" not in x.group() for x in re.finditer(r'<article\b[^>]*class="article-row"[^>]*>.*?</article>',body,re.S))
print("PASS: 15 latest NEWS; Guides exactly after tenth; chronology idempotent; Community importer preserves Guides")
