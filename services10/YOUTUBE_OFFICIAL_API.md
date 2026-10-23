# Import video ZazoomTek — due condizioni obbligatorie

## Regola editoriale 23 ottobre 2026

Il video entra nelle nuove pubblicazioni del sito SOLO se sono entrambe vere:

1. La durata ufficiale `contentDetails.duration` è superiore a 180 secondi, ovvero **181 secondi o più**.
2. Il formato sorgente ha un **display aspect ratio 16:9** verificato con informazioni autorizzate del proprietario o con un registro di ID già verificati.

Video **fino a 180 secondi**, verticali 9:16, quadrati 1:1, 4:3, privati, live e video non embeddable sono esclusi. Video più lunghi di 180 secondi ma con geometria non disponibile NON sono approvati: restano nell'archivio `services10-data/pending-videos.json` e non generano pagine Watch.

## Fonti tecniche

- YouTube Data API v3 con API key `YOUTUBE_API_KEY`: canale, playlist uploads, durata, titolo, visibilità; in caso di problema si conserva l'archivio precedente. RSS ufficiale per scoprire ID, ma non misura l'orientamento o la durata.
- YouTube Data API v3 `videos.list(part=fileDetails)` **autorizzata dal proprietario del canale**: usa `fileDetails.videoStreams[].aspectRatio` o larghezza/altezza con rotazione per certificare il formato 16:9. Rifiuta il 9:16, l'1:1 e il 4:3.
- Alternativa a OAuth: lista `ZT_CONFIRMED_16X9_IDS` contenente soltanto ID già controllati come 16:9. Anche gli ID registrati devono superare i 180 secondi.

Una API key pubblica da sola non dà accesso al rapporto d'aspetto originale: YouTube riserva `fileDetails` al proprietario. L'importatore non indovina la geometria dalle miniature o dai player 16:9.

## OAuth ufficiale opzionale, senza cookie browser

Per verifica totalmente automatica impostare in GitHub Actions **Secrets** (mai in chat, mai nel repository):

- `YOUTUBE_OAUTH_CLIENT_ID`
- `YOUTUBE_OAUTH_CLIENT_SECRET`
- `YOUTUBE_OAUTH_REFRESH_TOKEN`

Lo script usa il refresh token in modo server-to-server per ottenere un access token temporaneo e interrogare il `fileDetails` del proprietario, senza esportare le credenziali nei log. Il consenso OAuth deve essere concesso dal proprietario tramite il normale flusso di Google, separatamente dalla presente modifica.

Fino a quando il collegamento non è configurato, i video con orientamento sconosciuto restano in attesa: **non sono importati per errore**.

## Migrazione e verifiche

I record creati in precedenza con `verification=duration_over_3m_not_short` o `orientation=unverified` sono retrocessi dalla lista pubblicabile alla coda di verifica. I file precedenti chiaramente confermati non vengono cancellati. La coda non viene inserita in `dist`.

Collaudo isolato: `python3 services10/test-importers.py`, `python3 services10/test-state.py`, workflow `services10-offline-tests.yml`. Gli orari Europe/Rome rimangono 10:15, 12:45, 15:15, 17:45, 20:15 nel ramo di review. Nessun merge `main` o deploy Cloudflare production senza approvazione.
