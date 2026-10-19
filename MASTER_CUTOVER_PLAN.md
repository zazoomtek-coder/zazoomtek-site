# ZazoomTek: piano di cutover atomico GitHub → Master → Cloudflare

**Stato 19 ottobre 2026: NON ARMATO.** Il sito live e gli aggiornamenti esistenti non devono interrompersi per una migrazione parziale. `master-production-enabled.json` è intenzionalmente `false`; il workflow nuovo non ha una schedule, solo dispatch protetto. Un merge isolato della PR #106 NON rappresenta un cutover.

## Inventario: 14 writer legacy (7 con schedule)

| File workflow | Pianificazione | Destinazione nel Master |
|---|---|---|
| `youtube-sync.yml` | Ogni 5 minuti | Import Community/video JSON + rendering Cloudflare |
| `refresh-static-news-in-evidenza.yml` | Ogni 2 ore | Scansione portali + 5 slot 4 Tech / 1 Gaming |
| `refresh-home-editorials-daily.yml` | Quotidiana | Box editoriali JSON + rendering statico |
| `cloudflare-controlled-release.yml` | Più controlli all'ora | Unico gate Git/Cloudflare con verifica ricezione live |
| `publish-approved-reviews.yml` | Ogni 5 minuti | Coda JSON recensioni approvate + rendering |
| `publish-standard-news.yml` | Quotidiana | Pubblicazione news approvate nella build senza writer parallelo (**adattatore da collaudare**) |
| `seo-video-archive.yml` | Quotidiana | Archivio video JSON nel Master (**da integrare**) |
| `publish-special-news.yml` | Manuale | Tech Impact/Gaming Inside approvate (**da integrare**) |
| `discover-special-news.yml` | Manuale | Ricerca/proposta separata dalla pubblicazione (**da riconfigurare**) |
| `scan-trending-portals.yml` | Manuale/push | Ricerca trend e proposte nel modulo del Master (**da riconfigurare**) |
| `refresh-featured-cover-photos.yml` | Manuale | Solo copertine verificate su richiesta editoriale (**da riconfigurare**) |
| `build-guide-archive.yml` | Manuale/push | Indice Guide generato al build Cloudflare (**da integrare**) |
| `verify-rotating-sidebars.yml` | Manuale/push | Sidebar JSON nella build; audit read-only (**da integrare**) |
| `perf-header-logo-stage.yml` | Ramo di staging isolato | Ritirare, mantenere i test visuali in sola lettura |

## Due dispatchers indiretti da pensionare nel medesimo commit

- `youtube-publishing-safety-net.yml`: richiama `youtube-sync.yml`; sostituire con controllo read-only del Master.
- `zt-urgent-cloudflare-dispatch.yml`: richiama `cloudflare-controlled-release.yml`; sostituire con evento protetto verso il Master o eliminare il dispatch obsoleto.

## Sequenza inderogabile

1. Realizzare/validare gli adattatori ancora mancanti per news standard, speciali, guide, archivio video, sidebar e pubblicazioni editoriali.
2. Test completo con input reale autorizzato YouTube/portali e riproduzione JSON→HTML nel build disaccoppiato; screenshots desktop/tablet/mobile, nessun cambiamento ai file grafici.
3. Verificare da Cloudflare Pages che il progetto segua il repository Git e abbia build watch path **esclusivamente** `cloudflare-release-trigger.txt`; controllare quota disponibile e ultima ricevuta live. Il repository non prova da solo che Cloudflare sia configurato così.
4. Preparare **UN solo commit cutover**: i 14 workflow diventano senza permessi di scrittura/attivazione, i due dispatcher cessano di richiamarli; aggiungere `schedule` sul nuovo Master e mettere `enabled: true`.
5. Non dichiarare concluso solo dal merge: eseguire il Master, validare il primo commit dati, il trigger unico, i test predeploy e la ricevuta `/zt-release-status.json` sul dominio pubblico. In caso di guasto nessun force push, nessun nuovo trigger; conservare ultima release live.
6. Se il primo rilascio non è verificabile, ripristinare il sistema precedente **coordinatamente** e con una PR/commit sicuro, mai riaccendere singoli writer mentre il Master è operativo.

### Criterio GO/NO-GO

`scripts/master-cutover-audit.py` deve riportare **zero legacy writers**, **zero dispatcher indiretti** e `cutover_ready=true`; devono essere verdi anche test API, rendering e verifica pubblica Cloudflare. Fino a quel momento: **NO merge operativo e NO disattivazioni**.
