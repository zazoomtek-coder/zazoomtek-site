"""Repair publication dates in every published article/review on each live build.

The original visible calendar date is preferred. For corrupted/relative display
values use a verified dated archive row, then the page's own publication metadata.
Never replace a real publication date with today's deployment date.
"""
from datetime import datetime
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo
import re

MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
MONTH_PATTERN = "|".join(MONTHS)
ITALIAN_DATE = re.compile(r"\b([0-3]?\d)\s+(" + MONTH_PATTERN + r")\s+(20\d{2})\b", re.I)
CALENDAR_DATE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
ARTICLE_DATE = re.compile(
    r'(<div\b[^>]*class=["\'][^"\']*\barticle-meta\b[^"\']*["\'][^>]*>'
    r'[\s\S]*?<span[^>]*>\s*📅\s*)([\s\S]*?)(</span>)', re.I
)
PUBLISHED_META = re.compile(
    r'<meta\b[^>]*\bproperty=["\']article:published_time["\'][^>]*'
    r'\bcontent=["\']([^"\']+)', re.I
)
PUBLISHED_JSON = re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I)
ARCHIVE_META = re.compile(r'<div\b[^>]*class=["\']news-meta["\'][^>]*>(.*?)</div>', re.I | re.S)
ARCHIVE_ROW = re.compile(r'<article\b[^>]*class=["\'][^"\']*\bnews-row\b[^"\']*["\'][^>]*>.*?</article>', re.I | re.S)
ARTICLE_LINK = re.compile(r'href=["\']/([^"\']+\.html)["\']', re.I)


def calendar_label(value):
    """Accept only specific complete dates, never relative YouTube timestamps."""
    raw = unescape(re.sub(r"<[^>]*>", "", value or "")).strip()
    match = ITALIAN_DATE.search(raw)
    if match:
        day, month, year = match.groups()
        try:
            datetime(int(year), MONTHS.index(month.lower()) + 1, int(day))
            return f"{int(day)} {month.lower()} {year}"
        except ValueError:
            return ""
    match = CALENDAR_DATE.fullmatch(raw)
    if match:
        try:
            date = datetime.fromisoformat(raw)
            return f"{date.day} {MONTHS[date.month - 1]} {date.year}"
        except ValueError:
            return ""
    return ""


def label_from_iso(value):
    raw = (value or "").strip()
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if value.tzinfo is not None:
            value = value.astimezone(ZoneInfo("Europe/Rome"))
        return f"{value.day} {MONTHS[value.month - 1]} {value.year}"
    except (ValueError, TypeError, OverflowError):
        return ""


def archive_dates(root):
    dates = {}
    archives = [root / "news.html", root / "recensioni-scritte.html"]
    archives.extend(sorted(root.glob("news-[0-9]*.html")))
    archives.extend(sorted(root.glob("recensioni-scritte-[0-9]*.html")))
    for path in archives:
        if not path.is_file():
            continue
        document = path.read_text(encoding="utf-8")
        for match in ARCHIVE_ROW.finditer(document):
            row = match.group()
            link = ARTICLE_LINK.search(row)
            metadata = ARCHIVE_META.search(row)
            if not link or not metadata:
                continue
            label = calendar_label(metadata.group(1))
            if label:
                dates.setdefault(link.group(1), label)
    return dates


def repair_publication_dates(root):
    root = Path(root)
    archival = archive_dates(root)
    repaired = unresolved = audited = 0
    for path in sorted(root.glob("*.html")):
        if path.name.startswith(("preview-", "anteprima-")):
            continue
        page = path.read_text(encoding="utf-8")
        if "article-meta" not in page or "📅" not in page:
            continue
        found = ARTICLE_DATE.search(page)
        if not found:
            continue
        audited += 1
        current = unescape(re.sub(r"<[^>]*>", "", found.group(2))).strip()
        existing = calendar_label(current)
        # Preserve real calendar dates already printed by the article editor.
        if existing and "html.escape(" not in current and "p.get(" not in current:
            continue
        metadata = PUBLISHED_META.search(page)
        published = metadata.group(1) if metadata else ""
        if not published:
            metadata = PUBLISHED_JSON.search(page)
            published = metadata.group(1) if metadata else ""
        correct = archival.get(path.name) or label_from_iso(published)
        if not correct:
            unresolved += 1
            if "html.escape(" in current or "p.get(" in current:
                raise RuntimeError(path.name + ": leaked template without publication metadata")
            continue  # Never invent an exact date for undated legacy imports.
        replacement = found.group(1) + correct + found.group(3)
        page = page[:found.start()] + replacement + page[found.end():]
        if "📅 {html.escape(p.get(" in page:
            raise RuntimeError(path.name + ": unrendered publication date remains")
        path.write_text(page, encoding="utf-8")
        repaired += 1
    return repaired, unresolved, audited
