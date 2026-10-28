# ZazoomTek.it — SpotNews production

Il sito ufficiale viene generato dal branch `main` mediante Cloudflare Pages.

## Build
- Comando: `python3 tools/build.py`
- Output: `dist`
- Branch di pubblicazione: `main`
- Dominio ufficiale: `https://zazoomtek.it`

## Coda editoriale
- `editorial-queue`: acquisizione di video YouTube, post Community e contenuti di Studio.
- `main`: solo contenuti promossi negli slot delle **12:30** e delle **19:30** (`Europe/Rome`).
- Finestra primo slot: dalle **09:00** alle **12:20**.
- Finestra secondo slot: dalle **12:31** alle **19:20**.
- Pubblicazione soltanto se esistono variazioni rispetto ai contenuti già approvati.

Workflow GitHub Actions:
- `.github/workflows/editorial-collect.yml`
- `.github/workflows/editorial-publish.yml`

Le pianificazioni GitHub possono subire ritardi; verificare le esecuzioni prima di considerarle operative.
Le modifiche al sito devono mantenere i contenuti editoriali, le copertine e gli URL esistenti.
