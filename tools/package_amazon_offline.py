#!/usr/bin/env python3
"""Package the REAL built SpotNews website as an offline ZIP (no deployment)."""
from pathlib import Path
from urllib.parse import urlsplit
import html
import os
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = ROOT / "anteprima-zazoomtek-amazon"
ZIP = ROOT / "ZazoomTek_Anteprima_Amazon_Pagine_Reali_29-10-2026.zip"

def local_route(route, original):
    if not route.startswith("/") or route.startswith("//"):
        return route
    parsed = urlsplit(route)
    dest = DIST / parsed.path.lstrip("/")
    if not parsed.path or parsed.path == "/":
        dest = DIST / "index.html"
    elif parsed.path.endswith("/"):
        dest /= "index.html"
    elif not dest.exists():
        candidate = DIST / (parsed.path.lstrip("/") + ".html")
        if candidate.exists():
            dest = candidate
        else:
            return route
    if dest.is_dir():
        dest /= "index.html"
    if not dest.is_file():
        return route
    relative = os.path.relpath(dest, original.parent).replace("\\", "/")
    return relative + (("?" + parsed.query) if parsed.query else "") + (("#" + parsed.fragment) if parsed.fragment else "")

def main():
    if not (DIST / "index.html").is_file():
        raise RuntimeError("Missing real build dist/index.html")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DIST, OUT)
    for file in OUT.rglob("*.html"):
        original = DIST / file.relative_to(OUT)
        source = file.read_text(encoding="utf-8")
        def rewrite(match):
            attr, quote, raw = match.groups()
            url = local_route(html.unescape(raw), original)
            return attr + quote + html.escape(url, quote=True) + quote
        source = re.sub(r'((?:href|src|poster)=)(["\'])(/[^"\']*)\2', rewrite, source)
        file.write_text(source, encoding="utf-8")
    for file in OUT.rglob("*.css"):
        source = file.read_text(encoding="utf-8")
        original = DIST / file.relative_to(OUT)
        prefix = Path(os.path.relpath(DIST / "assets", original.parent)).as_posix()
        source = re.sub(r'url\((["\']?)/assets/', lambda m: 'url(' + m.group(1) + prefix + '/', source)
        file.write_text(source, encoding="utf-8")
    for file in OUT.rglob("*.html"):
        source = file.read_text(encoding="utf-8")
        if 'class="related"' in source and 'inner-layout' in source:
            assert 'inner-amazon-fill' in source, "Missing Amazon showcase: " + str(file)
    howto = (
        "ZAZOOMTEK.IT - ANTEPRIMA AMAZON NELLE PAGINE REALI\n"
        "29 ottobre 2026 | Solo file locali, nessun deploy Cloudflare.\n\n"
        "1. ESTRAI tutto lo ZIP in una cartella sul PC.\n"
        "2. Apri index.html con Firefox o Chrome.\n"
        "3. Per il confronto indicato nello screenshot apri:\n"
        "   community-extra-silki-sedia-3d-seta-riciclata-tracciabilita.html\n"
        "   Scorri in basso: a destra di Articoli correlati trovi la vetrina Amazon.\n"
        "4. Verifica anche alcune news/recensioni: il modulo e' inserito dal template\n"
        "   in tutte le pagine editoriali con Articoli correlati, presenti e future.\n"
        "5. La Home e le altre sezioni del sito non vengono modificate dal test.\n"
        "6. Alcune funzioni remote (Studio, API, ricerca, player YouTube) non possono\n"
        "   funzionare da disco; per verificarle serve il sito online.\n\n"
        "Sorgente: build completa del branch feature/amazon-empty-sidebar-preview-20261029.\n"
        "Il modulo usa le risorse gia' presenti e conserva la disclosure affiliata.\n"
        "NON E' STATO ESEGUITO ALCUN DEPLOY.\n"
    )
    (OUT / "LEGGIMI_ANTEPRIMA_AMAZON.txt").write_text(howto, encoding="utf-8")
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for file in OUT.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(OUT))
    with zipfile.ZipFile(ZIP) as check:
        assert check.testzip() is None, "Corrupt zip"
        assert len(check.namelist()) >= 235, "Incomplete snapshot"
    print("ZIP READY", ZIP.name, "files", len(list(OUT.rglob("*"))), "bytes", ZIP.stat().st_size, flush=True)

if __name__ == "__main__":
    main()
