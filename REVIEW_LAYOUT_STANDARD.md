# Standard grafico per le recensioni ZazoomTek.it

Riferimento visuale approvabile: `preview-recensione-sesame-street-ps5-20261012.html` (anteprima della recensione "Sesame Street: Amici e risate" PS5, 12 ottobre 2026).

## Ambito
Applicare lo stesso impaginato a TUTTE le recensioni presenti sul sito e a ogni recensione futura, sia importata dalla Community YouTube sia incollata manualmente e approvata per la pubblicazione. Per i contenuti esistenti, prima verificare e ottenere approvazione della live preview. Non modificare l'archivio pubblico sulla base della sola anteprima.

## Specifica impaginazione
- Conservare intestazione, logo colorato, navigazione e stile editoriale di ZazoomTek.it.
- Titolo leggibile, eventuale sommario/lead compatto, copertina grande con rapporto 16:9 senza sfumature nere sovrapposte alle foto.
- Sottotitoli in grassetto nero e paragrafi continui/compatti; niente interruzioni e spazi vuoti superflui. Evitare duplicazioni del cappello/Introduzione.
- Fotografare il contenuto con immagini effettivamente fornite/disponibili, mai inventate o intercambiabili fra prodotti. Distribuirle tra le sezioni: immagini panoramiche a piena larghezza e, dove opportuno, coppie di screenshot affiancati. Su smartphone le coppie diventano una colonna.
- Per videogiochi usare, quando pertinenti, Storia, Gameplay (ampio), Aspetto tecnico (ampio, riferito alla piattaforma provata), Esperienza complessiva, Conclusioni. Per hardware seguire le sezioni della recensione tech pertinenti. Nessun dato/test/performance inventati.
- Conclusioni in un unico paragrafo, una domanda ai lettori, Voto finale X/10 solo quando già presente, Pro e Contro separati e leggibili; evitare duplicati.
- Immagini responsive con dimensioni stabili, alt descrittivo, caricamento progressivo delle immagini interne, nessuna deformazione delle cover; mantenere accessibilità e leggibilità su desktop e smartphone.
- Preservare per le recensioni esistenti titolo, testo approvato, URL/slug, canonical, metadati SEO, Open Graph, dati strutturati, date, collegamenti, immagini e commenti. Intervenire sull'impaginazione, non riscrivere contenuti senza istruzione.

## Controlli prima della pubblicazione
1. Anteprima navigabile desktop e mobile completa con tutte le fotografie reali dell'articolo.
2. Controllare che ogni recensione sia elencata nell'archivio Recensioni e che link e miniature funzionino.
3. Su approvazione dell'utente applicare lo standard alle recensioni esistenti e al percorso di pubblicazione futura; verificare che l'import da YouTube non sovrascriva il layout personalizzato.
4. Niente deploy automatici o pubblicazioni che bypassino la revisione editoriale approvata.


## Regola fissa anti-doppioni — importazione Community YouTube
- Prima di importare una recensione scritta, confrontare gioco/prodotto (titolo normalizzato, indipendente da maiuscole, simboli, diciture Review/Recensione e sottotitoli) e piattaforma con le recensioni già pubblicate.
- Se è già presente, non creare una nuova pagina, una seconda scheda archivio o duplicati in Home/pagine paginate. Dare priorità alla recensione editoriale pubblicata manualmente.
- Anche due post Community distinti (ID YouTube diversi) sul medesimo prodotto/piattaforma devono produrre un solo articolo.
- Distinguere le recensioni di piattaforme diverse quando specificate; non confondere le News con le Recensioni.
- Preservare le recensioni editoriali manuali nel catalogo durante il successivo aggiornamento automatico.
- Il controllo è nello script scripts/update-youtube-posts.py con test offline scripts/test_review_dedup.py eseguiti dal workflow youtube-sync.yml.
