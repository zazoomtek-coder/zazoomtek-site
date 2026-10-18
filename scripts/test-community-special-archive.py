#!/usr/bin/env python3
"""No-network regression: distinct Community and approved specialist publishers."""
import importlib.util
from pathlib import Path
import tempfile

spec=importlib.util.spec_from_file_location("special",Path(__file__).with_name("community_special_archive.py"))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def test():
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)
        def archive(category):
            return (f'<html><main><section><div class="news-list" id="newsList" data-auto-articles="{category}">'
                    '<article class="news-row"><a href="/tech-impact-existing.html">Present</a>'
                    '<div class="news-meta">ZazoomTek · 2026-10-15</div></article>'
                    '</div><!-- ZT_COMMUNITY_BANNER_START --><p>Banner</p></section></main></html>')
        for section,filename in (("tech","tech-today.html"),("gaming","gaming-today.html")):
            (root/filename).write_text(archive(section),encoding="utf-8")
        news=(root/"news-UgkxExamplePost123456.html")
        news.write_text('<html><head><meta property="article:published_time" content="2026-10-17T14:24:58Z"></head>'
                        '<body><h1>News Tech Impact: Videogiochi e terapia clinica</h1>'
                        '<img class="article-hero" src="https://example.org/therapy.webp">'
                        '<div class="article-body"><p>Il videogioco viene usato con la guida di specialisti.</p></div>'
                        '</body></html>',encoding="utf-8")
        first=s.sync(root)
        assert first["tech"]==(1,2),first
        a=(root/"tech-today.html").read_text()
        b=(root/"gaming-today.html").read_text()
        assert "news-UgkxExamplePost123456.html" in a
        assert "news-UgkxExamplePost123456.html" not in b
        assert a.count("news-UgkxExamplePost123456.html")==3,a
        assert "News Tech Impact:" not in a
        assert "tech-impact-existing.html" in a
        assert s.sync(root)==first
        assert (root/"tech-today.html").read_text()==a,"Duplicate/reordering after retry"
        # Simulate the other publisher replacing the section with its own cards.
        (root/"tech-today.html").write_text(archive("tech"))
        s.sync(root)
        assert (root/"tech-today.html").read_text()==a,"A special-news release erased Community posts"
    print("PASS: existing + Community Tech Impact retained, no Gaming leak, retries idempotent")

if __name__=="__main__":test()
