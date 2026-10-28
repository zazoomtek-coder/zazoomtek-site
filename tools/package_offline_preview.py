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
ZIP = ROOT / "ZazoomTek_SpotNews_Anteprima_Mobile_Footer_28-10-2026.zip"

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
    phone = """<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Anteprima smartphone ZazoomTek SpotNews</title><style>*{box-sizing:border-box}body{font:16px Arial,sans-serif;background:#e4e6ea;margin:0;color:#222;text-align:center}header{padding:14px 10px 5px}h1{font-size:21px;margin:0 0 6px}p{font-size:13px;margin:8px 0 15px}.phone{height:80vh;max-height:850px;width:min(390px,calc(100vw - 20px));margin:10px auto 20px;border:7px solid #242424;border-radius:28px;overflow:hidden;background:white;box-shadow:0 10px 35px #1114}.phone iframe{display:block;width:100%;height:100%;border:0}a{color:#bd1230;font-weight:700}</style></head><body><header><h1>Anteprima smartphone · ZazoomTek</h1><p>Questa cornice mostra il VERO sito SpotNews in un viewport mobile da 390 px.</p><p><a href="index.html">Apri la versione desktop completa</a></p></header><div class="phone"><iframe src="index.html" title="ZazoomTek SpotNews mobile"></iframe></div><p>Scorri nella cornice fino al footer, poi controlla Privacy Policy, Cookie Policy e Contatti.</p></body></html>"""
    (OUT / "VISTA_SMARTPHONE.html").write_text(phone, encoding="utf-8")
    guide = (
        "ZAZOOMTEK.IT - ANTEPRIMA OFFLINE MOBILE CORRETTA\\n"
        "Solo branch di prova, nessun deploy sul sito ufficiale\\n\\n"
        "1. Estrai TUTTI i file dello ZIP sul PC. Non aprire lo ZIP direttamente.\\n"
        "2. Apri VISTA_SMARTPHONE.html per la cornice smartphone da 390 pixel.\\n"
        "3. Scorri all'interno del telefono sino al footer e verifica che sia nero.\\n"
        "4. Apri index.html per la Home completa e le pagine editoriali.\\n"
        "5. Immagini esterne (YouTube) richiedono connessione internet.\\n"
        "6. Studio e API non funzionano su disco offline.\\n\\n"
        "Modifica mirata: menu mobile limitato alla testata, footer scuro e nel flusso,\\n"
        "con link e informazioni legali visibili. La grafica desktop resta invariata.\\n"
        "Nessuna modifica o pubblicazione in produzione.\\n"
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
