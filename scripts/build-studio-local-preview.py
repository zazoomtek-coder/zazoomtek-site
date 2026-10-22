#!/usr/bin/env python3
"""Create a real-file offline preview of the permanent Studio, with zero deploys."""
from pathlib import Path
import base64
import json
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
ARTICLE="speciale-videogiochi-minori-politica-italia-ue-2026.html"
TITLE="ZazoomTek-Studio-Live-Preview-20261022.zip"

def build(destination:Path):
    source=ROOT/"studio/index.html"
    if not source.is_file() or not (ROOT/"studio/edit-existing.js").is_file() or not (ROOT/ARTICLE).is_file():
        raise RuntimeError("Missing real Studio or Speciale source files")
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder)/"ZazoomTek-Studio-Live"
        root.mkdir()
        source_html=(ROOT/ARTICLE).read_text(encoding="utf-8")
        # Real article and CSS, not sample text. Use site-hosted media in srcdoc
        # because browser file:// root paths cannot resolve local /assets.
        preview_html=source_html.replace('src="/assets/', 'src="https://zazoomtek.it/assets/')
        preview_html=preview_html.replace('href="/zt-design.css','href="https://zazoomtek.it/zt-design.css')
        preview_html=preview_html.replace('src="/zt-analytics.js"', 'src="https://zazoomtek.it/zt-analytics.js"')
        original=(ROOT/"studio/index.html").read_text(encoding="utf-8")
        original=original.replace('src="/studio/layouts.js"','src="./layouts.js"')
        original=original.replace('<script src="/studio/publisher.js" defer></script>',
                                  '<!-- Online publication disabled in this local live test. -->')
        code='window.ZTStudioDemoArticle = {path:'+json.dumps(ARTICLE)+',html: new TextDecoder().decode(Uint8Array.from(atob('+json.dumps(base64.b64encode(preview_html.encode("utf-8")).decode("ascii"))+'),c=>c.charCodeAt(0)))};'
        original=original.replace('<script src="/studio/edit-existing.js" defer></script>',
                                  '<script src="./demo-article.js"></script><script src="./edit-existing.js" defer></script>')
        (root/"index.html").write_text(original,encoding="utf-8")
        (root/"demo-article.js").write_text(code+"\n",encoding="utf-8")
        shutil.copy(ROOT/"studio/layouts.js",root/"layouts.js")
        shutil.copy(ROOT/"studio/edit-existing.js",root/"edit-existing.js")
        shutil.copy(ROOT/ARTICLE,root/ARTICLE)
        (root/"LEGGIMI.txt").write_text(
            "ZAZOOMTEK STUDIO - PROVA LIVE LOCALE\n\n"
            "Apri index.html con Chrome, Edge oppure Firefox.\n"
            "La sezione MODIFICA ARTICOLI si apre automaticamente sullo\n"
            "Speciale reale 'Videogiochi e minori'.\n"
            "Modifica il testo, seleziona le immagini, usa i cursori e\n"
            "trascinale per centrare; aggiungi URL YouTube, link e foto.\n"
            "Premi ANTEPRIMA REALE per vedere la pagina completa.\n"
            "Premi SALVA MODIFICHE: salva SOLO nel browser del tuo PC.\n"
            "Chiudi e riapri: i cambiamenti locali rimangono disponibili.\n"
            "Il video YouTube richiede una connessione Internet.\n"
            "Nessuna modifica a main, al sito o alle pubblicazioni.\n"
            "La vera modifica GitHub sara attivata solo dopo approvazione.\n",
            encoding="utf-8")
        destination.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(destination,"w",compression=ZIP_DEFLATED,compresslevel=9) as z:
            for file in sorted(root.rglob("*")):
                if file.is_file():z.write(file,file.relative_to(root.parent))
    return destination

if __name__=="__main__":
    print("Live local preview built:",build(ROOT/TITLE))
