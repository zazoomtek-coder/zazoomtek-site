#!/usr/bin/env python3
"""Prefer ZazoomTek's own recent reporting over external RSS press-review items.

Local-only matching: reads the repository's existing editorial JSON and
published article HTML, including Community / YouTube imports. No API, token,
remote LLM, or additional Cloudflare release is required.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
import json
import re
import unicodedata

WINDOW_DAYS = 14
STOP = frozenset("""
a ad ai al alla alle allo anche arriva arrivano arrivato come con cosa dai dal dalla
dalle degli dei del della delle dello dopo e ed ecco ecco come ecco tutti ecco tutte
fra gli ha hanno il in la le lo ma nel nella nelle nei non nuova nuovo nuovi nuove
per piu più prima primo quando quale quali questo questa questi queste si sono su
sul sulla tra un una uno tutte tutti aggiornamento annuncia annunciato annunciata
annunciati presenta presentati presenta ufficiale ufficialmente tutte novita novità
notizia notizie punto news tech gaming inside speciale speciali aggiornamenti
italia italiano italiani del tutto nel mondo online tutto quanto proprio nuovo
sito esclusiva scopri scoperta primo impressioni guida recensione test video
2025 2026 2027 2028
""".split())


def tokens(value: str) -> frozenset[str]:
    value = unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    # Preserve product model numbers, e.g. RTX 5090, Galaxy S27, PS5.
    words = re.findall(r"[a-z0-9]+", value)
    return frozenset(w for w in words if len(w) > 1 and w not in STOP)


def duplicates(first: str, second: str) -> bool:
    """Conservative topical overlap; generic brands alone never suffice."""
    a, b = tokens(first), tokens(second)
    if not a or not b:
        return False
    common = a & b
    if len(common) < 2:
        return False
    models_a = {x for x in a if any(d.isdigit() for d in x)}
    models_b = {x for x in b if any(d.isdigit() for d in x)}
    # Different model numbers are different announcements; don't suppress.
    if models_a and models_b and not models_a.intersection(models_b):
        return False
    coverage = len(common) / min(len(a), len(b))
    jaccard = len(common) / len(a | b)
    if len(common) >= 4 and coverage >= 0.60 and jaccard >= 0.38:
        return True
    if len(common) >= 3 and coverage >= 0.72 and jaccard >= 0.45:
        return True
    if len(common) >= 2 and coverage >= 0.78 and jaccard >= 0.60:
        return True
    # Shortened headline still matches a named product and its model number.
    return bool(models_a & models_b) and len(common) >= 2 and coverage >= 0.75 and jaccard >= 0.38


def recent(value: object, now: datetime) -> bool:
    if not value:
        return True  # Other filters establish this is an editorial article.
    try:
        stamp = datetime.fromisoformat(str(value)[:30].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        return now - timedelta(days=WINDOW_DAYS) <= stamp <= now + timedelta(days=1)
    except (TypeError, ValueError):
        return True


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _json_titles(root: Path, now: datetime):
    files = ("standard-news.json", "approved-special-articles.json",
             ".youtube-posts.json", ".youtube-latest.json",
             "zt-sidebar-feed.json", "studio/articoli.json")
    for name in files:
        data = _load(root / name)
        if data is None:
            continue
        if isinstance(data, list):
            batches = [data]
        elif isinstance(data, dict):
            batches = [x for key, x in data.items()
                       if key in ("articles", "posts", "items", "news", "tech",
                                  "gaming", "extra", "editorial", "reviews")
                       and isinstance(x, list)]
        else:
            continue
        for batch in batches:
            for row in batch:
                if not isinstance(row, dict):
                    continue
                title = row.get("title") or row.get("headline") or row.get("name")
                if title and recent(row.get("published_at") or row.get("publishedAt")
                                    or row.get("published") or row.get("date"), now):
                    yield str(title)


def _html_titles(root: Path, now: datetime):
    """Read real article H1, not archive cards or boilerplate page titles."""
    date_re = re.compile(r'["' + "'" + r']datePublished["' + "'" + r']\s*:\s*["' + "'" + r']([^"' + "'" + r']+)', re.I)
    h1_re = re.compile(r"<h1\b[^>]*>(.*?)</h1\s*>", re.I | re.S)
    for path in root.glob("*.html"):
        # Source and generated pages, including historic & YouTube Community.
        if path.name in {"index.html", "news.html", "tech-today.html",
                         "gaming-today.html", "extra.html", "speciali.html",
                         "guide.html", "recensioni-scritte.html"}:
            continue
        if path.name.startswith(("anteprima-", "preview-", "test-", "audit-", "check-")):
            continue
        if not path.name.startswith(("news-", "tech-impact-", "gaming-inside-",
                                      "speciale-", "recensione-", "guida-",
                                      "unboxing-", "test-", "extra-",
                                      "poly-", "70mai-")):
            # An editorial H1/date marker is required for other filenames.
            continue
        try:
            page = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        stamp = date_re.search(page[:16000])
        if stamp and not recent(stamp.group(1), now):
            continue
        title = h1_re.search(page)
        if title:
            yield unescape(re.sub(r"<[^>]+>", " ", title.group(1))).strip()


def local_headlines(root: Path, now: datetime | None = None) -> list[str]:
    now = now or datetime.now(timezone.utc)
    unique = {}
    for title in list(_json_titles(root, now)) + list(_html_titles(root, now)):
        key = tuple(sorted(tokens(title)))
        if key and key not in unique:
            unique[key] = title
    return list(unique.values())


def self_test():
    import tempfile
    assert duplicates("Samsung presenta Galaxy S27 con display OLED",
                      "Galaxy S27 ufficiale, Samsung annuncia il nuovo schermo OLED")
    assert duplicates("Corsair presenta periferiche Cyberpunk 2077 Arasaka",
                      "Periferiche Corsair Cyberpunk 2077, novità Arasaka")
    assert not duplicates("Samsung Galaxy S27 con display AMOLED",
                          "Samsung Galaxy S26 con display AMOLED")
    assert not duplicates("Apple iPad Pro con display OLED",
                          "Samsung Galaxy con display OLED")
    assert not duplicates("Google annuncia Pixel 12", "Google presenta Android 18")
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "standard-news.json").write_text(json.dumps({"articles": [
            {"title": "Galaxy S27 ufficiale: ecco i nuovi display",
             "published_at": "2026-10-21T12:00:00Z"},
            {"title": "Vecchia news Galaxy S26", "published_at": "2025-01-01T10:00:00Z"}]}))
        (root / ".youtube-posts.json").write_text(json.dumps([
            {"title": "Corsair presenta periferiche Cyberpunk 2077",
             "publishedAt": "2026-10-22T08:00:00Z"}]))
        (root / "news-Ugkx12345678.html").write_text(
            '<html><head><script>{"datePublished":"2026-10-20T12:00:00Z"}</script></head>'
            '<body><article><h1>Nuovo iRobot Roomba Combo 575</h1></article></body></html>')
        titles = local_headlines(root, now)
        assert len(titles) == 3, titles
        assert any(duplicates("iRobot lancia Roomba Combo 575", t) for t in titles)
    print("PASS: prioritize site headlines over external RSS and avoid false model collisions")


if __name__ == "__main__":
    self_test()
