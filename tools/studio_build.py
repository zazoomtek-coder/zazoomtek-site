"""Build the static Studio shell and an editable catalog of ALL current articles.
The catalog contains published editorial data only, not secrets or credentials.
Authentication and mutations are handled exclusively by protected Pages Functions.
"""
from pathlib import Path
from html import escape as esc
import json

def build_studio(output,rows):
 root=Path(output)/"studio"
 root.mkdir(parents=True,exist_ok=True)
 data={"version":1,"posts":[{
  "slug":row.get("slug"),"title":row.get("title"),"category":row.get("category"),
  "date":row.get("date"),"published_at":row.get("published_at"),
  "image":row.get("image"),"author":row.get("author"),
  "video_url":row.get("video_url"),"platform":row.get("platform"),
  "score":row.get("score"),"pros":row.get("pros"),"cons":row.get("cons"),
  "studio_blocks":bool(row.get("studio_blocks")),"body":row.get("body",[])
 } for row in rows]}
 (root/"catalog.json").write_text(json.dumps(data,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 html="""<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Studio | ZazoomTek</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<link rel="stylesheet" href="/assets/css/studio.css?v=1">
</head><body>
<section id="studio-gate" class="studio-gate">
  <h1>Zazoom<span style="color:#ed344b">Tek</span> Studio</h1>
  <p id="studio-gate-description">Verifica della sessione amministratore protetta…</p>
  <p>Accedi una volta tramite Cloudflare Access. In seguito, il browser usa automaticamente il cookie di sessione protetto finché è valido. Non inserire token o password nella pagina.</p>
  <a href="/cdn-cgi/access/login?redirect_url=%2Fstudio%2F">Accedi come amministratore</a>
  <p><small>Cloudflare Access deve essere configurato per /studio/* e /api/studio/* prima dell'uso.</small></p>
  <p><a href="/" style="background:transparent;color:#222;padding:0">Torna al sito</a></p>
</section>
<div class="studio-layout" id="studio-app" hidden>
 <aside class="studio-left">
  <div class="studio-brand">Zazoom<span>Tek</span> <small>Studio</small></div>
  <p class="studio-left-heading">Gestione editoriale</p>
  <button id="studio-new" class="studio-new">+ Crea nuovo contenuto</button>
  <div class="studio-search-row">
   <input id="studio-search" type="search" aria-label="Cerca articoli" placeholder="Cerca articoli, news, recensioni">
   <select id="studio-filter" aria-label="Filtra per categoria"></select>
  </div>
  <span id="studio-counter" class="studio-counter">Caricamento…</span>
  <div id="studio-content-list" class="studio-content-list"></div>
  <p class="studio-left-heading">Branch di prova · No pubblicazione sul sito ufficiale</p>
 </aside>
 <main class="studio-main">
  <header class="studio-topbar">
   <div><div class="studio-eyebrow">Il tuo spazio di pubblicazione</div>
    <h1 id="studio-mode">Modifica contenuto</h1></div>
   <div class="studio-topbar-actions">
    <a class="studio-secondary-btn" href="/">Visualizza sito</a>
    <button type="button" id="studio-save" class="studio-save">Salva modifiche</button>
   </div>
  </header>
  <p id="studio-status" class="studio-status" role="status" aria-live="polite"></p>
  <div id="studio-opening" class="studio-editor" hidden>
   <section class="studio-card">
    <h2>Informazioni del contenuto</h2>
    <label class="studio-field">Titolo editoriale<input id="studio-title" maxlength="220" placeholder="Titolo completo dell'articolo"></label>
    <div class="studio-grid">
     <label class="studio-field">Categoria<select id="studio-category"></select></label>
     <label class="studio-field">URL / Slug<input id="studio-slug" maxlength="150" placeholder="titolo-articolo"></label>
    </div>
    <label class="studio-field">Autore<input id="studio-author" placeholder="Redazione ZazoomTek"></label>
    <div class="studio-cover-row">
     <label class="studio-field">Copertina 16:9 o URL immagine<input id="studio-cover" placeholder="/assets/uploads/... oppure https://..."></label>
     <button type="button" class="studio-secondary-btn" id="studio-add-cover" style="margin-bottom:17px">Carica cover</button>
    </div>
    <div class="studio-grid">
     <label class="studio-field">Piattaforma / prodotto<input id="studio-platform"></label>
     <label class="studio-field">Voto recensione (0–10, facoltativo)<input id="studio-score" inputmode="decimal"></label>
    </div>
    <label class="studio-field">Link video YouTube dell'articolo<input id="studio-video-url" placeholder="https://www.youtube.com/watch?v=..."></label>
    <div class="studio-grid">
     <label class="studio-field">Pro (uno per riga)<textarea id="studio-pros" rows="3"></textarea></label>
     <label class="studio-field">Contro (uno per riga)<textarea id="studio-cons" rows="3"></textarea></label>
    </div>
   </section>
   <section class="studio-card">
    <h2>Contenuto e impaginazione</h2>
    <div class="studio-content-toolbar" role="group" aria-label="Inserisci nuovo blocco">
     <button type="button" data-add-block="paragraph">+ Testo</button>
     <button type="button" data-add-block="heading">+ Sottotitolo</button>
     <button type="button" data-add-block="image">+ Immagine</button>
     <button type="button" data-add-block="video">+ Video</button>
     <button type="button" data-add-block="button">+ Pulsante/link</button>
     <button type="button" data-add-block="quote">+ Citazione</button>
    </div>
    <div id="studio-block-list"></div>
    <p class="studio-hint">Usa i tasti ↑ ↓ per spostare i blocchi. Per aggiungere un link dentro il testo, scrivi [testo da mostrare](https://indirizzo.it). Tutte le modifiche vengono salvate nel branch SpotNews di prova.</p>
   </section>
   <p id="studio-editor-note" class="studio-hint"></p>
  </div>
 </main>
 <aside class="studio-right">
  <h2>Anteprima contenuto</h2>
  <p class="studio-sidebar-subtitle" id="studio-sidebar-active">Editor visuale</p>
  <div class="studio-preview-box" id="studio-preview"></div>
  <p id="studio-preview-foot" class="studio-preview-foot"></p>
  <div class="studio-session">
   <strong id="studio-admin-email">Amministratore</strong>
   <p id="studio-auth-status">Sessione verificata</p>
   <p>La sessione sicura è gestita da Cloudflare Access tramite cookie HttpOnly; nessuna API key salvata nel browser.</p>
   <a href="/cdn-cgi/access/logout" class="studio-source-link">Disconnetti</a>
  </div>
 </aside>
</div>
<script src="/assets/js/studio.js?v=1" defer></script>
</body></html>"""
 (root/"index.html").write_text(html,encoding="utf-8")
 print("Studio catalog:",len(rows),"articles; protected UI generated",flush=True)
