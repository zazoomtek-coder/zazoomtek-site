# ZazoomTek.it — Registro operativo pubblicazioni (20 ottobre 2026)

## Stato confermato
- Repository: `zazoomtek-coder/zazoomtek-site`, branch `main`.
- Cloudflare Pages: rilascio comandato da GitHub mediante `cloudflare-release-trigger.txt`.
- **Fix PR #114**: merge commit `e6e31fe924f3c7bf521ac5f6e4d7625f8a303c10`.
- Test PR #114 superati: Master Orchestrator staging, Cloudflare-equivalent build, Master release slot safety.
- Comando manuale esercitato realmente: commit `1b096bc609ff3b3b447c22ecd28328ba220a6ba7` su `cloudflare-manual-release-request.json`, messaggio `zt: manual Cloudflare release - verify restored publishing 2026-10-20`.
- Cloudflare trigger emesso da Master: source_commit `1b096bc609ff3b3b447c22ecd28328ba220a6ba7`, priority `urgent`; commit marker `02fcac988a3f7f45fe1dfa79b669945ca25b4715`.
- GitHub Actions run `39439906563` / job `118686685935`: **success**. Log alle 2026-10-20 14:40:55 UTC: `VERIFIED: public Cloudflare release matches master source`.
- La verifica pubblica conferma il receipt e i contenuti obbligatori previsti da `scripts/verify-live-cloudflare.py`.

## Pubblicazione manuale: procedura per ChatGPT
1. Verificare che la modifica richiesta sia approvata, già presente in `main` e compatibile con la protezione della home. Non anticipare contenuti con `publish_at` futuro senza richiesta esplicita.
2. Aggiornare **solo** il file di controllo `cloudflare-manual-release-request.json` usando il connettore GitHub, con JSON valido e commit message che **inizi** esattamente con `zt: manual Cloudflare release`.
3. Il workflow `.github/workflows/master-orchestrator-production.yml` identifica il comando e avvia `scripts/master-production-gateway.py --publish-pending --urgent`.
4. Questo percorso non esegue importazioni YouTube/news; mantiene esclusività di scrittura, protezione home, calcolo delle modifiche pubbliche, budget, build completa e verifica pubblica.
5. Controllare l'esito del run GitHub Actions e cercare il log `VERIFIED: public Cloudflare release matches master source`. **Non dichiarare pubblicato** prima della conferma.
6. Se non vi sono cambiamenti pubblici rispetto al rilascio precedente, non forzare build vuote. Se ci sono errori di quota, build, layout o hosting, segnalarli senza aggirare i controlli.

## Pubblicazioni programmate
- Le cinque finestre editoriali `Europe/Rome` sono 10:15, 12:45, 15:15, 17:45, 20:15. Le scansioni intermedie mantengono la modalità `poll`.
- `scripts/cloudflare-release-control.py` considera qualsiasi modifica pubblica approvata (recensioni, CSS, articoli, correzioni) e non pretende l'ingresso di nuove notizie a ogni finestra.
- Se un importatore fallisce durante una pubblicazione **programmata**, il gateway scarta le eventuali modifiche parziali e può rilasciare i contenuti già approvati con la build integrale e gli stessi controlli. Le importazioni fallite vanno comunque corrette.
- I contenuti con `publish_at` nel futuro devono rispettare l'orario. Esempio al 20 ottobre: `70mai-a900-ultra-20261020` risulta approvato per le 17:45 italiane, non viene anticipato automaticamente.

## Limiti e autorizzazioni
- Permessi GitHub amministrativi verificati. **Non** esiste prova di accesso diretto ChatGPT al pannello amministrativo Cloudflare, ma il deploy via GitHub è stato verificato end-to-end.
- Cloudflare può legittimamente rifiutare o ritardare un deploy per quota, outage, errore di build, DNS o policy: non bypassare i controlli di sicurezza.
- Non riattivare vecchi workflow concorrenti; non toccare Firebase; non usare GitHub Pages come prova del deploy Cloudflare.
- Il rollback del codice è possibile tramite git revert del merge `e6e31fe...` dopo verifica dei successivi commit. Per una release già distribuita serve un nuovo rilascio controllato dell'ultima versione buona.

## Stato residuo al 20 ottobre
- Pubblicazione manuale: **eseguita e verificata in produzione**.
- Le cinque finestre automatiche: nuova logica **testata e installata**; risultati dei prossimi slot da controllare quando avvengono.
- Accesso diretto Cloudflare amministrativo: **non verificato**.
