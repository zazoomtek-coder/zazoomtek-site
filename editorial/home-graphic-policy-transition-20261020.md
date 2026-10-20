# ZazoomTek.it — Home grafica: sblocco e politica transitoria (20 ottobre 2026)

## Decisione dell'editore
L'editore decide cosa modificare, come modificare la grafica e quando pubblicare.
L'assistente interviene direttamente sul codice con gli accessi disponibili, produce anteprime fedeli e verifica il rilascio.
Il Master importa, valida, pubblica e non impone immutabilità estetica.

## Intervento tecnico realmente eseguito
- PR #115, merge commit `5e1e63317d74663a6c7c65bd54f79c8c5ebd4668`.
- Rimosso il vecchio blocco rigido su hash CSS/JS, FNV dello stile inline e revisione cache Home del 18 ottobre.
- Sostituito `scripts/verify-home-layout-lock.py` con controllo di integrità transitorio senza impronte estetiche.
- Eliminati i test di pubblicazione che pretendevano implementazioni esatte delle colonne 10+10, allineamento storico, classi HTML e nomi di asset grafici datati.
- `verify-live-cloudflare.py` continua a verificare il receipt pubblico, il carosello servito, le recensioni e i loro asset, non stringhe di JS storico.
- `verify-editorial-home.py` preserva l'integrità di articoli, manifest del carosello, link, archivi, recensioni e miniature; non fissa più la vecchia disposizione delle colonne.
- Gli importatori continuano a utilizzare gli attuali marker HTML: cambiarli richiede adeguare anche gli importatori nello stesso intervento.

## Sicurezza conservata
Non rimuovere: validazione dati approvati, manifest del carosello attuale (cinque slot secondo configurazione in uso), deduplicazione, disponibilità dei file pubblici, build integrale, controlli Cloudflare live, budget di deploy, singolo writer e rollback Git.
Le scelte editoriali oggi configurate (es. composizione del carosello) non sono una protezione grafica immutabile: possono essere cambiate dall'editore, aggiornando generatori/validatori insieme.

## Parametri grafici NON ANCORA DECISI
Nessuna nuova regola di design è stata inventata o applicata. Si concordano successivamente: struttura sezioni, disposizione dei box, titoli e intestazioni, bordi, tipografia, spaziature, composizione responsive desktop/tablet/mobile e requisiti delle anteprime.
Non ripristinare vecchi hash o vecchie soglie estetiche senza autorizzazione esplicita dell'editore.

## Validazione
GitHub Actions PR #115:
- `Verify Cloudflare release pipeline (no deployment)`: success.
- `ZazoomTek Master Orchestrator - STAGING ONLY`: success, incluse anteprime desktop/tablet/mobile.
- Nessuna modifica grafica o articolo pubblicato dalla PR: soltanto codice dei controlli.
- Vecchia PR #111 chiusa come superata, senza merge.

## Regola per modifiche future
Quando l'utente richiede una modifica grafica, preparare il cambiamento e aggiornare, se serve, i contratti tra layout/importatori/validatori. Prima di rilasciare una modifica grafica sostanziale, presentare la preview della build effettiva e ottenere l'approvazione prevista; dopo il deploy verificare la home pubblica. Un errore di compilazione reale resta un errore da correggere, non un veto editoriale.
