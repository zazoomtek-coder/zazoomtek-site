# ZazoomTek – Urgent Layout + YouTube Import

**Ramo di pubblicazione manuale:** `release-2026-10-24-urgent-layout-youtube-import`

## Modifiche incluse
- `zt-release-menu.js`: stesso menu, categorie e collegamenti della home su pagine interne.
- `zt-release-layout.css`: menu responsive; recupero dello spazio inutilizzato nelle pagine articolo prive di colonna laterale.
- `services10/14-release-layout.py`: inietta gli asset nelle pagine editoriali esistenti e generate, senza modificare `index.html`.
- `studio/layouts.js`: applica il menu comune anche alle nuove pubblicazioni da Studio.
- `services10/02-video-16x9.py`: accetta tutti i video pubblici ottenuti dall'API ufficiale, senza dichiarare 16:9 quando non verificato.
- `services10/13-pending-public.py`: recupera i video identificati nella coda storica, senza duplicati.
- `services10/02-video-pages.py` e `services10/state.py`: preservano e pubblicano le schede video recuperate.
- `home-video-feed.json`: il catalogo conteneva già i 26 ID in sospeso, quindi non sono state create copie duplicate.
- Workflow: generazione e rilascio dopo merge manuale; **nessun merge automatico** di questo ramo.

## Importante
- Il post Community delle 11:00 del 24/10/2026 non era presente nell'ultimo archivio Community consultato: sarà rilevato dal collector YouTube al successivo avvio, **solo se YouTube lo restituisce**. Non viene creato un post artificiale.
- I 26 record provengono dalla coda `zt-services10-state` e mantengono titolo, ID e data; la proporzione reale del filmato non viene inventata.
- Il ramo non è stato unito a `main`. Fino al merge manuale e al successivo deploy, la modifica non è attiva sul sito.
- Nessun collaudo browser o suite test viene avviato da questo pacchetto.
