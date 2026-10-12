#!/usr/bin/env python3
"""Hourly, rights-safe ZazoomTek featured editorial publishing.
Select prominent outside headlines, reuse already published Community news first,
and generate wholly original, evidence-checked articles only when truly absent.
Failure to access evidence or to verify factual claims never publishes a story.
"""
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from featured_article_layout import decorate

def module(filename, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

trend = module("trending-crosscheck.py", "zt_trends")
sources = module("check-special-sources.py", "zt_sources")
audit = module("auto-approve-special.py", "zt_audit")
covers = module("build-special-covers.py", "zt_covers")

LEDGER = ROOT / "featured-import-state.json"
APPROVED = ROOT / "approved-special-articles.json"
MANUAL = ROOT / "manual-news.json"
SECTIONS = ("tech", "tech", "gaming", "gaming", "tech-impact", "gaming-inside")
KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
NOW = lambda: dt.datetime.now(dt.timezone.utc)
SOURCE_IDS = {"igncom", "gamespot", "eurogamer", "polygon", "pcgamer", "zazoom",
              "hdblog", "dday", "smartworld", "tomshw", "hwupgrade",
              "multiplayer", "everyeye", "spaziogames", "ign", "gamesurf"}

def read(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return fallback

def write(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def slugify(title):
    text = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:75].strip("-")

def topic_section(item):
    title = str(item.get("title", ""))
    kind = item.get("kind", "")
    low = trend.norm(title)
    game = kind == "gaming" or trend.classify(title, "gaming" if kind == "gaming" else "") in ("gaming", "gaming-inside")
    politics = bool(re.search(
        r"\b(law|laws|regulation|regulator|government|antitrust|lawsuit|"
        r"copyright|privacy|ban|banned|union|unionize|layoffs|laid off|"
        r"fired|rights|rights of|censorship|workers|labor|labour|"
        r"legge|norme|privacy|licenziament|sindacat|antitrust|"
        r"censura|diritti|sicurezza|tribunale|indagine|tutela|"
        r"acquisition|acquired)\b", low))
    if politics:
        return "gaming-inside" if game else "tech-impact"
    return "gaming" if game else "tech"

def active_sources():
    state = read(ROOT / "trending-sources.json", {})
    try:
        generated = dt.datetime.fromisoformat(state["generated_utc"])
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=dt.timezone.utc)
        if NOW() - generated > dt.timedelta(hours=3):
            print("Headline cache is stale; keeping existing carousel.")
            return []
    except (KeyError, TypeError, ValueError):
        return []
    incoming = []
    for item in state.get("items", []):
        if item.get("source") not in SOURCE_IDS or not item.get("url", "").startswith("https://"):
            continue
        if not 1 <= int(item.get("rank", 99)) <= 15:
            continue
        try:
            stamp = dt.datetime.fromisoformat(item.get("last_seen", ""))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=dt.timezone.utc)
            if NOW() - stamp > dt.timedelta(hours=30):
                continue
        except (ValueError, TypeError):
            continue
        if not trend.safe_url(item["url"], next(s[3] for s in trend.SITES if s[0] == item["source"])):
            continue
        item = dict(item)
        item["section"] = topic_section(item)
        incoming.append(item)
    incoming.sort(key=lambda x: (int(x.get("rank", 99)), x.get("first_seen", "")))
    return incoming

def score_existing(source_title, title):
    # Exact-event matching is deliberately conservative: product numbers and
    # named entities must overlap. An English/Italian near match can be checked
    # by the independent fact-checking model below if no clear match is found.
    a, b = set(trend.tokens(source_title)), set(trend.tokens(title))
    if a and b:
        x = {v for v in a if v.isdigit()}
        y = {v for v in b if v.isdigit()}
        if x and y and not (x & y):
            return 0
    return trend.similarity(source_title, title)

def existing_match(item, published):
    possibilities = [(score_existing(item["title"], x["title"]), x)
                     for x in published if x.get("section") == item["section"]]
    possibilities.sort(key=lambda row: row[0], reverse=True)
    return possibilities[0][1] if possibilities and possibilities[0][0] >= .56 else None

def ai_json(prompt, output_tokens=6500):
    if not KEY:
        return None
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + MODEL + ":generateContent"
    data = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json",
                                 "temperature": .12, "maxOutputTokens": output_tokens}}
    request = urllib.request.Request(endpoint, data=json.dumps(data).encode(),
          headers={"Content-Type": "application/json", "x-goog-api-key": KEY}, method="POST")
    with urllib.request.urlopen(request, timeout=85) as response:
        body = json.load(response)
    text = "".join(part.get("text", "") for c in body.get("candidates", [])
                   for part in c.get("content", {}).get("parts", []))
    return json.loads(text)

