#!/usr/bin/env python3
"""Regression: Home Speciali shows only real articles and accepts a second one."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("home_speciali",ROOT/"scripts/sync-home-speciali.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def check_source():
    index=(ROOT/"index.html").read_text(encoding="utf-8")
    js=(ROOT/"zt-home-live.js").read_text(encoding="utf-8")
    css=(ROOT/"zt-home-graphic-layout-20261016.css").read_text(encoding="utf-8")
    assert index.count('id="ztHomeSpeciali"')==1
    assert index.count(mod.HOME_START)==index.count(mod.HOME_END)==1
    assert index.index('id="ztHomeSpeciali"')<index.index('data-special-section="tech"')
    assert 'if(speciali)rail.appendChild(speciali)' in js
    assert 'if(pop)rail.appendChild(pop);' in js
    assert 'if(inside)rail.appendChild(inside);' in js
    assert 'shortsSlot=document.createElement' not in js
    assert 'for(const shorts of all.filter(' in js
    assert 'main.page .zt-shorts-box' in css
    assert 'justify-content:space-between!important' in css
    assert 'align-self:stretch!important' in css
    # Only on Home. The original Shorts video archives and imports stay intact.
    assert (ROOT/"shorts.html").exists() or (ROOT/"video.html").exists()


def check_builder():
    sample=(ROOT/"index.html").read_text(encoding="utf-8")
    archive=(ROOT/"speciali.html").read_text(encoding="utf-8")
    published=mod.special_cards(archive)
    assert len(published)==1, "The baseline has one verified published Speciale"
    with tempfile.TemporaryDirectory() as folder:
        temp=Path(folder)
        (temp/"index.html").write_text(sample,encoding="utf-8")
        (temp/"speciali.html").write_text(archive,encoding="utf-8")
        for row in published:
            shutil.copyfile(ROOT/row["url"].lstrip("/"),temp/row["url"].lstrip("/"))
            if row["image"].startswith("/"):
                image=temp/row["image"].lstrip("/")
                image.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(ROOT/row["image"].lstrip("/"),image)
        mod.sync(temp)
        source=(temp/"index.html").read_text(encoding="utf-8")
        block=source.split(mod.HOME_START,1)[1].split(mod.HOME_END,1)[0]
        assert block.count('class="zt-special-item"')==1
        assert published[0]["url"] in block
        assert not mod.sync(temp), "Second run must be idempotent"
        new='/speciale-secondo-articolo.html'
        fake=('<article data-zt-special="approved" class="news-row">'
              '<a href="'+new+'"><img src="https://example.org/new.jpg" '
              'alt="Secondo speciale"></a><div class="news-copy"><h2>'
              '<a href="'+new+'">Secondo speciale reale</a></h2></div></article>\n')
        a=archive.index(mod.ARCHIVE_START)+len(mod.ARCHIVE_START)
        archive=archive[:a]+fake+archive[a:]
        (temp/"speciali.html").write_text(archive,encoding="utf-8")
        (temp/new.lstrip("/")).write_text("<article>Approved</article>",encoding="utf-8")
        assert mod.sync(temp), "Second approved article must enter Home"
        result=(temp/"index.html").read_text(encoding="utf-8")
        block=result.split(mod.HOME_START,1)[1].split(mod.HOME_END,1)[0]
        assert block.count('class="zt-special-item"')==2
        assert new in block
        assert not mod.sync(temp)
    print("PASS: one real Speciale now; second is automatic, no fake placeholder, Home Shorts suppressed, independent category archives intact")


if __name__=="__main__":
    check_source()
    check_builder()
