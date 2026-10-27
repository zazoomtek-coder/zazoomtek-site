# Regole importazione YouTube (27 ottobre 2026)

Canale ufficiale: https://www.youtube.com/@ZazoomTek · UCJs0ZT10hUiPRD0UZtUpI1Q

## Video
\`data/videos.json\` contiene metadati dei video verificati attraverso il canale connesso (titoli, ID e date). Solo \`kind=review|test|unboxing\` appare in «Ultimi Video» e in \`/video.html\`. Gameplay, news video, promozioni e Shorts non appaiono in questa sezione. Collegamenti e miniature aprono YouTube. Il menu **VIDEO** va direttamente al canale YouTube.

Per aggiornamenti successivi usare \`python3 tools/sync_videos.py\`, che legge il feed ufficiale RSS e aggiunge solo video con tipologia e argomento riconosciuti. **Nessuna pianificazione è attiva** sul branch di prova.

## Post scritti YouTube Community
La YouTube Data API e gli strumenti attualmente collegati non forniscono qui l'elenco e il testo originale di tutti i post Community. È vietato sostituire una recensione scritta con il titolo di un video o con un testo inventato.

\`data/community.json\` accetta esclusivamente post originali verificati con campi:
\`id, date (ISO 8601), title, text, type (news|review|guide|speciali|extra), topic (tech|gaming), url\`. \`category\` può sostituire \`type\`+\`topic\` (es. \`recensioni-tech\`, \`news-gaming\`).

I post scritti \`review\` entrano nelle Recensioni **senza limiti di data**; le \`news\` entrano solo se datate negli ultimi 14 giorni dalla build. Guide, Speciali, Extra sono sezioni dedicate. Classificazioni senza argomento Tech/Gaming sicuro vengono omesse anziché assegnate a caso. Nessuna duplicazione: l'ID del post forma uno slug univoco.

**Stato Community:** nessun post caricato perché qui non è disponibile una fonte autenticata per i testi completi. Questo non equivale ad aver importato tutte le recensioni scritte.

**Stato Cloudflare:** un nuovo commit al branch di prova dovrebbe avviare il deployment configurato; la riuscita si verifica separatamente nella dashboard.
