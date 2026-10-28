"""Build the independent SpotNews Studio (original editorial UI, not old Studio).
The HTML shell and public editorial catalog contain ZERO authentication secrets.
"""
from pathlib import Path
from html import escape
import json

def build_studio(output, rows):
 root=Path(output)/"studio"
 root.mkdir(parents=True,exist_ok=True)
 catalog={"version":2,"posts":[{
   "slug":r.get("slug"),"title":r.get("title"),"category":r.get("category"),
   "date":r.get("date"),"published_at":r.get("published_at"),
   "image":r.get("image"),"author":r.get("author"),
   "video_url":r.get("video_url"),"platform":r.get("platform"),
   "score":r.get("score"),"pros":r.get("pros"),"cons":r.get("cons"),
   "studio_blocks":bool(r.get("studio_blocks")),"body":r.get("body",[])
 } for r in rows]}
 (root/"catalog.json").write_text(
  json.dumps(catalog,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 html="""<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="color-scheme" content="light">
<title>Studio — ZazoomTek</title>
<link rel="stylesheet" href="/assets/css/studio.css?v=20261028-studio-fresh-2">
<script src="/assets/js/studio.js?v=20261028-studio-fresh-2" defer></script>
</head><body>
<div class="studio-auth-wrap" id="studio-auth">
 <main class="studio-auth-card">
  <div class="studio-auth-logo">Zazoom<span>Tek</span><small>STUDIO</small></div>
  <div class="studio-auth-tag">Lo spazio editoriale di ZazoomTek</div>
  <h1>Accedi al tuo Studio</h1>
  <p>Il tuo pannello personale per creare, modificare e pubblicare articoli, news e recensioni sul branch di prova.</p>
  <div id="studio-setup" class="studio-auth-alert" hidden>
   <strong>Attivazione iniziale richiesta</strong>
   <p>Manca una sola chiave di sicurezza server: <code>STUDIO_SESSION_SECRET</code> nelle impostazioni <strong>Preview</strong> di Cloudflare Pages. Non servono Zero Trust, piani a pagamento o altre applicazioni.</p>
   <a target="_blank" rel="noopener noreferrer" href="https://dash.cloudflare.com/">Apri Cloudflare</a>
  </div>
  <form id="studio-login-form" autocomplete="off" hidden>
   <label for="studio-token">Token personale GitHub (solo il primo accesso)</label>
   <input type="password" id="studio-token" name="token" placeholder="github_pat_..." required spellcheck="false" autocomplete="off">
   <p class="studio-help">Il token è verificato con GitHub e cifrato in un cookie protetto, non salvato in JavaScript o nella memoria del browser. Il cookie cifrato si rinnova automaticamente ad ogni visita: nessuna scadenza periodica di accesso.</p>
   <button type="submit" id="studio-login-submit" class="studio-primary">Entra in Studio</button>
  </form>
  <p id="studio-login-status" class="studio-state" role="status" aria-live="polite">Controllo accesso amministratore…</p>
  <button type="button" id="studio-check-again" class="studio-link-button" hidden>Riprova la verifica</button>
  <a href="/" class="studio-quiet-link">Torna al sito</a>
 </main>
</div>
<div class="studio-layout" id="studio-app" hidden>
 <aside class="studio-rail">
  <div class="studio-rail-brand">Zazoom<span>Tek</span><small>STUDIO</small></div>
  <div class="studio-workspace"><span class="studio-workspace-mark">Z</span><div><b>La tua redazione</b><small>SpotNews · ambiente di prova</small></div></div>
  <button type="button" id="studio-new" class="studio-create">＋ Crea un contenuto</button>
  <div class="studio-section-label">La tua libreria</div>
  <div class="studio-rail-filters">
   <input id="studio-search" type="search" placeholder="Cerca per titolo" aria-label="Cerca contenuti">
   <select id="studio-filter" aria-label="Filtra per categoria"></select>
  </div>
  <div class="studio-total" id="studio-count"></div>
  <div class="studio-article-list" id="studio-list"></div>
  <div class="studio-rail-footer">
   <p>Modifiche riservate al branch di prova</p>
   <a href="/">Visualizza il sito <span aria-hidden="true">↗</span></a>
  </div>
 </aside>
 <main class="studio-center">
  <header class="studio-toolbar">
   <div><div class="studio-eyebrow">ZazoomTek / Studio</div>
    <h1 id="studio-current-mode">Modifica articolo</h1>
    <p id="studio-current-category">Spazio editoriale</p></div>
   <div class="studio-toolbar-actions">
    <button type="button" id="studio-preview-toggle" class="studio-text-button">Anteprima</button>
    <button type="button" id="studio-save" class="studio-primary">Salva modifiche</button>
   </div>
  </header>
  <div class="studio-edit-body">
   <p role="status" aria-live="polite" id="studio-status" class="studio-state"></p>
   <section class="studio-form-section">
    <div class="studio-form-heading"><h2>Informazioni principali</h2><p>Il contenuto, il titolo e la categoria</p></div>
    <label class="studio-input-group">Titolo dell'articolo
     <input id="studio-title" type="text" maxlength="220" placeholder="Inserisci il titolo completo">
    </label>
    <div class="studio-double">
     <label class="studio-input-group">Categoria
      <select id="studio-category"></select>
     </label>
     <label class="studio-input-group">Indirizzo articolo
      <input id="studio-slug" type="text" maxlength="150" placeholder="url-articolo">
     </label>
    </div>
    <label class="studio-input-group">Autore
     <input id="studio-author" type="text" placeholder="Redazione ZazoomTek">
    </label>
    <label class="studio-input-group">Immagine di copertina
     <div class="studio-media-field">
      <input id="studio-cover" type="text" placeholder="https://... oppure /assets/uploads/...">
      <button type="button" id="studio-cover-upload" class="studio-outline">Carica</button>
     </div>
    </label>
    <p class="studio-hint">Immagini JPEG, PNG o WebP. Il sito usa miniature 16:9; una cover con titolo centrale è preferibile.</p>
   </section>
   <section class="studio-form-section">
    <div class="studio-form-heading"><h2>Corpo dell'articolo</h2><p>Sposta, aggiungi e modifica liberamente ogni blocco</p></div>
    <div id="studio-blocks" class="studio-blocks"></div>
    <div class="studio-insert" role="group" aria-label="Aggiungi blocco">
     <button type="button" data-block="paragraph">＋ Testo</button>
     <button type="button" data-block="heading">＋ Sottotitolo</button>
     <button type="button" data-block="image">＋ Foto</button>
     <button type="button" data-block="video">＋ Video</button>
     <button type="button" data-block="button">＋ Pulsante/link</button>
     <button type="button" data-block="quote">＋ Citazione</button>
    </div>
    <p class="studio-hint">Nei paragrafi puoi inserire un collegamento con <code>[testo del link](https://indirizzo.it)</code>. I sottotitoli diventano intestazioni H2 con la barra rossa.</p>
   </section>
   <section class="studio-form-section">
    <div class="studio-form-heading"><h2>Dettagli aggiuntivi</h2><p>Video principale, piattaforma, voto, pro e contro</p></div>
    <label class="studio-input-group">Link del video YouTube
     <input id="studio-video" type="url" placeholder="https://www.youtube.com/watch?v=...">
    </label>
    <div class="studio-double">
     <label class="studio-input-group">Piattaforma / prodotto
      <input id="studio-platform" type="text">
     </label>
     <label class="studio-input-group">Voto recensione (0–10)
      <input id="studio-score" type="text" inputmode="decimal" placeholder="Facoltativo">
     </label>
    </div>
    <div class="studio-double">
     <label class="studio-input-group">Pro (una voce per riga)
      <textarea id="studio-pros" rows="4"></textarea>
     </label>
     <label class="studio-input-group">Contro (una voce per riga)
      <textarea id="studio-cons" rows="4"></textarea>
     </label>
    </div>
   </section>
   <footer class="studio-edit-footer">
    <span id="studio-save-detail">Le modifiche interessano soltanto il branch SpotNews di prova.</span>
    <button type="button" id="studio-save-bottom" class="studio-primary">Salva articolo</button>
   </footer>
  </div>
 </main>
 <aside class="studio-preview-column" id="studio-preview-column">
  <div class="studio-preview-heading"><h2>Anteprima</h2>
   <span>Come apparirà nel sito</span></div>
  <article class="studio-preview-document" id="studio-preview"></article>
  <div class="studio-session">
   <div id="studio-account-name">Amministratore</div>
   <p id="studio-session-expiry"></p>
   <button type="button" id="studio-logout">Disconnetti</button>
  </div>
 </aside>
</div>
</body></html>"""
 (root/"index.html").write_text(html,encoding="utf-8")
 print("STUDIO FRESH BUILD: "+str(len(rows))+" editorial entries",flush=True)
