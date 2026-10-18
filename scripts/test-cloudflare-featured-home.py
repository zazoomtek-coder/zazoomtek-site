#!/usr/bin/env python3
"""Regression: Cloudflare carousel retains five cards across idle publishing days."""
import importlib.util
import json
from pathlib import Path
import tempfile

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("featured_sync", root/"scripts/cloudflare-sync-featured-home.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def run():
    with tempfile.TemporaryDirectory() as folder:
        p = Path(folder)
        (p/"index.html").write_text(
            '<html><body><header>ZT</header>\n'+module.START+
            '\nOLD TWO SPECIAL ARTICLES\n'+module.END+
            '\n<footer>ZazoomTek</footer></body></html>', encoding="utf-8")
        # Build independently of production data. Old cards must be accepted
        # until genuinely newer posts arrive, never blanked at midnight.
        sample={"items":[
            {"section":kind,"url":"/news-"+slug+".html",
             "title":"Verified news "+slug,"image":"https://images.example.com/"+slug+".jpg",
             "published_date":"2026-10-01" if i<4 else "2026-10-02"}
            for i,(kind,slug) in enumerate([
                ("tech","phone"),("tech","laptop"),("tech","router"),
                ("tech","headset"),("gaming","game")])]}
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        (p/"featured-editorial-pins.json").write_text('{"items":[]}', encoding="utf-8")
        for item in sample["items"]:
            (p/item["url"].lstrip("/")).write_text("article", encoding="utf-8")
        assert module.sync(p,check=True) is True
        assert module.sync(p) is True
        assert module.sync(p) is False
        changed = (p/"index.html").read_text(encoding="utf-8")
        assert changed.count('class="zt-feature-card')==5
        assert "OLD TWO SPECIAL ARTICLES" not in changed
        assert changed.count("Tech Impact")==0
        assert changed.count("<footer>ZazoomTek</footer>")==1
        assert all(item["url"] in changed for item in sample["items"])

        # Reject category leaks without changing the last good Home.
        sample["items"][0]["section"]="tech-impact"
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Category mismatch must block the build")
        sample["items"][0]["section"]="tech"

        # Missing slot must never overwrite the last complete five cards.
        (p/"featured-carousel.json").write_text(
            json.dumps({"items":sample["items"][:1]}), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Partial carousel must block the build")

        sample["items"][0]["url"]="/news-missing.html"
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Missing article must block the build")
        assert (p/"index.html").read_text(encoding="utf-8")==changed
    print("PASS: Five featured stories survive idle days; invalid updates fail closed")
if __name__=="__main__":
    run()
