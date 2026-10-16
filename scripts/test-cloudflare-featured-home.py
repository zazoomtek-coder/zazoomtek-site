#!/usr/bin/env python3
"""Fast regression checks for HTML/JSON featured carousel consistency."""
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
        sample = json.loads((root/"featured-carousel.json").read_text(encoding="utf-8"))
        # The mock fixture stays fresh regardless of when this CI runs.
        import datetime as dt
        from zoneinfo import ZoneInfo
        today=dt.datetime.now(ZoneInfo("Europe/Rome")).date()
        for item in sample["items"]:
            if item["section"] in ("tech","gaming"):
                item["published_date"]=(today-dt.timedelta(days=1)).isoformat()
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        (p/"featured-editorial-pins.json").write_text('{"items":[]}', encoding="utf-8")
        for item in sample["items"]:
            (p/item["url"].lstrip("/")).write_text("article", encoding="utf-8")
            if item["image"].startswith("/"):
                image = p/item["image"].lstrip("/")
                image.parent.mkdir(parents=True, exist_ok=True)
                image.write_bytes(b"cover")
        assert module.sync(p,check=True) is True
        assert module.sync(p) is True
        assert module.sync(p) is False
        changed = (p/"index.html").read_text(encoding="utf-8")
        assert changed.count('class="zt-feature-card')==len(sample["items"])
        assert "OLD TWO SPECIAL ARTICLES" not in changed
        assert changed.count("Tech Impact")==0
        assert changed.count("<footer>ZazoomTek</footer>")==1
        for item in sample["items"]:
            assert item["url"] in changed
        sample["items"][0]["section"]="tech-impact"
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Category mismatch must block the build")
        sample["items"][0]["section"]="tech"
        sample["items"][0]["published_date"]="2026-10-09"
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Older-than-yesterday news must block the build")
        sample["items"][0]["published_date"]=(__import__("datetime").datetime.now(
            __import__("zoneinfo").ZoneInfo("Europe/Rome")).date()
            - __import__("datetime").timedelta(days=1)).isoformat()

        sample["items"][0]["url"]="/news-missing.html"
        (p/"featured-carousel.json").write_text(json.dumps(sample), encoding="utf-8")
        try:
            module.sync(p)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Missing article must block the build")
        assert (p/"index.html").read_text(encoding="utf-8")==changed
    print("PASS: Featured sync is safe, idempotent, and blocks invalid stories")
if __name__=="__main__":
    run()