def multilingual_reuse(item, published):
    # The model only classifies a shared event: it cannot create or change a URL.
    same_category = [x for x in published if x.get("section") == item["section"]][:110]
    if not same_category or not KEY:
        return None
    options = [{"url": x["url"], "title": x["title"]} for x in same_category]
    prompt = ("Confronta un titolo di cronaca estera con le notizie GIA pubblicate su ZazoomTek. "
              "Solo quando si riferiscono ESATTAMENTE allo stesso avvenimento, prodotto, versione, "
              "data e protagonisti restituisci il relativo URL preso DALL'ELENCO. "
              "Differenti annunci della stessa serie non sono duplicati. "
              "Se dubbio restituisci null. JSON: {\"url\":null oppure \"/news-...html\"}. "
              "NUOVA NOTIZIA: " + item["title"] + "\nESISTENTI: " +
              json.dumps(options, ensure_ascii=False))
    try:
        result = ai_json(prompt, 500)
    except (ValueError, urllib.error.URLError, TimeoutError) as error:
        print("Optional multilingual match unavailable:", type(error).__name__)
        return None
    choice = result.get("url") if isinstance(result, dict) else None
    matched = next((p for p in same_category if p["url"] == choice), None)
    if not matched:
        return None
    # At least one distinctive named or numeric token shared by both titles.
    common = set(trend.tokens(item["title"])) & set(trend.tokens(matched["title"]))
    distinct = common - {"gaming", "games", "game", "sony", "microsoft", "nintendo",
                         "apple", "playstation", "xbox", "google", "steam", "2026", "2027"}
    return matched if distinct else None

def documents(item, peers):
    requests = [item] + [p for p in peers if p["url"] != item["url"]][:2]
    docs = []
    origins = set()
    for row in requests:
        try:
            page = sources.fetch(row["url"])
        except (ValueError, urllib.error.URLError, TimeoutError, OSError) as error:
            print("Source unavailable:", row["url"], type(error).__name__)
            continue
        words = len(" ".join(page.get("excerpts", [])).split())
        host = (sources.urllib.parse.urlsplit(page["url"]).hostname or "").removeprefix("www.")
        if words < 180 or not host or host in origins:
            continue
        origins.add(host)
        docs.append({"url": page["url"], "excerpts": page["excerpts"][:20],
                     "metadata": page.get("metadata", {}),
                     "text": " ".join(page["excerpts"])})
    return docs

def draft_original(item, docs):
    evidence = [{"url": d["url"], "metadata": d["metadata"], "excerpts": d["excerpts"][:17]}
                for d in docs]
    instruction = (
       "Sei un redattore di ZazoomTek.it. Scrivi una NOTIZIA COMPLETAMENTE ORIGINALE "
       "in italiano partendo da FATTI DOCUMENTATI, NON una traduzione e NON una parafrasi "
       "del testo altrui. Proponi nuovo titolo, sommario e 4-6 paragrafi corposi e "
       "compatti (400-600 parole effettive complessive nel corpo). "
       "Non copiare frasi, sequenza del racconto, immagini o esclusive dalle fonti. "
       "Attribuisci nel testo le dichiarazioni o il reportage del giornale originale. "
       "Niente speculazioni, rumors come fatti, benchmark o informazioni inventate. "
       "Le fonti possono essere inglesi, ma il contenuto deve essere italiano. "
       "Se i dati sono insufficienti, {\"status\":\"insufficient_evidence\"}. "
       "Restituisci SOLO JSON: {\"status\":\"draft\",\"title\":\"...\","
       "\"summary\":\"...\",\"paragraphs\":[\"...\"],\"date\":\"YYYY-MM-DD\"}. "
       "Usa la data corrente se i metadati di pubblicazione non sono attendibili, "
       "senza dichiarare che l'evento si è verificato oggi. "
       "CATEGORIA: " + item["section"] + "\nTITOLO DELLA PISTA: " + item["title"] +
       "\nDOCUMENTI DI RICERCA: " + json.dumps(evidence, ensure_ascii=False)[:21000])
    raw = ai_json(instruction)
    if not isinstance(raw, dict) or raw.get("status") != "draft":
        return None
    result = {"title": raw.get("title"), "summary": raw.get("summary"),
              "paragraphs": raw.get("paragraphs"), "status": "needs_human_fact_check"}
    if not isinstance(result["paragraphs"], list):
        return None
    try:
        verdict = audit.review(result, docs)
    except (ValueError, KeyError, urllib.error.URLError, TimeoutError) as error:
        print("Fact audit unavailable:", type(error).__name__)
        return None
    if not audit.verified(result, docs, verdict):
        print("Article rejected by strict quote-grounded audit:", item["title"][:65])
        return None
    return result

