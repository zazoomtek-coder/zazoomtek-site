# ZazoomTek SpotNews - branch di prova

Il generatore unico \`tools/build.py\` applica a tutte le pagine:
- Menu universale HOME, NEWS, RECENSIONI, GUIDE, SPECIALI, EXTRA, VIDEO.
- Il link **VIDEO** apre direttamente https://www.youtube.com/@ZazoomTek.
- Home verticale: In evidenza, News Tech, News Gaming, Ultime Recensioni, Guide e Extra, Ultimi Video, Notizie Web.
- Sidebar Home continua; sidebar interna vincolata all'altezza del testo; articoli correlati solo titoli in grassetto.

**Import YouTube**: i dati dei video verificati sono in \`data/videos.json\`. Solo recensioni, test e unboxing appaiono in Ultimi Video. Per aggiornare i nuovi video da RSS: \`python3 tools/sync_videos.py\`. I post scritti originali Community vanno in \`data/community.json\`: nessun testo è stato inventato. News filtrate automaticamente agli ultimi 14 giorni, recensioni scritte senza limite di data. Regole complete: \`IMPORT-YOUTUBE.md\`.

**Build Cloudflare Pages**: \`python3 tools/build.py\` con output \`dist\`. Preview branch \`feature/spotnews-clean-rebuild\`. Nessuna modifica a \`main\`.
