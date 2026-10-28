#!/usr/bin/env python3
"""Offline snapshot of the REAL SpotNews build: no deployment or Cloudflare API."""
from pathlib import Path
from urllib.parse import urlsplit
import html
import os
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = ROOT / "anteprima-zazoomtek-spotnews"
ZIP = ROOT / "ZazoomTek_SpotNews_Anteprima_Completa_28-10-2026.zip"

def local_route(route, from_file):
    if not route.startswith("/") or route.startswith("//"):
        return route
    parsed = urlsplit(route)
    target = DIST / parsed.path.lstrip("/")
    if not parsed.path or parsed.path == "/":
        target = DIST / "index.html"
    elif parsed.path.endswith("/"):
        target = target / "index.html"
    elif not target.exists():
        if (DIST / (parsed.path.lstrip("/") + ".html")).exists():
            target = DIST / (parsed.path.lstrip("/") + ".html")
        else:
            return route
    if target.is_dir():
        target /= "index.html"
    if not target.exists():
        return route
    rel = os.path.relpath(target, from_file.parent).replace("\\", "/")
    return rel + (("?" + parsed.query) if parsed.query else "") + (("#" + parsed.fragment) if parsed.fragment else "")

def main():
    if not (DIST / "index.html").exists():
        raise RuntimeError("Build dist/index.html first, from real editorial data.")
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(DIST, OUT)
    # Each original static article and cover remains unchanged. Only local links
    # are made relative so double-clicking index.html works via file://.
    for f in OUT.rglob("*.html"):
        original = DIST / f.relative_to(OUT)
        s = f.read_text(encoding="utf-8")
        def rewrite(m):
            attr, quote, url = m.group(1), m.group(2), m.group(3)
            return attr + quote + html.escape(local_route(html.unescape(url), original), quote=True) + quote
        s = re.sub(r'((?:href|src|poster)=)(["\'])(/[^"\']*)\2', rewrite, s)
        f.write_text(s, encoding="utf-8")
    for f in OUT.rglob("*.css"):
        s = f.read_text(encoding="utf-8")
        relative = Path(os.path.relpath(DIST / "assets", (DIST / f.relative_to(OUT)).parent)).as_posix()
        # css is normally under assets/css, so root /assets/... -> ../...
        s = re.sub(r'url\((["\']?)/assets/', lambda m: 'url(' + m.group(1) + relative + '/', s)
        f.write_text(s, encoding="utf-8")
    guide = (
        "ZAZOOMTEK.IT — ANTEPRIMA OFFLINE COMPLETA SPOTNEWS\n"
        "28 ottobre 2026 — SOLO PROVA LOCALE, NON PUBBLICATA\n\n"
        "1. Estrai tutto l'archivio ZIP in una cartella sul tuo PC.\n"
        "2. Apri index.html con Firefox o Chrome per vedere la Home.\n"
        "3. Clicca sulle notizie per aprire le pagine HTML presenti nell'archivio.\n"
        "4. Per un confronto completo con funzionalità JS, se Python è installato:\n"
        "   apri un terminale dentro questa cartella ed esegui:\n"
        "   python -m http.server 8765\n"
        "   poi visita http://localhost:8765/\n\n"
        "La copia contiene gli articoli, le recensioni, gli stili, le immagini,\n"
        "le guide e le pagine generate dallo stesso codice del sito reale.\n"
        "Immagini ospitate da YouTube o altre fonti HTTPS richiedono internet.\n"
        "Accesso amministratore Studio e API non funzionano offline.\n\n"
        "MODIFICHE DI QUESTA ANTEPRIMA:\n"
        "- Quattro titoli laterali News Gaming piu' grandi e scuri.\n"
        "- Solo il testo introduttivo della notizia GRANDE ampliato.\n"
        "- Pulsante sotto la copertina delle recensioni con video verificato.\n\n"
        "Nessun file di questo ZIP e' stato pubblicato su zazoomtek.it.\n"
    )
    (OUT / "LEGGIMI_ANTEPRIMA.txt").write_text(guide, encoding="utf-8")
    if ZIP.exists():
        ZIP.unlink()
    count = 0
    with zipfile.ZipFile(ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in OUT.rglob("*"):
            if f.is_file():
                z.write(f, f.relative_to(OUT))
                count += 1
    if count < 170:
        raise RuntimeError("Snapshot incomplete; expected generated editorial pages and assets.")
    print(f"OFFLINE SNAPSHOT READY: {ZIP.name}; {count} files; {ZIP.stat().st_size} bytes", flush=True)

if __name__ == "__main__":
    main()
