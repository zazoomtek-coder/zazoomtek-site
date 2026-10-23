# Import video ZazoomTek — YouTube Data API v3

## Principio
Video standard secondo la regola editoriale **durata > 180 secondi**, senza Shorts; i video corti si importano soltanto quando sono già stati confermati 16:9. Nessun cookie personale, download video o yt-dlp.

Lo script 02-video-16x9.py usa channels.list, playlistItems.list (fino a 100 nuovi video), videos.list (blocchi da 50), e feed RSS ufficiale come sorgente di riserva. I metodi costano 1 unità API per chiamata, invece della ricerca generica.

La chiave si configura esclusivamente come GitHub Actions secret YOUTUBE_API_KEY, mai nel codice. La chiave è risultata già disponibile nel collaudo reale del 23 ottobre 2026.

## Regola automatica editoriale (23 ottobre 2026)
YouTube Data API v3 con sola API Key NON restituisce il rapporto d'aspetto originale. La dimensione delle miniature e dell'embed non equivale alle dimensioni della sorgente; il campo contentDetails.dimension significa 2D/3D. **Un video di oltre tre minuti non è uno Short, ma può essere verticale, quadrato o 4:3: questa regola è una scelta editoriale e non una certificazione 16:9.**

- Durata fino a 180 secondi: possibile Short; mai importare automaticamente in assenza di prova diretta del formato.
- **Durata > 180 secondi (181 o più): importazione automatica** come video standard su ZazoomTek. Metadata `type=landscape_video`, `verification=duration_over_3m_not_short`, `orientation=unverified`. Non si mette in coda di verifica.
- ID di durata fino a 180 s confermato 16:9: può entrare in services10-data/videos.json con `type=landscape_video` e `verification=confirmed_16x9_registry`.
- Video privati, di un altro canale, futuri, live e non riproducibili: ignorare.
- In caso di API key mancante, quota esaurita o API irraggiungibile, il feed RSS aggiorna solo gli ID già confermati, senza perdere i video preesistenti.

## Eccezione per video corti confermati
Nelle GitHub Actions repository variables, aggiungere ZT_CONFIRMED_16X9_IDS, valore con ID video confermati e separati da virgole, ad esempio:
ABCDEFGHIJK,LmnopqrstUV

È anche possibile predisporre services10-data/confirmed-16x9.json nel workspace, con oggetti JSON aventi id e confirmed=true. I nuovi elementi vengono verificati solo se identificati dalla Data API o dal RSS ufficiale.

L'elenco pending non è distribuito come pagina pubblica. Le vecchie voci con durata maggiore di 180 secondi sono promosse automaticamente dall'archivio pending; le voci residue vengono eliminate dalla coda obsoleta.

La nuova regola non richiede OAuth. Qualora in futuro si volesse una certificazione automatica *esatta* del rapporto d'aspetto, YouTube rende fileDetails.videoStreams[].aspectRatio disponibile SOLO al proprietario del canale con autorizzazione OAuth. L'API Key da sola non è sufficiente. Un'integrazione OAuth ufficiale sarebbe una soluzione futura e distinta dai cookie del browser.

## Verifiche
Test offline: python3 services10/test-importers.py e python3 services10/test-state.py.
Collegamento reale: job real-youtube di services10-offline-tests.yml.
Anteprima Cloudflare: il flag ZT_SERVICES10_PREVIEW_ENABLED deve essere true, evitando deploy inutili a ogni commit.
I cinque slot Europe/Rome restano nella branch di sviluppo fino all'autorizzazione finale.
