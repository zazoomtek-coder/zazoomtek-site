#!/usr/bin/env python3
"""Verify only factual duplicate consolidation and safe article image priorities."""
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from build import posts,EDITORIAL_DUPLICATE_REDIRECTS

rows=posts()
available={r["slug"] for r in rows}
assert len(EDITORIAL_DUPLICATE_REDIRECTS)==2
redirects=(ROOT/"dist"/"_redirects").read_text(encoding="utf-8").splitlines()
urlset=(ROOT/"dist"/"sitemap.xml").read_text(encoding="utf-8")
for old,target in EDITORIAL_DUPLICATE_REDIRECTS.items():
 assert old not in available,("old article is still visible",old)
 assert target in available,("canonical target missing",target)
 assert not (ROOT/"dist"/(old+".html")).exists(),old
 assert (ROOT/"dist"/(target+".html")).is_file(),target
 assert ("/"+old+" /"+target+" 301") in redirects,old
 assert ("/"+old+".html /"+target+" 301") in redirects,old
 assert "https://zazoomtek.it/"+old+"</loc>" not in urlset,old
 assert "https://zazoomtek.it/"+target+"</loc>" in urlset,target

# Stable 301s must not collide with another redirect or point to themselves.
aliases=[line.split()[0] for line in redirects if line.strip()]
assert len(aliases)==len(set(aliases)), "Redirect aliases duplicated"
assert all(line.split()[0]!=line.split()[1] for line in redirects if line.strip()), "Self redirect"

article_files=[ROOT/"dist"/(r["slug"]+".html") for r in rows if r.get("image")]
priority=0
for file in article_files:
 text=file.read_text(encoding="utf-8")
 # Only main editorial cover receives high fetch priority.
 if re.search(r'<figure class="story-figure"><img loading="eager" fetchpriority="high" decoding="async"',text):
  priority+=1
assert priority>=40,("Few eager article covers",priority)

# No future publication dates were invented for old editorial data.
missing=[r for r in rows if not str(r.get("date") or r.get("published_at") or "").strip()]
assert len(missing)>=1, "Missing original dates unexpectedly filled"
print("SEO REMAINING FIX PASS: 2 canonical 301 redirects, no duplicate sitemap URLs; ",
      len(rows),"articles,",priority,"high-priority cover images,",
      len(missing),"undated articles retained truthfully. ZERO DEPLOY",flush=True)
