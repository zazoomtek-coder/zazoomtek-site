# ZazoomTek — Importazione YouTube protetta

## Regola editoriale e tecnica prioritaria

L'importazione automatica di **news dalla Community, recensioni scritte,
video e relativi dati da YouTube @ZazoomTek** è un servizio critico del sito.
Ogni altra modifica a ZazoomTek.it deve preservarla.

## Confine protetto

- Importazione news/recensioni: `scripts/update-youtube-posts.py`.
- Importazione video: `scripts/update-youtube.py`.
- Controlli: `scripts/validate-sync-output.py`, `scripts/test_review_dedup.py`.
- Coordinamento: `.github/workflows/youtube-sync.yml`.
- Recupero deploy: `.github/workflows/youtube-publishing-safety-net.yml`.
- Stato: `.youtube-posts.json` e `.youtube-latest.json` (mai cancellarli o resettarli durante le normali modifiche).

**Non modificare questi file quando si lavora su carosello, design, Tech Impact,
Gaming Inside, Google Analytics, SEO, ricerca, Guide o articoli manuali**, se la
modifica non richiede espressamente un intervento all'importazione YouTube.

## Regola vincolante: video solo via player YouTube

- **Non scaricare, copiare, caricare o conservare file video** (MP4, WebM, ecc.) su GitHub, Firebase Hosting o Cloudflare. Il video rimane ospitato da YouTube.
- L'importatore `scripts/update-youtube.py` acquisisce **solo ID, titoli, date, categorie, URL, miniature/link e metadati** necessari alle schede del sito; l'espressione «importare video» significa importare le schede, **mai i file audiovisivi**.
- Nelle pagine di ZazoomTek.it, cliccando sulla copertina si apre il **player incorporato di YouTube** (preferire `https://www.youtube-nocookie.com/embed/VIDEO_ID`), come nella recensione «Poly Fighter PC»: riproduzione dai server YouTube, non dalla banda del nostro hosting.
- Preferire miniature remote `https://i.ytimg.com/vi/VIDEO_ID/...` quando disponibili; non confondere le copertine locali degli **articoli Community**, che restano pubblicazioni editoriali, con file video.
- **Priorità assoluta durante la migrazione Cloudflare**: preservare separatamente sia l'importazione automatica di video/player sia quella dei post Community (news e recensioni). Non dimezzare né sospendere queste due importazioni per risparmiare build o traffico. Eventuali riduzioni riguardano prima automazioni non essenziali.
- L'integrazione player richiede che il video sia pubblico e consenta l'incorporamento; se non è incorporabile, mostrare un link di apertura su YouTube, senza copiarne il file.
- Verificare per ogni migrazione che le schede mostrino miniatura, titolo, clic, player e fallback, e che nessun flusso produca file video locali.

## Separazione degli errori

1. Ogni 5 minuti verificare il canale YouTube.
2. Validare la Community e pubblicarla (commit, push, Firebase) PRIMA di ogni
   script accessorio. Le recensioni scritte fanno parte della Community.
3. Validare e pubblicare i video con un percorso indipendente, anche se la
   Community fallisce, e viceversa.
4. Lo script del carosello, le copertine editoriali, i box, gli articoli
   correlati, l'analytics e l'indice di ricerca NON sono prerequisiti
   dell'importazione né del suo deploy.
5. Se una fonte o una validazione fallisce, non cancellare i file pubblicati
   validi: mantenere l'ultima versione buona e segnalare l'errore.
6. Prima di ogni deploy ricaricare `origin/main` per non sovrascrivere
   importazioni più recenti con un checkout vecchio.
7. Il recupero Firebase separato ridistribuisce ogni ora l'ultima versione
   validata presente su GitHub, senza riscrivere gli articoli.

## Verifica obbligatoria quando si modifica il sito

- Syntax check degli importatori e dei workflow.
- Test di deduplicazione delle recensioni.
- Validazione dello stato YouTube e presenza dei link agli ultimi contenuti.
- Verifica dell'esecuzione del workflow e del commit prodotto.
- Distinguere sempre **importato nel repository** da **visibile su Firebase**.
- In caso di errore di una funzione opzionale, fare rollback della sola
  funzione opzionale, MAI dei contenuti YouTube verificati e già pubblicati.

## CODEOWNERS

`.github/CODEOWNERS` segnala i file più sensibili. Per bloccare modifiche
dirette o non revisionate occorre inoltre configurare su GitHub una regola
di protezione di `main` che richieda pull request e code-owner approval.
CODEOWNERS da solo non impone questa restrizione.

Nessuna automazione può garantire assenza assoluta di guasti di YouTube,
GitHub o Firebase; l'obiettivo è evitare guasti incrociati, contenere i
fallimenti e recuperare in modo sicuro l'ultimo stato valido.
