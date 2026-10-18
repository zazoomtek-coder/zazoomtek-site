/* ZazoomTek Studio - pubblicatore autonomo. Non modifica home o script editoriali. */
(function(){
"use strict";
const REPO="zazoomtek-coder/zazoomtek-site", BRANCH="main", ROOT="https://zazoomtek.it/";
const $=id=>document.getElementById(id);
const enc=s=>String(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const categories={"News Tech":["News Tech","/news.html"],"News Gaming":["News Gaming","/gaming-today.html"],"Recensioni Gaming":["Recensioni","/recensioni-scritte.html"],"Recensioni Hi-Tech":["Recensioni","/recensioni-scritte.html"],"Test":["Test","/test.html"],"Unboxing":["Unboxing","/unboxing.html"],"Guide":["Guide","/guide.html"],"Tech Impact":["Tech Impact","/tech-today.html"],"Gaming Inside":["Gaming Inside","/gaming-today.html"],"Extra":["Extra","/extra.html"]};
let token="",working=false;const attachments=new Map();
document.title="ZazoomTek Studio · Pubblicazione articoli";
const robots=document.createElement("meta");robots.name="robots";robots.content="noindex,nofollow,noarchive";document.head.append(robots);
const style=document.createElement("style");style.textContent=".zt-connect{background:#fff;border:1px solid #d9dfe8;border-radius:11px;padding:16px;margin-bottom:16px;box-shadow:0 8px 28px #16182409}.zt-connect h3{font-size:14px;margin:0 0 7px}.zt-connect p{font-size:12px;color:#616977;line-height:1.6;margin:7px 0}.zt-connect label{display:block;font-weight:750;font-size:12px;margin:11px 0 5px}.zt-connect input{width:100%;padding:11px;border:1px solid #d6dae2;border-radius:7px}.zt-connect .zt-row{display:flex;gap:8px;margin-top:10px;align-items:center;flex-wrap:wrap}.zt-connect .zt-state{font-size:12px;font-weight:650;color:#565e6a}.zt-connect .zt-state.ok{color:#136f41}.zt-connect .zt-state.error{color:#b51e38}.zt-connect .zt-note{font-size:11px;color:#7b8290}.zt-result{display:none;margin-top:12px;padding:12px;border-radius:8px;background:#f1f9f4;border:1px solid #bce0ca;font-size:12px;overflow-wrap:anywhere}.zt-result a{color:#176c3f;font-weight:800}.zt-result.show{display:block}.zt-connect a{color:#a70b2a}.zt-connect button{font-size:12px}";
document.head.append(style);
const panel=document.createElement("section");panel.className="zt-connect";panel.innerHTML='<h3>Collega GitHub per pubblicare</h3><p>La scrittura e le bozze funzionano senza accesso. Per pubblicare serve un token GitHub <b>fine-grained</b> autorizzato soltanto sul repository <b>zazoomtek-coder/zazoomtek-site</b>, con <b>Contents: Read and write</b>.</p><label for="ztToken">Token GitHub (non viene salvato)</label><input id="ztToken" type="password" autocomplete="off" spellcheck="false" placeholder="github_pat_…"><div class="zt-row"><button type="button" class="btn mini" id="ztConnect">Verifica collegamento</button><button type="button" class="btn mini" id="ztDisconnect">Disconnetti</button></div><p class="zt-state" id="ztConnection">Non collegato · nessun articolo può essere pubblicato senza autorizzazione.</p><p class="zt-note">Il token resta soltanto nella memoria della pagina e viene inviato direttamente a api.github.com. Non incollarlo in chat e non usare un token con accesso a tutti i repository.</p><div id="ztPublished" class="zt-result"></div>';
const right=document.querySelector(".right");
if(right)right.insertBefore(panel,right.firstChild);
const local=document.querySelector(".local");if(local)local.textContent="● Studio online · GitHub";
const intro=document.querySelector(".intro");if(intro)intro.innerHTML='<span style="color:#d51232;font-size:19px">✎</span><span><strong>Editor completo:</strong> scrivi come su Patreon e usa <b>+</b> per immagini, video e altri contenuti. <strong>La home e gli script automatici non vengono toccati.</strong> La pubblicazione crea una nuova pagina e la registra nell’archivio dello Studio, senza inserirla automaticamente nelle sezioni del sito.</span>';
const locks=document.querySelectorAll(".locked");locks.forEach(n=>{const t=n.textContent||"";if(/automatic|automatici|SEO|correlati/i.test(t))n.title="Le nuove pagine hanno i propri metadati SEO e un riquadro notizie; non vengono aggiunte automaticamente agli archivi storici."});
const btn=$("publishBtn");if(btn){btn.textContent="Pubblica articolo";btn.onclick=publish;}
const state=(t,error=false)=>{const n=$("ztConnection");n.textContent=t;n.className="zt-state "+(error?"error":token?"ok":"");};

// ZT_STUDIO_ENCRYPTED_VAULT_1. The GitHub PAT is never stored unencrypted.
const VAULT_STORAGE_KEY="zazoomtek.studio.github.vault.v1";
const VAULT_ITERATIONS=600000;
const vaultBox=document.createElement("section");
vaultBox.id="ztVault";
vaultBox.className="zt-vault";
vaultBox.innerHTML='<h3>Accesso persistente protetto</h3><p>Salva il collegamento GitHub su questo computer, cifrato con una password scelta da te. Ai prossimi accessi userai solo questa password, non il codice GitHub.</p><div id="ztVaultSave"><label for="ztVaultPass">Crea una password di sblocco (minimo 12 caratteri)</label><input type="password" id="ztVaultPass" autocomplete="new-password" minlength="12" placeholder="Password di almeno 12 caratteri"><label for="ztVaultRepeat">Ripeti la password</label><input type="password" id="ztVaultRepeat" autocomplete="new-password" minlength="12" placeholder="Ripeti la password"><div class="zt-row"><button type="button" class="btn mini" id="ztVaultSaveBtn">Salva accesso cifrato</button></div></div><div id="ztVaultUnlock" hidden><label for="ztVaultUnlockPass">Password di sblocco</label><input type="password" id="ztVaultUnlockPass" autocomplete="current-password" placeholder="La password scelta in precedenza"><div class="zt-row"><button type="button" class="btn mini" id="ztVaultUnlockBtn">Sblocca GitHub</button></div></div><div id="ztVaultStatus" class="zt-vault-message" role="status"></div><div class="zt-row"><button type="button" id="ztVaultForget" class="btn mini" hidden>Elimina accesso salvato</button></div><p class="zt-vault-note">Il token è cifrato AES-GCM con una chiave derivata dalla password (PBKDF2). Nessun token in chiaro né password viene salvato. Il salvataggio è valido solo su questo browser; in modalità privata o cancellando i dati del sito potrebbe scomparire. La password dello Studio non ha scadenza. Per evitare la scadenza del token, crea su GitHub un fine-grained token con No expiration, limitato a questo repository. GitHub può comunque revocarlo per sicurezza o dopo un anno di inattività.</p>';
panel.insertBefore(vaultBox,panel.querySelector("#ztPublished"));
style.textContent+='.zt-vault{border-top:1px solid #e5e8ee;margin-top:15px;padding-top:12px}.zt-vault h3{margin-bottom:6px}.zt-vault p{font-size:12px}.zt-vault label{margin-top:9px}.zt-vault input{background:#fff}.zt-vault [hidden]{display:none!important}.zt-vault-message{padding-top:6px;font-size:12px;line-height:1.5;color:#136f41}.zt-vault-message.error{color:#b51e38}.zt-vault-note{color:#757e8e!important;font-size:11px!important;line-height:1.55!important}';
let vaultBusy=false;
const vaultEls={save:$("ztVaultSave"),unlock:$("ztVaultUnlock"),forget:$("ztVaultForget"),message:$("ztVaultStatus")};
function vaultMessage(s,error=false){vaultEls.message.textContent=s;vaultEls.message.className="zt-vault-message"+(error?" error":"");}
function getSavedVault(){try{const raw=localStorage.getItem(VAULT_STORAGE_KEY);return raw?JSON.parse(raw):null;}catch{return null;}}
function renderVault(){
  const saved=!!getSavedVault();
  vaultEls.save.hidden=!token;
  vaultEls.unlock.hidden=!saved||!!token;
  vaultEls.forget.hidden=!saved;
  if(saved&&token)vaultMessage("Accesso cifrato salvato sul dispositivo. Pronto per pubblicare.");
  else if(saved)vaultMessage("Accesso salvato: inserisci la password per sbloccare GitHub.");
  else if(token)vaultMessage("Collegato: crea adesso una password per evitare di incollare il token nei prossimi accessi.");
  else vaultMessage("Collega GitHub una sola volta, poi proteggi l'accesso con una password.");
}
function toBase64(bytes){let out="";for(let i=0;i<bytes.length;i+=8192)out+=String.fromCharCode(...bytes.subarray(i,i+8192));return btoa(out);}
function fromBase64(value){if(typeof value!=="string"||value.length>12000||!/^[A-Za-z0-9+/]*={0,2}$/.test(value))throw Error("Archivio salvato non valido");const binary=atob(value);return Uint8Array.from(binary,c=>c.charCodeAt(0));}
function vaultAAD(){return new TextEncoder().encode("ZazoomTek Studio encrypted GitHub token v1|"+location.origin);}
async function keyFromPassword(password,salt){
  const secret=await crypto.subtle.importKey("raw",new TextEncoder().encode(password),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:VAULT_ITERATIONS,hash:"SHA-256"},secret,{name:"AES-GCM",length:256},false,["encrypt","decrypt"]);
}
async function saveCredential(){
  if(vaultBusy)return;
  if(!token){vaultMessage("Prima verifica il collegamento GitHub.",true);return;}
  if(!globalThis.crypto?.subtle||!globalThis.isSecureContext){vaultMessage("Per la cifratura serve HTTPS e un browser aggiornato.",true);return;}
  const pass=$("ztVaultPass").value,repeat=$("ztVaultRepeat").value;
  if(pass.length<12){vaultMessage("La password deve avere almeno 12 caratteri.",true);return;}
  if(pass!==repeat){vaultMessage("Le due password non coincidono.",true);return;}
  vaultBusy=true;$("ztVaultSaveBtn").disabled=true;
  try{
    const salt=crypto.getRandomValues(new Uint8Array(16));
    const iv=crypto.getRandomValues(new Uint8Array(12));
    const key=await keyFromPassword(pass,salt);
    const encrypted=await crypto.subtle.encrypt({name:"AES-GCM",iv,additionalData:vaultAAD()},key,new TextEncoder().encode(token));
    const record={v:1,iterations:VAULT_ITERATIONS,salt:toBase64(salt),iv:toBase64(iv),ciphertext:toBase64(new Uint8Array(encrypted))};
    localStorage.setItem(VAULT_STORAGE_KEY,JSON.stringify(record));
    $("ztVaultPass").value="";$("ztVaultRepeat").value="";
    renderVault();state("Collegato a "+REPO+" · accesso protetto salvato.");
  }catch(e){vaultMessage("Impossibile salvare l'accesso protetto su questo browser. Controlla se sono consentiti i dati dei siti.",true);}
  finally{vaultBusy=false;$("ztVaultSaveBtn").disabled=false;}
}
async function unlockCredential(){
  if(vaultBusy)return;
  if(!globalThis.crypto?.subtle||!globalThis.isSecureContext){vaultMessage("Per sbloccare il token occorre HTTPS e un browser aggiornato.",true);return;}
  const pass=$("ztVaultUnlockPass").value;
  const saved=getSavedVault();
  if(!saved||!pass){vaultMessage("Inserisci la password di sblocco.",true);return;}
  vaultBusy=true;$("ztVaultUnlockBtn").disabled=true;
  try{
    if(saved.v!==1||saved.iterations!==VAULT_ITERATIONS)throw Error("Formato non supportato");
    const salt=fromBase64(saved.salt),iv=fromBase64(saved.iv),ciphertext=fromBase64(saved.ciphertext);
    if(salt.length!==16||iv.length!==12||ciphertext.length<16)throw Error("Formato non valido");
    const key=await keyFromPassword(pass,salt);
    const decrypted=await crypto.subtle.decrypt({name:"AES-GCM",iv,additionalData:vaultAAD()},key,ciphertext);
    const candidate=new TextDecoder("utf-8",{fatal:true}).decode(decrypted);
    if(!/^(github_pat_|ghp_)[A-Za-z0-9_]+$/.test(candidate))throw Error("Token non valido");
    token=candidate;
    $("ztVaultUnlockPass").value="";
    // A successful decryption is insufficient: verify the token still works.
    try{
      const verified=await req("GET","firebase.json?ref="+BRANCH);
      if(!verified)throw Error("Repository non accessibile");
      state("Collegato a "+REPO+" · accesso protetto sbloccato.");
      renderVault();
    }catch(e){
      token="";
      renderVault();
      vaultMessage("La password è corretta, ma GitHub ha rifiutato l'accesso. Se il token è scaduto, creane uno nuovo e salvalo qui.",true);
      state("GitHub non collegato: token salvato scaduto o non autorizzato.",true);
    }
  }catch(e){vaultMessage("Password errata oppure dati cifrati non leggibili. Riprova o elimina l'accesso salvato.",true);}
  finally{vaultBusy=false;$("ztVaultUnlockBtn").disabled=false;}
}
$("ztVaultSaveBtn").addEventListener("click",saveCredential);
$("ztVaultUnlockBtn").addEventListener("click",unlockCredential);
$("ztVaultUnlockPass").addEventListener("keydown",e=>{if(e.key==="Enter"){e.preventDefault();unlockCredential();}});
$("ztVaultForget").addEventListener("click",()=>{
  if(!confirm("Eliminare il codice GitHub cifrato da questo browser? Dovrai collegarti di nuovo con il token."))return;
  try{localStorage.removeItem(VAULT_STORAGE_KEY);}catch(e){vaultMessage("Non riesco ad eliminare i dati dal browser.",true);return;}
  $("ztVaultUnlockPass").value="";
  $("ztVaultPass").value="";$("ztVaultRepeat").value="";
  renderVault();
  vaultMessage("Accesso salvato eliminato. Il collegamento già attivo rimane valido fino a quando chiudi la pagina.");
});
renderVault();
const endpoint=p=>{const parts=p.split("?");return "https://api.github.com/repos/"+REPO+"/contents/"+parts[0].split("/").map(encodeURIComponent).join("/")+(parts[1]?"?"+parts.slice(1).join("?"):"");};
async function req(method,p,body){
const res=await fetch(endpoint(p),{method,headers:{"Accept":"application/vnd.github+json","Authorization":"Bearer "+token,"X-GitHub-Api-Version":"2022-11-28",...(body?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined,cache:"no-store"});
if(res.status===404&&method==="GET")return null;
const data=await res.json().catch(()=>({}));
if(!res.ok)throw Error((data.message||("GitHub HTTP "+res.status))+(res.status===401?" — token non valido":res.status===403?" — verifica permessi Contents: Read and write":""));
return data;
}
function b64UTF8(s){const bytes=new TextEncoder().encode(s);let a="";for(let i=0;i<bytes.length;i+=16384)a+=String.fromCharCode(...bytes.subarray(i,i+16384));return btoa(a);}
async function writeNew(path,base64,message){
const exists=await req("GET",path+"?ref="+BRANCH);
if(exists)throw Error("File già presente: "+path+". Pubblicazione fermata per non sovrascrivere nulla.");
return req("PUT",path,{message,content:base64,branch:BRANCH});
}
async function upsertManifest(article){
const path="studio/articoli.json";
for(let tries=0;tries<3;tries++){
const old=await req("GET",path+"?ref="+BRANCH);
let items=[];
if(old&&old.content){try{items=JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(old.content.replace(/\s/g,"")),c=>c.charCodeAt(0))))}catch{throw Error("Archivio dello Studio non leggibile: non sovrascrivo i dati.");}}
if(!Array.isArray(items))throw Error("Formato archivio non valido.");
if(items.some(x=>x.url===article.url))return;
items.unshift(article);
try{return await req("PUT",path,{message:"Studio: registra nuovo articolo "+article.slug,content:b64UTF8(JSON.stringify(items,null,2)+"\n"),branch:BRANCH,...(old?{sha:old.sha}:{})});}
catch(e){if(tries===2||!/sha|conflict|409|422/i.test(e.message))throw e;}
}
}
const normalize=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,65).replace(/-+$/,"");
const mimeExt=(type)=>type==="application/pdf"?".pdf":type==="text/plain"?".txt":type==="application/zip"?".zip":type==="application/vnd.openxmlformats-officedocument.wordprocessingml.document"?".docx":null;
const basename=s=>normalize(String(s).replace(/\.[^.]+$/,"")).slice(0,45)||"allegato";
function photoPayload(src){const m=/^data:image\/(jpeg|jpg|png|webp);base64,([A-Za-z0-9+/=]+)$/i.exec(src||"");return m?{ext:m[1].toLowerCase()==="jpg"?"jpeg":m[1].toLowerCase(),b64:m[2]}:null;}
const ytID=s=>{try{const u=new URL(s);if(!["youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be","youtube-nocookie.com"].includes(u.hostname))return"";const id=u.hostname.includes("youtu.be")?u.pathname.slice(1):u.pathname==="/watch"?u.searchParams.get("v"):(u.pathname.match(/^\/(?:embed|live|shorts)\/([\w-]+)/)||[])[1];return/^[\w-]{11}$/.test(id||"")?id:"";}catch{return"";}};
function cleanArticle(coverSrc,slug){
const draft=window.ZTStudio?.safeDoc?.();
if(!draft)throw Error("Editor non disponibile: aggiorna la pagina.");
const shell=document.createElement("div");shell.innerHTML=draft;
shell.querySelectorAll(".media-remove,iframe,script,style").forEach(n=>n.remove());
const upload=[],imgCover=photoPayload(coverSrc);
if(!imgCover)throw Error("Carica una cover valida prima di pubblicare.");
const coverPath="assets/studio/"+slug+"-cover."+imgCover.ext;
upload.push({path:coverPath,b64:imgCover.b64});
let count=0;
shell.querySelectorAll('figure[data-zt-kind="photo"] img').forEach(img=>{
const p=photoPayload(img.getAttribute("src"));
if(!p)throw Error("Una foto non è stata salvata correttamente. Reinseriscila.");
const path="assets/studio/"+slug+"-foto-"+(++count)+"."+p.ext;
upload.push({path,b64:p.b64});img.src="/"+path;img.loading="lazy";img.alt=img.alt||"Fotografia articolo ZazoomTek";
});
shell.querySelectorAll('figure[data-zt-kind="video"]').forEach(fig=>{
const id=ytID(fig.getAttribute("data-video-url"));
if(!id)throw Error("Un video YouTube non è valido.");
fig.removeAttribute("contenteditable");
fig.className="zt-video";
fig.innerHTML='<div class="zt-player" data-yt="'+enc(id)+'"><img loading="lazy" alt="Anteprima video" src="https://i.ytimg.com/vi/'+enc(id)+'/hqdefault.jpg"><button type="button" aria-label="Riproduci video YouTube">▶</button></div><p><a href="https://www.youtube.com/watch?v='+enc(id)+'" target="_blank" rel="noopener noreferrer">Apri il video su YouTube ↗</a></p>';
});
const allFiles=[...$("editor").querySelectorAll('[data-zt-kind="file"]')];
const copyFiles=[...shell.querySelectorAll('[data-zt-kind="file"]')];
copyFiles.forEach((el,i)=>{
const original=allFiles[i],file=attachments.get(original?.dataset.ztAttachment);
if(!file)throw Error("Ricarica l’allegato «"+(original?.textContent||"file").trim()+"» prima di pubblicare: il file non è più disponibile in questa sessione.");
const ext=mimeExt(file.mime);if(!ext)throw Error("Tipo allegato non supportato: "+file.name);
const path="assets/studio/"+slug+"-allegato-"+(i+1)+"-"+basename(file.name)+ext;
upload.push({path,b64:file.b64});
el.className="zt-attachment";el.removeAttribute("contenteditable");el.innerHTML='<a href="/'+enc(path)+'" download>↓ '+enc(file.name)+'</a>';
});
shell.querySelectorAll("[contenteditable],[data-zt-kind],[data-video-url],[data-zt-attachment]").forEach(el=>{["contenteditable","data-zt-kind","data-video-url","data-zt-attachment"].forEach(k=>el.removeAttribute(k));});
return {content:shell.innerHTML,upload,cover:"/"+coverPath};
}
function articleHTML(title,category,cover,body,description,date,url){
const t=enc(title),c=enc(category),img=enc(ROOT+cover.slice(1)),canon=enc(ROOT+url),d=enc(description),when=enc(date),link=categories[category]?.[1]||"/news.html";
const ld=JSON.stringify({"@context":"https://schema.org","@type":"NewsArticle",headline:title,description:description,image:[ROOT+cover.slice(1)],datePublished:date,dateModified:date,author:{"@type":"Organization",name:"ZazoomTek"},publisher:{"@type":"Organization",name:"ZazoomTek",logo:{"@type":"ImageObject",url:ROOT+"ChatGPT.png"}},mainEntityOfPage:ROOT+url}).replace(/</g,"\\u003c");
return '<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+t+' | ZazoomTek</title><meta name="description" content="'+d+'"><meta name="robots" content="index,follow,max-image-preview:large"><meta name="author" content="ZazoomTek"><link rel="canonical" href="'+canon+'"><meta property="og:type" content="article"><meta property="og:site_name" content="ZazoomTek"><meta property="og:title" content="'+t+'"><meta property="og:description" content="'+d+'"><meta property="og:image" content="'+img+'"><meta property="og:url" content="'+canon+'"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="'+img+'"><meta property="article:published_time" content="'+when+'"><script type="application/ld+json">'+ld+'</script><link rel="icon" href="/ChatGPT.png"><style>'+ARTICLE_CSS+'</style></head><body><header class="zt-head"><div class="wrap bar"><a class="logo" href="/"><img src="/ChatGPT.png" alt=""><span><b>ZAZOOM<span style="color:#e3344c">TEK</span></b><small>TECH GAMING COMMUNITY</small></span></a><nav><a href="/">Home</a><a href="/news.html">News</a><a href="/recensioni-scritte.html">Recensioni</a><a href="/guide.html">Guide</a><a href="/tech-today.html">Tech Impact</a><a href="/gaming-today.html">Gaming Inside</a><a href="/extra.html">Extra</a><a href="https://www.youtube.com/@ZazoomTek/posts">Community</a><a href="https://www.youtube.com/@ZazoomTek/videos">Video</a></nav></div></header><main class="wrap layout"><article class="story"><div class="crumb"><a href="/">Home</a> / <a href="'+enc(link)+'">'+c+'</a></div><div class="tag">'+c+'</div><h1>'+t+'</h1><div class="meta">ZazoomTek · <time datetime="'+when+'">'+enc(new Date(date).toLocaleDateString("it-IT",{day:"numeric",month:"long",year:"numeric"}))+'</time></div><img class="cover" src="'+enc(cover)+'" alt="'+t+'" fetchpriority="high"><div class="body">'+body+'</div><div class="end">© ZazoomTek.it · <a href="'+enc(link)+'">Torna alla sezione '+c+'</a></div></article><aside class="related"><h2>Ultimi articoli</h2><div id="ztRecommendations"><p>Altre notizie e recensioni ZazoomTek.</p></div><div class="sideblock"><b>Scopri ZazoomTek</b><p><a href="/news.html">News</a> · <a href="/guide.html">Guide</a> · <a href="/recensioni-scritte.html">Recensioni</a></p></div></aside></main><footer>© 2026 ZazoomTek · <a href="/">Home</a> · <a href="/privacy.html">Privacy</a> · <a href="/contatti.html">Contatti</a></footer><script>'+ARTICLE_SCRIPT+'</script></body></html>';
}
const ARTICLE_CSS=':root{--red:#d51232}*{box-sizing:border-box}body{margin:0;background:#ececec;color:#292d34;font:16px/1.7 Arial,Helvetica,sans-serif}a{color:inherit;text-decoration:none}.wrap{width:min(1450px,calc(100% - 32px));margin:auto}.zt-head{background:#191919;border-top:3px solid var(--red);color:#fff}.bar{display:flex;align-items:center;gap:20px;min-height:82px;flex-wrap:wrap}.logo{display:flex;align-items:center;gap:8px;flex:none}.logo img{width:48px;height:48px;object-fit:cover;border-radius:5px}.logo b{font-size:24px;letter-spacing:-1px}.logo small{display:block;color:#ddd;font-size:9px;letter-spacing:2px;line-height:1.1}.bar nav{display:flex;flex-wrap:wrap;margin-left:auto}.bar nav a{font-size:11px;font-weight:800;padding:13px 9px;text-transform:uppercase}.bar nav a:hover{background:var(--red)}.layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:24px;padding:25px 0 55px;align-items:start}.story,.related{background:white;border:1px solid #e2e2e2;border-radius:3px}.story{padding:28px 34px 45px;min-width:0}.crumb{font-size:12px;color:#798089;margin-bottom:15px}.crumb a:hover{color:var(--red)}.tag{display:inline-block;background:var(--red);color:white;font-weight:800;padding:4px 10px;font-size:11px;text-transform:uppercase}.story h1{font-size:clamp(28px,3vw,43px);line-height:1.15;margin:17px 0;letter-spacing:-.8px}.meta{color:#7a7a7a;font-size:12px;margin-bottom:20px}.cover{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;border-radius:3px;margin:0 0 25px}.body{font-size:17px;line-height:1.73;overflow-wrap:anywhere}.body p{margin:0 0 17px}.body h2,.body h3{font-size:23px;line-height:1.3;margin:26px 0 10px;color:#151719}.body img{max-width:100%;height:auto}.body figure{margin:22px auto;text-align:center}.body figure img{display:block;margin:auto;border-radius:4px}.body figcaption{font-size:12px;color:#7b8086}.body blockquote{margin:22px 0;border-left:4px solid var(--red);background:#f5f5f5;padding:14px 20px}.body hr{border:0;border-top:1px solid #dadada;margin:25px 0}.body a{color:#ae1431;text-decoration:underline}.body .inline-link{background:#f4f6f7;border-left:4px solid var(--red);padding:15px}.body .paypal-button,.body .custom-button{display:inline-flex;padding:10px 17px;background:#083d7a;color:#fff!important;text-decoration:none;border-radius:6px;font-weight:800}.body .custom-button{background:var(--red)}.body .zt-video{max-width:800px}.zt-player{position:relative;aspect-ratio:16/9;display:grid;place-items:center;background:#111;overflow:hidden}.zt-player img{position:absolute;width:100%;height:100%;object-fit:cover;filter:brightness(.7)}.zt-player button{position:relative;background:#ed1c24;color:white;border:0;border-radius:12px;padding:13px 25px;font-size:24px;cursor:pointer}.zt-player iframe{position:absolute;inset:0;width:100%;height:100%;border:0}.body .zt-attachment{border:1px solid #ddd;background:#f6f6f6;padding:14px}.related{padding:0 0 12px}.related h2{background:#202020;color:white;font-size:14px;margin:0;padding:12px 16px;text-transform:uppercase}.related .item{display:grid;grid-template-columns:96px 1fr;gap:12px;padding:12px;border-bottom:1px solid #eee;align-items:start}.related .item img{width:96px;aspect-ratio:16/9;object-fit:cover}.related .item span{font-size:13px;font-weight:750;line-height:1.35}.related .item:hover span{color:var(--red)}.related p{padding:0 14px}.sideblock{padding:12px;font-size:13px}.sideblock a{color:var(--red)}.end{padding-top:23px;margin-top:34px;border-top:1px solid #ddd;font-size:13px}.end a{color:var(--red)}footer{background:#1a1a1a;padding:25px;text-align:center;color:#ddd;font-size:12px}footer a{color:#fff}@media(max-width:980px){.layout{grid-template-columns:1fr}.related{max-width:none}.bar nav{margin-left:0}}@media(max-width:570px){.story{padding:18px}.bar{padding:12px 0}.bar nav a{padding:8px}.body{font-size:16px}.related .item{grid-template-columns:90px 1fr}}';
const ARTICLE_SCRIPT='(function(){document.querySelectorAll(".zt-player[data-yt]").forEach(function(p){var b=p.querySelector("button");if(!b)return;b.addEventListener("click",function(){var id=p.getAttribute("data-yt");if(!/^[\\w-]{11}$/.test(id))return;var f=document.createElement("iframe");f.src="https://www.youtube-nocookie.com/embed/"+id+"?autoplay=1&rel=0";f.title="Video YouTube";f.allow="autoplay; encrypted-media; picture-in-picture";f.allowFullscreen=true;p.replaceChildren(f);});});fetch("/zt-sidebar-feed.json",{cache:"no-store"}).then(function(r){if(!r.ok)throw Error();return r.json()}).then(function(d){var root=document.getElementById("ztRecommendations"),items=(d.news||[]).filter(function(x){return x&&x.url&&x.title&&x.image&&x.url!==location.pathname}).slice(0,12);if(!root||!items.length)return;root.replaceChildren();items.forEach(function(x){var a=document.createElement("a"),im=document.createElement("img"),sp=document.createElement("span");a.className="item";a.href=x.url;im.src=x.image;im.loading="lazy";im.alt="";sp.textContent=x.title;a.append(im,sp);root.append(a);});}).catch(function(){});})();';
async function publish(){
if(working)return;
const title=$("headline").value.trim(),category=$("category").value,words=($("editor").innerText.trim().match(/\S+/g)||[]).length;
if(!token){state("Collega GitHub prima di pubblicare.",true);panel.scrollIntoView({behavior:"smooth",block:"center"});return;}
if(title.length<15||words<60||!$("coverPreview").getAttribute("src")){state("Controlli mancanti: titolo di almeno 15 caratteri, 60 parole e cover 16:9.",true);return;}
if(!categories[category]){state("Categoria non riconosciuta.",true);return;}
if(!confirm("Pubblicare un nuovo articolo sul repository principale? La home e gli archivi esistenti non verranno modificati."))return;
working=true;btn.disabled=true;const finish=(s,bad=false)=>state(s,bad);
try{
const slug="studio-"+normalize(category).slice(0,22)+"-"+normalize(title);
if(slug.length<25)throw Error("Titolo non adatto a creare un indirizzo leggibile.");
const filename=slug+".html";
finish("Controllo duplicati su GitHub…");
if(await req("GET",filename+"?ref="+BRANCH))throw Error("Esiste già un articolo con questo titolo. Nessun file sarà sovrascritto.");
const exported=cleanArticle($("coverPreview").getAttribute("src"),slug);
if(exported.upload.some(x=>x.b64.length>9000000))throw Error("Un file supera il limite consigliato di caricamento. Riduci le dimensioni.");
const description=($("editor").innerText||"").replace(/\s+/g," ").trim().slice(0,155);
const date=new Date().toISOString();
const html=articleHTML(title,category,exported.cover,exported.content,description,date,filename);
window.ZTStudio?.saveDraft?.(true);
for(let i=0;i<exported.upload.length;i++){
finish("Caricamento immagini e allegati "+(i+1)+"/"+exported.upload.length+"…");
const file=exported.upload[i];await writeNew(file.path,file.b64,"Studio: aggiunge risorsa per "+slug);
}
finish("Creazione pagina articolo su GitHub…");
await writeNew(filename,b64UTF8(html),"Studio: pubblica articolo "+title.slice(0,70));
const url=ROOT+filename;
let manifestOK=true;
try{finish("Articolo creato. Registro nell’archivio dello Studio…");await upsertManifest({slug,title,category,url:"/"+filename,image:exported.cover,published_at:date});}
catch(e){manifestOK=false;finish("Articolo pubblicato nel repository, ma l’archivio non è stato aggiornato: "+e.message,true);}
const result=$("ztPublished");result.classList.add("show");result.innerHTML='<b>Articolo inviato a GitHub.</b><br><a href="'+enc(url)+'" target="_blank" rel="noopener noreferrer">'+enc(url)+'</a><br>Il sito mostrerà la pagina solo dopo il prossimo rilascio. '+(manifestOK?"Registrato nell’archivio dello Studio.":"L’archivio richiede una verifica.");
if(manifestOK)finish("Pubblicazione GitHub completata. Attendi il deploy per vedere la pagina sul sito.");
window.ZTStudio?.saveDraft?.(true);
}catch(e){finish("Pubblicazione non completata: "+e.message,true);}
finally{working=false;btn.disabled=false;}
}
$("ztConnect").addEventListener("click",async()=>{
const v=$("ztToken").value.trim();if(!/^((github_pat_|ghp_)[A-Za-z0-9_]+)$/.test(v)){state("Inserisci un token GitHub valido, fine-grained e limitato al repository.",true);return;}
token=v;$("ztToken").value="";
try{state("Verifica accesso al repository…");const x=await req("GET","firebase.json?ref="+BRANCH);if(!x)throw Error("Repository non accessibile.");state("Collegato a "+REPO+" · pronto per pubblicare.");renderVault();}catch(e){token="";state("Collegamento non riuscito: "+e.message,true);renderVault();}
});
$("ztDisconnect").addEventListener("click",()=>{token="";$("ztToken").value="";state("Sessione bloccata. Il token in memoria è stato cancellato.");renderVault();});
const fileInput=$("attachFile"),old=fileInput.onchange;
fileInput.onchange=e=>{
const file=e.target.files&&e.target.files[0];if(!file)return;
const ext=mimeExt(file.type);if(!ext||file.size>4*1024*1024){e.target.value="";state("Allegato non valido. PDF, TXT, ZIP o DOCX fino a 4 MB.",true);return;}
const id="f"+Date.now().toString(36)+Math.random().toString(36).slice(2,8);
if(old)old.call(fileInput,e);
const els=[...$("editor").querySelectorAll('[data-zt-kind="file"]')],el=els[els.length-1];if(el)el.dataset.ztAttachment=id;
const reader=new FileReader();reader.onload=()=>{const b64=String(reader.result||"").split(",")[1];if(b64){attachments.set(id,{name:file.name,mime:file.type,b64});state("Allegato «"+file.name+"» pronto per il caricamento.");}};
reader.onerror=()=>state("Errore di lettura allegato, reinseriscilo.",true);reader.readAsDataURL(file);
};
})();
