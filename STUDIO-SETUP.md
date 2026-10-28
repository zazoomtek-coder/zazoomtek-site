# ZazoomTek Studio — sistema nuovo, accesso una sola volta

Studio è stato ricreato da zero esclusivamente per il branch
`feature/spotnews-clean-rebuild`, senza Cloudflare Zero Trust.

## Una sola configurazione prima del primo login

Cloudflare Pages → progetto `zazoomtek-spotnews-preview` → Settings
→ Variables and Secrets → **Preview**:

- **STUDIO_SESSION_SECRET** = stringa casuale generata in modo sicuro,
  lunga almeno 32 caratteri, salvata come **secret** (non variabile pubblica).
  Deve rimanere stabile: cambiarla invalida i cookie già emessi.
  Non copiarla nel codice, GitHub, messaggi o JavaScript.

Non servono app Access, abbonamenti, account nuovi, login Cloudflare
Zero Trust, CF_ACCESS_AUD o segreti GitHub permanenti nel server.

## Primo accesso e riconoscimento automatico

1. Apri Studio sul dominio **stabile** della preview SpotNews (non un
   hostname con hash diverso per ogni deploy). Il cookie `__Host-zzt-studio`
   è legato al singolo host per sicurezza.
2. Solo la prima volta, inserisci un **GitHub Personal Access Token**
   dell'account proprietario `zazoomtek-coder`, abilitato esclusivamente
   al repository `zazoomtek-coder/zazoomtek-site` con Contents: Read & write.
3. L'API server verifica GitHub account e permessi. Il token viene
   cifrato (AES-256-GCM) dal server e memorizzato solo nel cookie
   **Secure, HttpOnly, SameSite=Strict**, non in `localStorage`.
4. Ogni volta che si apre Studio o un articolo, la chiamata di verifica
   rinnova **automaticamente** il cookie persistente. Non esiste
   alcuna scadenza periodica fissa in Studio.
5. Se apri un articolo nel medesimo browser e sul medesimo dominio,
   `Modifica` appare solo se il server verifica il cookie. Cliccandolo
   si apre direttamente Studio sull'articolo selezionato.
6. Nuovi contenuti e modifiche agli importati scrivono **soltanto**
   sul branch SpotNews: `data/studio_posts.json` e
   `data/studio_overrides.json`. Ogni salvataggio produce una nuova
   build di preview. Il branch `main` e zazoomtek.it restano invariati.

## Limite tecnico reale

I browser (es. Chrome) limitano la persistenza di un cookie a 400 giorni
dalla sua ultima emissione. Studio **rinnova a ogni visita** il cookie:
per un uso regolare non ci sono scadenze periodiche. Non è però
possibile garantire accesso letteralmente eterno dopo cancellazione
cookie, cambio browser/dispositivo, lungo periodo di inattività,
revoca o scadenza del token GitHub, perdita della chiave del server
o cambiamento di dominio. In questi casi serve ripetere il primo accesso.

## Sicurezza e test

- Username GitHub del proprietario verificato via API, permessi
  di scrittura sul repository controllati.
- Cookie crittografato e rinnovato solo dal server (mai salvato in
  chiaro nel browser o in JavaScript).
- Protezione CSRF same-origin e Content-Type JSON.
- Upload immagine JPEG/PNG/WebP con limite 3,2 MB e validazione signature.
- Nessun endpoint consente scritture a `main` o path arbitrari.
- Sito di prova `noindex`, Studio assente dalla sitemap.
- La build verifica editor, protezioni, routing e formattazione.
- Il login e il salvataggio reali possono essere verificati solo dopo
  l'inserimento del secret nel pannello Pages e un primo token valido.

Documentazione sul limite 400 giorni:
https://developer.chrome.com/blog/cookie-max-age-expires/
