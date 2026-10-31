/**
 * ZazoomTek Studio — new, independent GitHub-authenticated session service.
 *
 * First access: owner enters a fine-grained GitHub PAT ONCE, over HTTPS.
 * The server verifies GitHub identity and repository write permission, then
 * seals the PAT using AES-256-GCM and sets an HttpOnly Secure SameSite=Strict
 * rolling first-party cookie renewed at each visit: no periodic login deadline.
 * Never localStorage; never a PAT
 * in public Javascript, logs, markup, URLs or repository.
 *
 * Only secret required in Cloudflare Pages Preview settings:
 * STUDIO_SESSION_SECRET (cryptographically random 32+ characters).
 *
 * All GitHub mutations target ONLY editorial-queue, NEVER main.
 * Without the secret, the login fails closed with an actionable status.
 */
const REPO="zazoomtek-coder/zazoomtek-site";
const OWNER="zazoomtek-coder";
const BRANCH="editorial-queue";
const COOKIE="__Host-zzt-studio";
const AGE=400*24*60*60; // Browser cookie inactivity bound, refreshed on each visit.
const CATEGORIES=new Set(["news-tech","news-gaming","recensioni-tech","recensioni-gaming","guide","speciali","extra"]);
const BLOCKS=new Set(["paragraph","heading","image","video","button","quote","audio","attachment","poll","divider"]);
const jsonHeaders={"Content-Type":"application/json;charset=utf-8","Cache-Control":"no-store, private","X-Content-Type-Options":"nosniff"};
function respond(data,status=200,extra={}){
 return new Response(JSON.stringify(data),{status,headers:{...jsonHeaders,...extra}});
}
const clean=v=>typeof v==="string"?v.trim():"";
const toBytes=v=>new TextEncoder().encode(v);
function fromBase64(s){
 const value=String(s).replace(/-/g,"+").replace(/_/g,"/");
 return Uint8Array.from(atob(value),c=>c.charCodeAt(0));
}
function toBase64(bytes){
 let text="";
 for(let i=0;i<bytes.length;i+=8192)
  text+=String.fromCharCode(...bytes.slice(i,i+8192));
 return btoa(text).replace(/\+/g,"-").replace(/\//g,"_").replace(/=+$/,"");
}
// GitHub Contents API requires standard padded Base64, not URL-safe Base64.
function encodeUtf8(s){
 const bytes=toBytes(s);
 let binary="";
 for(let i=0;i<bytes.length;i+=8192)
  binary+=String.fromCharCode(...bytes.slice(i,i+8192));
 return btoa(binary);
}
function assertSetup(env){
 const secret=clean(env.STUDIO_SESSION_SECRET);
 if(secret.length<32)throw new Error("SETUP_REQUIRED");
 return secret;
}
async function keyFor(env){
 const bytes=await crypto.subtle.digest("SHA-256",toBytes(assertSetup(env)));
 return crypto.subtle.importKey("raw",bytes,"AES-GCM",false,["encrypt","decrypt"]);
}
function cookieValue(request,name=COOKIE){
 const s=request.headers.get("Cookie")||"";
 for(const pair of s.split(";")){
  const i=pair.indexOf("=");
  if(i>=0&&pair.slice(0,i).trim()===name)return pair.slice(i+1).trim();
 }
 return "";
}
async function seal(payload,env){
 const iv=crypto.getRandomValues(new Uint8Array(12));
 const cipher=await crypto.subtle.encrypt(
  {name:"AES-GCM",iv},await keyFor(env),toBytes(JSON.stringify(payload)));
 return toBase64(iv)+"."+toBase64(new Uint8Array(cipher));
}
async function openSession(request,env){
 const raw=cookieValue(request);
 if(!raw||raw.length>12000)return null;
 const parts=raw.split(".");
 if(parts.length!==2)return null;
 try{
  const iv=fromBase64(parts[0]);
  if(iv.byteLength!==12)return null;
  const data=await crypto.subtle.decrypt({name:"AES-GCM",iv},await keyFor(env),fromBase64(parts[1]));
  const v=JSON.parse(new TextDecoder().decode(data));
  const now=Math.floor(Date.now()/1000);
  if(v.v!==1||v.owner!==OWNER||v.branch!==BRANCH||
     !Number.isSafeInteger(v.iat)||!Number.isSafeInteger(v.exp)||
     v.exp<=now||v.iat>now+60||v.exp-v.iat>AGE||!/^gh[pousr]_|^github_pat_/.test(v.token||""))
   return null;
  if(v.login!==OWNER)return null;
  return v;
 }catch(_){return null;}
}
function setCookie(value,maxAge){
 return COOKIE+"="+value+"; Path=/; Max-Age="+maxAge+"; HttpOnly; Secure; SameSite=Strict";
}
const clearCookie=()=>setCookie("",0);
async function githubRequest(token,path,options={}){
 const pathUrl="https://api.github.com"+path;
 const res=await fetch(pathUrl,{
  method:options.method||"GET",
  headers:{"Accept":"application/vnd.github+json",
   "Authorization":"Bearer "+token,
   "X-GitHub-Api-Version":"2022-11-28",
   "User-Agent":"ZazoomTek-Studio-Preview","Content-Type":"application/json"},
  body:options.body?JSON.stringify(options.body):undefined
 });
 if(res.status===204)return {};
 const data=await res.json().catch(()=>({}));
 if(!res.ok){
  if(res.status===409||(res.status===422&&/sha|does not match|conflict/i.test(String(data.message||"")))){
   const err=new Error("Conflitto di versione GitHub (HTTP "+res.status+"): "+clean(data.message).slice(0,180));
   err.isShaConflict=true;throw err;
  }
  if(res.status===422)throw new Error("GitHub ha rifiutato il salvataggio (422): "+clean(data.message).slice(0,220));
  if(res.status===401||res.status===403)throw new Error("Token GitHub scaduto, revocato o senza autorizzazioni.");
  throw new Error("GitHub: "+clean(data.message).slice(0,160));
 }
 return data;
}
async function authenticate(token){
 // Only an actual owner account token with write rights can log in.
 if(!/^(github_pat_|gh[pousr]_)/.test(token)||token.length<20||token.length>300)
  throw new Error("Inserisci un token personale GitHub valido.");
 const user=await githubRequest(token,"/user");
 if(clean(user.login).toLowerCase()!==OWNER)
  throw new Error("Questo token non appartiene all'account amministratore del repository.");
 const repo=await githubRequest(token,"/repos/"+REPO);
 if(repo.full_name?.toLowerCase()!==REPO||repo.permissions?.push!==true)
  throw new Error("Il token deve avere permesso Contents: Read & write su zazoomtek-site.");
 return {login:OWNER,id:user.id};
}
function secureUrl(v){
 const x=clean(v);
 if(!x)return "";
 if(x.startsWith("/")&&!x.startsWith("//")&&!/[<>"'\\]/.test(x))return x;
 try{
  const p=new URL(x);
  if(p.protocol==="https:"&&!p.username&&!p.password&&x.length<=1800)return p.toString();
 }catch(_){}
 return "";
}
function secureVideo(v){
 const url=secureUrl(v);if(!url)return "";
 try{
  const p=new URL(url);
  if(["youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtube-nocookie.com"].includes(p.hostname))
   return url;
 }catch(_){}
 return "";
}
const bounded=(v,lo,hi,f)=>Number.isFinite(Number(v))?Math.min(hi,Math.max(lo,Number(v))):f;
function normalizeArticle(value){
 if(!value||typeof value!=="object")throw new Error("Articolo non valido.");
 const slug=clean(value.slug).toLowerCase(),title=clean(value.title),category=clean(value.category);
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)||slug.length>150)throw new Error("URL articolo non valido.");
 if(title.length<12||title.length>220)throw new Error("Inserisci un titolo tra 12 e 220 caratteri.");
 if(!CATEGORIES.has(category))throw new Error("Categoria non valida.");
 const image=secureUrl(value.image);
 if(!image)throw new Error("Inserisci o carica una copertina.");
 if(!Array.isArray(value.body)||value.body.length<1||value.body.length>160)throw new Error("Inserisci i blocchi dell'articolo.");
 let characters=0;
 const body=value.body.map(block=>{
  const type=clean(block?.type);
  if(!BLOCKS.has(type))throw new Error("Tipo di blocco sconosciuto.");
  const t=clean(block.text),url=secureUrl(block.url);
  if(["paragraph","heading","quote"].includes(type)){
   if(!t||t.length>12000)throw new Error("Blocco vuoto o troppo lungo.");
   characters+=t.length;
   return {type,text:t};
  }
  if(type==="image"){
   if(!url)throw new Error("Link immagine non valido.");
   return {type,url,alt:clean(block.alt).slice(0,180),caption:clean(block.caption).slice(0,250),
 align:["left","center","right"].includes(block.align)?block.align:"center",
 focus_x:bounded(block.focus_x,0,100,50),focus_y:bounded(block.focus_y,0,100,50),
 zoom:bounded(block.zoom,100,250,100),rotation:bounded(block.rotation,-180,180,0)};
  }
  if(type==="video"){
   const video=secureVideo(block.url);
   if(!video)throw new Error("Inserisci un link YouTube HTTPS.");
   return {type,url:video,caption:clean(block.caption).slice(0,250)};
  }
  if(type==="button"){
   if(!url||!t||t.length>110)throw new Error("Il pulsante richiede testo e collegamento.");
   return {type,text:t,url};
  }
  if(type==="audio"||type==="attachment"){
   if(!url)throw new Error("Inserisci un allegato HTTPS o carica il file.");
   return {type,url,text:t.slice(0,180),caption:clean(block.caption).slice(0,250)};
  }
  if(type==="divider")return {type};
  if(type==="poll"){
   const options=Array.isArray(block.options)?block.options.map(clean).filter(Boolean).slice(0,8):[];
   if(!t||options.length<2)throw new Error("Il sondaggio richiede una domanda e due opzioni.");
   return {type,text:t.slice(0,500),options};
  }
 });
 if(characters<260)throw new Error("Inserisci almeno 260 caratteri di testo originale per rispettare i controlli di pubblicazione.");
 let score=null;
 if(value.score!==""&&value.score!==undefined&&value.score!==null){
  score=Number(String(value.score).replace(",","."));
  if(!Number.isFinite(score)||score<0||score>10)throw new Error("Il voto deve essere da 0 a 10.");
 }
 const strings=k=>Array.isArray(value[k])?value[k].map(clean).filter(Boolean).slice(0,8):[];
 return {slug,title,category,image,body,studio_blocks:true,source:"studio-editor",
  author:clean(value.author).slice(0,100)||"Redazione ZazoomTek",
  video_url:secureVideo(value.video_url),
  score,platform:clean(value.platform).slice(0,130),
  cover_focus_x:bounded(value.cover_focus_x,0,100,50),
  cover_focus_y:bounded(value.cover_focus_y,0,100,50),
  cover_zoom:bounded(value.cover_zoom,100,250,100),
  cover_rotation:bounded(value.cover_rotation,-180,180,0),
  pros:strings("pros"),cons:strings("cons"),updated_at:new Date().toISOString()};
}
const allowedPath=p=>/^(data\/studio_(?:posts|overrides|v2_drafts)\.json|assets\/uploads\/[a-z0-9-]+\/[a-z0-9-]+\.(?:jpg|jpeg|png|webp|mp3|m4a|wav|pdf|txt))$/.test(p);
async function readFile(token,path){
 if(!allowedPath(path))throw new Error("Percorso non autorizzato.");
 const p="/repos/"+REPO+"/contents/"+path+"?ref="+encodeURIComponent(BRANCH);
 try{
  const j=await githubRequest(token,p);
  return {sha:j.sha,content:JSON.parse(new TextDecoder().decode(fromBase64((j.content||"").replace(/\s+/g,""))))};
 }catch(e){
  if(/Not Found/i.test(e.message))return {sha:null,content:null};
  throw e;
 }
}
async function writeFile(token,path,document,oldSHA,description){
 if(!allowedPath(path))throw new Error("Percorso non autorizzato.");
 const encoded=encodeUtf8(JSON.stringify(document,null,2)+"\n");
 const body={message:description,branch:BRANCH,content:encoded};
 if(oldSHA)body.sha=oldSHA;
 return githubRequest(token,"/repos/"+REPO+"/contents/"+path,{method:"PUT",body});
}
async function publishedCatalog(request,env){
 if(!env.ASSETS)throw new Error("La build Studio non è disponibile.");
 const asset=await env.ASSETS.fetch(new Request(new URL("/studio/catalog.json",request.url)));
 if(!asset.ok)throw new Error("Catalogo editoriale non disponibile.");
 return asset.json();
}
async function parseInput(request,max=6000000){
 const length=Number(request.headers.get("content-length")||0);
 if(length>max)throw new Error("File troppo grande.");
 const raw=await request.text();
 if(raw.length>max)throw new Error("File troppo grande.");
 try{return JSON.parse(raw)}catch(_){throw new Error("Richiesta JSON non valida.");}
}
async function saveArticle(request,env,session){
 const req=await parseInput(request,1000000);
 const record=normalizeArticle(req.record);
 const list=await publishedCatalog(request,env);
 const current=(list.posts||[]).find(r=>r.slug===record.slug);
 if(Boolean(req.creating)===Boolean(current))
  throw new Error(current?"L'URL esiste già. Apri «Modifica».":"L'articolo non è nel catalogo: ricarica Studio.");
 const file=current?"data/studio_overrides.json":"data/studio_posts.json";
 const target=await readFile(session.token,file);
 const document=target.content||(current?{overrides:{}}:{posts:[]});
 if(current){
  document.overrides=document.overrides||{};
  record.date=current.date||new Date().toISOString().slice(0,10);
  record.published_at=current.published_at||record.date;
  document.overrides[record.slug]=record;
 }else{
  record.date=new Date().toISOString().slice(0,10);
  record.published_at=new Date().toISOString();
  document.posts=Array.isArray(document.posts)?document.posts:[];
  if(document.posts.some(p=>p.slug===record.slug))
   throw new Error("Questo articolo è già stato pubblicato.");
  document.posts.unshift(record);
 }
 await writeFile(session.token,file,document,target.sha,
  "Studio (editorial queue): "+(current?"update ":"create ")+record.slug);
 return respond({ok:true,slug:record.slug,message:"Salvato sul branch SpotNews di prova."});
}
async function upload(request,session){
 const data=await parseInput(request,8500000);
 const slug=clean(data.slug).toLowerCase();
 const extension=({"image/jpeg":"jpg","image/png":"png","image/webp":"webp",
 "audio/mpeg":"mp3","audio/mp4":"m4a","audio/wav":"wav",
 "application/pdf":"pdf","text/plain":"txt"})[data.mime];
 const b64=clean(data.base64).replace(/^data:[^;]+;base64,/,"");
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)||!extension||
  !/^[A-Za-z0-9+/=]+$/.test(b64))throw new Error("Immagine o formato non valido.");
 const bytes=fromBase64(b64);
 if(bytes.byteLength<50||bytes.byteLength>5000000)throw new Error("Il file deve essere inferiore a 5 MB.");
 const jpg=bytes[0]===0xff&&bytes[1]===0xd8&&bytes[2]===0xff;
 const png=bytes[0]===0x89&&bytes[1]===0x50&&bytes[2]===0x4e&&bytes[3]===0x47;
 const webp=String.fromCharCode(...bytes.slice(0,4))==="RIFF"&&String.fromCharCode(...bytes.slice(8,12))==="WEBP";
 const pdf=String.fromCharCode(...bytes.slice(0,5))==="%PDF-";
 const mp3=bytes[0]===0x49&&bytes[1]===0x44&&bytes[2]===0x33||(bytes[0]===0xff&&(bytes[1]&0xe0)===0xe0);
 const m4a=String.fromCharCode(...bytes.slice(4,8))==="ftyp";
 const wav=String.fromCharCode(...bytes.slice(0,4))==="RIFF"&&String.fromCharCode(...bytes.slice(8,12))==="WAVE";
 const plain=extension==="txt"&&!Array.from(bytes.slice(0,50)).includes(0);
 if(!(extension==="jpg"&&jpg||extension==="png"&&png||extension==="webp"&&webp||
  extension==="pdf"&&pdf||extension==="mp3"&&mp3||extension==="m4a"&&m4a||
  extension==="wav"&&wav||plain))
  throw new Error("La firma del file non corrisponde al formato.");
 const id=crypto.randomUUID().replace(/-/g,"").slice(0,20);
 const name="assets/uploads/"+slug+"/"+id+"."+extension;
 const payload={message:"Studio: upload "+slug+" (SpotNews preview)",
  branch:BRANCH,content:b64};
 await githubRequest(session.token,"/repos/"+REPO+"/contents/"+name,{method:"PUT",body:payload});
 return respond({ok:true,url:"/"+name});
}

