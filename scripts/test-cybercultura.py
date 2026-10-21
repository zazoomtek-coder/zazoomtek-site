#!/usr/bin/env python3
"""No-deploy Cybercultura regression: both importers, navigation, SEO and 301s."""
from __future__ import annotations
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
spec=spec_from_file_location("cyber",ROOT/"scripts/build-cybercultura.py")
mod=module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def test_site_sources():
    home=(ROOT/"index.html").read_text(encoding="utf-8")
    nav=re.search(r'<nav\s+class="nav"[^>]*>(.*?)</nav>',home,re.S)
    assert nav
    markup=nav.group(1)
    assert markup.count('href="/cybercultura.html"')==1
    assert markup.count('href="/speciali.html"')==1
    assert markup.index('href="/cybercultura.html"')<markup.index('href="/speciali.html"')
    assert ">INSIGHTS</button>" not in markup
    assert 'href="/tech-today.html"' not in markup
    assert 'href="/gaming-today.html"' not in markup
    for name in ("tech-today.html","gaming-today.html","speciali.html",
                 "cybercultura.html"):
        assert (ROOT/name).is_file()
    redirect=(ROOT/"_redirects").read_text(encoding="utf-8")
    for old in ("/tech-today.html","/gaming-today.html",
                "/tech-today","/gaming-today"):
        assert old+" /cybercultura.html 301" in redirect.splitlines()
    assert "/tech-impact-" not in redirect and "/gaming-inside-" not in redirect, (
        "Original article URLs must never be redirected")


def test_merge():
    tech=mod.read_archive(ROOT,"Tech Impact","tech-today.html","tech-impact")
    gaming=mod.read_archive(ROOT,"Gaming Inside","gaming-today.html","gaming-inside")
    assert len(tech)>=15 and len(gaming)>=4
    assert len({x[1] for x in tech+gaming})==len(tech)+len(gaming), (
        "Preexisting article URLs unexpectedly overlap; examine dedup")
    with TemporaryDirectory(prefix="zt-cyber-tests-") as folder:
        work=Path(folder)
        for name in ("cybercultura.html","tech-today.html","gaming-today.html"):
            (work/name).write_text((ROOT/name).read_text(encoding="utf-8"),encoding="utf-8")
        for row in tech+gaming:
            (work/row[1].lstrip("/")).write_text("Published existing article",encoding="utf-8")
        count,unique=mod.sync(work)
        assert count==unique==len(tech)+len(gaming)
        page=(work/"cybercultura.html").read_text(encoding="utf-8")
        first=page.split(mod.START,1)[1].split(mod.END,1)[0]
        assert first.count('data-cyber-section="tech-impact"')==len(tech)
        assert first.count('data-cyber-section="gaming-inside"')==len(gaming)
        assert first.count('zt-cyber-badge')>=len(tech)+len(gaming)
        assert 'https://zazoomtek.it/cybercultura.html' in page
        assert len(re.findall(r'<article\b[^>]*class="news-row"',first))==count
        assert mod.sync(work)==(count,unique)
        # A newly imported approved Gaming Inside story is picked up
        # automatically without needing a manual Cybercultura edit.
        new="/gaming-inside-nuovo-speciale-verificato.html"
        (work/new.lstrip("/")).write_text("Approved new article",encoding="utf-8")
        existing=(work/"gaming-today.html").read_text(encoding="utf-8")
        anchor=existing.index('<div class="news-list" id="newsList"')
        begin=existing.index(">",anchor)+1
        fresh=('<article class="news-row"><a href="'+new+'">'
               '<img src="/ChatGPT.png" alt="Un nuovo articolo" loading="lazy"></a>'
               '<div class="news-copy"><h2><a href="'+new+'">Un nuovo articolo verificato'
               '</a></h2><div class="news-meta">ZazoomTek · 2026-10-21</div>'
               '<p>Il testo è già verificato e pubblicato.</p></div></article>')
        (work/"gaming-today.html").write_text(existing[:begin]+fresh+existing[begin:],encoding="utf-8")
        count2,_=mod.sync(work)
        updated=(work/"cybercultura.html").read_text(encoding="utf-8")
        items=updated.split(mod.START,1)[1].split(mod.END,1)[0]
        assert count2==count+1 and new in items
        assert items.count('href="'+new+'"')>=1
        assert mod.sync(work)==(count2,count2)
    print(f"PASS: {len(tech)} Impact + {len(gaming)} Gaming entries; new imports auto-appear; "
          "all original URLs kept, top-level navigation and Cloudflare 301 safe")


if __name__=="__main__":
    test_site_sources()
    test_merge()
