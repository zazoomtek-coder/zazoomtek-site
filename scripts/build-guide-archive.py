#!/usr/bin/env python3
"""Rigenera l'archivio Guide usando lo stesso layout di News.
Le nuove pagine guida-*.html e guide-*.html entrano automaticamente nell'elenco.
Non modifica mai gli articoli sorgente.
"""
from datetime import datetime, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "news.html"
DESTINATION = ROOT / "guide.html"
PAGE_FILE = re.compile(r"^(?:guida|guide)-[a-zA-Z0-9_-]+\.html$")


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.meta = {}
        self.title = ""
        self.h1 = ""
        self.paragraph = ""
        self._text = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta":
            key = (attrs.get("property") or attrs.get("name") or "").lower()
            if key and attrs.get("content"):
                self.meta.setdefault(key, attrs["content"])
        elif tag in ("title", "h1", "p") and self._text is None:
            self._text = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if tag == self._text:
            content = " ".join("".join(self._buffer).split())
            if tag == "title" and not self.title:
                self.title = content
            elif tag == "h1" and not self.h1:
                self.h1 = content
            elif tag == "p" and content and not self.paragraph and len(content) >= 35:
                self.paragraph = content
            self._text = None
            self._buffer = []

    def handle_data(self, data):
        if self._text:
            self._buffer.append(data)


def attr(markup, name):
    match = re.search(r'\b' + re.escape(name) + r'\s*=\s*["\']([^"\']+)["\']', markup, flags=re.I)
    return unescape(match.group(1)) if match else ""


def image_for(page, metadata):
    for match in re.finditer(r"<img\b[^>]*>", page, re.I):
        tag = match.group()
        if "article-hero" in tag or "hero-image" in tag:
            source = attr(tag, "src")
            if source:
                return source
    figure = re.search(r'<figure\b[^>]*class=["\'][^"\']*hero[^"\']*["\'][^>]*>.*?</figure>', page, re.I | re.S)
    if figure:
        image = re.search(r"<img\b[^>]*>", figure.group(), re.I)
        if image and attr(image.group(), "src"):
            return attr(image.group(), "src")
    return metadata.meta.get("og:image", "")


def date_for(page, metadata):
    raw = (metadata.meta.get("article:published_time")
           or metadata.meta.get("date")
           or metadata.meta.get("datepublished")
           or "")
    if not raw:
        match = re.search(r'"datePublished"\s*:\s*"([^"]+)"', page)
        raw = match.group(1) if match else ""
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value, value.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return datetime.min.replace(tzinfo=timezone.utc), "ZazoomTek"


def guide_record(path):
    page = path.read_text(encoding="utf-8", errors="replace")
    meta = Metadata()
    meta.feed(page)
    title = meta.meta.get("og:title") or meta.h1 or meta.title
    title = re.sub(r"\s*[|–-]\s*ZazoomTek\s*$", "", title or "", flags=re.I).strip()
    if not title:
        return None
    summary = (meta.meta.get("description") or meta.meta.get("og:description")
               or meta.paragraph or "Scopri questa guida su ZazoomTek.")
    published, label = date_for(page, meta)
    image = image_for(page, meta)
    if image.startswith("https://zazoomtek.it/") or image.startswith("https://www.zazoomtek.it/"):
        image = "/" + image.split(".it/", 1)[1]
    return {"slug": path.name, "title": title, "summary": summary,
            "date": published, "date_label": label, "image": image}


