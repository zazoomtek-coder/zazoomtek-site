/* Protected Studio API for the isolated SpotNews preview branch.
 * All writes are authorized server-side with verified Cloudflare Access JWT,
 * using a GitHub fine-grained token stored only as Pages encrypted secret.
 * Cloudflare Access maintains the durable browser session cookie.
 */
const REPO="zazoomtek-coder/zazoomtek-site",BRANCH="feature/spotnews-clean-rebuild";
const CATEGORIES=new Set(["news-tech","news-gaming","recensioni-tech","recensioni-gaming","guide","speciali","extra"]);
const BLOCKS=new Set(["paragraph","heading","image","video","button","quote"]);
const headers={"content-type":"application/json;charset=utf-8","cache-control":"no-store","x-content-type-options":"nosniff"};
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers});
const txt=x=>typeof x==="string"?x.trim():"";
function from64(value){
 const s=String(value).replace(/-/g,"+").replace(/_/g,"/");
 return Uint8Array.from(atob(s),ch=>ch.charCodeAt(0));
}
function base64Utf8(value){
 const bytes=new TextEncoder().encode(value);
 let str="";
 for(let i=0;i<bytes.length;i+=8192)str+=String.fromCharCode(...bytes.subarray(i,i+8192));
 return btoa(str);
}
let keyCache=null,cacheDeadline=0;
async function verifyAdmin(request,env){
 const team=txt(env.CF_ACCESS_TEAM_DOMAIN).toLowerCase().replace(/^https?:\/\//,"").replace(/\/+$/,"");
 const audience=txt(env.CF_ACCESS_AUD),admin=txt(env.STUDIO_ADMIN_EMAIL).toLowerCase();
 if(!team||!audience||!admin)throw Error("Access not configured: CF_ACCESS_TEAM_DOMAIN, CF_ACCESS_AUD and STUDIO_ADMIN_EMAIL required");
 if(!/^[a-z0-9.-]+\.cloudflareaccess\.com$/.test(team))throw Error("Invalid Access team hostname");
 const raw=txt(request.headers.get("Cf-Access-Jwt-Assertion"));
 if(!raw)return null;
 const parts=raw.split(".");
 if(parts.length!==3)return null;
 let head,payload;
 try{
  head=JSON.parse(new TextDecoder().decode(from64(parts[0])));
  payload=JSON.parse(new TextDecoder().decode(from64(parts[1])));
 }catch(_){return null;}
 const now=Math.floor(Date.now()/1000);
 if(head.alg!=="RS256"||!head.kid||payload.iss!=="https://"+team||
  !Array.isArray(payload.aud)||!payload.aud.includes(audience)||
  txt(payload.email).toLowerCase()!==admin||
  !Number.isFinite(payload.exp)||payload.exp<=now||
  !Number.isFinite(payload.iat)||payload.iat>now+60||
  (payload.nbf&&payload.nbf>now+60))return null;
 if(!keyCache||Date.now()>cacheDeadline){
  const certs=await fetch("https://"+team+"/cdn-cgi/access/certs");
  if(!certs.ok)throw Error("Cloudflare Access certificates unavailable");
  keyCache=await certs.json();
  cacheDeadline=Date.now()+15*60*1000;
 }
 const jwk=(keyCache.keys||[]).find(k=>k.kid===head.kid);
 if(!jwk){keyCache=null;return null;}
 const publicKey=await crypto.subtle.importKey("jwk",jwk,{name:"RSASSA-PKCS1-v1_5",hash:"SHA-256"},false,["verify"]);
 const signature=from64(parts[2]);
 const valid=await crypto.subtle.verify("RSASSA-PKCS1-v1_5",publicKey,signature,new TextEncoder().encode(parts[0]+"."+parts[1]));
 return valid?{email:admin,expires:payload.exp}:null;
}
function safeUrl(v){
 const s=txt(v);
 if(!s)return "";
 if(s.startsWith("/")&&!s.startsWith("//")&&!/[<>"'\\]/.test(s))return s;
 try{
  const u=new URL(s);
  if(u.protocol==="https:"&&!u.username&&!u.password&&s.length<1800)return u.toString();
 }catch(_){}
 return "";
}
function validVideo(v){
 const url=safeUrl(v);
 if(!url)return "";
 try{
  const p=new URL(url);
  if(["www.youtube.com","youtube.com","m.youtube.com","youtu.be","www.youtube-nocookie.com"].includes(p.hostname))return url;
 }catch(_){}
 return "";
}
function sanitize(incoming){
 if(!incoming||typeof incoming!=="object")throw Error("Article is missing");
 const slug=txt(incoming.slug).toLowerCase(),title=txt(incoming.title),category=txt(incoming.category);
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)||slug.length>150)throw Error("Invalid article slug");
 if(!CATEGORIES.has(category))throw Error("Invalid category");
 if(title.length<12||title.length>220)throw Error("Title must be 12–220 characters");
 if(!Array.isArray(incoming.body)||!incoming.body.length||incoming.body.length>160)throw Error("Add between 1 and 160 blocks");
 const body=[];let total=0;
 for(const source of incoming.body){
  const type=txt(source?.type);
  if(!BLOCKS.has(type))throw Error("Unknown block type: "+type);
  const value=txt(source.text),url=safeUrl(source.url);
  if(["heading","paragraph","quote"].includes(type)){
   if(!value||value.length>12000)throw Error("Block text missing or too long");
   total+=value.length;
   body.push({type,text:value});
  }else if(type==="image"){
   if(!url)throw Error("Invalid inline image URL");
   body.push({type,url,alt:txt(source.alt).slice(0,180),caption:txt(source.caption).slice(0,250)});
  }else if(type==="button"){
   if(!url||!value||value.length>110)throw Error("Button requires label and link");
   body.push({type,text:value,url});
  }else if(type==="video"){
   const video=validVideo(source.url);
   if(!video)throw Error("Use an HTTPS YouTube link for video embeds");
   body.push({type,url:video,caption:txt(source.caption).slice(0,200)});
  }
 }
 if(total<260)throw Error("Article requires at least 260 characters of original editorial text");
 const image=safeUrl(incoming.image);
 if(!image)throw Error("A valid cover is required");
 let score=null;
 if(incoming.score!==""&&incoming.score!==null&&incoming.score!==undefined){
  score=Number(String(incoming.score).replace(",","."));
  if(!Number.isFinite(score)||score<0||score>10)throw Error("Rating must be 0–10");
 }
 const list=k=>Array.isArray(incoming[k])?incoming[k].map(txt).filter(Boolean).slice(0,8):[];
 return {slug,title,category,image,body,studio_blocks:true,source:"studio-editor",
  author:txt(incoming.author).slice(0,100)||"Redazione ZazoomTek",
  score,pros:list("pros"),cons:list("cons"),
  video_url:validVideo(incoming.video_url),
  platform:txt(incoming.platform).slice(0,130),
  updated_at:new Date().toISOString()};
}
async function github(env,path,verb="GET",payload){
 const token=txt(env.STUDIO_GITHUB_TOKEN);
 if(!token)throw Error("GitHub write token not configured");
 if(!/^(data\/studio_(?:posts|overrides)\.json|assets\/uploads\/[a-z0-9-]+\/[a-z0-9-]+\.(?:jpg|jpeg|png|webp))$/.test(path))
  throw Error("Not an allowed repository path");
 const url="https://api.github.com/repos/"+REPO+"/contents/"+path+
  (verb==="GET"?"?ref="+BRANCH:"");
 const response=await fetch(url,{method:verb,headers:{
  "Accept":"application/vnd.github+json","Authorization":"Bearer "+token,
  "X-GitHub-Api-Version":"2022-11-28","Content-Type":"application/json",
  "User-Agent":"ZazoomTek-Studio-preview"},
  body:payload?JSON.stringify(payload):undefined});
 if(verb==="GET"&&response.status===404)return {sha:null,content:null};
 const result=await response.json().catch(()=>({}));
 if(!response.ok){
  if([409,422].includes(response.status))throw Error("Conflitto di versione: ricarica Studio e riprova");
  throw Error("GitHub API "+response.status+": "+txt(result.message).slice(0,130));
 }
 if(verb==="GET"){
  const text=new TextDecoder().decode(from64((result.content||"").replace(/\s/g,"")));
  return {sha:result.sha,content:JSON.parse(text)};
 }
 return result;
}
async function catalog(request,env){
 if(!env.ASSETS)throw Error("Cloudflare Pages ASSETS binding unavailable");
 const url=new URL("/studio/catalog.json",request.url);
 const response=await env.ASSETS.fetch(new Request(url,{method:"GET"}));
 if(!response.ok)throw Error("Catalog not built");
 return response.json();
}
async function input(request,max=1800000){
 const length=Number(request.headers.get("content-length")||0);
 if(length>max)throw Error("Payload exceeds limit");
 const raw=await request.text();
 if(raw.length>max)throw Error("Payload exceeds limit");
 return JSON.parse(raw);
}
async function save(request,env){
 const data=await input(request);
 const record=sanitize(data.record);
 const listing=await catalog(request,env);
 const old=(listing.posts||[]).find(row=>row.slug===record.slug);
 if(Boolean(data.creating)===Boolean(old))
  throw Error(old?"This slug exists; open Edit rather than New":"Original article no longer exists");
 // Original YouTube content is never deleted: an editorial override wins by slug.
 const file=old?"data/studio_overrides.json":"data/studio_posts.json";
 const object=await github(env,file);
 const doc=object.content||(old?{overrides:{}}:{posts:[]});
 if(old){
  doc.overrides=doc.overrides||{};
  record.date=txt(old.date)||new Date().toISOString().slice(0,10);
  record.published_at=txt(old.published_at)||record.date;
  doc.overrides[record.slug]=record;
 }else{
  doc.posts=Array.isArray(doc.posts)?doc.posts:[];
  record.date=new Date().toISOString().slice(0,10);
  record.published_at=new Date().toISOString();
  doc.posts.unshift(record);
 }
 const mutation={message:"Studio: "+(old?"Edit ":"Create ")+record.slug+" (preview branch)",
  branch:BRANCH,content:base64Utf8(JSON.stringify(doc,null,2)+"\n")};
 if(object.sha)mutation.sha=object.sha;
 await github(env,file,"PUT",mutation);
 return json({ok:true,slug:record.slug,preview:true,
  message:"Saved on preview branch. New Cloudflare Pages build triggered."});
}
async function upload(request,env){
 const payload=await input(request,6300000);
 const slug=txt(payload.slug).toLowerCase(),mime=txt(payload.mime);
 const ext=({"image/jpeg":"jpg","image/png":"png","image/webp":"webp"})[mime];
 const image=txt(payload.base64).replace(/^data:[^;]+;base64,/,"");
 if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug)||!ext||
  !/^[A-Za-z0-9+/=]+$/.test(image))throw Error("Invalid image upload");
 const bytes=from64(image);
 if(bytes.byteLength<100||bytes.byteLength>3200000)throw Error("Image must be smaller than 3.2MB");
 const jpg=bytes[0]===0xff&&bytes[1]===0xd8&&bytes[2]===0xff;
 const png=bytes[0]===0x89&&bytes[1]===0x50&&bytes[2]===0x4e&&bytes[3]===0x47;
 const webp=String.fromCharCode(...bytes.slice(0,4))==="RIFF"&&String.fromCharCode(...bytes.slice(8,12))==="WEBP";
 if(!(jpg&&ext==="jpg"||png&&ext==="png"||webp&&ext==="webp"))throw Error("Image data does not match its MIME type");
 const id=crypto.randomUUID().replace(/-/g,"").slice(0,20);
 const filename="assets/uploads/"+slug+"/"+id+"."+ext;
 await github(env,filename,"PUT",{
  message:"Studio: upload cover/inline artwork (preview)",branch:BRANCH,content:image});
 return json({ok:true,url:"/"+filename,preview:true});
}
export async function onRequest(context){
 const {request,env}=context;
 if(request.method==="OPTIONS")return json({error:"Not allowed"},405);
 let admin;
 try{admin=await verifyAdmin(request,env);}
 catch(e){
  const detail=String(e.message||e);
  if(detail.startsWith("Access not configured:")||detail==="Invalid Access team hostname")
   return json({ok:false,configured:false,code:"ACCESS_CONFIGURATION_REQUIRED",
    error:"Cloudflare Access non è configurato. Completa l'attivazione del progetto SpotNews: dominio del team, AUD e email amministratore."},503);
  return json({ok:false,code:"ACCESS_UNAVAILABLE",
   error:"La verifica sicura dell'amministratore non è disponibile al momento."},503);
 }
 if(!admin)return json({ok:false,authenticated:false},401);
 const requestUrl=new URL(request.url);
 const path=requestUrl.pathname.replace(/\/+$/,"");
 if(request.method==="POST"){
  const origin=txt(request.headers.get("Origin"));
  if(origin!==requestUrl.origin)return json({ok:false,error:"Cross-origin modification blocked"},403);
  if(!(request.headers.get("Content-Type")||"").toLowerCase().startsWith("application/json"))
   return json({ok:false,error:"Content-Type must be application/json"},415);
 }
 try{
  if(path==="/api/studio/session"&&request.method==="GET")
   return json({ok:true,authenticated:true,admin:true,expires:admin.expires,email:admin.email});
  if(path==="/api/studio/save"&&request.method==="POST")return save(request,env);
  if(path==="/api/studio/upload"&&request.method==="POST")return upload(request,env);
  return json({error:"Endpoint unavailable"},404);
 }catch(e){return json({ok:false,error:String(e.message||e)},400);}
}