async function v2Catalog(request,env){
 const result=await env.ASSETS.fetch(new Request(new URL("/studio-v2/catalog.json",request.url)));
 if(!result.ok)throw new Error("Catalogo V2 non disponibile.");
 return result.json();
}
async function getDrafts(token){
 const target=await readFile(token,"data/studio_v2_drafts.json");
 return {sha:target.sha,drafts:target.content?.drafts||{}};
}
function draftValue(raw){
 const r=raw||{},slug=clean(r.slug).toLowerCase(),title=clean(r.title);
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)||slug.length>150)
  throw new Error("La bozza richiede un URL valido.");
 if(!title||title.length>220)throw new Error("La bozza richiede un titolo.");
 if(!CATEGORIES.has(r.category))throw new Error("Categoria non valida.");
 if(!Array.isArray(r.body)||r.body.length>160)throw new Error("Corpo bozza non valido.");
 const allowed=new Set(BLOCKS);
 const blocks=r.body.map(b=>{
  if(!allowed.has(b?.type))throw new Error("Blocco di bozza non valido.");
  const copy={type:b.type};
  for(const key of ["text","url","alt","caption","align"]){
   if(b[key]!=null)copy[key]=clean(b[key]).slice(0,12000);
  }
  for(const key of ["focus_x","focus_y","zoom","rotation"]){
   if(b[key]!=null)copy[key]=Number(b[key]);
  }
  if(b.type==="poll")copy.options=Array.isArray(b.options)?b.options.map(clean).slice(0,8):[];
  return copy;
 });
 return {slug,title,category:r.category,image:secureUrl(r.image),body:blocks,
  studio_blocks:true,source:"studio-editor",
  author:clean(r.author).slice(0,100),video_url:secureVideo(r.video_url),
  platform:clean(r.platform).slice(0,130),score:clean(String(r.score??"")).slice(0,12),
  pros:Array.isArray(r.pros)?r.pros.map(clean).slice(0,8):[],
  cons:Array.isArray(r.cons)?r.cons.map(clean).slice(0,8):[],
  cover_focus_x:bounded(r.cover_focus_x,0,100,50),
  cover_focus_y:bounded(r.cover_focus_y,0,100,50),
  cover_zoom:bounded(r.cover_zoom,100,250,100),
  cover_rotation:bounded(r.cover_rotation,-180,180,0)
 };
}
async function pendingV2(token){
 const [pending,edits]=await Promise.all([readFile(token,"data/studio_posts.json"),readFile(token,"data/studio_overrides.json")]);
 return {posts:Array.isArray(pending.content?.posts)?pending.content.posts:[],
  overrides:edits.content?.overrides&&typeof edits.content.overrides==="object"?edits.content.overrides:{}};
}
async function saveV2(request,env,session){
 const data=await parseInput(request,1000000),mode=clean(data.mode);
 if(!["draft","publish"].includes(mode))throw new Error("Comando non riconosciuto.");
 const record=mode==="draft"?draftValue(data.record):normalizeArticle(data.record);
 if(mode==="draft"){
  // Reload GitHub SHA and merge this draft whenever concurrent writes conflict.
  for(let attempt=0;attempt<4;attempt++){
   const file=await getDrafts(session.token);
   const drafts={...file.drafts};
   drafts[record.slug]={record,kind:data.creating?"new":"edit",updated_at:new Date().toISOString()};
   try{
    await writeFile(session.token,"data/studio_v2_drafts.json",{drafts},
     file.sha,"Studio V2: salva bozza "+record.slug);
    return respond({ok:true,mode:"draft",slug:record.slug,
     message:"Bozza salvata senza cambiare alcuna pagina."});
   }catch(err){
    if(!err.isShaConflict||attempt===3)throw err;
   }
  }
 }
 const catalog=await v2Catalog(request,env);
 const existing=(catalog.posts||[]).find(p=>p.slug===record.slug);
 const queuedPosts=await readFile(session.token,"data/studio_posts.json");
 const pendingItems=Array.isArray(queuedPosts.content?.posts)?queuedPosts.content.posts:[];
 const queuedIndex=pendingItems.findIndex(p=>p.slug===record.slug);
 const queuedExisting=queuedIndex>=0?pendingItems[queuedIndex]:null;
 if(data.creating&&existing)throw new Error("L'indirizzo esiste già: usa Modifica.");
 if(!data.creating&&!existing&&!queuedExisting)throw new Error("Articolo non trovato: aggiorna la libreria.");
 if(existing){
  const oldSeo=existing.seo_lock;
  if(oldSeo&&typeof oldSeo.title==="string"&&typeof oldSeo.description==="string")
   record.seo_lock={title:oldSeo.title,description:oldSeo.description,
    keywords:Array.isArray(oldSeo.keywords)?oldSeo.keywords.slice(0,8):[]};
  record.date=existing.date||new Date().toISOString().slice(0,10);
  record.published_at=existing.published_at||record.date;
  for(let attempt=0;attempt<5;attempt++){
   const file=await readFile(session.token,"data/studio_overrides.json");
   const overrides={...(file.content?.overrides||{}),[record.slug]:record};
   try{
    await writeFile(session.token,"data/studio_overrides.json",{overrides},file.sha,
     "Studio V2: pubblica modifica "+record.slug+" (in coda)");
    break;
   }catch(err){if(!err.isShaConflict||attempt===4)throw err;}
  }
 }else{
  for(let attempt=0;attempt<5;attempt++){
   const file=await readFile(session.token,"data/studio_posts.json");
   const posts=Array.isArray(file.content?.posts)?[...file.content.posts]:[];
   const index=posts.findIndex(p=>p.slug===record.slug);
   const next={...record};
   if(index>=0){
    next.date=posts[index].date||next.date;
    next.published_at=posts[index].published_at||next.published_at;
    posts[index]=next;
   }else{
    next.date=new Date().toISOString().slice(0,10);
    next.published_at=new Date().toISOString();
    posts.unshift(next);
   }
   try{
    await writeFile(session.token,"data/studio_posts.json",{posts},file.sha,
     "Studio V2: "+(index>=0?"aggiorna articolo accodato ":"accoda nuovo articolo ")+record.slug);
    break;
   }catch(err){if(!err.isShaConflict||attempt===4)throw err;}
  }
 }
 // Successful publication is never rolled back by a failure to clean a draft.
 try{
  const drafts=await getDrafts(session.token);
  if(drafts.drafts[record.slug]){
   delete drafts.drafts[record.slug];
   await writeFile(session.token,"data/studio_v2_drafts.json",{drafts:drafts.drafts},
    drafts.sha,"Studio V2: archivia bozza pubblicata "+record.slug);
  }
 }catch(_){}
 return respond({ok:true,mode:"publish",slug:record.slug,
  record,status:"queued",next_slots:["12:30","19:30"],
  message:"Salvato in coda: anteprima disponibile subito; pubblicazione online soltanto al prossimo slot."});
}

