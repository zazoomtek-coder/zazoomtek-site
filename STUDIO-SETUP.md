# ZazoomTek Studio — attivazione autenticazione persistente
Studio usa Cloudflare Access, non salva password o API token nel browser.

1. In Cloudflare Zero Trust proteggi /studio/* e /api/studio/* della preview con una app self-hosted e una policy Allow per la sola email amministratrice. Le altre pagine pubbliche NON devono essere protette.
2. Imposta la durata delle sessioni Global, Application e Policy a un mese, il massimo supportato. Entro quella scadenza la sessione browser (cookie CF_Authorization) resta valida senza reinserire credenziali. Dopo la scadenza sarà necessaria una nuova autenticazione.
3. In Cloudflare Pages, progetto zazoomtek-spotnews-preview, ambiente Preview, configura:
   - CF_ACCESS_TEAM_DOMAIN = dominio team cloudflareaccess.com
   - CF_ACCESS_AUD = Audience tag Cloudflare Access
   - STUDIO_ADMIN_EMAIL = unica email amministratrice consentita
   - STUDIO_GITHUB_TOKEN = segreto cifrato, GitHub fine-grained, permission Contents read/write solo per zazoomtek-coder/zazoomtek-site
4. Pubblica la nuova build di prova. Accedi a /studio/ e autentica una volta il browser. Le pagine articolo mostrano Modifica soltanto quando /api/studio/session verifica firma JWT, identità, email, audience e scadenza.

Il pannello salva nuovi articoli in data/studio_posts.json, e modifiche degli importati in data/studio_overrides.json. Ogni successiva build li unisce ai contenuti reali. Nessuna scrittura a main.
La pagina non è inclusa in sitemap, e viene contrassegnata noindex.
Le API accettano solo richieste same-origin, blocchi approvati e immagini JPEG/PNG/WebP fino a 3.2 MB; i token sono disponibili unicamente al runtime server.
NOTA: senza configurazione Zero Trust + segreti l'editor rimane bloccato correttamente; non è possibile renderlo effettivamente autenticato soltanto con un commit GitHub.