def original_cover(item, name):
    folder = ROOT / "assets" / "special"
    folder.mkdir(parents=True, exist_ok=True)
    relative = "/assets/special/" + name + ".webp"
    path = ROOT / relative.lstrip("/")
    model = {"section": "gaming" if item["section"] in ("gaming", "gaming-inside") else "tech",
             "slug": name, "title": item["title"], "summary": item["summary"],
             "cover_label": {"tech":"TECNOLOGIA","gaming":"GAMING",
                  "tech-impact":"TECH IMPACT","gaming-inside":"GAMING INSIDE"}[item["section"]]}
    path.write_bytes(covers.encode(covers.render(model, None)))
    return relative

def card(item):
    path = ROOT / item["url"].lstrip("/")
    image = item.get("image", "")
    return bool(item.get("url","").startswith("/") and path.is_file() and
                (image.startswith("https://") or
                 (image.startswith("/") and (ROOT/image.lstrip("/")).is_file())))

def make_standard_page(item, filename):
    esc = lambda s: html.escape(str(s), quote=True)
    body = "".join("<p>" + esc(p) + "</p>" for p in item["paragraphs"])
    page = ('<!doctype html><html lang="it"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>' + esc(item["title"]) + ' | ZazoomTek</title>'
            '<meta name="description" content="' + esc(item["summary"]) + '">'
            '<link rel="canonical" href="https://zazoomtek.it/' + filename + '">'
            '</head><body><main><div class="eyebrow">News · ' +
            esc(item["section"].upper()) + '</div><h1>' + esc(item["title"]) +
            '</h1><div class="meta">' + NOW().date().isoformat() +
            ' · Redazione ZazoomTek</div><figure class="hero"><img src="' +
            esc(item["image"]) + '" alt="' + esc(item["title"]) +
            '"></figure><p class="lead">' + esc(item["summary"]) +
            '</p><div class="article-copy">' + body +
            '</div><p><a href="/news.html">← Tutte le News</a></p></main></body></html>')
    (ROOT / filename).write_text(decorate(page, "News"), encoding="utf-8")

def inject_news_row(item):
    path = ROOT / "news.html"
    body = path.read_text(encoding="utf-8")
    if 'href="' + item["url"] + '"' in body:
        return
    esc = lambda v: html.escape(str(v), quote=True)
    row = ('<article class="news-row" data-auto-trend="true"><a href="' +
           esc(item["url"]) + '"><img src="' + esc(item["image"]) +
           '" loading="lazy" alt="' + esc(item["title"]) +
           '"></a><div class="news-copy"><h2><a href="' +
           esc(item["url"]) + '">' + esc(item["title"]) +
           '</a></h2><div class="news-meta">ZazoomTek · ' +
           NOW().date().isoformat() + '</div><p>' + esc(item["summary"]) +
           '</p><a class="news-read" href="' + esc(item["url"]) +
           '">Leggi tutto</a></div></article>')
    pattern = '<div class="news-list" id="newsList">'
    if body.count(pattern) != 1:
        raise RuntimeError("Cannot safely insert standard article into NEWS")
    path.write_text(body.replace(pattern, pattern + row, 1), encoding="utf-8")

def save_original(item, content, docs, records):
    fingerprint = hashlib.sha256(item["url"].encode()).hexdigest()[:14]
    base = slugify(content["title"])[:56] + "-" + fingerprint
    now = NOW()
    article = {**content, "section": item["section"], "date": now.date().isoformat()}
    if item["section"] in ("tech", "gaming"):
        filename = "news-auto-" + base + ".html"
        article["url"] = "/" + filename
        article["image"] = original_cover(article, "news-auto-" + base)
        make_standard_page(article, filename)
        manual = read(MANUAL, {"items":[]})
        if not any(x.get("slug") == filename for x in manual.get("items",[])):
            manual["items"].insert(0, {"slug": filename, "title": article["title"],
                    "image": article["image"], "excerpt": article["summary"],
                    "date": article["date"], "published_at": now.isoformat(),
                    "kind": "trend"})
            write(MANUAL, manual)
        inject_news_row(article)
    else:
        name = "tech-impact" if item["section"] == "tech-impact" else "gaming-inside"
        short = "auto-" + base
        filename = name + "-" + short + ".html"
        article["url"] = "/" + filename
        article["image"] = original_cover(article, filename[:-5])
        approved = read(APPROVED, {"articles":[]})
        src_urls = [d["url"] for d in docs]
        if not any(x.get("slug") == short and x.get("section") == ("tech" if name == "tech-impact" else "gaming") for x in approved["articles"]):
            approved["articles"].append({
                "section": "tech" if name == "tech-impact" else "gaming",
                "slug": short, "title": article["title"], "summary": article["summary"],
                "paragraphs": article["paragraphs"], "date": article["date"],
                "image": article["image"], "sources": src_urls,
                "auto_approved": True, "approval_method": "strict_source_evidence",
                "evidence_review": {"paragraphs_supported": True, "source_count":len(docs)},
                "source_fingerprints": [hashlib.sha256(u.encode()).hexdigest() for u in src_urls],
                "trend_verified": len(docs) >= 2, "cover_mode": "original",
                "home_featured": len(docs) >= 2})
            write(APPROVED, approved)
    records["by_source"][item["url"]] = {"article_url": article["url"],
       "section": article["section"], "title": article["title"],
       "image": article["image"], "published_date": article["date"]}
    return {k: article[k] for k in ("url", "title", "image", "section")}