def render_records(records):
    if not records:
        return ('<div class="guides-empty" style="background:#fff;padding:30px 24px;'
                'border-bottom:1px solid #ddd;color:#333">'
                '<h2 style="margin:0 0 10px;font-size:1.35rem">Le guide di ZazoomTek</h2>'
                '<p style="margin:0;line-height:1.6">Qui troverai tutte le guide pubblicate,'
                ' con immagine, titolo, data e descrizione, ordinate dalla più recente alla più'
                ' vecchia. La sezione è pronta per le prime pubblicazioni.</p></div>')
    rows = []
    for item in records:
        link = "/" + escape(item["slug"], quote=True)
        title = escape(item["title"])
        summary = escape(item["summary"][:260] + ("…" if len(item["summary"]) > 260 else ""))
        cover = escape(item["image"] or "/ChatGPT.png", quote=True)
        search = escape((item["title"] + " " + item["summary"]).lower(), quote=True)
        rows.append(
            f'<article class="news-row" data-news-search="{search}">'
            f'<a href="{link}"><img src="{cover}" alt="{title}" loading="lazy"></a>'
            f'<div class="news-copy"><h2><a href="{link}">{title}</a></h2>'
            f'<div class="news-meta">ZazoomTek · {escape(item["date_label"])}</div>'
            f'<p>{summary}</p><a class="news-read" href="{link}">Leggi la guida ›</a>'
            f'</div></article>')
    return "\n".join(rows)


def build():
    news = TEMPLATE.read_text(encoding="utf-8")
    if not re.search(r'<aside class="news-sidebar">[\s\S]*?</aside>', news):
        raise RuntimeError("Impossibile leggere il layout della pagina News")
    side = re.search(r'<aside class="news-sidebar">[\s\S]*?</aside>', news).group()
    records = [item for path in ROOT.iterdir()
               if path.is_file() and PAGE_FILE.fullmatch(path.name)
               for item in [guide_record(path)] if item]
    # Nuove guide in cima; per date mancanti usa nome file come ordine stabile.
    records.sort(key=lambda row: (row["date"], row["slug"]), reverse=True)
    main = ('<main class="news-page"><div class="zt-wrap news-layout">'
            '<section class="news-main"><div class="news-main-head"><h1>Guide</h1></div>'
            '<div class="news-list" id="guideList">' + render_records(records)
            + '</div></section>' + side + '</div></main>')
    content = news
    content = re.sub(r'<title>[^<]*</title>',
                     '<title>Guide: tutorial e consigli pratici | ZazoomTek</title>', content, count=1)
    content = re.sub(r'<meta name="description" content="[^"]*">',
                     '<meta name="description" content="Tutte le guide di ZazoomTek in un unico archivio: tutorial su PC, Windows, smartphone, console, gaming e reti Wi-Fi.">',
                     content, count=1)
    content = re.sub(r'<link rel="canonical" href="[^"]*">',
                     '<link rel="canonical" href="https://zazoomtek.it/guide.html">',
                     content, count=1)
    content = content.replace('<a class="active" href="/news.html">News</a>',
                              '<a href="/news.html">News</a>', 1)
    if '<a href="/guide.html">Guide</a>' not in content:
        raise RuntimeError("La pagina News non include ancora Guide nel menu")
    content = content.replace('<a href="/guide.html">Guide</a>',
                              '<a class="active" aria-current="page" href="/guide.html">Guide</a>', 1)
    content = re.sub(r'<div class="zt-strip">[\s\S]*?</div></div>',
                     '<div class="zt-strip"><div class="zt-wrap"><strong>Guide</strong>'
                     '<span>Tutorial e consigli pratici su tecnologia e gaming</span></div></div>',
                     content, count=1)
    content, count = re.subn(r'<main class="news-page">[\s\S]*?</main>', lambda _: main,
                            content, count=1)
    if count != 1:
        raise RuntimeError("Impossibile sostituire l'archivio News con Guide")
    metadata = ('<meta name="robots" content="index,follow,max-image-preview:large">'
                '<meta property="og:type" content="website">'
                '<meta property="og:site_name" content="ZazoomTek">'
                '<meta property="og:title" content="Guide: tutorial e consigli pratici | ZazoomTek">'
                '<meta property="og:description" content="Tutte le guide pratiche di ZazoomTek, raccolte in ordine cronologico.">'
                '<meta property="og:url" content="https://zazoomtek.it/guide.html">')
    content = content.replace('</head>', metadata + '</head>', 1)
    before = DESTINATION.read_text(encoding="utf-8") if DESTINATION.exists() else ""
    if before != content:
        DESTINATION.write_text(content, encoding="utf-8")
        print(f"Aggiornata Guide: {len(records)} articoli (dal più recente al più vecchio).")
    else:
        print(f"Guide già aggiornata: {len(records)} articoli.")


if __name__ == "__main__":
    build()
