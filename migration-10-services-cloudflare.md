# ZazoomTek — migrazione a 10 servizi indipendenti (BOZZA, NON ATTIVA)

Obiettivo: mantenere contenuti e Home correnti; recuperare il funzionamento indipendente del 15–16 ottobre, adattando gli script a Cloudflare Pages, senza riattivare Firebase.

**Importante:** questo documento non abilita workflow, non rimuove il Master, non modifica `main`, non invia deploy a Cloudflare.

## I dieci contratti operativi

1. `01-community.py` — sincronizza post Community da YouTube; scrive archivio persistente, non manipola il layout.
2. `02-video-shorts.py` — sincronizza video e Shorts; salva manifest persistente, non modifica le news Community.
3. `03-home.py` — genera le sezioni Home dai dati editoriali, mantenendo HTML e CSS approvati.
4. `04-in-evidenza.py` — seleziona e aggiorna 4 Tech + 1 Gaming dalle news pubblicate, senza eliminare automaticamente le precedenti se non vi sono nuove notizie.
5. `05-da-non-perdere.py` — rende *cinque* miniature Tech visibili, senza passaggi successivi che le sovrascrivano.
6. `06-notizie-web.py` — aggiorna le cinque notizie da fonti configurate; una grande a sinistra e quattro verticali a destra; nessun «Vedi tutte»; posizionato dopo Esplora ultimi video.
7. `07-recensioni.py` — pubblica recensioni e aggiorna indici Tech/Gaming, senza alterare la Home fuori dai relativi riquadri.
8. `08-studio.py` — pubblicazioni manuali Studio/articoli e SEO, bottoni Modifica soltanto sulle pagine di dettaglio in sessione Studio.
9. `09-layout.py` — applica assets/grafica autorizzata: nessuna importazione dati ha il diritto di modificare CSS o struttura Home.
10. `10-cloudflare-publish.py` — costruisce e rilascia una snapshot completa del sito solo su richiesta manuale autorizzata o ai cinque slot previsti; purge cache dopo deploy riuscito.

## Invarianti e dipendenze

- Ogni processo opera indipendentemente su dati persistenti, con scrittura atomica e mantenimento dell'ultima versione buona.
- Solo il servizio n. 10 esegue il deploy: evitare consumo incontrollato del limite mensile Cloudflare.
- Il deploy non deve ricostruire contenuti a partire da cache vecchie sopra i dati appena importati.
- Nessun servizio può sostituire markup delle sezioni possedute da un altro.
- Gli script automatici possono aggiornare l'archivio senza generare automaticamente un deploy fuori dagli slot.
- Il flusso manuale non deve dipendere dall'esecuzione dei cinque slot.
- Versione precedente ripristinabile; controlli di integrità su snapshot e URL restano necessari per evitare pubblicazione corrotta.
- Fino al collaudo offline i dieci script sono solo una specifica: nessuno va attivato, nessun vecchio script eliminato.
- Riutilizzare il codice già collaudato degli importatori e degli editor, invece di riscriverlo arbitrariamente.
- L'hosting di produzione resta Cloudflare Pages; nessun vecchio workflow Firebase può essere riattivato.

## Regola di rilascio

Prima di integrare su `main`, confrontare la distribuzione generata con quella corrente, verificarne contenuti e grafica, disattivare in un solo rilascio le vecchie automazioni in conflitto e richiedere autorizzazione esplicita all'utente. Non abilitare due pubblicatori concorrenti.
