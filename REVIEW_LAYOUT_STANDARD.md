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

## Regola permanente — video nelle recensioni (13 ottobre 2026)
- Priorità assoluta ai video pertinenti, già pubblicati sul canale YouTube `@ZazoomTek` (ID `UCJs0ZT10hUiPRD0UZtUpI1Q`). Verificare sempre titolo, gioco/prodotto, piattaforma e ID YouTube; non scegliere un video generico, una notizia su un titolo omonimo o un video non pubblicato.
- Se il video corretto non è disponibile sul canale ZazoomTek, usare esclusivamente un trailer o video ufficiale del relativo gioco/prodotto disponibile su YouTube, caricato dal publisher/sviluppatore o da fonte autorizzata, con incorporamento consentito. Non trattare la mera presenza su YouTube come prova assoluta dei diritti.
- Player unico a fine recensione, **dopo Voto finale e Pro e Contro**, preceduto da intestazione descrittiva (per il video del canale: `Video recensione ZazoomTek`; per l'esterno: `Trailer ufficiale di [titolo]`). Non duplicare il video in altri punti dell'articolo.
- Il filmato rimane interamente ospitato sul servizio video esterno: NON caricare file MP4/MKV/HLS su Firebase Hosting, GitHub, né copiare video Steam o usare `video.fastly.steamstatic.com` come sorgente del player.
- Incorporamento ufficiale YouTube tramite `https://www.youtube-nocookie.com/embed/VIDEO_ID`. Su apertura pagina visualizzare un poster leggero e un pulsante Play; **non caricare l'iframe fino al clic consapevole del lettore**. Includere spiegazione sui contenuti terzi/link YouTube ed eventuale informativa privacy; non introdurre cookie non necessari senza le opportune verifiche/consenso.
- Player responsive 16:9, `title` accessibile, pulsanti video standard, link diretto alla fonte in caso di indisponibilità; verificare che l'incorporamento sia abilitato e riproducibile. Se non esiste alcun video appropriato e incorporabile, mostrare soltanto un link alla pagina ufficiale, senza player rotto.
- Applicare questo criterio a TUTTE le nuove recensioni, importate o incollate, **senza modificare automaticamente le recensioni esistenti non approvate** e senza sovrascrivere sezioni, menu, CSS condiviso, struttura, SEO o layout del sito.
- Per Poly Fighter del 13 ottobre 2026, l'anteprima approvata con questa logica è `anteprima-poly-fighter-trailer-youtube-20261013.html`; la pagina finale programmata è `poly-fighter-recensione-pc.html`. Se prima della pubblicazione compare una video recensione ZazoomTek verificata e incorporabile, usarla in via preferenziale; altrimenti mantenere il trailer ufficiale YouTube già approvato (`cYkb8Z7JyqQ`).

