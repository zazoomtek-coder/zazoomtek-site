#!/usr/bin/env python3
"""Regression: Guides remains immediately under Latest Reviews after NEWS syncs."""
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
templ=(ROOT/"includes/home-guides-inset.html").read_text(encoding="utf-8").strip()
body=page.split(m.FEED_START,1)[1].split(m.FEED_END,1)[0]
rows=list(re.finditer(r'<article\b[^>]*class="article-row"',body))
assert len(rows)==15,len(rows)
assert page.count(templ)==1
assert "<!-- HOME_GUIDES_INSET_START -->" not in body
assert page.index("<!-- HOME_LATEST_REVIEWS_MAIN_END -->") < page.index("<!-- HOME_GUIDES_INSET_START -->") < page.index('id="articoli"')
standard,special=m.load()
result=m.chronological_home_feed(body,standard)
assert "<!-- HOME_GUIDES_INSET_START -->" not in result
assert len(list(re.finditer(r'<article\b[^>]*class="article-row"',result)))==15
assert m.chronological_home_feed(result,standard)==result
posts=json.loads((ROOT/".youtube-posts.json").read_text(encoding="utf-8"))
recent=[x for x in posts if (x.get("text") or "").lower().lstrip().startswith("news:")][:15]
feed=community.render_article_feed(recent,templ)
assert "<!-- HOME_GUIDES_INSET_START -->" not in feed
assert len(list(re.finditer(r'<article\b[^>]*class="article-row"',feed)))==15
assert all("recensione-" not in x.group() for x in re.finditer(r'<article\b[^>]*class="article-row"[^>]*>.*?</article>',body,re.S))
print("PASS: 15 latest NEWS; Guides under Latest Reviews; no duplicates; syncs preserve placement")
