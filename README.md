# ZazoomTek · SpotNews — branch di prova

Menu universale: HOME · NEWS · RECENSIONI · GUIDE · SPECIALI · EXTRA · VIDEO.

Home verticale nell'ordine tassativo: In evidenza, News Tech, News Gaming, Ultime Recensioni, Guide e Extra, Ultimi Video, Notizie Web. Sidebar destra continua fino alla fine Home.

Tutte le pagine interne, articoli e recensioni: sidebar laterale che termina esattamente a fine testo; i correlati sono sotto, esclusivamente titoli in grassetto e senza immagini.

Nessun post XML/Blogger migrato. data/posts.json e data/web.json inizialmente vuoti. Un solo generatore di pagine: tools/build.py. Tutte le pagine future ereditano le stesse regole.

Cloudflare Pages: build command `python3 tools/build.py`; output directory `dist`.
Branch preview: `feature/spotnews-clean-rebuild`, **non** modificare `main`. Preview noindex. Non dichiarare attivi deploy o importatori se non configurati.

Per pubblicare articoli, inserire oggetti nei dati senza duplicare i template. L'integrazione YouTube e l'acquisizione dei post Community richiedono configurazione separata.
