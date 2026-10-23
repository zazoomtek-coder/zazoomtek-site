# ZazoomTek — Migrazione ai 10 servizi indipendenti

Stato: **ramo di sviluppo, nessun merge e nessun deploy di produzione**.

## Servizi

1. `services10/01-community.py`: acquisizione dei post YouTube Community da più pagine ufficiali, senza perdere dati in caso di guasto temporaneo.
2. `services10/02-video-16x9.py`: acquisizione di video YouTube orizzontali 16:9, controllando dimensioni dei flussi tramite yt-dlp. Shorts e video verticali non vengono importati.
3. `services10/03-home.py`: pubblicazione incrementale di articoli Community e pagine Watch, conservando Home, archivi e contenuti preesistenti.
4. `services10/04-in-evidenza.py`: quattro notizie Tech più una Gaming, aggiornate da articoli pubblicati e senza toccare CSS e box non posseduti.
5. `services10/05-da-non-perdere.py`: esattamente cinque schede Tech visibili e correzione della vecchia regola che nascondeva la quarta e la quinta.
6. `services10/06-notizie-web.py`: cinque notizie RSS, aggiornamento al massimo ogni 24 ore, una grande a sinistra e quattro piccole a destra, nessun «Vedi tutte».
7. `services10/07-recensioni.py`: aggiornamento autonomo degli archivi recensioni, senza riscrivere recensioni, voti o immagini.
8. `services10/08-studio.py`: pulsante Modifica nelle pagine interne, quando l'accesso Studio è attivo; Home esclusa.
9. `services10/09-layout.py`: preparazione di una snapshot Cloudflare statica con HTML, CSS, immagini e asset invariati.
10. `services10/10-cloudflare-publish.py`: comando reale Wrangler per Cloudflare Pages; in fase di review il ramo di destinazione è `zt-services10-review`, non `main`.

## GitHub Actions

Solo due workflow nel ramo:
- `services10-scheduled-cloudflare.yml`: cinque cron quotidiani Europe/Rome, 10:15, 12:45, 15:15, 17:45, 20:15. Le Actions pianificate non funzionano su questo ramo di prova: GitHub esegue gli schedule dal ramo predefinito.
- `services10-offline-tests.yml`: compilazione Python, test degli importatori e degli archivi persistenti, verifica dei box e generazione dell'intero sito senza deploy.

I dati importati sono conservati dal servizio `services10/state.py` su un ramo dati indipendente, con unione delle versioni concorrenti.

## Verifiche eseguite

- Test con dati simulati: Community, video 16:9 senza Shorts, guasti per singolo elemento, archiviazione e recupero, Home, recensioni, Studio, layout, cron, RSS e argomenti Wrangler.
- Generazione statica di **816 pagine HTML** eseguita su GitHub Actions.
- Nell'ultima scansione sono rimasti **13 riferimenti storici mancanti**, non introdotti dai nuovi componenti.
- Nessun deploy Cloudflare di anteprima o produzione eseguito finora per questa ricostruzione.

## Da completare prima del merge

- Testare l'acquisizione reale dei post Community dal canale: il lettore attuale rileva le pagine pubbliche disponibili, ma non copre ancora tutte le continuazioni/paginazioni storiche.
- Collaudare il deploy su ramo Cloudflare **non di produzione**, una volta autorizzato il consumo di una pubblicazione di anteprima.
- Verificare la resa grafica in un browser di Home, news, Watch e recensioni, e confrontarla visivamente con il sito online.
- Recuperare, ove possibile, i 13 collegamenti storici mancanti senza inventare contenuti.
- Aggiornare il workflow finale dalla branch preview a `main` soltanto dopo review e autorizzazione espressa.

**Non sostituire `main` né attivare la pubblicazione live prima della review.**
