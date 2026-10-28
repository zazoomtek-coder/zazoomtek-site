# Studio — accesso amministratore sicuro, senza 404

## Perché compareva «Access not configured» e il pulsante «Modifica» non appariva
Il codice di Studio è presente nella preview, ma non è stata configurata
un'applicazione Cloudflare Access né sono state definite tutte le variabili
server indispensabili. **Il collegamento precedente a
`/cdn-cgi/access/login` è stato eliminato**: senza un'app Access restituisce
404, e non può autenticare nessuno. La pagina ora mostra la procedura di
attivazione invece di simulare un login operativo.

## Attivazione iniziale — riservata al proprietario Cloudflare

1. Apri Cloudflare Dashboard → **Workers & Pages** →
   **zazoomtek-spotnews-preview**. L'autenticazione è una configurazione
   esterna al repository e richiede i permessi proprietario/account.
2. In **Zero Trust → Access → Applications**, crea/configura la protezione
   dell'hostname di anteprima e dei percorsi **/studio/**, **/studio/***
   e **/api/studio/***. Limita la policy **Allow** esclusivamente alla tua
   email. La protezione delle preview dal pannello Pages (Settings → General
   → Enable access policy) copre l'intera preview, non soltanto Studio:
   usala solo se vuoi rendere privata tutta la replica. Consulta la guida
   ufficiale: https://developers.cloudflare.com/pages/configuration/preview-deployments/
3. Recupera il **team domain** (`<team>.cloudflareaccess.com`) e l'**AUD**
   dell'applicazione Access che protegge le richieste a Studio.
4. Su Pages → progetto **zazoomtek-spotnews-preview** → Settings →
   Variables and Secrets → ambiente **Preview**, configura:
   - `CF_ACCESS_TEAM_DOMAIN`: team domain verificato
   - `CF_ACCESS_AUD`: audience tag dell'app Access
   - `STUDIO_ADMIN_EMAIL`: email autorizzata (non pubblica nel codice)
   - `STUDIO_GITHUB_TOKEN`: **segreto cifrato** GitHub fine-grained con
     Contents: Read & write soltanto per
     `zazoomtek-coder/zazoomtek-site`
5. Salva e avvia un deploy del branch di prova. Apri **/studio/**:
   Cloudflare Access presenterà il login sul proprio flusso ufficiale,
   prima di caricare il pannello. Dopo il primo login, il browser conserva
   il cookie sicuro fino alla scadenza prevista dalla policy Access.
6. Quando `/api/studio/session` risponde `authenticated:true` con la
   tua sessione valida, il pulsante **Modifica** appare in ogni articolo
   sullo **stesso dominio di anteprima**. Gli altri visitatori non lo vedono.

Per minimizzare nuove autenticazioni quando la preview viene ricompilata,
usa lo stesso hostname stabile di branch, anziché cambiare dominio hashed
a ogni deploy, se configurato su Cloudflare Pages.

## Verifiche e protezioni
- Senza Access configurato, Studio rimane chiuso: non attiviamo login fittizi.
- Le verifiche server controllano JWT, firma, email, issuer, audience,
  scadenza e origine delle mutazioni.
- Il token GitHub resta **esclusivamente server-side**, mai in browser.
- Le scritture usano soltanto il branch
  `feature/spotnews-clean-rebuild`; `main` non viene toccato.
- Articoli nuovi: `data/studio_posts.json`; modifiche agli importati:
  `data/studio_overrides.json`.
- Studio resta `noindex` ed escluso dalla sitemap.

**Stato:** una build riuscita verifica la presenza di editor e API;
**non** attiva automaticamente Cloudflare Access, le variabili e il token.
