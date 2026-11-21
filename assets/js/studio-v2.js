"use strict";
(()=>{
const E=id=>document.getElementById(id),S=(tag,cls,text)=>{let e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e};
const cats={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra"};
const authors={"news-tech":"Gimmi","news-gaming":"Gimmi","recensioni-tech":"Beppe","recensioni-gaming":"Beppe","guide":"Beppe","speciali":"Alex","extra":"Alex"};
const authorForCategory=category=>authors[category]||"Gimmi";
let state={rows:[],drafts:{},current:null,body:[],mode:"home",filter:"",newContent:false,busy:false,cover:"",coverPreview:"",context:null,contextBtn:null,newDraftId:null,categoryTouched:false,coverFocusX:50,coverFocusY:50,coverZoom:100,coverRotation:0,modalApply:null,at:0};
const val=id=>E(id).value.trim(),num=(v,lo,hi,def)=>Math.min(hi,Math.max(lo,Number.isFinite(+v)?+v:def));
const slugify=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,135);
function notify(msg,error=false){const t=E("v2-toast");t.hidden=false;t.textContent=msg;t.classList.toggle("error",error)}
async function api(endpoint,data){
 const opt={credentials:"same-origin",cache:"no-store",redirect:"manual",headers:{"Accept":"application/json"}};
 if(data!==undefined){opt.method="POST";opt.headers["Content-Type"]="application/json";opt.body=JSON.stringify(data)}
 let response;
 try{response=await fetch("/api/studio/"+endpoint,opt)}
 catch(_){throw Error("Connessione a Studio interrotta. Il testo resta protetto nella bozza locale.")}
 const type=(response.headers.get("Content-Type")||"").toLowerCase();
 if(!type.includes("application/json")){
  const status=response.type==="opaqueredirect"?"reindirizzamento":String(response.status||"sconosciuto");
  throw Error("L'API Studio non ha restituito JSON (HTTP "+status+"). Nessuna pubblicazione confermata.");
 }
 let result;
 try{result=await response.json()}catch(_){throw Error("Risposta di Studio non valida. Nessuna pubblicazione confermata.")}
 if(!response.ok||result.ok!==true){
  if(response.status===401||result.code==="UNAUTHENTICATED"||result.code==="AUTH_REQUIRED")
   throw Error("Sessione amministratore non valida. Accedi nuovamente allo Studio principale e riprova.");
  throw Error(result.error||"Operazione non riuscita (HTTP "+response.status+").");
 }
 return result;
}

function editorFields(row){
 const fields={"v2-title":row.title||"","v2-slug":row.slug||"","v2-author":authorForCategory(row.category||"news-tech"),
 "v2-video-url":row.video_url||"","v2-platform":row.platform||row.device||"","v2-score":row.score??"",
 "v2-pros":Array.isArray(row.pros)?row.pros.join("\n"):"","v2-cons":Array.isArray(row.cons)?row.cons.join("\n"):""};
 for(const [id,v] of Object.entries(fields))E(id).value=v;
 E("v2-category").value=row.category||"news-tech";
 E("v2-author").readOnly=true;
 E("v2-slug").readOnly=!state.newContent;
 state.cover=row.image||"";state.coverPreview="";
 state.coverFocusX=num(row.cover_focus_x,0,100,50);state.coverFocusY=num(row.cover_focus_y,0,100,50);
 state.coverZoom=num(row.cover_zoom,100,250,100);state.coverRotation=num(row.cover_rotation,-180,180,0);
 state.body=convertBody(row);
 syncCover();syncArticleChrome(row);renderBlocks();seoStatus();
}



function articleEquipment(row){
 const supplied=String(row.platform||row.device||"").trim();
 if(supplied)return supplied;
 const title=String(row.title||"").trim();
 if(row.category==="recensioni-gaming"){
  for(const pattern of [/\bPS5\s*Pro\b/i,/\bPS5\b/i,/\bPS4\b/i,/\bPlayStation\s*5\b/i,/\bNintendo\s*Switch\s*2\b/i,/\bNintendo\s*Switch\b/i,/\bXbox\s*Series\s*[XS]\b/i,/\bPC\b/i]){
   const match=title.match(pattern);if(match)return match[0];
  }
  return "Piattaforma non indicata";
 }
 return title.replace(/\s*[|–-]?\s*(?:recensione|review)\b.*$/i,"").trim()||"Dispositivo non indicato";
}

function syncArticleChrome(row){
 const review=String(row.category||val("v2-category")||"").startsWith("recensioni-");
 const gaming=String(row.category||val("v2-category")||"")==="recensioni-gaming";
 const paper=E("v2-edit-article");
 paper.classList.toggle("review-article",review);
 paper.classList.toggle("news-article",!review);
 const topline=E("v2-live-topline");
 topline.hidden=!review;topline.textContent=cats[row.category||val("v2-category")]||"Recensione";
 const meta=E("v2-live-meta");meta.replaceChildren();
 const date=String(row.date||row.published_at||"").slice(0,10);
 let dateLabel="Data non disponibile";
 if(/^\d{4}-\d{2}-\d{2}$/.test(date)){
  const parsed=new Date(date+"T12:00:00");
  if(!Number.isNaN(parsed.getTime()))dateLabel=parsed.toLocaleDateString("it-IT",{day:"numeric",month:"long",year:"numeric"});
 }
 for(const [cls,label,value] of [
  ["story-meta-author","Autore:",authorForCategory(row.category||val("v2-category"))],
  ["story-meta-date","Data:",dateLabel],
  ["story-meta-category","Categoria:",cats[row.category||val("v2-category")]||"Articolo"]
 ]){
  const span=S("span",cls),strong=S("strong","",label+" ");
  span.append(strong,document.createTextNode(value));meta.append(span);
 }
 const equipment=E("v2-live-equipment"),device=articleEquipment(row);
 equipment.hidden=!review||!device;equipment.replaceChildren();
 if(review&&device)equipment.append(S("strong","",gaming?"Piattaforma: ":"Dispositivo: "),document.createTextNode(device));
 const video=E("v2-live-video");video.replaceChildren();
 let videoId=String(row.youtube_id||"");
 const match=String(row.video_url||"").match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/);
 if(!/^[a-zA-Z0-9_-]{11}$/.test(videoId)&&match)videoId=match[1];
 video.hidden=!review||!videoId;
 if(!video.hidden){
  const link=S("a","review-video-link","▶ GUARDA LA VIDEORECENSIONE SU YOUTUBE ↗");
  link.href="https://www.youtube.com/watch?v="+videoId;link.target="_blank";link.rel="noopener noreferrer";video.append(link);
 }
 const verdict=E("v2-live-verdict");verdict.replaceChildren();
 const score=String(row.score??"").trim(),pros=Array.isArray(row.pros)?row.pros.filter(Boolean):[],cons=Array.isArray(row.cons)?row.cons.filter(Boolean):[];
 verdict.hidden=!review||(!score&&!pros.length&&!cons.length);
 if(!verdict.hidden){
  if(score){
   const header=S("div","verdict-heading");
   header.append(S("h2","","Voto finale"),S("strong","verdict-score",score.replace(".",",")+"/10"));verdict.append(header);
  }
  if(pros.length||cons.length){
   const grid=S("div","verdict-grid");
   for(const [label,items,cls] of [["Pro",pros,"verdict-pro"],["Contro",cons,"verdict-con"]]){
    if(!items.length)continue;
    const side=S("div",cls);side.append(S("h3","",label));
    const ul=S("ul");items.forEach(item=>ul.append(S("li","",item)));side.append(ul);grid.append(side);
   }
   verdict.append(grid);
  }
 }
}

function convertBody(row){
 // A saved Studio override is authoritative: the live catalog's editor_blocks
 // can be older than the body just committed to main. Never reopen stale prose.
 if(row.source==="studio-editor"&&Array.isArray(row.body)&&row.body.length)
  return row.body.map(b=>({...b}));
 // The server supplies the *same editorial paragraphs, red-bar H2s and order*
 // as the live article. Old imported articles retain their generated editor blocks.
 if(Array.isArray(row.editor_blocks)&&row.editor_blocks.length)
  return row.editor_blocks.map(b=>({...b}));
 if(row.studio_blocks&&Array.isArray(row.body))return row.body.map(b=>({...b}));
 const input=Array.isArray(row.body)?row.body:[row.body||""],output=[];
 for(const part of input){
  const p=typeof part==="string"?part:String(part?.text||part?.content||"");
  const trimmed=p.trim();if(!trimmed)continue;
  if(/^#{1,3}\s/.test(trimmed))output.push({type:"heading",text:trimmed.replace(/^#{1,3}\s+/,"")});
  else if(/^\*\*[^*]+\*\*$/.test(trimmed))output.push({type:"heading",text:trimmed.slice(2,-2)});
  else output.push({type:"paragraph",text:p});
 }
 return output.length?output:[{type:"paragraph",text:""}];
}
function signature(parts){
 return (Array.isArray(parts)?parts:[]).map(x=>typeof x==="string"?x:
  [x?.type||"",x?.text||"",x?.html||"",x?.url||"",x?.caption||"",...(Array.isArray(x?.options)?x.options:[])].join(" ")).join(" ")
  .replace(/\s+/g," ").trim();
}


/* Article BODY only: the Github PAT remains exclusively in the encrypted HttpOnly
   session cookie. This local recovery copy is not an authentication mechanism. */
const BACKUP_PREFIX="zazoomtek:studio-v2:article:";
let backupTimer=0;
function backupKey(){
 // Ogni nuova composizione ha una chiave autonoma: non deve mai recuperare
 // l’autosave generico lasciato da un altro articolo creato in precedenza.
 return BACKUP_PREFIX+(state.newContent?"new:"+String(state.newDraftId||"sessione"):String(state.current?.slug||"new"));
 }
function backupNow(){
 if(state.mode!=="editor"||!state.restoreReady)return;
 try{
  const payload={record:collect(),category_touched:!!state.categoryTouched,updated_at:Date.now()};
  localStorage.setItem(backupKey(),JSON.stringify(payload));
  const label=E("v2-autosave-status");
  if(label)label.textContent="Testo protetto sul dispositivo · "+new Date(payload.updated_at).toLocaleTimeString("it-IT",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
 }catch(e){
  const label=E("v2-autosave-status");
  if(label&&!String(label.textContent||"").startsWith("Bozza salvata su GitHub"))label.textContent="Copia di recupero locale non disponibile · puoi comunque salvare la bozza su GitHub.";
 }
}
function scheduleBackup(){
 if(state.mode!=="editor"||!state.restoreReady)return;
 clearTimeout(backupTimer);
 backupTimer=setTimeout(backupNow,250);
}
function restoreBackup(){
 try{
  const cached=JSON.parse(localStorage.getItem(backupKey())||"null");
  if(!cached||!cached.record||!Array.isArray(cached.record.body))return;
  const slug=state.newContent?String(cached.record.slug||""):String(state.current?.slug||"");
  const server=state.drafts[slug];
  const serverTime=Math.max(Date.parse(server?.updated_at||"")||0,Date.parse(state.current?.updated_at||state.current?.published_at||state.current?.date||"")||0);
  if(cached.updated_at < serverTime)return;
  // Never inherit the slug from another published article.
  const copy={...cached.record,slug:state.newContent?cached.record.slug:state.current.slug};
  editorFields(copy);
  if(cached.category_touched)state.categoryTouched=true;
  notify("Testo recuperato dal salvataggio automatico del browser. Premi Salva bozza per conservarlo anche su GitHub.");
 }catch(e){}
}
function formattedTextBlocks(input,category,title){
 // Il testo incollato è la fonte editoriale: preserva paragrafi e titoli espliciti.
 // Non dividere i paragrafi per lunghezza e non generare intestazioni automatiche.
 const raw=String(input||"").replace(/\r\n?/g,"\n").trim();
 if(!raw)return [{type:"paragraph",text:""}];
 const output=[],paragraph=[];
 const flush=()=>{
  if(!paragraph.length)return;
  const text=paragraph.join(" ").replace(/\s+/g," ").trim();
  if(text)output.push({type:"paragraph",text});
  paragraph.length=0;
 };
 const lines=raw.split("\n");
 for(let i=0;i<lines.length;i++){
  const value=lines[i].trim();
  if(!value){flush();continue}
  const markdownHeading=value.match(/^#{1,3}\s+(.+?)\s*#*$/);
  const boldHeading=value.match(/^\*\*([^*\n]{1,120})\*\*$/);
  // Recognize plain, isolated editorial subtitles pasted without Markdown.
  // A heading must start a new block, be concise, have no sentence-ending
  // punctuation, and be followed by further article text.
  const nextText=lines.slice(i+1).find(line=>line.trim());
  const plainHeading=!paragraph.length&&!!nextText&&value.length<=100&&
   value.split(/\s+/).length<=14&&!/[.!?]$/.test(value)&&
   !/^(?:[-•]|\d+[.)])\s/.test(value);
  if(markdownHeading||boldHeading||plainHeading){
   flush();
   const heading=(markdownHeading?markdownHeading[1]:boldHeading?boldHeading[1]:value).trim();
   if(heading)output.push({type:"heading",text:heading});
   continue;
  }
  paragraph.push(value);
 }
 flush();
 return output.length?output:[{type:"paragraph",text:""}];
}
function editorialBodyForDisplay(){
 const onlyText=state.body.every(b=>["paragraph","heading","quote"].includes(b.type));
 const hasHeading=state.body.some(b=>b.type==="heading");
 if(onlyText&&!hasHeading){
  return formattedTextBlocks(state.body.map(b=>b.text||"").join("\n\n"),val("v2-category"),val("v2-title"));
 }
 return state.body.map(b=>({...b}));
}
function applyEditorialFormat(){
 const formatted=editorialBodyForDisplay();
 if(JSON.stringify(formatted)!==JSON.stringify(state.body)){
  state.body=formatted;renderBlocks();scheduleBackup();
 }
}
function previewMediaUrl(url){
 const value=String(url||"");
 if(value.startsWith("data:"))return value;
 const ok=value.startsWith("/assets/uploads/")&&
  ["jpg","jpeg","png","webp","mp3","m4a","wav","pdf","txt"].includes(value.split(".").pop());
 return ok?"/api/studio/v2-asset?path="+encodeURIComponent(value.slice(1)):value;
}

function showArticlePreview(savedRecord=null){
 const record={...(state.current||{}),...(savedRecord&&savedRecord.slug?savedRecord:{}),...collect()};
 const article=E("v2-preview-article-content");article.replaceChildren();
 const review=String(record.category||"").startsWith("recensioni-");
 article.className="article story-article "+(review?"review-article":"news-article");
 article.append(S("h1","",record.title||"Titolo dell'articolo"));
 const meta=S("div","story-meta");
 const date=String(record.date||record.published_at||"").slice(0,10);
 let dateNode=null;
 if(/^\d{4}-\d{2}-\d{2}$/.test(date)){
  const parsed=new Date(date+"T12:00:00");
  if(!Number.isNaN(parsed.getTime())){
   dateNode=S("time","",String(parsed.getDate())+" "+parsed.toLocaleDateString("it-IT",{month:"long"})+" "+parsed.getFullYear());
   dateNode.dateTime=date;
  }
 }
 for(const [cls,label,value] of [
  ["story-meta-author","Autore:",authorForCategory(record.category)],
  ["story-meta-date","Data:",dateNode],
  ["story-meta-category","Categoria:",cats[record.category]||"Articolo"]
 ]){
  const span=S("span",cls),strong=S("strong","",label+" ");
  span.append(strong);
  if(value instanceof Node)span.append(value);else span.append(document.createTextNode(value||"Data non disponibile"));
  meta.append(span);
 }
 article.append(meta);
 const device=articleEquipment(record);
 if(review&&device){
  const equipment=S("p","review-equipment"),gaming=record.category==="recensioni-gaming";
  equipment.append(S("strong","",gaming?"Piattaforma: ":"Dispositivo: "),document.createTextNode(device));article.append(equipment);
 }
 if(record.image||state.coverPreview){
  const figure=S("figure","story-figure"),cover=S("img");
  cover.alt=record.image_caption||record.title||"Copertina";cover.src=state.coverPreview||previewMediaUrl(record.image);
  cover.loading="eager";cover.fetchPriority="high";cover.decoding="async";
  figure.append(cover);if(record.image_caption)figure.append(S("figcaption","",record.image_caption));article.append(figure);
 }else{
  const fallback=S("div","story-cover-fallback");
  fallback.setAttribute("role","img");fallback.setAttribute("aria-label","Copertina editoriale senza fotografia originale");
  fallback.append(S("span","",review?"Recensione":"Articolo"),S("strong","",record.title||"Articolo"));article.append(fallback);
 }
 let videoId=String(record.youtube_id||"");
 const parsed=String(record.video_url||"").match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/);
 if(!/^[a-zA-Z0-9_-]{11}$/.test(videoId)&&parsed)videoId=parsed[1];
 if(review&&videoId){
  const wrapper=S("div","review-video"),link=S("a","review-video-link","▶ GUARDA LA VIDEORECENSIONE SU YOUTUBE ↗");
  link.href="https://www.youtube.com/watch?v="+videoId;link.target="_blank";link.rel="noopener noreferrer";wrapper.append(link);article.append(wrapper);
 }
 const text=S("div","article-text"),blocks=Array.isArray(state.body)?state.body:[];
 for(let i=0;i<blocks.length;i++){
  const block=blocks[i],typ=block.type,t=String(block.text||"");
  if(["paragraph","heading","quote"].includes(typ)){
   const node=S(typ==="heading"?"h2":typ==="quote"?"blockquote":"p",typ==="quote"?"studio-content-quote":"");
   node.append(richContent(t));text.append(node);
  }else if(typ==="image"){
   const figure=S("figure","story-figure studio-content-image studio-align-"+(block.align||"center"));
   const crop=S("div","studio-image-crop"),im=S("img");
   im.alt=block.alt||record.title||"";im.src=state.body[i]?.preview||block.preview||previewMediaUrl(block.url);
   im.style.objectPosition=(block.focus_x??50)+"% "+(block.focus_y??50)+"%";
   im.style.transform="scale("+Number(block.zoom??100)/100+") rotate("+Number(block.rotation??0)+"deg)";
   crop.append(im);figure.append(crop);if(block.caption)figure.append(S("figcaption","",block.caption));text.append(figure);
  }else if(typ==="video"){
   const id=String(block.url||"").match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/)?.[1];
   if(id){const box=S("div","player studio-content-video"),thumb=S("img");thumb.src="https://i.ytimg.com/vi/"+id+"/hqdefault.jpg";thumb.alt="Anteprima video YouTube";box.append(thumb,S("p","v2-preview-media","▶ Riproduci video"));text.append(box)}
  }else if(typ==="button"){
   const p=S("p","studio-content-action"),link=S("a","v2-preview-action",t||"Apri collegamento");link.href=block.url||"#";p.append(link);text.append(p);
  }else if(typ==="html")text.append(safeHtmlFragment(block.html||""));
  else if(typ==="divider")text.append(S("hr","studio-content-divider"));
  else if(typ==="poll"){
   const poll=S("section","studio-content-poll");poll.append(S("h3","",t));
   const ul=S("ul");(block.options||[]).forEach(x=>ul.append(S("li","",x)));poll.append(ul,S("p","studio-poll-note","Sondaggio editoriale — raccolta voti non attivata."));text.append(poll);
  }else if(typ==="audio"){
   const p=S("div","studio-content-audio"),audio=S("audio");audio.controls=true;audio.preload="none";audio.src=block.url||"";p.append(audio);if(block.caption)p.append(S("p","",block.caption));text.append(p);
  }else if(typ==="attachment"){
   const p=S("p","studio-content-attachment"),a=S("a","",t||"Apri allegato");a.href=block.url||"#";p.append(a);text.append(p);
  }
 }
 const notes=Array.isArray(record.ending_notes)?record.ending_notes:[];
 notes.forEach(note=>{if(String(note||"").trim())text.append(S("p","",String(note).trim()))});
 const images=Array.isArray(record.images)?record.images:[];
 images.forEach(item=>{
  if(!item||!item.src)return;
  const figure=S("figure","story-figure"),im=S("img");im.src=previewMediaUrl(item.src);im.alt=item.caption||record.title||"Immagine articolo";
  figure.append(im);if(item.caption)figure.append(S("figcaption","",item.caption));text.append(figure);
 });
 article.append(text);
 if(review){
  const score=String(record.score??"").trim(),pros=Array.isArray(record.pros)?record.pros.filter(Boolean):[],cons=Array.isArray(record.cons)?record.cons.filter(Boolean):[];
  if(score||pros.length||cons.length){
   const verdict=S("section","review-verdict"),grid=S("div","verdict-grid");
   if(score){
    const header=S("div","verdict-heading");
    header.append(S("h2","","Voto finale"),S("strong","verdict-score",score.replace(".",",")+"/10"));verdict.append(header);
   }
   for(const [label,items,cls] of [["Pro",pros,"verdict-pro"],["Contro",cons,"verdict-con"]]){
    if(!items.length)continue;
    const side=S("div",cls);side.append(S("h3","",label));
    const ul=S("ul");items.forEach(v=>ul.append(S("li","",v)));side.append(ul);grid.append(side);
   }
   if(pros.length||cons.length)verdict.append(grid);article.append(verdict);
  }
 }
 backupNow();E("v2-article-preview").hidden=false;
}

function closeArticlePreview(){E("v2-article-preview").hidden=true}

function seoStatus(){
 const lock=state.current?.seo_lock;
 E("v2-seo-status").textContent=lock&&!state.newContent
  ?"SEO originale protetto. Modificare testo o immagini non cambia i metadati editoriali già assegnati."
  :"SEO generato automaticamente dal titolo e da tutto il testo quando pubblichi. Non devi configurare nulla.";
 E("v2-seo-title").textContent=lock&&!state.newContent?lock.title:(val("v2-title")||"Nuovo articolo")+" | ZazoomTek";
 E("v2-seo-description").textContent=lock&&!state.newContent?lock.description:
  state.body.filter(b=>b.type==="paragraph").map(b=>b.text||"").join(" ").slice(0,155)||"Il sito crea una descrizione SEO personalizzata dal contenuto completo.";
}
function syncCover(){
 const hasCover=!!(state.cover||state.coverPreview);
 E("v2-cover-add").hidden=hasCover;
 E("v2-cover-stage").hidden=!hasCover;
 const i=E("v2-cover-image");
 const visibleSrc=state.coverPreview||previewMediaUrl(state.cover)||"";
 i.onerror=null;
 // Newly uploaded assets live on GitHub before the Cloudflare build publishes them.
 // Retry only these first-party uploads, never remote third-party covers.
 if(visibleSrc.startsWith("/assets/uploads/")){
  let retries=0;
  i.onerror=()=>{
   if(retries++>=12){i.onerror=null;notify("La copertina è stata salvata ma l'anteprima pubblica non è ancora disponibile. Ricarica Studio.",true);return}
   setTimeout(()=>{
    if(state.cover===visibleSrc&&!state.coverPreview)
     i.src=visibleSrc+(visibleSrc.includes("?")?"&":"?")+"preview-retry="+Date.now();
   },5000);
  };
 }
 i.src=visibleSrc;
 i.style.objectPosition=state.coverFocusX+"% "+state.coverFocusY+"%";
 i.style.transform="scale("+(state.coverZoom/100)+") rotate("+state.coverRotation+"deg)";
 const box=E("v2-settings-cover");box.replaceChildren();
 if(hasCover){const copy=S("img");copy.src=state.coverPreview||state.cover;copy.alt="Miniatura copertina";copy.style.objectPosition=state.coverFocusX+"% "+state.coverFocusY+"%";box.append(copy)}
 else box.textContent="Nessuna copertina";
}
async function refreshLibrary(){
 try{
  const response=await fetch("/studio-v2/catalog.json",{cache:"no-store"});
  if(!response.ok)return;
  const catalog=(await response.json()).posts||[];
  const pending=await api("v2-pending");
  const liveSlugs=new Set(catalog.map(item=>item.slug));
  const bySlug=new Map(catalog.map(item=>[item.slug,item]));
  for(const item of pending.posts||[]){
   if(item?.slug)bySlug.set(item.slug,{...(bySlug.get(item.slug)||{}),...item,__queued:!liveSlugs.has(item.slug)});
  }
  for(const [slug,override] of Object.entries(pending.overrides||{})){
   if(bySlug.has(slug))bySlug.set(slug,{...bySlug.get(slug),...override});
  }
  state.rows=[...bySlug.values()];
  E("v2-count-all").textContent=state.rows.length;
  E("v2-count-tech").textContent=state.rows.filter(x=>x.category==="news-tech").length;
  E("v2-count-gaming").textContent=state.rows.filter(x=>x.category==="news-gaming").length;
  E("v2-count-reviews").textContent=state.rows.filter(x=>String(x.category||"").startsWith("recensioni-")).length;
  renderList();
 }catch(_){
  // Mantieni visibile l'ultima libreria valida se il refresh remoto non è disponibile.
 }
}
function showHome(){
 backupNow();
 hideContext();
 state.mode="home";E("v2-home").hidden=false;E("v2-editor").hidden=true;E("v2-back").hidden=true;
 E("v2-crumb").textContent="Studio / Contenuti";E("v2-home-nav").classList.add("on");
 renderList();history.replaceState({}, "", "/studio-v2/");
 refreshLibrary();
}
function showEditor(row,newContent,skipBackup=false){
 if(!skipBackup)backupNow(); // Protect previous article before replacing the editor contents.
 state.current=row;state.newContent=!!newContent;state.categoryTouched=false;
 if(state.newContent&&!state.newDraftId)state.newDraftId=makeDraftId();
 if(!state.newContent)state.newDraftId=null;
 state.mode="editor";state.restoreReady=false;
 E("v2-home").hidden=true;E("v2-editor").hidden=false;E("v2-back").hidden=false;
 E("v2-home-nav").classList.remove("on");
 E("v2-editor-heading").textContent=newContent?"Crea un nuovo contenuto":"Modifica il contenuto";
 E("v2-editor-note").textContent=newContent?"Scrivi e pubblica quando vuoi.":"Puoi cambiare tutto, senza aprire altri pannelli.";
 E("v2-crumb").textContent="Studio / "+(newContent?"Nuovo contenuto":"Modifica");
 editorFields(row);
 restoreBackup();state.restoreReady=true;
 history.replaceState({}, "", "/studio-v2/"+(newContent?"?new=1&draft="+encodeURIComponent(state.newDraftId):"?edit="+encodeURIComponent(row.slug)));
 window.scrollTo(0,0);
}
function makeDraftId(){
 return (typeof crypto!=="undefined"&&crypto.randomUUID)?crypto.randomUUID():Date.now().toString(36)+"-"+Math.random().toString(36).slice(2,12);
}
function startNew(draftId=null){
 if(state.busy)return;
 // Save the current article under its own recovery key before switching drafts.
 backupNow();
 state.categoryTouched=false;
 state.newDraftId=draftId||makeDraftId();
 showEditor({title:"",slug:"",category:"news-tech",author:"Gimmi",body:[{type:"paragraph",text:""}]},true,true);
}
function renderList(){
 const q=val("v2-search").toLocaleLowerCase("it"),cat=state.filter||val("v2-select-filter");
 const draftOnly=Object.values(state.drafts).filter(d=>d&&d.kind==="new"&&d.record&&
  !state.rows.some(x=>x.slug===d.record.slug)).map(d=>({...d.record,__draftNew:true}));
 const rows=[...draftOnly,...state.rows].filter(r=>(!cat||r.category===cat)&&(!q||String(r.title).toLocaleLowerCase("it").includes(q)));
 E("v2-library-caption").textContent=rows.length+" contenuti disponibili · Ordine: più recenti";
 const host=E("v2-list");host.replaceChildren();
 if(!rows.length)host.append(S("p","v2-no-results","Nessun contenuto trovato."));
 for(const row of rows){
  const item=S("div","v2-list-item");
  const img=S("img","v2-list-cover");img.loading="lazy";img.alt="";img.src=previewMediaUrl(row.image)||"";item.append(img);
  const meta=S("div"),title=S("div","v2-list-title",row.title||"Senza titolo");
  const desc=S("div","v2-list-meta");
  desc.append(S("b","",cats[row.category]||"Articolo"),S("span","", " · "+(row.date||"")+" · "+(state.drafts[row.slug]?"Bozza disponibile":row.__queued?"Salvato in main · in attesa del deploy":"Pubblicato")));
  meta.append(title,desc);item.append(meta);
  const btn=S("button","v2-list-edit","Modifica");btn.type="button";btn.addEventListener("click",()=>openExisting(row));
  item.append(btn);host.append(item);
 }
}
function openExisting(row){
 const draft=state.drafts[row.slug];
 const content=draft?.record||row;
 const sameAsOriginal=draft&&signature(row.body)===signature(draft.record?.body);
 const originalBlocks=Array.isArray(row.editor_blocks)&&row.editor_blocks.length?row.editor_blocks:null;
 const useImportedBlocks=!!originalBlocks&&row.source!=="studio-editor";
 const editorData=(draft&&sameAsOriginal&&useImportedBlocks)?{...content,body:originalBlocks}:content;
 if(!draft&&useImportedBlocks)editorData.editor_blocks=originalBlocks;
 showEditor({...editorData,slug:row.slug,seo_lock:row.seo_lock},!!row.__draftNew);
 if(draft)notify("È stata caricata la tua bozza non ancora pubblicata.");
}
function modal(title,body,apply){
 E("v2-modal-title").textContent=title;
 const slot=E("v2-modal-body");slot.replaceChildren();slot.append(body);
 E("v2-modal").hidden=false;state.modalApply=apply;
}
function closeModal(){E("v2-modal").hidden=true;state.modalApply=null}
function field(container,title,value="",type="text"){
 const label=S("label"),span=S("span","",title),input=document.createElement(type==="textarea"?"textarea":"input");
 if(type!=="textarea")input.type=type;else input.rows=4;
 input.value=value;label.append(span,input);container.append(label);return input;
}
function openMenu(at){
 state.at=Math.max(0,Math.min(state.body.length,Number.isInteger(at)?at:state.body.length));
 E("v2-insert-menu").hidden=false;
}
function addBlock(kind){
 E("v2-insert-menu").hidden=true;
 if(kind==="link"&&state.context){inlineLink();return}
 const position=Math.max(0,Math.min(state.body.length,Number.isInteger(state.at)?state.at:state.body.length));
 const block={type:kind==="link"?"paragraph":kind,text:"",html:"",url:"",caption:"",alt:"",align:"center",focus_x:50,focus_y:50,zoom:100,rotation:0};
 if(kind==="divider")block.text="—";
 if(kind==="poll")block.options=["Opzione 1","Opzione 2"];
 state.body.splice(position,0,block);state.at=position+1;renderBlocks();
 if(["image","audio","attachment","video","button","poll","html"].includes(kind))editMedia(block);
 else if(["paragraph","heading","quote"].includes(block.type)){
  const row=E("v2-blocks").querySelector('[data-index="'+position+'"]');
  const editable=row?.querySelector(".v2-rich-text");
  if(editable){editable.focus();const range=document.createRange();range.selectNodeContents(editable);range.collapse(false);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range)}
 }
 seoStatus();scheduleBackup();
}
function drawField(wrapper,text,initial,onChange,textarea=false){
 const input=document.createElement(textarea?"textarea":"input");
 if(!textarea)input.type="text";
 input.className=textarea?"v2-block-text":"v2-media-input";input.placeholder=text;input.value=initial||"";
 if(textarea)input.rows=2;
 input.addEventListener("input",()=>{onChange(input.value);seoStatus()});
 wrapper.append(input);return input;
}
function addTextAfterBlock(i){
 const next=i+1;
 state.body.splice(next,0,{type:"paragraph",text:""});
 renderBlocks();
 const row=E("v2-blocks").querySelector('[data-index="'+next+'"]');
 const editable=row?.querySelector(".v2-rich-text");
 if(editable){
  editable.focus();
  const range=document.createRange();
  range.selectNodeContents(editable);range.collapse(false);
  const selection=window.getSelection();
  selection.removeAllRanges();selection.addRange(range);
  cursorHere(next,editable);
 }
 seoStatus();scheduleBackup();
}
function moveBlock(i,delta){
 let j=i+delta;if(j<0||j>=state.body.length)return;
 [state.body[i],state.body[j]]=[state.body[j],state.body[i]];renderBlocks();
}

