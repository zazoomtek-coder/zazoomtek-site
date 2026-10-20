# 70mai A900 Ultra — pubblicazione effettiva

Data: 20 ottobre 2026 (Europe/Rome).
Titolo: 70mai A900 Ultra Recensione | Dual 4K e Sony STARVIS 2.
URL pubblico: https://zazoomtek.it/70mai-a900-ultra-recensione-dual-4k.html

## Esito verificato

**PUBBLICATA E VERIFICATA ONLINE il 20 ottobre 2026, alle 18:41–18:42 italiane.**
- La pubblicazione programmata delle 17:45 **non è avvenuta all'orario previsto**.
- Il controllo pubblico di GitHub Actions run 39459698151, job 118755635582, alle 16:41:53 UTC ha stampato: `LIVE REVIEW OK: https://zazoomtek.it/70mai-a900-ultra-recensione-dual-4k.html`.
- Il Master run 39458479290, job 118751435085, concluso con `success` alle 16:42 UTC, ha registrato `release_requested: true`, source_commit `5e2fa6139648e5ddab47cb6b76b2e0161b6603da` e `VERIFIED: public Cloudflare release matches master source`.
- Il marker di rilascio Cloudflare è stato emesso nel commit `45c92c9c01454b59fe9ef976e5a41cb13072ed22`, con priorità `urgent`.

## Perché lo slot delle 17:45 è stato mancato

- Alle 17:53 il workflow Master aveva completato soltanto un controllo `poll`, non un rilascio.
- Il watchdog delle 18:01, run 39453711618, ha rilevato il target mancante ma ha tentato di eseguire `publish-approved-reviews.yml`, workflow ritirato senza trigger `workflow_dispatch`: errore HTTP 422.
- I tentativi urgenti iniziali erano stati interrotti da modifiche concorrenti a `main`; il vecchio retry lasciava file generati non tracciati e falliva con `Checkout contains uncommitted files`.
- Il controllo pubblico delle 18:40, run 39459420181, ha ancora rilevato HTTP 404 per l'articolo.
- È stata applicata la PR #116, merge commit `c7b63a66e7ca2abb65268dafb1bf7f2526b89b97`, che controlla l'URL live e richiama il Master esistente, oltre a ripulire i file temporanei nei retry del CI.
- Dopo il rilascio, il nuovo watchdog ha verificato la disponibilità della pagina.

## Elementi editoriali

- Coda approvata: `editorial/review-publication-queue.json`, ID `70mai-a900-ultra-20261020`, `publish_at=2026-10-20T17:45:00+02:00`.
- Fonte: `anteprima-70mai-a900-ultra.html` (contenuto completo), target `70mai-a900-ultra-recensione-dual-4k.html`.
- Le immagini risultavano caricate sotto `assets/recensioni/70mai-a900-ultra/` nella preparazione.
- La disponibilità del singolo URL e il receipt live sono verificati; l'esatta presenza nelle liste della Home e nella pagina Recensioni Tech non è stata verificata separatamente da questo registro.

## Regola per i prossimi rilasci

Distinguere sempre: approvato, build in corso, marker inviato, deploy verificato e **URL pubblico testato**. Un run `poll` o una build GitHub Pages riuscita non provano la pubblicazione su Cloudflare. Non dichiarare la recensione pubblicata se l'URL pubblico è ancora 404.
