# Import video ZazoomTek — YouTube Data API v3

## Principio
Solo video orizzontali 16:9, senza Shorts. Nessun cookie personale, download video o yt-dlp.

Lo script 02-video-16x9.py usa channels.list, playlistItems.list (fino a 100 nuovi video), videos.list (blocchi da 50), e feed RSS ufficiale come sorgente di riserva. I metodi costano 1 unità API per chiamata, invece della ricerca generica.

La chiave si configura esclusivamente come GitHub Actions secret YOUTUBE_API_KEY, mai nel codice. La chiave è risultata già disponibile nel collaudo reale del 23 ottobre 2026.

## Limite tecnico importante
YouTube Data API v3 con sola API Key NON restituisce il rapporto d'aspetto originale. La dimensione delle miniature e dell'embed non equivale alle dimensioni della sorgente; il campo contentDetails.dimension significa 2D/3D.

- Durata fino a 180 secondi: possibile Short; mai importare automaticamente in assenza di prova diretta del formato.
- Durata oltre 180 secondi: non Short secondo le attuali regole della piattaforma, ma l'orientamento resta sconosciuto; salvare in services10-data/pending-videos.json.
- ID confermato 16:9: importare in services10-data/videos.json con type=landscape_video e verification=confirmed_16x9_registry.
- Video privati, di un altro canale, futuri, live e non riproducibili: ignorare.
- In caso di API key mancante, quota esaurita o API irraggiungibile, il feed RSS aggiorna solo gli ID già confermati, senza perdere i video preesistenti.

## Approvazione dei singoli video
Nelle GitHub Actions repository variables, aggiungere ZT_CONFIRMED_16X9_IDS, valore con ID video confermati e separati da virgole, ad esempio:
ABCDEFGHIJK,LmnopqrstUV

È anche possibile predisporre services10-data/confirmed-16x9.json nel workspace, con oggetti JSON aventi id e confirmed=true. I nuovi elementi vengono verificati solo se identificati dalla Data API o dal RSS ufficiale.

L'elenco pending non è distribuito come pagina pubblica. Quando un ID viene confermato e pubblicato, il backup Git lo rimuove dalla coda pending.

Per una certificazione automatica esatta del rapporto d'aspetto senza conferme manuali, YouTube rende fileDetails.videoStreams[].aspectRatio disponibile SOLO al proprietario del canale con autorizzazione OAuth. L'API Key da sola non è sufficiente. Un'integrazione OAuth ufficiale sarebbe una soluzione futura e distinta dai cookie del browser.

## Verifiche
Test offline: python3 services10/test-importers.py e python3 services10/test-state.py.
Collegamento reale: job real-youtube di services10-offline-tests.yml.
Anteprima Cloudflare: il flag ZT_SERVICES10_PREVIEW_ENABLED deve essere true, evitando deploy inutili a ogni commit.
I cinque slot Europe/Rome restano nella branch di sviluppo fino all'autorizzazione finale.
