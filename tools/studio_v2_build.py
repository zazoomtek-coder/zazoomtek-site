"""Studio V2 opt-in preview: separate from the current Studio and public site."""
import json,re
from pathlib import Path
from html.parser import HTMLParser
from seo import title_tag, description, keywords
from article_templates import sectioned_body

class _EditorInline(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True)
  self.output=[]
  self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=="br":self.output.append("\n")
  elif tag=="strong":self.output.append("**")
  elif tag=="em":self.output.append("*")
  elif tag=="a":
   href=dict(attrs).get("href","")
   self.links.append(href if href.startswith(("https://","/")) else "")
   if self.links[-1]:self.output.append("[")
 def handle_endtag(self,tag):
  if tag=="strong":self.output.append("**")
  elif tag=="em":self.output.append("*")
  elif tag=="a":
   href=self.links.pop() if self.links else ""
   if href:self.output.append("]("+href+")")
 def handle_data(self,data):self.output.append(data)

def editorial_blocks_for_editor(row):
 """Keep the exact published editorial headings and original text in their order."""
 # Preserve media blocks exactly. For text-only Studio edits, parse the
 # actual published HTML so editorial H2 and paragraphs match the site.
 if row.get("studio_blocks") and isinstance(row.get("body"),list) and row["body"]:
  if any(isinstance(x,dict) and x.get("type") in
         ("image","video","audio","button","attachment","poll","divider")
         for x in row["body"]):
   return row["body"]
 source=sectioned_body(row)
 blocks=[]
 for match in re.finditer(r"<(h2|p|blockquote)\b[^>]*>(.*?)</\1>",source,re.S|re.I):
  tag,raw=match.groups()
  text=_EditorInline()
  text.feed(raw)
  value="".join(text.output).strip()
  if value:blocks.append({
   "type":"heading" if tag=="h2" else "quote" if tag=="blockquote" else "paragraph",
   "text":value})
 if not blocks:
  # Nonempty fallback: never show a blank editor for an existing article.
  raw=row.get("body") or []
  if isinstance(raw,str):raw=[raw]
  for part in raw:
   value=str(part if isinstance(part,str) else part.get("text") or part.get("content") or "").strip()
   if value:blocks.append({"type":"paragraph","text":value})
 return blocks


CATEGORIES={
 "news-tech":"News Tech","news-gaming":"News Gaming",
 "recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming",
 "guide":"Guide","speciali":"Speciali","extra":"Extra"
}
def snapshot(row):
 locked=row.get("seo_lock")
 if isinstance(locked,dict) and all(isinstance(locked.get(k),str) for k in ("title","description")):
  return locked
 return {"title":title_tag(row),"description":description(row),
         "keywords":keywords(row)}