def peers_for(item, all_items):
    found = []
    for x in all_items:
        if x["source"] == item["source"] or x["url"] == item["url"]:
            continue
        if x["section"] != item["section"]:
            continue
        if trend.similarity(x["title"], item["title"]) >= .58:
            found.append(x)
    return found[:2]

def main():
    if not KEY:
        print("GEMINI_API_KEY missing: no automatic article generation. Existing content unchanged.")
        return
    state = read(LEDGER, {"by_source":{}, "selected":[]})
    state.setdefault("by_source", {})
    current = active_sources()
    if not current:
        return
    owned = trend.owned_candidates()
    print("Eligible featured headlines:", len(current), "already published:", len(owned))
    chosen = []
    reserved = set()
    for section in SECTIONS:
        option = None
        candidates = [x for x in current if x["section"] == section][:18]
        for item in candidates:
            stored = state["by_source"].get(item["url"])
            if stored:
                if stored["section"] == section and (ROOT/stored["article_url"].lstrip("/")).is_file():
                    already = {"url":stored["article_url"], "title":stored["title"],
                               "image":stored["image"], "section":section}
                    if already["url"] not in reserved and card(already):
                        option = already
                        break
                continue
            match = existing_match(item, owned)
            if not match:
                match = multilingual_reuse(item, owned)
            if match and match["url"] not in reserved:
                state["by_source"][item["url"]] = {
                    "article_url":match["url"], "title":match["title"],
                    "image":match["image"], "section":section,
                    "published_date": NOW().date().isoformat()}
                option = {k:match[k] for k in ("url", "title", "image", "section")}
                break
            if match:
                continue
            peers = peers_for(item, current)
            docs = documents(item, peers)
            if not docs:
                continue
            try:
                draft = draft_original(item, docs)
            except (ValueError, urllib.error.URLError, TimeoutError) as error:
                print("Draft rejected:", type(error).__name__)
                continue
            if draft is None:
                continue
            option = save_original(item, draft, docs, state)
            owned.append(option)
            print("New verified original:", section, option["url"])
            break
        if option and option["url"] not in reserved:
            chosen.append(option)
            reserved.add(option["url"])
    # Prior selections remain eligible when a desk has no new verified lead.
    # The trend picker fills any missing slots with its existing own-news logic.
    if chosen:
        state["selected"] = chosen
    state["checked_at"] = NOW().isoformat()
    write(LEDGER, state)
    if any(x.get("url","").startswith(("/tech-impact-auto-","/gaming-inside-auto-")) for x in chosen):
        publisher = module("publish-special-news.py", "zt_special_publisher")
        publisher.main()
    # Re-run once all new pages and special archives actually exist.
    if chosen:
        trend.apply()
    print("Hourly editorial review complete:",len(chosen),"/6 verified source-led placements")

def selftest():
    assert SECTIONS == ("tech","tech","gaming","gaming","tech-impact","gaming-inside")
    assert topic_section({"kind":"gaming","title":"Xbox game studio employees union rights"}) == "gaming-inside"
    assert topic_section({"kind":"gaming","title":"Nintendo Switch Zelda sequel announced"}) == "gaming"
    assert topic_section({"kind":"tech","title":"Government AI privacy regulation advances"}) == "tech-impact"
    assert slugify("Prova: Titolo Originale!").startswith("prova-titolo-originale")
    assert len(SOURCE_IDS) == 16
    print("AUTO FEATURED REPORTER SELF-TEST OK")

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        selftest()
    else:
        main()