function richContent(value){
 const f=document.createDocumentFragment(),text=String(value||"");
 const re=/\[([^\]\n]{1,300})\]\((https:\/\/[^)\s]+|\/[^)\s]+)\)|\*\*([^*\n]+)\*\*|\*([^*\n]+)\*|(\n)/g;let m,at=0;
 while((m=re.exec(text))){
  if(m.index>at)f.append(document.createTextNode(text.slice(at,m.index)));
  if(m[1]){const link=S("a","",m[1]);link.href=m[2];link.addEventListener("click",e=>e.preventDefault());f.append(link)}
  else if(m[3])f.append(S("strong","",m[3]));
  else if(m[4])f.append(S("em","",m[4]));
  else f.append(document.createElement("br"));
  at=re.lastIndex;
 }
 if(at<text.length)f.append(document.createTextNode(text.slice(at)));
 return f;
}
function richValue(node){
 if(node.nodeType===3)return node.nodeValue;
 if(node.nodeType!==1&&node.nodeType!==11)return "";
 const tag=node.nodeName.toLowerCase();
 if(tag==="br")return "\n";
 const val=Array.from(node.childNodes).map(richValue).join("");
 if(tag==="strong"||tag==="b")return "**"+val+"**";
 if(tag==="em"||tag==="i")return "*"+val+"*";
 if(tag==="a"){
  const url=node.getAttribute("href")||"";
  return /^https:\/\//.test(url)||url.startsWith("/")&&!url.startsWith("//")?"["+val+"]("+url+")":val;
 }
 if(tag==="p"||tag==="div")return val+"\n";
 return val;
}
function detectEditorialCategory(input,title){
  const text=String(title||"")+" "+String(input||"");
  const normalized=text.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLocaleLowerCase("it");
  const hasAny=patterns=>patterns.some(pattern=>pattern.test(normalized));
  const gaming=hasAny([
    /\b(videogioch\w*|videogame\w*|gaming|gamepad|joypad|playstation|ps5|ps4|ps vr|xbox|nintendo|switch 2|switch|steam deck|steam|epic games|game pass|gameplay|dlc|multiplayer|console|esport|e sport)\b/,
    /\b(gears of war|call of duty|grand theft auto|gta|resident evil|final fantasy|the witcher|fortnite|minecraft|elden ring|assassin s creed)\b/
  ]);
  const review=hasAny([
    /\b(recensione|recensioni|review tech|review gaming|review:|abbiamo provato|la nostra prova|test completo|prova approfondita|voto finale|pro e contro)\b/
  ]);
  const guide=hasAny([
    /\b(guida|tutorial|come fare|come configurare|come installare|come risolvere|passo dopo passo|procedura|istruzioni pratiche)\b/
  ]);
  const special=hasAny([/\b(speciale|dossier|inchiesta|approfondimento|analisi approfondita|report speciale)\b/]);
  const extra=hasAny([/\b(intervista|dietro le quinte|retroscena|evento dal vivo|fiera di settore)\b/]);
  if(guide&&!review)return "guide";
  if(review)return gaming?"recensioni-gaming":"recensioni-tech";
  if(special)return "speciali";
  if(extra)return "extra";
  return gaming?"news-gaming":"news-tech";
}
function updateAutoCategory(){
 if(state.categoryTouched)return;
 const title=val("v2-title");
 const body=state.body.map(block=>block.type==="html"?String(block.html||"").replace(/<[^>]*>/g," "):String(block.text||"")).join(" ");
 if(!title&&!body.trim())return;
 const detected=detectEditorialCategory(body,title);
 if(E("v2-category").value!==detected){
  E("v2-category").value=detected;
  E("v2-author").value=authorForCategory(detected);
  state.current={...(state.current||{}),category:detected,author:authorForCategory(detected)};
  syncArticleChrome({...state.current,...collect()});
 }
}
function safePaste(e){
 e.preventDefault();
 const raw=e.clipboardData?.getData("text/plain")||"";
 if(!raw)return;
 const idx=Number(e.currentTarget.closest("[data-index]")?.dataset.index);
 const current=state.body[idx];
 if(current&&current.type==="paragraph"&&!String(current.text||"").trim()){
  const blocks=formattedTextBlocks(raw,val("v2-category"),val("v2-title"));
  state.body.splice(idx,1,...blocks);updateAutoCategory();renderBlocks();seoStatus();scheduleBackup();
  notify("Testo inserito e impaginato. Categoria aggiornata automaticamente in base a titolo e contenuto.");
  return;
 }
 const sel=window.getSelection();if(!sel?.rangeCount)return;
 const r=sel.getRangeAt(0),node=document.createTextNode(raw);
 r.deleteContents();r.insertNode(node);r.setStartAfter(node);r.collapse(true);
 sel.removeAllRanges();sel.addRange(r);e.currentTarget.dispatchEvent(new Event("input",{bubbles:true}));
}
function safeHtmlFragment(source){
 const template=document.createElement("template");template.innerHTML=String(source||"");
 const allowed=new Set(["a","p","br","strong","b","em","i","u","s","ul","ol","li","h2","h3","h4","blockquote","hr","img","iframe","figure","figcaption","div","span","small","sup","sub","code","pre","table","thead","tbody","tr","th","td","section"]);
 const blocked=new Set(["script","style","object","embed","svg","math","form","input","button","textarea","select","option","video","audio","source","link","meta"]);
 const cleanNode=node=>{
  if(node.nodeType===Node.TEXT_NODE)return document.createTextNode(node.nodeValue||"");
  if(node.nodeType!==Node.ELEMENT_NODE)return document.createDocumentFragment();
  const tag=node.tagName.toLowerCase();if(blocked.has(tag))return document.createDocumentFragment();
  const children=Array.from(node.childNodes).map(cleanNode);
  if(!allowed.has(tag)){const fragment=document.createDocumentFragment();children.forEach(child=>fragment.append(child));return fragment;}
  const element=document.createElement(tag);
  if(tag==="a"){
   const href=node.getAttribute("href")||"";
   if(/^https:\/\//i.test(href)||(/^\/(?!\/)/.test(href)))element.href=href;
   if(element.href){element.rel="noopener noreferrer external";if(/^https:\/\//i.test(href))element.target="_blank";}
   const title=node.getAttribute("title");if(title)element.title=title.slice(0,180);
  }else if(tag==="iframe"){
   let src=node.getAttribute("src")||"";
   if(src.startsWith("//"))src="https:"+src;
   if(!/^https:\/\//i.test(src))return document.createDocumentFragment();
   element.src=src;element.loading="lazy";element.referrerPolicy="no-referrer";
   element.setAttribute("sandbox","allow-scripts allow-forms allow-popups");
   const title=node.getAttribute("title")||"Contenuto incorporato";element.title=title.slice(0,180);
   for(const name of ["width","height"]){const v=Number(node.getAttribute(name));if(Number.isInteger(v)&&v>0&&v<=2000)element.setAttribute(name,String(v));}
  }else if(tag==="img"){
   const src=node.getAttribute("src")||"";
   if(/^https:\/\//i.test(src)||(/^\/(?!\/)/.test(src)))element.src=src;else return document.createDocumentFragment();
   element.alt=(node.getAttribute("alt")||"").slice(0,180);element.loading="lazy";element.decoding="async";
  }else if(tag==="td"||tag==="th"){
   for(const name of ["colspan","rowspan"]){const v=Number(node.getAttribute(name));if(Number.isInteger(v)&&v>0&&v<=12)element.setAttribute(name,String(v));}
  }
  children.forEach(child=>element.append(child));return element;
 };
 const fragment=document.createDocumentFragment();Array.from(template.content.childNodes).map(cleanNode).forEach(node=>fragment.append(node));return fragment;
}
function hideContext(){if(state.contextBtn)state.contextBtn.hidden=true}
function cursorHere(){/* Insertion is managed by between-block controls, like Patreon. */}
function insertPosition(){
 const ctx=state.context;let pos=state.body.length;
 if(ctx&&state.body[ctx.index]){
  pos=ctx.index+1;
  const b=state.body[ctx.index],r=ctx.range,field=ctx.field;
  if(["paragraph","heading","quote"].includes(b.type)&&r&&field.isConnected&&field.contains(r.startContainer)){
   const l=document.createRange();l.selectNodeContents(field);l.setEnd(r.startContainer,r.startOffset);
   const rr=document.createRange();rr.selectNodeContents(field);rr.setStart(r.startContainer,r.startOffset);
   const left=richValue(l.cloneContents()).trim(),right=richValue(rr.cloneContents()).trim();
   if(left&&right){b.text=left;state.body.splice(ctx.index+1,0,{type:b.type==="heading"?"paragraph":b.type,text:right})}
   else if(!left)pos=ctx.index;
  }
 }
 state.context=null;hideContext();return pos;
}
function inlineLink(){
 const ctx=state.context,body=S("div");
 const label=field(body,"Testo del collegamento",ctx?.range?.toString().trim()||"");
 const address=field(body,"Indirizzo HTTPS","https://");
 modal("Link nel testo",body,()=>{
  const u=address.value.trim(),t=label.value.trim();
  if(!t||!(u.startsWith("https://")||u.startsWith("/")&&!u.startsWith("//"))){notify("Inserisci un testo e un URL HTTPS.",true);return false}
  if(ctx?.range&&ctx.field?.isConnected){
   const r=ctx.range.cloneRange(),a=S("a","",t);a.href=u;
   r.deleteContents();r.insertNode(a);
   state.body[ctx.index].text=richValue(ctx.field).trim();seoStatus();
  }
  state.context=null;hideContext();return true;
 });
}
function renderBlocks(){
 const host=E("v2-blocks");host.replaceChildren();hideContext();state.context=null;
 state.body.forEach((b,i)=>{
  const row=S("div","v2-editorial-row"+(["paragraph","heading","quote"].includes(b.type)?" article-text":""));row.dataset.index=i;
  if(["paragraph","heading","quote"].includes(b.type)){
   const tag=b.type==="heading"?"h2":b.type==="quote"?"blockquote":"p";
   const editable=S(tag,"v2-rich-text");
   editable.contentEditable="true";editable.spellcheck=true;
   editable.setAttribute("role","textbox");
   editable.setAttribute("aria-label",b.type==="heading"?"Modifica sottotitolo":"Modifica il testo");
   editable.dataset.placeholder=b.type==="heading"?"Scrivi un sottotitolo...":"Clicca per scrivere...";
   editable.append(richContent(b.text||""));
   editable.addEventListener("input",()=>{b.text=richValue(editable).trim();updateAutoCategory();seoStatus();scheduleBackup()});
   editable.addEventListener("paste",safePaste);
   const tools=S("div","v2-media-hover-tools");
   tools.append(actionButton("↑",()=>moveBlock(i,-1)));
   tools.append(actionButton("↓",()=>moveBlock(i,1)));
   tools.append(actionButton("Rimuovi",()=>{
    state.body.splice(i,1);
    renderBlocks();
    seoStatus();
    notify("Blocco di testo rimosso.");
   }));
   row.append(editable,tools);
  }else{
   const card=S("div","v2-media-block v2-inline-media");
   if(b.type==="image"){
    const image=S("img");image.src=b.preview||b.url||"";image.alt=b.alt||"Immagine articolo";
    image.style.maxWidth=b.align==="left"||b.align==="right"?"55%":"100%";
    image.style.marginLeft=b.align==="right"?"auto":"0";
    image.style.objectPosition=num(b.focus_x,0,100,50)+"% "+num(b.focus_y,0,100,50)+"%";
    image.style.transform="scale("+num(b.zoom,100,250,100)/100+") rotate("+num(b.rotation,-180,180,0)+"deg)";
    card.append(image);
    if(b.caption)card.append(S("figcaption","",b.caption));
   }else if(b.type==="video"){
    const m=(b.url||"").match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/);
    if(m){const image=S("img","v2-video-thumb");image.src="https://i.ytimg.com/vi/"+m[1]+"/hqdefault.jpg";image.alt="Anteprima video";card.append(image)}
    card.append(S("div","v2-inline-video-title","▶ "+(b.caption||"Video YouTube")));
   }else if(b.type==="divider")card.append(S("hr"));
   else if(b.type==="poll"){
    card.append(S("h3","",b.text||"Sondaggio"));
    const ul=S("ul");(b.options||[]).forEach(x=>ul.append(S("li","",x)));card.append(ul);
   }else if(b.type==="button")card.append(S("span","v2-action-example",b.text||"Pulsante"));
   else if(b.type==="html"){card.classList.add("v2-html-block");card.append(safeHtmlFragment(b.html||""));}
   else if(b.type==="audio"){
    if(b.url&&!b.preview){const player=S("audio");player.controls=true;player.preload="none";player.src=b.url;card.append(player)}
    card.append(S("p","",b.text||"Audio"));
   }else card.append(S("span","v2-action-example",b.text||"Allegato"));
   const tools=S("div","v2-media-hover-tools");
   if(b.type!=="divider")tools.append(actionButton("Modifica",()=>editMedia(b)));
   if(b.type==="image")tools.append(actionButton("Sostituisci",()=>chooseFile(b)));
    if(b.type==="image")tools.append(actionButton("＋ Testo dopo",()=>addTextAfterBlock(i)));
   tools.append(actionButton("↑",()=>moveBlock(i,-1)));
   tools.append(actionButton("↓",()=>moveBlock(i,1)));
   tools.append(actionButton("Rimuovi",()=>{state.body.splice(i,1);renderBlocks();seoStatus()}));
   card.append(tools);row.append(card);
  }
  host.append(row);
  // Never place the insertion control immediately after a subtitle.
  // It will appear after the following paragraph/content block instead.
  if(b.type!=="heading"){
   const slot=S("div","v2-insert-slot");
   const insert=S("button","v2-insert-trigger","＋  Aggiungi contenuto");
   insert.type="button";insert.setAttribute("aria-label","Inserisci un blocco dopo questo paragrafo o contenuto");
   insert.addEventListener("click",()=>openMenu(i+1));
   slot.append(insert);host.append(slot);
  }
 });
 if(!state.body.length){
  const slot=S("div","v2-insert-slot"),insert=S("button","v2-insert-trigger","＋  Aggiungi contenuto");
  insert.type="button";insert.addEventListener("click",()=>openMenu(0));slot.append(insert);host.append(slot);
 }
 scheduleBackup();
}

function actionButton(text,callback){
 const b=S("button","",text);b.type="button";b.addEventListener("click",callback);return b;
}

function readImageFile(file){
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onload=()=>typeof reader.result==="string"?resolve(reader.result):reject(new Error("File immagine non leggibile."));
  reader.onerror=()=>reject(new Error("Non riesco a leggere "+file.name+"."));
  reader.readAsDataURL(file);
 });
}

async function chooseFile(target,onUploaded){
 const chooser=document.createElement("input");chooser.type="file";
 chooser.accept=target?.type==="audio"?"audio/mpeg,audio/mp4,audio/wav":target?.type==="attachment"?"application/pdf,text/plain":"image/jpeg,image/png,image/webp";
 chooser.addEventListener("change",async()=>{
  const file=chooser.files?.[0];if(!file)return;
  if(file.size>5000000){notify("File oltre 5 MB: scegli un file più leggero.",true);return}
  try{
   const preview=await readImageFile(file);
   if(target){target.url=preview;target.text=target.text||file.name;target.preview=preview;renderBlocks()}
   else{state.cover=preview;state.coverPreview=preview;syncCover();if(typeof onUploaded==="function")onUploaded()}
   notify("File caricato nella prova locale: nessun invio al server.");scheduleBackup();
  }catch(e){notify("Lettura file non riuscita: "+e.message,true)}
 });chooser.click();
}
function editMedia(block){
 const body=S("div"),kind=block.type,initial={...block},change={...block};
 const u=["image","video","audio","button","attachment"].includes(kind)?field(body,kind==="button"?"Collegamento HTTPS":"URL o percorso del file",block.url||""):null;
 const t=["button","poll","audio","attachment"].includes(kind)?field(body,kind==="poll"?"Domanda":"Titolo / etichetta",block.text||""):null;
 const cap=["image","video","audio"].includes(kind)?field(body,"Didascalia (facoltativa)",block.caption||""):null;
 const alt=kind==="image"?field(body,"Descrizione immagine per Google",block.alt||""):null;
 const options=kind==="poll"?field(body,"Opzioni del sondaggio (una per riga)",(block.options||[]).join("\n"),"textarea"):null;
 const html=kind==="html"?field(body,"HTML personalizzato · link affiliati, immagini e formattazione",block.html||"","textarea"):null;
 if(html){
  const preview=S("div","v2-html-live-preview");body.append(preview);
  const refresh=()=>preview.replaceChildren(safeHtmlFragment(html.value));
  html.addEventListener("input",refresh);refresh();
 }
 if(["image","audio","attachment"].includes(kind)){
  const upload=actionButton("Carica dal computer",()=>{closeModal();chooseFile(block)});upload.className="v2-soft";
  body.append(upload);
 }
 let crop=null;
 if(kind==="image"){
  const grid=S("div","v2-modal-grid");
  const align=field(grid,"Allineamento (left, center, right)",block.align||"center");
  const focusX=field(grid,"Centro orizzontale 0–100",block.focus_x??50,"number");
  const focusY=field(grid,"Centro verticale 0–100",block.focus_y??50,"number");
  const zoom=field(grid,"Zoom 100–250%",block.zoom??100,"number");
  const rotation=field(grid,"Rotazione -180° / 180°",block.rotation??0,"number");
  crop={align,focusX,focusY,zoom,rotation};body.append(grid);
 }
 modal(({image:"Modifica immagine",video:"Inserisci video YouTube",audio:"Aggiungi audio",button:"Modifica pulsante e link",attachment:"Allegato",poll:"Sondaggio",html:"HTML personalizzato"})[kind],body,()=>{
  if(u)block.url=u.value.trim();if(t)block.text=t.value.trim();if(cap)block.caption=cap.value.trim();if(alt)block.alt=alt.value.trim();
  if(options)block.options=options.value.split("\n").map(v=>v.trim()).filter(Boolean).slice(0,8);
  if(html)block.html=html.value;
  if(crop){
   block.align=["left","center","right"].includes(crop.align.value)?crop.align.value:"center";
   block.focus_x=num(crop.focusX.value,0,100,50);block.focus_y=num(crop.focusY.value,0,100,50);
   block.zoom=num(crop.zoom.value,100,250,100);block.rotation=num(crop.rotation.value,-180,180,0);
  }
  renderBlocks();return true;
 });
}
function editCover(){
 const body=S("div"),url=field(body,"URL della cover (puoi anche caricarla)",state.cover);
 const upload=actionButton("Carica copertina dal PC",()=>chooseFile(null,()=>{url.value=state.cover;draw()}));
 upload.className="v2-soft";body.append(upload);
 const preview=S("div","v2-modal-preview v2-cover-drag-preview");
 const pic=S("img");pic.alt="Anteprima della copertina: trascina con il mouse per cambiare inquadratura";
 pic.draggable=false;preview.append(pic);body.append(preview);
 body.append(S("p","v2-cover-hint","Trascina la cover con il mouse per posizionarla, poi premi Applica modifiche."));
 const grid=S("div","v2-modal-grid");
 const x=field(grid,"Centro X (0–100)",state.coverFocusX,"number");
 const y=field(grid,"Centro Y (0–100)",state.coverFocusY,"number");
 const zoom=field(grid,"Zoom 100–250%",state.coverZoom,"number");
 const rot=field(grid,"Rotazione -180° / 180°",state.coverRotation,"number");body.append(grid);
 function draw(){
  const source=url.value.trim();
  pic.src=source===state.cover&&state.coverPreview?state.coverPreview:(previewMediaUrl(source)||source);
  pic.style.objectPosition=num(x.value,0,100,50)+"% "+num(y.value,0,100,50)+"%";
  pic.style.transform="scale("+num(zoom.value,100,250,100)/100+") rotate("+num(rot.value,-180,180,0)+"deg)";
 }
 [url,x,y,zoom,rot].forEach(c=>c.addEventListener("input",draw));
 let pointer=null;
 preview.addEventListener("pointerdown",event=>{
  if(event.button!==0)return;
  pointer={id:event.pointerId,px:event.clientX,py:event.clientY,x:num(x.value,0,100,50),y:num(y.value,0,100,50)};
  preview.setPointerCapture(event.pointerId);event.preventDefault();
 });
 preview.addEventListener("pointermove",event=>{
  if(!pointer||pointer.id!==event.pointerId)return;
  x.value=Math.round(num(pointer.x-(event.clientX-pointer.px)/Math.max(1,preview.clientWidth)*100,0,100,50));
  y.value=Math.round(num(pointer.y-(event.clientY-pointer.py)/Math.max(1,preview.clientHeight)*100,0,100,50));draw();
 });
 preview.addEventListener("pointerup",()=>pointer=null);
 preview.addEventListener("pointercancel",()=>pointer=null);
 draw();
 modal("Copertina · ritaglio e inquadratura",body,()=>{
  const newUrl=url.value.trim();
  if(newUrl!==state.cover)state.coverPreview="";
  state.cover=newUrl;state.coverFocusX=num(x.value,0,100,50);state.coverFocusY=num(y.value,0,100,50);
  state.coverZoom=num(zoom.value,100,250,100);state.coverRotation=num(rot.value,-180,180,0);
  syncCover();return true;
 });
}
function collect(){
 const text=id=>val(id),lines=id=>text(id).split("\n").map(v=>v.trim()).filter(Boolean);
 const title=(text("v2-title")||"Senza titolo").slice(0,220);
 const slug=state.newContent?(text("v2-slug")||slugify(title)):state.current.slug;
 return {slug,title,category:text("v2-category")||"news-tech",author:authorForCategory(text("v2-category")||"news-tech"),
  image:state.cover,cover_focus_x:state.coverFocusX,cover_focus_y:state.coverFocusY,
  cover_zoom:state.coverZoom,cover_rotation:state.coverRotation,
  body:state.body.map(block=>({...block})),
  studio_blocks:true,video_url:text("v2-video-url"),platform:text("v2-platform"),score:text("v2-score"),
  pros:lines("v2-pros"),cons:lines("v2-cons")};
}
async function uploadLocalAsset(value,slug){
 const source=String(value??"").trim();
 if(!/^data:/i.test(source))return value;
 const match=source.match(/^data:([^;,]+)(?:;[^,]*)*;base64,([\s\S]*)$/i);
 if(!match)throw Error("Immagine incorporata non riconosciuta: ricarica il file nel blocco interessato.");
 const mime=match[1].toLowerCase();
 const base64=match[2].replace(/\s/g,"").replace(/-/g,"+").replace(/_/g,"/");
 if(!base64||!/^[A-Za-z0-9+/]*={0,2}$/.test(base64))
  throw Error("Dati dell'immagine non validi: il contenuto originale è ancora conservato nella bozza.");
 const result=await api("upload",{slug,mime,base64});
 if(!result.url)throw Error("Il caricamento dell'immagine non ha restituito il percorso del file.");
 return result.url;
}
async function uploadRecordMedia(row){
 // Salvataggio e pubblicazione non dipendono dalla presenza o dal caricamento dei media.
 // Se un file locale non è trasferibile, viene omesso e il contenuto testuale prosegue.
 try{row.image=await uploadLocalAsset(row.image,row.slug)}catch(_){row.image=""}
 const normalized=[];
 for(const original of row.body){
  const block={...original};
  if(["image","audio","attachment"].includes(block.type)){
   const source=block.url||block.src||block.preview||block.image||block.file||"";
   if(!String(source).trim())continue;
   try{
    if(source)block.url=await uploadLocalAsset(source,row.slug);
    if(/^data:/i.test(String(block.url||"")))continue;
   }catch(_){continue}
   delete block.preview;delete block.src;delete block.image;delete block.file;
   if(!block.url)continue;
  }
  normalized.push(block);
 }
 row.body=normalized;
}
async function cancelDraft(){
 if(state.busy)return;
 const title=val("v2-title")||state.current?.title||"bozza senza titolo";
 const slug=state.newContent?(val("v2-slug")||slugify(title)):String(state.current?.slug||"");
 const confirmed=window.confirm("Vuoi cancellare la bozza «"+title+"»? Verranno eliminati il testo e i dati salvati automaticamente. Gli articoli già pubblicati non verranno cancellati.");
 if(!confirmed)return;
 state.busy=true;
 for(const id of ["v2-cancel-draft","v2-cancel-draft-bottom"])E(id).disabled=true;
 try{
  if(slug)await api("v2-draft-delete",{slug});
  const key=backupKey();
  try{localStorage.removeItem(key)}catch(_){}
  if(slug)delete state.drafts[slug];
  try{
   const draftKey="zazoomtek:studio-v2:local-drafts";
   if(Object.keys(state.drafts).length)localStorage.setItem(draftKey,JSON.stringify(state.drafts));
   else localStorage.removeItem(draftKey);
  }catch(e){throw Error("La bozza remota è stata eliminata, ma il salvataggio locale del browser non è stato aggiornato.")}
  state.restoreReady=false;
  state.current=null;state.newContent=false;state.newDraftId=null;state.body=[];
  state.cover="";state.coverPreview="";
  showHome();
  notify("Bozza «"+title+"» cancellata. Puoi creare un nuovo contenuto.");
 }catch(error){
  notify(error.message||"Impossibile cancellare la bozza. Il contenuto locale è stato conservato.",true);
 }finally{
  state.busy=false;
  for(const id of ["v2-cancel-draft","v2-cancel-draft-bottom"])E(id).disabled=false;
 }
}

async function save(mode){
 if(state.busy)return;
 applyEditorialFormat();const row=collect();
 if(!row.title||!row.slug){notify("Inserisci prima titolo e indirizzo del contenuto.",true);return}
 backupNow();
 if(mode==="draft"){
  state.busy=true;
  for(const id of ["v2-publish","v2-publish-bottom","v2-save-draft","v2-draft-bottom"])E(id).disabled=true;
  try{
   notify("Caricamento immagini e salvataggio della bozza su GitHub...");
   await uploadRecordMedia(row);
   const result=await api("v2-save",{mode:"draft",creating:state.newContent,record:row});
   state.cover=row.image;state.coverPreview="";state.body=row.body;
   const updatedAt=new Date().toISOString();
   state.drafts[row.slug]={record:row,kind:state.newContent?"new":"edit",updated_at:updatedAt};
   E("v2-autosave-status").textContent="Bozza salvata su GitHub · "+new Date(updatedAt).toLocaleTimeString("it-IT",{hour:"2-digit",minute:"2-digit"});
   backupNow();renderBlocks();renderList();
   notify(result.message||"Bozza salvata su GitHub senza pubblicare la pagina.");
  }catch(e){notify(e.message||"Salvataggio della bozza non riuscito. Il contenuto resta aperto nell'editor.",true)}
  finally{
   state.busy=false;
   for(const id of ["v2-publish","v2-publish-bottom","v2-save-draft","v2-draft-bottom"])E(id).disabled=false;
  }
  return;
 }
 state.busy=true;
 for(const id of ["v2-publish","v2-publish-bottom","v2-save-draft","v2-draft-bottom"])E(id).disabled=true;
 try{
  notify("Preparazione dei contenuti e salvataggio su main...");
  await uploadRecordMedia(row);
  const result=await api("v2-save",{mode:"publish",creating:state.newContent,record:row});
  state.cover=row.image;state.coverPreview="";state.body=row.body;
  if(state.newContent){try{localStorage.removeItem(backupKey())}catch(_){}}
  state.current={...(result.record||row),__queued:true};state.newContent=false;state.newDraftId=null;
  const index=state.rows.findIndex(item=>item.slug===row.slug);
  if(index>=0)state.rows[index]=state.current;else state.rows.unshift(state.current);
  delete state.drafts[row.slug];
  try{
   const draftKey="zazoomtek:studio-v2:local-drafts";
   if(Object.keys(state.drafts).length)localStorage.setItem(draftKey,JSON.stringify(state.drafts));
   else localStorage.removeItem(draftKey);
  }catch(_){}
  E("v2-autosave-status").textContent="Salvato su main · in attesa del primo slot editoriale disponibile.";
  renderList();notify(result.message||"Articolo salvato su main e inserito nella coda editoriale.");
  previewFinalArticle();
 }catch(e){notify(e.message||"Pubblicazione non riuscita. Il testo resta nella bozza locale.",true)}
 finally{
  state.busy=false;
  for(const id of ["v2-publish","v2-publish-bottom","v2-save-draft","v2-draft-bottom"])E(id).disabled=false;
 }
}
async function init(){
 try{
  const session=await api("session");
  const r=await fetch("/studio-v2/catalog.json",{cache:"no-store"});if(!r.ok)throw Error("Catalogo Studio V2 non disponibile");
  const catalog=(await r.json()).posts||[];
  const pending=await api("v2-pending");
  const remoteDrafts=await api("v2-drafts");
  const liveSlugs=new Set(catalog.map(item=>item.slug));
  const bySlug=new Map(catalog.map(item=>[item.slug,item]));
  for(const item of pending.posts||[])if(item?.slug)bySlug.set(item.slug,{...(bySlug.get(item.slug)||{}),...item,__queued:!liveSlugs.has(item.slug)});
  for(const [slug,override] of Object.entries(pending.overrides||{}))if(bySlug.has(slug))bySlug.set(slug,{...bySlug.get(slug),...override});
  state.rows=[...bySlug.values()];
  try{const saved=JSON.parse(localStorage.getItem("zazoomtek:studio-v2:local-drafts")||"{}");if(saved&&typeof saved==="object"&&!Array.isArray(saved))state.drafts=saved}catch(_){state.drafts={}}
  if(remoteDrafts.drafts&&typeof remoteDrafts.drafts==="object")state.drafts={...state.drafts,...remoteDrafts.drafts};
  E("v2-user").textContent="Account GitHub: "+(session.login||"amministratore");
  for(const [cat,label] of Object.entries(cats))E("v2-select-filter").add(new Option(label,cat));
  for(const [cat,label] of Object.entries(cats))E("v2-category").add(new Option(label,cat));
  E("v2-count-all").textContent=state.rows.length;
  E("v2-count-tech").textContent=state.rows.filter(x=>x.category==="news-tech").length;
  E("v2-count-gaming").textContent=state.rows.filter(x=>x.category==="news-gaming").length;
  E("v2-count-reviews").textContent=state.rows.filter(x=>String(x.category||"").startsWith("recensioni-")).length;
  E("v2-app").hidden=false;E("v2-auth").hidden=true;
  const params=new URLSearchParams(location.search);
  if(params.get("edit")){const row=state.rows.find(r=>r.slug===params.get("edit"));if(row)openExisting(row);else showHome()}
  else if(params.has("new"))startNew(params.get("draft")||null);else showHome();
 }catch(e){
  E("v2-auth").hidden=false;E("v2-app").hidden=true;
  const p=E("v2-auth").querySelector("p");
  if(p)p.textContent=e.message.includes("Sessione amministratore")?"Accedi allo Studio principale: al termine verrai riportato automaticamente qui.": "Studio 2 non disponibile: "+e.message;
 }
}
E("v2-home-nav").onclick=showHome;E("v2-back").onclick=showHome;E("v2-new-nav").onclick=startNew;E("v2-create-main").onclick=startNew;
E("v2-new-from-editor").onclick=()=>startNew();E("v2-new-from-editor-bottom").onclick=()=>startNew();
E("v2-append-block").onclick=()=>openMenu(state.body.length);
E("v2-search").oninput=renderList;E("v2-select-filter").onchange=()=>{state.filter="";renderList()};
for(const nav of document.querySelectorAll("[data-rail-filter]"))nav.addEventListener("click",()=>{
 state.filter=nav.dataset.railFilter;E("v2-select-filter").value=state.filter;
 document.querySelectorAll("[data-rail-filter]").forEach(x=>x.classList.toggle("on",x===nav));showHome();
});
for(const b of document.querySelectorAll("[data-kind]"))b.addEventListener("click",()=>addBlock(b.dataset.kind));
E("v2-menu-close").onclick=()=>E("v2-insert-menu").hidden=true;
E("v2-cover-add").onclick=editCover;E("v2-cover-change").onclick=()=>chooseFile(null);E("v2-cover-edit").onclick=editCover;
E("v2-cover-remove").onclick=()=>{state.cover="";state.coverPreview="";syncCover()};
E("v2-cover-sidebar").onclick=editCover;
E("v2-title").oninput=()=>{if(state.newContent)E("v2-slug").value=slugify(val("v2-title"));updateAutoCategory();syncArticleChrome({...state.current,...collect()});seoStatus()};
E("v2-category").addEventListener("change",()=>{state.categoryTouched=true;E("v2-author").value=authorForCategory(val("v2-category"));syncArticleChrome({...state.current,...collect()});scheduleBackup()});
for(const id of ["v2-category","v2-author","v2-platform","v2-score","v2-pros","v2-cons","v2-video-url"]) E(id).addEventListener("input",()=>syncArticleChrome({...state.current,...collect()}));
E("v2-modal-close").onclick=closeModal;E("v2-modal-cancel").onclick=closeModal;
E("v2-modal-apply").onclick=()=>{if(state.modalApply?.()!==false)closeModal()};
function previewFinalArticle(){
 // Mostra la stessa struttura editoriale che save("publish") prepara alla pubblicazione.
 applyEditorialFormat();
 showArticlePreview();
}
E("v2-preview-top").onclick=previewFinalArticle;E("v2-preview-bottom").onclick=previewFinalArticle;
E("v2-close-preview").onclick=closeArticlePreview;
E("v2-article-preview").addEventListener("click",e=>{if(e.target===E("v2-article-preview"))closeArticlePreview()});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!E("v2-article-preview").hidden)closeArticlePreview()});
E("v2-editor").addEventListener("input",scheduleBackup);
E("v2-editor").addEventListener("change",scheduleBackup);
window.addEventListener("beforeunload",backupNow);
window.addEventListener("pagehide",backupNow);
document.addEventListener("visibilitychange",()=>{if(document.hidden)backupNow()});
E("v2-save-draft").onclick=()=>save("draft");E("v2-draft-bottom").onclick=()=>save("draft");
E("v2-cancel-draft").onclick=cancelDraft;E("v2-cancel-draft-bottom").onclick=cancelDraft;
E("v2-publish").onclick=()=>save("publish");E("v2-publish-bottom").onclick=()=>save("publish");

// Show the contextual '+' only while editing the position selected with the mouse.
document.addEventListener("pointerdown",event=>{
 const target=event.target;
 if(!target.closest?.("#v2-blocks .v2-rich-text,.v2-floating-plus,#v2-insert-menu,#v2-modal"))
  hideContext();
});
window.addEventListener("scroll",()=>hideContext(),{passive:true});

init();
})();