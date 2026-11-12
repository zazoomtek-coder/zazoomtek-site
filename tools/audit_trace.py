#!/usr/bin/env python3
"""Record-by-record editorial traceability audit for every static-site build."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET
import json
import re


class CanonicalReader(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href", ""))
        if tag == "a":
            href = attrs.get("href")
            if href:
                self.links.append(href)


def _records(path):
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("posts", []) if isinstance(payload, dict) else None
    if not isinstance(values, list):
        raise ValueError("Invalid source collection: " + str(path))
    return values


def _sitemap_urls(root):
    sitemap = ET.parse(root / "sitemap.xml").getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = set()
    if sitemap.tag.endswith("sitemapindex"):
        for node in sitemap.findall("sm:sitemap/sm:loc", ns):
            part = Path(node.text.rsplit("/", 1)[-1])
            document = ET.parse(root / part).getroot()
            urls.update(x.text for x in document.findall(".//sm:url/sm:loc", ns))
    else:
        urls.update(x.text for x in sitemap.findall(".//sm:url/sm:loc", ns))
    return urls


def run(project_root, output_root, rows, events):
    project_root = Path(project_root)
    output_root = Path(output_root)
    domain = "https://zazoomtek.it"
    rows_by_slug = {str(row.get("slug") or ""): row for row in rows}
    rows_by_id = {str(row.get("source_post_id") or ""): row for row in rows
                  if row.get("source_post_id")}
    sitemap_urls = _sitemap_urls(output_root)
    errors = []
    lines = []
    expected_sources = (
        "posts.json", "community_imported.json", "community_full.json",
        "studio_posts.json", "community.json"
    )
    raw_counts = {}
    for name in expected_sources:
        raw_counts[name] = len(_records(project_root / "data" / name))

    # Keep the final state for each source record; intermediate pipeline stages
    # deliberately emit candidate -> generated or candidate -> merged transitions.
    latest = {}
    for event in events:
        latest[(event.get("source"), event.get("index"))] = event

    status_counts = Counter()
    for name in expected_sources:
        count = raw_counts[name]
        for index in range(count):
            event = latest.get((name, index))
            if event is None:
                errors.append(f"{name}[{index}]: no trace event was emitted")
                lines.append(f"LOST | {name}[{index}] | reason=no trace event from build pipeline")
                continue
            status = event.get("status", "unknown")
            reason = event.get("reason", "")
            target = event.get("target", "")
            status_counts[status] += 1
            title = event.get("title", "")
            identifier = event.get("id", "")
            label = f"{name}[{index}] id={identifier or '-'} title={title!r}"
            if status == "generated":
                slug = target or event.get("slug", "")
                url = domain + "/" + slug
                page = output_root / (slug + ".html")
                if slug not in rows_by_slug:
                    errors.append(label + ": generated row missing from final article set")
                if not page.is_file():
                    errors.append(label + ": HTML file missing: " + str(page.name))
                if url not in sitemap_urls:
                    errors.append(label + ": canonical URL missing from sitemap: " + url)
                if page.is_file():
                    parser = CanonicalReader()
                    parser.feed(page.read_text(encoding="utf-8"))
                    if parser.canonicals != [url]:
                        errors.append(label + ": canonical mismatch " + repr(parser.canonicals) +
                                      " expected " + url)
                lines.append(f"GENERATED | {label} | url={url}")
            elif status == "merged_duplicate":
                canonical_row = rows_by_id.get(identifier)
                slug = str(canonical_row.get("slug") or "") if canonical_row else target
                url = domain + "/" + slug
                if slug not in rows_by_slug or url not in sitemap_urls:
                    errors.append(label + ": duplicate-source target is not a sitemap article: " + url)
                lines.append(f"MERGED DUPLICATE | {label} | canonical_target={url} | reason={reason}")
            elif status == "merged_alias":
                target_row = rows_by_id.get(target)
                if target_row is None:
                    errors.append(label + ": historical alias target ID has no generated article: " + target)
                    target_url = "UNRESOLVED"
                else:
                    target_url = domain + "/" + str(target_row["slug"])
                    if target_url not in sitemap_urls:
                        errors.append(label + ": historical alias target missing from sitemap: " + target_url)
                lines.append(f"MERGED ALIAS | {label} | canonical_target={target_url} | reason={reason}")
            elif status == "excluded":
                if not reason:
                    errors.append(label + ": excluded without a technical reason")
                lines.append(f"EXCLUDED WITH REASON | {label} | reason={reason}")
            else:
                errors.append(label + ": unfinished pipeline status " + str(status))
                lines.append(f"UNRESOLVED | {label} | status={status} | reason={reason}")

    # Every final article must have one physical HTML page and one exact sitemap URL.
    for row in rows:
        slug = str(row.get("slug") or "")
        url = domain + "/" + slug
        page = output_root / (slug + ".html")
        if not slug or not page.is_file():
            errors.append("Final article has no physical HTML file: " + slug)
        if url not in sitemap_urls:
            errors.append("Final article is absent from sitemap.xml: " + url)

    # All generated archive and pagination routes must be discoverable in the sitemap.
    archive_prefixes = (
        "news", "news-tech", "news-gaming", "recensioni", "recensioni-tech",
        "recensioni-gaming", "guide", "speciali", "extra"
    )
    archive_pages = [p for p in output_root.glob("*.html")
                     if p.stem in archive_prefixes or any(
                         p.stem.startswith(prefix + "-page-") or
                         p.stem.startswith(prefix + "-archivio")
                         for prefix in archive_prefixes)]
    for page in archive_pages:
        url = domain + ("/" + page.stem)
        if url not in sitemap_urls:
            errors.append("Archive/pagination page missing from sitemap: " + url)

    # Verify that the homepage exposes real crawlable links to the main archives.
    home = output_root / "index.html"
    if not home.is_file():
        errors.append("Homepage HTML is missing")
    else:
        parser = CanonicalReader()
        parser.feed(home.read_text(encoding="utf-8"))
        home_links = set(parser.links)
        for route in ("/news", "/recensioni", "/guide", "/speciali", "/extra"):
            if route not in home_links:
                errors.append("Homepage has no real anchor to archive " + route)

    report = {
        "sources": raw_counts,
        "source_records": sum(raw_counts.values()),
        "final_articles": len(rows),
        "html_article_pages": sum((output_root / (str(row.get("slug")) + ".html")).is_file()
                                  for row in rows),
        "sitemap_urls": len(sitemap_urls),
        "archive_pages": len(archive_pages),
        "statuses": dict(status_counts),
        "errors": errors,
        "record_log": lines,
    }
    report_path = project_root / "build-trace-audit.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print("EDITORIAL TRACEABILITY AUDIT")
    print(json.dumps({k: v for k, v in report.items() if k != "record_log"},
                     ensure_ascii=False, indent=2))
    for line in lines:
        print(line, flush=True)
    if errors:
        raise AssertionError("Editorial traceability audit failed: " +
                             str(len(errors)) + " unexplained/missing records or routes. " +
                             "Full report: build-trace-audit.json")
    print("EDITORIAL TRACEABILITY AUDIT PASS: every source record is generated, "
          "merged to a canonical article, or excluded with an explicit technical reason; "
          "all generated article and archive routes are in the sitemap.", flush=True)
    return report


if __name__ == "__main__":
    raise SystemExit("Import run() from tools/build.py; this audit requires the exact in-memory build rows.")
