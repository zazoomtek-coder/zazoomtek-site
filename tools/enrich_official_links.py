#!/usr/bin/env python3
"""Verified official product/game links for ZazoomTek's YouTube Community news.

Run ONLY inside the already authorized 12:30/19:30 editorial publisher.
No search results or third-party shopping pages. No guessed URLs.
An external lookup failure NEVER aborts the editorial publication.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
import ipaddress
import json
import os
import re
import unicodedata
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "official_links.json"
WIKIDATA = "https://www.wikidata.org/w/api.php"
UA = "ZazoomTekEditorialEnrichment/1.0 (https://zazoomtek.it/contatti) Python-urllib"
MAX_NEW_SEARCHES = 10
MAX_AGE_DAYS = 21
LOOKUP_TIMEOUT = 5

# URLs checked against the actual creator/manufacturer's official site.
# Keep exact game/model phrase matching; never infer product URLs from slugs.
VERIFIED = (
    ("news-gaming", "The Sims 4", "https://www.ea.com/it/games/the-sims/the-sims-4"),
    ("news-gaming", "ArcheAge Chronicles", "https://archeagechronicles.com/"),
    ("news-gaming", "Dragon Ball Xenoverse 2", "https://it.bandainamcoent.eu/dragon-ball/dragon-ball-xenoverse-2"),
    ("news-tech", "vivo X500 Series", "https://vivo-official.com/pages/x500"),
)
TYPE_LABEL = {
    "news-gaming": "Sito ufficiale del gioco",
    "news-tech": "Scheda ufficiale del prodotto",
}
NEWS_VERBS = re.compile(
    r"\s+(?:riceve|arriva|mostra|apre|celebra|svela|debutta|lancia|"
    r"annuncia|presenta|introduce|conferma|ottiene|torna|sarà|è|"
    r"si prepara|diventa|disponibile|rivelato|raggiunge|conquista|"
    r"approda|entra|porta|pubblica|esce|si aggiorna)\b", re.I
)

def norm(value):
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in s if not unicodedata.combining(c))).strip()

def safe_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        return ""
    try:
        u = urlsplit(value)
        if u.scheme != "https" or u.username or u.password or u.port not in (None, 443):
            return ""
        domain = (u.hostname or "").rstrip(".").lower()
        if not domain or "." not in domain or any(x in domain for x in ("localhost", ".local")):
            return ""
        try:
            ipaddress.ip_address(domain)
            return ""
        except ValueError:
            pass
        if domain.endswith((".internal", ".invalid", ".test", ".example")):
            return ""
        if not re.fullmatch(r"[a-z0-9.-]+", domain):
            return ""
        return value
    except ValueError:
        return ""

def headline(value, category):
    s = re.sub(r"^\s*#*\s*News\s+(?:Gaming|Tech)\s*[:–—-]\s*", "", str(value or ""), flags=re.I).strip()
    s = s.split(" | ", 1)[0]
    p = NEWS_VERBS.search(s)
    if p:
        s = s[:p.start()]
    return s.strip(" :.,–—-")[:110]

def verified_match(title, category):
    h = norm(headline(title, category))
    for cat, name, url in VERIFIED:
        key = norm(name)
        if category == cat and (h == key or h.startswith(key + " ")):
            return {"url": url, "label": TYPE_LABEL[category], "source": "publisher_verified"}
    return None

def wiki_json(params):
    url = WIKIDATA + "?" + urlencode(dict(params, format="json", formatversion=2))
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=LOOKUP_TIMEOUT) as response:
        return json.load(response)

def extract_websites(record):
    claims = record.get("claims") or {}
    result = []
    for statement in claims.get("P856", []):
        if statement.get("rank") == "deprecated":
            continue
        raw = (((statement.get("mainsnak") or {}).get("datavalue") or {}).get("value"))
        url = safe_url(raw)
        if url and url not in result:
            result.append(url)
    return result

def wiki_match(name, category):
    """Only match exact entity labels/aliases AND a correct entity description."""
    if len(name) < 4 or len(norm(name)) < 4:
        return None, True
    results = wiki_json({"action": "wbsearchentities", "search": name,
                         "language": "en", "uselang": "en", "type": "item", "limit": 5})
    records = results.get("search") or []
    candidate = norm(name)
    for row in records:
        labels = [row.get("label", "")] + [a.get("value", "") for a in row.get("aliases", []) if isinstance(a, dict)]
        if candidate not in {norm(v) for v in labels}:
            continue
        d = str(row.get("description") or "").casefold()
        if category == "news-gaming":
            if not re.search(r"\b(?:video game|videogame|computer game|online game|role-playing game)\b", d):
                continue
        elif not re.search(r"\b(?:smartphone|smart watch|smartwatch|camera|headphones|"
                           r"headset|device|consumer electronic|laptop|tablet|"
                           r"graphics card|router|power station|computer model)\b", d):
            continue
        qid = row.get("id")
        if not isinstance(qid, str) or not re.fullmatch(r"Q[0-9]+", qid):
            continue
        data = wiki_json({"action": "wbgetentities", "ids": qid, "props": "claims",
                          "languages": "en"})
        entity = (data.get("entities") or {}).get(qid) or {}
        urls = extract_websites(entity)
        if urls:
            return {"url": urls[0], "label": TYPE_LABEL[category],
                    "source": "wikidata:P856", "entity": qid}, True
    return None, True

def main():
    if os.environ.get("EDITORIAL_SLOT") not in ("12:30", "19:30"):
        raise SystemExit("Official-link enrichment is restricted to the two editorial slots.")
    imported = json.loads((DATA / "community_imported.json").read_text(encoding="utf-8")).get("posts", [])
    current = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"links": {}, "misses": {}}
    links = current.get("links") or {}
    misses = current.get("misses") or {}
    now = datetime.now(timezone.utc)
    new_found = 0
    searched = 0
    failures = 0
    for item in sorted(imported, key=lambda r: str(r.get("published_at") or r.get("date") or ""), reverse=True):
        if not isinstance(item, dict) or not item.get("text_complete"):
            continue
        category = str(item.get("category") or item.get("type") or "").strip().lower()
        if category in ("tech", "news tech"):
            category = "news-tech"
        elif category in ("gaming", "news gaming"):
            category = "news-gaming"
        if category not in TYPE_LABEL:
            # The importer stores categories sometimes as "type": "news-tech".
            headline_text = str(item.get("title") or "")
            if re.match(r"^\s*#*\s*News\s+Tech\b", headline_text, re.I):
                category = "news-tech"
            elif re.match(r"^\s*#*\s*News\s+Gaming\b", headline_text, re.I):
                category = "news-gaming"
            else:
                continue
        post_id = str(item.get("id") or "")
        if not re.fullmatch(r"Ug[A-Za-z0-9_-]{12,}", post_id):
            continue
        slug = "community-" + re.sub(r"[^a-z0-9]+", "-", post_id.lower()).strip("-")
        if slug in links:
            continue
        title = str(item.get("title") or "")
        selected = verified_match(title, category)
        if not selected:
            cached = misses.get(slug)
            if cached:
                try:
                    if (now - datetime.fromisoformat(cached.replace("Z", "+00:00"))).days < 7:
                        continue
                except (TypeError, ValueError):
                    pass
            if searched >= MAX_NEW_SEARCHES:
                break
            searched += 1
            try:
                selected, _ = wiki_match(headline(title, category), category)
            except Exception as exc:
                failures += 1
                print("Official source unavailable; skipping", slug, type(exc).__name__, flush=True)
                continue  # Do not cache network failures.
        if selected:
            selected["topic"] = headline(title, category)
            selected["category"] = category
            links[slug] = selected
            misses.pop(slug, None)
            new_found += 1
        else:
            misses[slug] = now.isoformat(timespec="seconds")
    current["links"] = links
    current["misses"] = misses
    updated = json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if not CACHE.exists() or CACHE.read_text(encoding="utf-8") != updated:
        CACHE.write_text(updated, encoding="utf-8")
    print("OFFICIAL LINK ENRICHMENT:", new_found, "new verified links;",
          searched, "Wikidata lookups;", failures, "source errors;",
          len(links), "cached official links. No blocking.", flush=True)

if __name__ == "__main__":
    main()
