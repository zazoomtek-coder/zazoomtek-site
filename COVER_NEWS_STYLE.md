# ZazoomTek.it — regole permanenti per le cover delle NEWS

Approvato dalla redazione il 9 ottobre 2026. Questo è lo standard da applicare alle nuove notizie pubblicate sul sito.

## Stile da mantenere
- Usare una fotografia reale, riconoscibile e specificamente pertinente alla notizia: edifici istituzionali per notizie istituzionali, dispositivi reali per notizie hardware, persone che giocano o scene pertinenti per videogiochi.
- Mai usare come ripiego sfondi vettoriali, icone astratte o fotografie fuori tema. Se non esiste un'immagine sicura e pertinente, sospendere la pubblicazione della cover e richiedere una scelta editoriale.
- Composizione come le cover fotografiche Tech Impact / Gaming Inside approvate il 9 ottobre: soggetto fotografico ben visibile, leggera sfumatura scura sul lato del testo, marchio ZazoomTek.it e categoria, titolo principale bianco leggibile, breve richiamo in basso e sottile accento colorato.
- Non coprire eccessivamente il soggetto della foto e non affollare la cover con troppo testo.
- Mantenere varietà degli accenti di colore, ma conservare la coerenza tipografica e riconoscibilità della testata.
- 16:9, 1280 x 720 pixel, formato WebP, massimo 300.000 byte; non alterare immagini editoriali già approvate se non richiesto.
- Per ogni foto, verificare la licenza per uso editoriale, salvare fonte, autore, licenza, URL e modifiche nei manifest e mostrare l'attribuzione quando necessaria. Utilizzare solo fotografie da fonti autorizzate, incluse immagini Wikimedia Commons verificate CC0, pubblico dominio, CC BY o CC BY-SA nel rispetto delle condizioni.
- I videogiochi/prodotti illustrati indirettamente devono essere descritti come fotografie illustrative, mai confusi con screenshot ufficiali.

## Ordine e aggiornamento della homepage
- Le NEWS nel carosello “News in evidenza” sono le 10 pubblicazioni fotografiche idonee più recenti, ordinate per data/ora di pubblicazione decrescente. I nuovi articoli entrano in cima e quelli più vecchi escono automaticamente dalla selezione.
- Lo scorrimento visivo è automatico (ogni 6 secondi) e mantiene i controlli precedente/successiva.
- La stessa notizia deve apparire una sola volta. Per articoli pubblicati nello stesso giorno, usare `published_at` ISO 8601 quando disponibile; in assenza di un'ora esatta, mantenere l'ordine editoriale come criterio di parità, senza inventare orari.
- Conservare le cover locali e le relative licenze; le news importate automaticamente da YouTube restano gestite dagli importatori esistenti, che non vanno modificati in questa pipeline.

## Pubblicazione giornaliera
- GitHub Actions controlla ogni mattina gli articoli Tech Impact, Gaming Inside e NEWS standard approvati, e prepara le loro cover fotografiche.
- Le nuove notizie devono essere già originali, documentate e approvate; la scansione RSS/Google News di ricerca NON è autorizzazione automatica alla pubblicazione.
- Se non ci sono nuove notizie approvate, non ripubblicare artificialmente gli articoli vecchi e non generare nuove immagini solo per riempire la homepage.
- Mantenere intatti importatori VIDEO, RECENSIONI e NEWS Community.