export async function onRequest(context){
 const {request,env}=context;
 const pathname=new URL(request.url).pathname.replace(/\/+$/,"");
 if(request.method==="OPTIONS")return respond({ok:false},405);
 if(request.method==="POST"){
  const origin=request.headers.get("Origin")||"";
  if(origin!==new URL(request.url).origin)
   return respond({ok:false,error:"Origine non autorizzata."},403);
  if(!(request.headers.get("Content-Type")||"").toLowerCase().startsWith("application/json"))
   return respond({ok:false,error:"Sono accettate solo richieste JSON."},415);
 }
 if(pathname==="/api/studio/logout"&&request.method==="POST")
  return respond({ok:true,authenticated:false},200,{"Set-Cookie":clearCookie()});
 try{
  assertSetup(env);
 }catch(_){
  return respond({ok:false,code:"SETUP_REQUIRED",
   error:"Per attivare Studio serve soltanto STUDIO_SESSION_SECRET nelle impostazioni Preview di Cloudflare Pages."},503);
 }
 try{
  if(pathname==="/api/studio/login"&&request.method==="POST"){
   const data=await parseInput(request,2000);
   const token=clean(data.token);
   const identity=await authenticate(token);
   const now=Math.floor(Date.now()/1000);
   const payload={v:1,owner:OWNER,branch:BRANCH,token,
    login:identity.login,uid:identity.id,iat:now,exp:now+AGE};
   return respond({ok:true,authenticated:true,login:identity.login,expires:payload.exp},
    200,{"Set-Cookie":setCookie(await seal(payload,env),AGE)});
  }
  const session=await openSession(request,env);
  if(!session||!session.token)return respond({ok:false,authenticated:false,code:"UNAUTHENTICATED",error:"Sessione amministratore assente o non valida. Accedi nuovamente allo Studio di questo dominio."},401);
  if(pathname==="/api/studio/session"&&request.method==="GET"){
   // Sliding session: every visit automatically extends the encrypted
   // HttpOnly browser cookie. There is no fixed recurring login date.
   // Browsers may still erase cookies; revoked GitHub credentials cannot write.
   const now=Math.floor(Date.now()/1000);
   const renewed={...session,iat:now,exp:now+AGE};
   return respond({ok:true,authenticated:true,admin:true,login:session.login,
     persistent:true,renewed:true},200,{"Set-Cookie":setCookie(await seal(renewed,env),AGE)});
  }
  if(pathname==="/api/studio/v2-drafts"&&request.method==="GET")
   return respond({ok:true,drafts:(await getDrafts(session.token)).drafts});
  if(pathname==="/api/studio/v2-pending"&&request.method==="GET")
   return respond({ok:true,...await pendingV2(session.token)});
  // Media caricati su editorial-queue: anteprima autenticata prima dello slot.
  if(pathname==="/api/studio/v2-asset"&&request.method==="GET"){
   let asset=clean(new URL(request.url).searchParams.get("path"));
   if(asset.startsWith("/"))asset=asset.slice(1);
   if(!asset.startsWith("assets/uploads/")||!allowedPath(asset))
    return respond({ok:false,error:"Media non autorizzato."},400);
   const file=await githubRequest(session.token,"/repos/"+REPO+"/contents/"+asset+"?ref="+BRANCH);
   if(file.encoding!=="base64"||!file.content)throw new Error("Media non disponibile in anteprima.");
   const ext=asset.split(".").pop();
   const mime={jpg:"image/jpeg",jpeg:"image/jpeg",png:"image/png",webp:"image/webp",
    mp3:"audio/mpeg",m4a:"audio/mp4",wav:"audio/wav",pdf:"application/pdf",txt:"text/plain"}[ext];
   return new Response(fromBase64(file.content.split(String.fromCharCode(10)).join("")),{status:200,
    headers:{"Content-Type":mime,"Cache-Control":"no-store, private",
     "X-Content-Type-Options":"nosniff"}});
  }
  if(pathname==="/api/studio/v2-save"&&request.method==="POST")
   return await saveV2(request,env,session);
  if(pathname==="/api/studio/save"&&request.method==="POST")
   return await saveArticle(request,env,session);
  if(pathname==="/api/studio/upload"&&request.method==="POST")
   return await upload(request,session);
  return respond({ok:false,error:"Percorso non trovato."},404);
 }catch(e){
  const message=String(e?.message||e||"Errore sconosciuto").slice(0,240);
  const unauth=/Token GitHub scaduto|revocato|senza autorizzazioni|autenticazion|sessione|credenzial/i.test(message);
  return respond({ok:false,authenticated:!unauth,code:unauth?"AUTH_REQUIRED":"STUDIO_REQUEST_FAILED",
   error:unauth?"Sessione o autorizzazione GitHub non valida. Effettua nuovamente l'accesso sul dominio di questa anteprima.":message},unauth?401:400);
 }
}
