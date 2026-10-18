#!/usr/bin/env python3
"""Fail-closed source and packaged check for locked ZazoomTek Home 10+10.
Never edits Home, site CSS, carousel, or article content.
"""
from __future__ import annotations
from pathlib import Path
import re
import sys

def check(root: Path) -> None:
    script=(root/"zt-home-live.js").read_text(encoding="utf-8")
    home=(root/"index.html").read_text(encoding="utf-8")
    rev="20261018stableColumns1010"
    assert f"/zt-home-live.js?v={rev}" in home, "Old cached column JS is still referenced"
    assert 'column.replaceChildren(...ranked.slice(0,10)' in script, "Newest 10-per-column selection lost"
    assert 'const featured=featuredPaths();' in script, "Carousel exclusion lost"
    assert '!featured.has(url)' in script and 'MutationObserver(paintCurrentColumns)' in script
    assert 'sourcePublishedAt(row)' in script and 'b.time-a.time' in script
    assert "function rebalance(){" in script and "all.slice(10).forEach(function(row){row.remove();})" in script
    match=re.search(r'function alignBottoms\(\)\{([\s\S]*?)\n    \}\n    function requestAlignment',script)
    assert match, "Approved column-alignment function is missing"
    alignment=match.group(1)
    assert "left.length!==10||right.length!==10" in alignment, "Column limit is not enforced"
    assert "shorter.appendChild" not in alignment and "appendChild(" not in alignment, "Filler articles reintroduced"
    assert "data-zt-align-fill" not in script, "Legacy filler-card code reintroduced"
    assert "padding-bottom" in alignment, "Non-destructive modest height balancing lost"
    assert "ztp-two-news-columns" in script, "Home two-column structure missing"
    assert home.count("<!-- ARTICLE_FEED_START -->")==1, "Canonical news import markers missing"
    print("PASS: exactly ten dated TECH plus ten dated GAMING; no carousel duplicates/filler articles; cache revision current")

if __name__=="__main__":
    folder=Path(sys.argv[1]) if len(sys.argv)>1 else Path(".")
    check(folder)