def build_studio_v2(output,rows):
 root=Path(output)/"studio-v2"
 root.mkdir(parents=True,exist_ok=True)
 catalog={"version":3,"mode":"opt-in-preview","posts":[{
  "slug":row.get("slug"),"title":row.get("title"),
  "category":row.get("category"),"date":row.get("date"),
  "published_at":row.get("published_at"),"updated_at":row.get("updated_at"),"image":row.get("image"),
  "cover_focus_x":row.get("cover_focus_x"),"cover_focus_y":row.get("cover_focus_y"),
  "cover_zoom":row.get("cover_zoom"),"cover_rotation":row.get("cover_rotation"),
  "author":row.get("author"),"video_url":row.get("video_url"),
  "platform":row.get("platform"),"score":row.get("score"),
  "pros":row.get("pros"),"cons":row.get("cons"),
  "studio_blocks":bool(row.get("studio_blocks")),
  "body":row.get("body",[]),"editor_blocks":editorial_blocks_for_editor(row),
  "seo_lock":snapshot(row)
 } for row in rows]}
 (root/"catalog.json").write_text(json.dumps(catalog,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 html="""<!doctype html><html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive">
<!-- Keep branch-specific Studio previews on their own hostname.
     Authentication cookies are host-specific and must not redirect to another build. -->
<title>Studio V2 — Anteprima | ZazoomTek</title>
<link rel="stylesheet" href="/assets/css/studio-v2.css?v=20261028-studio-draft-preview-1">
<script src="/assets/js/studio-v2.js?v=20261028-rich-4" defer></script>
</head><body>
<div id="v2-auth" class="v2-auth" hidden>
 <div class="v2-auth-card">
  <div class="v2-brand">Zazoom<span>Tek</span><small>STUDIO V2</small></div>
  <h1>Accedi a Studio</h1>
  <p>Questa anteprima utilizza la stessa sessione amministratore di Studio. Se hai già effettuato l'accesso sullo stesso dominio, entrerai automaticamente.</p>
  <a class="v2-primary" href="/studio/">Apri la pagina di accesso</a>
  <a class="v2-link" href="/studio-v2/">Riprova</a>
 </div>
</div>
<div id="v2-app" hidden>
 <aside class="v2-rail">
  <a class="v2-logo" href="/studio-v2/">Zazoom<span>Tek</span><small>STUDIO</small></a>
  <div class="v2-rail-heading">IL TUO SPAZIO</div>
  <button id="v2-home-nav" class="v2-rail-nav on">◫ &nbsp; Contenuti</button>
  <button id="v2-new-nav" class="v2-rail-nav">＋ &nbsp; Crea</button>
  <div class="v2-rail-divider"></div>
  <div class="v2-rail-heading">FILTRA I CONTENUTI</div>
  <button data-rail-filter="" class="v2-rail-nav on">Tutti gli articoli</button>
  <button data-rail-filter="news-tech" class="v2-rail-nav">News Tech</button>
  <button data-rail-filter="news-gaming" class="v2-rail-nav">News Gaming</button>
  <button data-rail-filter="recensioni-tech" class="v2-rail-nav">Recensioni Tech</button>
  <button data-rail-filter="recensioni-gaming" class="v2-rail-nav">Recensioni Gaming</button>
  <button data-rail-filter="guide" class="v2-rail-nav">Guide</button>
  <button data-rail-filter="speciali" class="v2-rail-nav">Speciali</button>
  <button data-rail-filter="extra" class="v2-rail-nav">Extra</button>
  <div class="v2-rail-spacer"></div>
  <div class="v2-admin">Amministratore GitHub<div id="v2-user" class="v2-user">Autenticazione in corso</div></div>
  <a href="/" class="v2-rail-site">↗ Visita il sito</a>
 </aside>
 <main class="v2-main">
  <header class="v2-top">
   <div id="v2-crumb">Studio <span>/</span> Contenuti</div>
   <div class="v2-top-right"><span class="v2-preview-badge">ANTEPRIMA V2</span><button id="v2-back" class="v2-soft" hidden>← Contenuti</button></div>
  </header>
  <div id="v2-home" class="v2-home">
   <div class="v2-home-intro"><div><div class="v2-eyebrow">IL TUO CENTRO EDITORIALE</div>
    <h1>Gestisci i tuoi contenuti</h1>
    <p>Cerca un articolo e modificalo in pochi clic. Oppure crea una nuova pubblicazione.</p>
   </div><button class="v2-primary" id="v2-create-main">＋ Crea contenuto</button></div>
   <div class="v2-home-stats"><div><strong id="v2-count-all">—</strong><span>Articoli disponibili</span></div>
    <div><strong id="v2-count-tech">—</strong><span>News Tech</span></div>
    <div><strong id="v2-count-gaming">—</strong><span>News Gaming</span></div>
    <div><strong id="v2-count-reviews">—</strong><span>Recensioni</span></div></div>
   <section class="v2-library">
    <div class="v2-library-heading"><h2>I tuoi contenuti</h2><div class="v2-filters">
     <input id="v2-search" type="search" aria-label="Cerca contenuti" placeholder="⌕  Cerca titolo, prodotto, videogioco">
     <select id="v2-select-filter" aria-label="Categoria"><option value="">Tutte le categorie</option></select>
    </div></div>
    <div class="v2-library-caption" id="v2-library-caption">Caricamento...</div>
    <div id="v2-list" class="v2-content-list"></div>
   </section>
  </div>
  <div id="v2-editor" class="v2-editor-view" hidden>
   <div class="v2-editor-header">
    <div><div class="v2-eyebrow">EDITOR VISUALE</div><h1 id="v2-editor-heading">Modifica contenuto</h1>
     <p id="v2-editor-note">Scrivi e modifica liberamente, come su Patreon.</p></div>
    <div class="v2-editor-actions">
      <button type="button" id="v2-preview-top" class="v2-soft">Anteprima</button>
      <button type="button" id="v2-save-draft" class="v2-soft">Salva bozza</button>
      <button type="button" id="v2-publish" class="v2-primary">Pubblica</button>
    </div>
   </div>
   <div class="v2-editor-layout">
    <div class="v2-paper-wrap">
     <article class="v2-paper">
      <label class="v2-field-title" for="v2-title">Titolo</label>
      <input id="v2-title" class="v2-title-input" type="text" placeholder="Inizia con un titolo..." maxlength="220">
      <button type="button" id="v2-cover-add" class="v2-cover-add">▧ &nbsp; Aggiungi una copertina</button>
      <div id="v2-cover-stage" class="v2-cover-stage" hidden>
       <img id="v2-cover-image" alt="Copertina del contenuto">
       <div class="v2-cover-controls"><button id="v2-cover-change">Sostituisci</button><button id="v2-cover-edit">Ritaglia e centra</button><button id="v2-cover-remove">Rimuovi</button></div>
      </div>
      <div id="v2-blocks" class="v2-blocks" aria-label="Corpo dell'articolo"></div>
      <button id="v2-append-block" class="v2-add-line" hidden>＋ <span>Aggiungi contenuto</span></button>
      <p class="v2-paper-tip">Clicca nel testo dove vuoi inserire un elemento: apparirà un solo <strong>＋</strong>, proprio nel punto scelto.</p>
     </article>
     <div class="v2-footer-actions"><button type="button" id="v2-preview-bottom" class="v2-soft">Anteprima</button>
      <button type="button" id="v2-draft-bottom" class="v2-soft">Salva bozza</button>
      <button type="button" id="v2-publish-bottom" class="v2-primary">Pubblica</button></div>
    <p id="v2-autosave-status" class="v2-autosave-status" role="status" aria-live="polite">Bozza locale: protezione automatica del testo.</p>
    </div>
    <aside class="v2-settings">
     <div class="v2-settings-header"><strong>Impostazioni</strong><span>CONTENUTO</span></div>
     <label class="v2-field">Categoria <select id="v2-category"></select></label>
     <label class="v2-field">Autore <input id="v2-author" type="text" placeholder="Redazione ZazoomTek"></label>
     <label class="v2-field">Indirizzo dell'articolo <input id="v2-slug" type="text" placeholder="titolo-articolo"></label>
     <div class="v2-settings-section">
      <div class="v2-setting-title">Copertina</div>
      <div class="v2-settings-cover" id="v2-settings-cover">Nessuna copertina</div>
      <button id="v2-cover-sidebar" class="v2-soft v2-wide">Carica o modifica copertina</button>
     </div>
     <div class="v2-settings-section"><div class="v2-setting-title">Media e dettagli</div>
      <label class="v2-field">Video YouTube principale <input id="v2-video-url" type="url" placeholder="https://youtube.com/..."></label>
      <label class="v2-field">Piattaforma o prodotto <input id="v2-platform" type="text"></label>
      <label class="v2-field">Voto recensione / 10 <input id="v2-score" type="text" inputmode="decimal" placeholder="Facoltativo"></label>
      <label class="v2-field">Pro <textarea id="v2-pros" placeholder="Una voce per riga" rows="3"></textarea></label>
      <label class="v2-field">Contro <textarea id="v2-cons" placeholder="Una voce per riga" rows="3"></textarea></label>
     </div>
     <div class="v2-settings-section"><div class="v2-setting-title">SEO automatico <span class="v2-auto">AUTOMATICO</span></div>
      <p class="v2-seo-description" id="v2-seo-status">I metadati vengono gestiti dal sito. Non devi inserire nulla.</p>
      <div class="v2-seo-preview"><div>Anteprima titolo SEO</div><strong id="v2-seo-title">Generazione automatica</strong>
       <div>Descrizione</div><span id="v2-seo-description">Ottimizzata automaticamente dal contenuto completo.</span></div>
     </div>
     <div class="v2-settings-section"><div class="v2-setting-title">Pubblicazione</div>
      <p class="v2-settings-hint">Anteprima non modifica il sito. Salva bozza conserva il lavoro. Pubblica salva l’articolo in coda e apre subito la sua anteprima: sarà online solo nello slot delle 12:30 o delle 19:30. I testi restano protetti dal salvataggio locale.</p>
      <a id="v2-public-link" href="#" target="_blank" rel="noopener noreferrer" hidden>↗ Apri articolo pubblicato</a>
     </div>
    </aside>
   </div>
  </div>
  <div id="v2-toast" class="v2-toast" role="status" aria-live="polite" hidden></div>
 <div id="v2-article-preview" class="v2-article-preview" role="dialog" aria-modal="true" aria-label="Anteprima dell'articolo" hidden>
  <div class="v2-preview-sheet"><div class="v2-preview-toolbar"><strong>ANTEPRIMA SALVATA · IN CODA, NON ONLINE</strong><button type="button" id="v2-close-preview">Chiudi anteprima ×</button></div>
   <article class="v2-preview-article" id="v2-preview-article-content"></article>
   <p class="v2-preview-disclaimer">Questa anteprima non pubblica nulla e riproduce titolo, immagine, paragrafi e sottotitoli editoriali.</p>
  </div>
 </div>
 </main>
</div>
<div id="v2-insert-menu" class="v2-insert-menu" hidden role="dialog" aria-label="Inserisci contenuto">
 <div class="v2-menu-label">AGGIUNGI AL POST</div>
 <div class="v2-menu-grid">
 <button data-kind="paragraph">☷ <span>Testo</span></button>
 <button data-kind="heading">H₂ <span>Sottotitolo</span></button>
 <button data-kind="image">▧ <span>Immagine</span></button>
 <button data-kind="video">▶ <span>Video</span></button>
 <button data-kind="audio">♫ <span>Audio</span></button>
 <button data-kind="link">🔗 <span>Link nel testo</span></button>
 <button data-kind="button">↗ <span>Pulsante</span></button>
 <button data-kind="attachment">▤ <span>Allegato</span></button>
 <button data-kind="divider">— <span>Divisore</span></button>
 <button data-kind="quote">❞ <span>Citazione</span></button>
 <button data-kind="poll">◉ <span>Sondaggio</span></button>
 </div>
 <button id="v2-menu-close" class="v2-menu-close">Annulla</button>
</div>
<div id="v2-modal" class="v2-modal" hidden role="dialog" aria-modal="true" aria-labelledby="v2-modal-title">
 <div class="v2-modal-card">
  <div class="v2-modal-header"><h2 id="v2-modal-title">Modifica elemento</h2><button id="v2-modal-close" aria-label="Chiudi">×</button></div>
  <div id="v2-modal-body" class="v2-modal-body"></div>
  <div class="v2-modal-footer"><button id="v2-modal-cancel" class="v2-soft">Annulla</button><button id="v2-modal-apply" class="v2-primary">Applica modifiche</button></div>
 </div>
</div>
</body></html>"""
 (root/"index.html").write_text(html,encoding="utf-8")
 print("STUDIO V2 PREVIEW:",len(rows),"articles; separate opt-in route",flush=True)
