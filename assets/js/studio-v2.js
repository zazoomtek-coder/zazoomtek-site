"use strict";
(()=>{
const E=id=>document.getElementById(id),S=(tag,cls,text)=>{let e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e};
const cats={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra"};
let state={rows:[],drafts:{},current:null,body:[],mode:"home",filter:"",newContent:false,busy:false,cover:"",coverPreview:"",context:null,contextBtn:null,coverFocusX:50,coverFocusY:50,coverZoom:100,coverRotation:0,modalApply:null,at:0};
const val=id=>E(id).value.trim(),num=(v,lo,hi,def)=>Math.min(hi,Math.max(lo,Number.isFinite(+v)?+v:def));
const slugify=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,135);
function notify(msg,error=false){const t=E("v2-toast");t.hidden=false;t.textContent=msg;t.classList.toggle("error",error)}
async function api(endpoint,data){
 const opt={credentials:"same-origin",cache:"no-store",redirect:"manual",
  headers:{"Accept":"application/json"}};
 if(data!==undefined){opt.method="POST";opt.headers["Content-Type"]="application/json";opt.body=JSON.stringify(data)}
 let r;
 try{r=await fetch("/api/studio/"+endpoint,opt)}
 catch(err){throw Error("Connessione a Studio interrotta. Le modifiche sono conservate nella bozza locale.")}
 const contentType=(r.headers.get("Content-Type")||"").toLowerCase();
 if(!contentType.includes("application/json")){
  const status=r.type==="opaqueredirect"?"reindirizzamento":String(r.status||"sconosciuto");
  throw Error("Cloudflare non ha restituito la risposta JSON di Studio (HTTP "+status+
   "). Nessun salvataggio confermato. Il testo resta nella bozza locale: controlla l'accesso in una nuova scheda.");
 }
 let j;
 try{j=await r.json()}catch(_){throw Error("Risposta di Studio non valida. Nessun salvataggio confermato; il testo resta nella bozza locale.")}
 if(!r.ok||j.ok!==true){
  if(r.status===401||j.code==="UNAUTHENTICATED"||j.code==="AUTH_REQUIRED")
   throw Error("Accesso amministratore scaduto o non riconosciuto. La bozza locale è protetta: apri Studio in una nuova scheda, accedi e riprova.");
  if(r.status===403)throw Error(j.error||"Permesso negato. La bozza locale resta disponibile.");
  throw Error(j.error||"Operazione non autorizzata (HTTP "+r.status+").");
 }
 return j;
}
function editorFields(row){
 const fields={"v2-title":row.title||"","v2-slug":row.slug||"","v2-author":row.author||"Redazione ZazoomTek",
 "v2-video-url":row.video_url||"","v2-platform":row.platform||"","v2-score":row.score??"",
 "v2-pros":Array.isArray(row.pros)?row.pros.join("\n"):"","v2-cons":Array.isArray(row.cons)?row.cons.join("\n"):""};
 for(const [id,v] of Object.entries(fields))E(id).value=v;
 E("v2-category").value=row.category||"news-tech";
 E("v2-slug").readOnly=!state.newContent;
 state.cover=row.image||"";state.coverPreview="";
 state.coverFocusX=num(row.cover_focus_x,0,100,50);state.coverFocusY=num(row.cover_focus_y,0,100,50);
 state.coverZoom=num(row.cover_zoom,100,250,100);state.coverRotation=num(row.cover_rotation,-180,180,0);
 state.body=convertBody(row);
 syncCover();renderBlocks();seoStatus();
}

function convertBody(row){
 // The server supplies the *same editorial paragraphs, red-bar H2s and order*
 // as the live article. Old Studio drafts are preserved, never discarded.
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
 return (Array.isArray(parts)?parts:[]).map(x=>typeof x==="string"?x:String(x?.text||"")).join(" ")
  .replace(/\s+/g," ").trim();
}


/* Article BODY only: the Github PAT remains exclusively in the encrypted HttpOnly
   session cookie. This local recovery copy is not an authentication mechanism. */
const BACKUP_PREFIX="zazoomtek:studio-v2:article:";
let backupTimer=0;
function backupKey(){
 return BACKUP_PREFIX+(state.newContent?"new":String(state.current?.slug||"new"));
}
function backupNow(){
 if(state.mode!=="editor"||!state.restoreReady)return;
 try{
  const payload={record:collect(),updated_at:Date.now()};
  localStorage.setItem(backupKey(),JSON.stringify(payload));
  const label=E("v2-autosave-status");
  if(label)label.textContent="Testo protetto sul dispositivo · "+new Date(payload.updated_at).toLocaleTimeString("it-IT",{hour:"2-digit",minute:"2-digit",second:"2-digit"});
 }catch(e){
  const label=E("v2-autosave-status");
  if(label)label.textContent="Salvataggio automatico locale non disponibile: premi Salva bozza.";
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
  const serverTime=Date.parse(server?.updated_at||"")||0;
  if(cached.updated_at < serverTime)return;
  // Never inherit the slug from another published article.
  const copy={...cached.record,slug:state.newContent?cached.record.slug:state.current.slug};
  editorFields(copy);
  notify("Testo recuperato dal salvataggio automatico del browser. Premi Salva bozza per conservarlo anche su GitHub.");
 }catch(e){}
}
function sentenceParts(text,limit=370){
 const pieces=String(text||"").replace(/\s+/g," ").trim().split(/(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Ý0-9«“"'])/u);
 const output=[];let current="";
 for(let piece of pieces){
  if(!piece)continue;
  if((current?current.length+1:0)+piece.length<=limit){current+=(current?" ":"")+piece;continue}
  if(current){output.push(current);current=""}
  while(piece.length>limit){
   let cut=piece.lastIndexOf(" ",limit);
   if(cut<160)cut=piece.indexOf(" ",limit);
   if(cut<0)break;
   output.push(piece.slice(0,cut).trim());piece=piece.slice(cut+1).trim();
  }
  current=piece;
 }
 if(current)output.push(current);
 return output;
}
function articleHeading(paragraph,used){
 const p=String(paragraph).toLowerCase();
 const choices=[
  [/\b(prezzo|prezzi|euro|sconto|sconti)\b|€/i,"Prezzi e offerte"],
  [/\b(disponibile|disponibilità|uscita|arriva|debutta|lancio)\b/i,"Uscita e disponibilità"],
  [/\b(gameplay|giocatori|missioni|combattimento|modalità)\b/i,"Gameplay e contenuti"],
  [/\b(storia|avventura|personaggi|ambientazione)\b/i,"Storia e ambientazione"],
  [/\b(aggiornamento|espansione|dlc|patch|novità)\b/i,"Contenuti e novità"],
  [/\b(funzioni|funzionalità|software|intelligenza artificiale|sensori)\b/i,"Funzioni e tecnologia"],
  [/\b(design|materiali|schermo|display|hardware)\b/i,"Design e caratteristiche"],
  [/\b(prestazioni|autonomia|batteria|velocità)\b/i,"Prestazioni e caratteristiche"]
 ];
 for(const [re,name] of choices)if(re.test(p)&&!used.has(name.toLowerCase()))return name;
 for(const name of ["Tutti i dettagli","Gli elementi principali","Altri dettagli","Il quadro completo","Ulteriori informazioni"])
  if(!used.has(name.toLowerCase()))return name;
 return "Approfondimento";
}
function formattedTextBlocks(input,category,title){
 const raw=String(input||"").replace(/\r\n?/g,"\n").trim();
 if(!raw)return [{type:"paragraph",text:""}];
 const chunks=raw.split(/\n\s*\n+/).map(x=>x.trim()).filter(Boolean);
 // A paste with a separate line per editorial paragraph, but no blank lines.
 if(chunks.length===1&&raw.split("\n").filter(x=>x.trim()).length>=4){
  const rows=raw.split("\n").map(x=>x.trim()).filter(Boolean);
  chunks.splice(0,1,...rows);
 }
 const tokens=[];
 for(let i=0;i<chunks.length;i++){
  let piece=chunks[i],heading="";
  if(/^#{1,3}\s+\S/.test(piece))heading=piece.replace(/^#{1,3}\s+/,"");
  else if(/^\*\*[^*\n]{3,100}\*\*$/.test(piece))heading=piece.slice(2,-2);
  else if(piece.indexOf("\n")<0&&piece.length<=80&&piece.split(/\s+/).length<=12
       &&i+1<chunks.length&&chunks[i+1].length>95
       &&/^[A-ZÀ-Ý]/.test(piece)&&!/[.!?;,]$/.test(piece))
   heading=piece;
  if(heading){
   if(i===0&&(heading.toLowerCase()===String(title||"").toLowerCase()||/^news (tech|gaming):/i.test(heading)))continue;
   tokens.push({type:"heading",text:heading});continue;
  }
  if(i===0&&piece.split("\n").length>1){
   const lines=piece.split("\n");
   if(lines[0].trim().replace(/^#\s*/,"").toLowerCase()===String(title||"").trim().toLowerCase())
    piece=lines.slice(1).join("\n").trim();
  }
  for(const part of sentenceParts(piece))if(part)tokens.push({type:"paragraph",text:part});
 }
 if(!tokens.length)return [{type:"paragraph",text:""}];
 const output=[],explicit=new Set(tokens.filter(x=>x.type==="heading").map(x=>x.text.toLowerCase()));
 let n=0,lead=0,hadHeading=false;
 const review=String(category||"").startsWith("recensioni-");
 const outline=category==="recensioni-gaming"
  ?["Introduzione","Storia","Gameplay","Aspetto tecnico","Conclusioni"]
  :["Introduzione","Materiali e Design","Hardware e Prestazioni","Esperienza d'uso quotidiana","Conclusioni"];
 const explicitHeadings=tokens.some(x=>x.type==="heading");
 for(const token of tokens){
  if(token.type==="heading"){
   const label=token.text.trim().toLowerCase();
   if(!output.some(x=>x.type==="heading"&&x.text.toLowerCase()===label)){
    output.push(token);hadHeading=true;n=0;explicit.add(label)
   }
   continue;
  }
  if(review&&!explicitHeadings){
   if(!hadHeading||n>=2){
    const name=outline[Math.min(4,Math.floor(lead/2))];
    if(!output.some(x=>x.type==="heading"&&x.text===name))output.push({type:"heading",text:name});
    hadHeading=true;n=0;
   }
  }else if((!hadHeading&&lead>=2)||(hadHeading&&n>=2)){
   const name=articleHeading(token.text,explicit);explicit.add(name.toLowerCase());
   output.push({type:"heading",text:name});hadHeading=true;n=0;
  }
  output.push(token);n++;lead++;
 }
 return output;
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
 const ok=value.startsWith("/assets/uploads/")&&
  ["jpg","jpeg","png","webp","mp3","m4a","wav","pdf","txt"].includes(value.split(".").pop());
 return ok?"/api/studio/v2-asset?path="+encodeURIComponent(value.slice(1)):value;
}
function showArticlePreview(savedRecord=null){
 const record={...collect(),...(savedRecord||{})};
 const article=E("v2-preview-article-content");article.replaceChildren();
 const review=String(record.category||"").startsWith("recensioni-");
 article.className="v2-preview-article article story-article "+(review?"review-article":"news-article");
 if(review)article.append(S("div","review-topline",cats[record.category]||"Recensione"));
 article.append(S("h1","",record.title||"Titolo dell'articolo"));
 const meta=S("div","story-meta");
 meta.append(S("span","story-meta-author","Autore: "+(record.author||"Redazione ZazoomTek")),
  S("span","story-meta-date","Data: "+(record.date||new Date().toLocaleDateString("it-IT"))),
  S("span","story-meta-category","Categoria: "+(cats[record.category]||"Articolo")));
 article.append(meta);
 if(review&&record.platform)article.append(S("p","review-equipment","Piattaforma o dispositivo: "+record.platform));
 if(record.image||state.coverPreview){
  const cover=S("img","v2-preview-cover");cover.alt=record.title||"Copertina";
  cover.src=state.coverPreview||previewMediaUrl(record.image);cover.style.objectPosition=(record.cover_focus_x??state.coverFocusX)+"% "+(record.cover_focus_y??state.coverFocusY)+"%";
  cover.style.transform="scale("+Number(record.cover_zoom??state.coverZoom)/100+") rotate("+Number(record.cover_rotation??state.coverRotation)+"deg)";
  const wrapper=S("div","v2-preview-cover-frame");wrapper.append(cover);article.append(wrapper);
 }
 const text=S("div","article-text");
 const blocks=Array.isArray(record.body)?record.body:editorialBodyForDisplay();
 if(!blocks.some(b=>b.type==="heading"))text.append(S("h2","","Approfondimento"));
 for(let i=0;i<blocks.length;i++){
  const block=blocks[i],typ=block.type,t=String(block.text||"");
  if(["paragraph","heading","quote"].includes(typ)){
   const node=S(typ==="heading"?"h2":typ==="quote"?"blockquote":"p",typ==="quote"?"studio-content-quote":"");
   if(typ==="heading")node.textContent=t;else node.append(richContent(t));
   text.append(node);
  }else if(typ==="image"){
   const figure=S("figure","story-figure studio-content-image studio-align-"+(block.align||"center"));
   const crop=S("div","studio-image-crop"),im=S("img");
   im.alt=block.alt||record.title||"";im.src=state.body[i]?.preview||block.preview||previewMediaUrl(block.url);
   im.style.objectPosition=(block.focus_x??50)+"% "+(block.focus_y??50)+"%";
   im.style.transform="scale("+Number(block.zoom??100)/100+") rotate("+Number(block.rotation??0)+"deg)";
   crop.append(im);figure.append(crop);
   if(block.caption)figure.append(S("figcaption","",block.caption));
   text.append(figure);
  }else if(typ==="video"){
   const id=String(block.url||"").match(/(?:youtu\.be\/|[?&]v=|\/embed\/|\/shorts\/)([a-zA-Z0-9_-]{11})/)?.[1];
   if(id){const box=S("div","player studio-content-video"),thumb=S("img");thumb.src="https://i.ytimg.com/vi/"+id+"/hqdefault.jpg";thumb.alt="Anteprima video YouTube";box.append(thumb,S("p","v2-preview-media","▶ Riproduci video"));text.append(box)}
  }else if(typ==="button"){
   const p=S("p","studio-content-action"),link=S("a","v2-preview-action",t||"Apri collegamento");link.href=block.url||"#";p.append(link);text.append(p);
  }else if(typ==="divider")text.append(S("hr","studio-content-divider"));
  else if(typ==="poll"){
   const poll=S("section","studio-content-poll");poll.append(S("h3","",t));
   const ul=S("ul");(block.options||[]).forEach(x=>ul.append(S("li","",x)));poll.append(ul,S("p","studio-poll-note","Sondaggio editoriale — raccolta voti non attivata."));text.append(poll);
  }else if(typ==="audio"){
   const p=S("div","studio-content-audio"),audio=S("audio");audio.controls=true;audio.preload="none";audio.src=block.url||"";p.append(audio);if(block.caption)p.append(S("p","",block.caption));text.append(p);
  }else if(typ==="attachment"){
   const p=S("p","studio-content-attachment"),a=S("a","",t||"Apri allegato");a.href=block.url||"#";p.append(a);text.append(p);
  }
 }
 article.append(text);
 if(review){
  const block=S("section","review-verdict"),header=S("div","verdict-heading");
  header.append(S("h2","","Voto finale"),S("strong","verdict-score",record.score!==null&&record.score!==undefined&&record.score!==""?String(record.score).replace(".",",")+"/10":"Voto non disponibile"));
  block.append(header);
  const grid=S("div","verdict-grid");
  for(const [label,values,cls] of [["Pro",record.pros,"verdict-pro"],["Contro",record.cons,"verdict-con"]]){
   const side=S("div",cls);side.append(S("h3","",label));
   const arr=Array.isArray(values)?values:[];if(arr.length){const ul=S("ul");arr.forEach(v=>ul.append(S("li","",v)));side.append(ul)}
   else side.append(S("p","review-data-missing","Nessun elemento verificato nel testo attualmente disponibile."));
   grid.append(side);
  }
  block.append(grid);article.append(block);
 }
 backupNow();
 E("v2-article-preview").hidden=false;
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
function showHome(){
 backupNow();
 hideContext();
 state.mode="home";E("v2-home").hidden=false;E("v2-editor").hidden=true;E("v2-back").hidden=true;
 E("v2-crumb").textContent="Studio / Contenuti";E("v2-home-nav").classList.add("on");
 renderList();history.replaceState({}, "", "/studio-v2/");
}
function showEditor(row,newContent){
 backupNow(); // Protect previous article before replacing the editor contents.
 state.current=row;state.newContent=!!newContent;state.mode="editor";state.restoreReady=false;
 E("v2-home").hidden=true;E("v2-editor").hidden=false;E("v2-back").hidden=false;
 E("v2-home-nav").classList.remove("on");
 E("v2-editor-heading").textContent=newContent?"Crea un nuovo contenuto":"Modifica il contenuto";
 E("v2-editor-note").textContent=newContent?"Scrivi e pubblica quando vuoi.":"Puoi cambiare tutto, senza aprire altri pannelli.";
 E("v2-crumb").textContent="Studio / "+(newContent?"Nuovo contenuto":"Modifica");
 editorFields(row);
 restoreBackup();state.restoreReady=true;
 history.replaceState({}, "", "/studio-v2/"+(newContent?"?new=1":"?edit="+encodeURIComponent(row.slug)));
 window.scrollTo(0,0);
}
function startNew(){showEditor({title:"",slug:"",category:"news-tech",author:"Redazione ZazoomTek",body:[{type:"paragraph",text:""}]},true)}
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
  const img=S("img","v2-list-cover");img.loading="lazy";img.alt="";img.src=row.image||"";item.append(img);
  const meta=S("div"),title=S("div","v2-list-title",row.title||"Senza titolo");
  const desc=S("div","v2-list-meta");
  desc.append(S("b","",cats[row.category]||"Articolo"),S("span","", " · "+(row.date||"")+" · "+(state.drafts[row.slug]?"Bozza disponibile":row.__queued?"In coda · non online":"Pubblicato")));
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
 const editorData=(draft&&sameAsOriginal&&originalBlocks)?{...content,body:originalBlocks}:content;
 if(!draft&&originalBlocks)editorData.editor_blocks=originalBlocks;
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
 state.at=at;E("v2-insert-menu").hidden=false;
}
function addBlock(kind){
 E("v2-insert-menu").hidden=true;
 if(kind==="link"){inlineLink();return}
 state.at=insertPosition();
 const block={type:kind,text:"",url:"",caption:"",alt:"",align:"center",focus_x:50,focus_y:50,zoom:100,rotation:0};
 if(kind==="divider")block.text="—";
 if(kind==="poll")block.options=["Opzione 1","Opzione 2"];
 state.body.splice(state.at,0,block);renderBlocks();
 if(["image","audio","attachment","video","button","poll"].includes(kind))editMedia(block);
}
function drawField(wrapper,text,initial,onChange,textarea=false){
 const input=document.createElement(textarea?"textarea":"input");
 if(!textarea)input.type="text";
 input.className=textarea?"v2-block-text":"v2-media-input";input.placeholder=text;input.value=initial||"";
 if(textarea)input.rows=2;
 input.addEventListener("input",()=>{onChange(input.value);seoStatus()});
 wrapper.append(input);return input;
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
function safePaste(e){
 e.preventDefault();
 const raw=e.clipboardData?.getData("text/plain")||"";
 const idx=Number(e.currentTarget.closest("[data-index]")?.dataset.index);
 const current=state.body[idx];
 if(current&&current.type==="paragraph"&&!String(current.text||"").trim()
    &&(raw.includes("\n")||raw.length>370)){
  const blocks=formattedTextBlocks(raw,val("v2-category"),val("v2-title"));
  state.body.splice(idx,1,...blocks);renderBlocks();seoStatus();scheduleBackup();
  notify("Testo inserito e impaginato secondo il modello editoriale ZazoomTek.");
  return;
 }
 const sel=window.getSelection();if(!sel?.rangeCount)return;
 const r=sel.getRangeAt(0),node=document.createTextNode(raw);
 r.deleteContents();r.insertNode(node);r.setStartAfter(node);r.collapse(true);
 sel.removeAllRanges();sel.addRange(r);e.currentTarget.dispatchEvent(new Event("input",{bubbles:true}));
}
function hideContext(){if(state.contextBtn)state.contextBtn.hidden=true}
function cursorHere(i,field){
 const sel=window.getSelection();
 if(!sel?.rangeCount||!field.contains(sel.anchorNode))return;
 const r=sel.getRangeAt(0).cloneRange();
 state.context={index:i,field,range:r};
 if(!state.contextBtn){
  const plus=S("button","v2-floating-plus","＋");plus.type="button";
  plus.title="Inserisci contenuto qui";plus.setAttribute("aria-label","Inserisci qui");
  plus.addEventListener("mousedown",e=>e.preventDefault());
  plus.addEventListener("click",()=>{hideContext();E("v2-insert-menu").hidden=false});
  document.body.append(plus);state.contextBtn=plus;
 }
 const fieldRect=field.getBoundingClientRect(),caret=r.getBoundingClientRect();
 const y=caret.height?caret.top:fieldRect.top,plus=state.contextBtn;
 plus.style.left=Math.max(6,fieldRect.left-42)+"px";
 plus.style.top=Math.max(8,Math.min(innerHeight-45,y-3))+"px";plus.hidden=false;
}
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
  const row=S("div","v2-editorial-row");row.dataset.index=i;
  if(["paragraph","heading","quote"].includes(b.type)){
   const tag=b.type==="heading"?"h2":b.type==="quote"?"blockquote":"p";
   const editable=S(tag,"v2-rich-text");
   editable.contentEditable="true";editable.spellcheck=true;
   editable.setAttribute("role","textbox");
   editable.setAttribute("aria-label",b.type==="heading"?"Modifica sottotitolo":"Modifica il testo");
   editable.dataset.placeholder=b.type==="heading"?"Scrivi un sottotitolo...":"Clicca per scrivere...";
   editable.append(richContent(b.text||""));
   editable.addEventListener("input",()=>{b.text=richValue(editable).trim();seoStatus();scheduleBackup()});
   editable.addEventListener("paste",safePaste);
   for(const event of ["focus","click","keyup","mouseup"])editable.addEventListener(event,()=>cursorHere(i,editable));
   row.append(editable);
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
   else if(b.type==="audio"){
    if(b.url&&!b.preview){const player=S("audio");player.controls=true;player.preload="none";player.src=b.url;card.append(player)}
    card.append(S("p","",b.text||"Audio"));
   }else card.append(S("span","v2-action-example",b.text||"Allegato"));
   const tools=S("div","v2-media-hover-tools");
   if(b.type!=="divider")tools.append(actionButton("Modifica",()=>editMedia(b)));
   if(b.type==="image")tools.append(actionButton("Sostituisci",()=>chooseFile(b)));
   tools.append(actionButton("↑",()=>moveBlock(i,-1)));
   tools.append(actionButton("↓",()=>moveBlock(i,1)));
   tools.append(actionButton("Rimuovi",()=>{state.body.splice(i,1);renderBlocks();seoStatus()}));
   card.append(tools);row.append(card);
  }
  host.append(row);
 });
 scheduleBackup();
}

function actionButton(text,callback){
 const b=S("button","",text);b.type="button";b.addEventListener("click",callback);return b;
}

async function chooseFile(target){
 const chooser=document.createElement("input");
 chooser.type="file";
 chooser.accept=target?.type==="audio"?"audio/mpeg,audio/mp4,audio/wav":
  target?.type==="attachment"?"application/pdf,text/plain":"image/jpeg,image/png,image/webp";
 chooser.addEventListener("change",()=>{
  const file=chooser.files?.[0];if(!file)return;
  if(file.size>5000000){notify("Il file supera 5 MB.",true);return}
  const reader=new FileReader();
  reader.onload=async()=>{
   const preview=typeof reader.result==="string"?reader.result:"";
   const beforeCover=state.cover,oldPreview=state.coverPreview;
   if(!target){state.coverPreview=preview;syncCover()}
   try{
    notify("Anteprima immediata disponibile. Caricamento file su GitHub...");
    const result=await api("upload",{
     slug:val("v2-slug")||slugify(val("v2-title"))||"contenuto",
     mime:file.type,base64:preview
    });
    if(target){
     target.url=result.url;target.text=target.text||file.name;
     // Pending deploy: keep this temporary local preview until the page reloads.
     target.preview=preview;
     renderBlocks();
    }else{
     state.cover=result.url;state.coverPreview=preview;syncCover();
    }
    notify("Copertina caricata. Si vede subito qui; sul sito sarà disponibile dopo il deploy. Salva in bozza o pubblica.");
   }catch(e){
    if(!target){state.cover=beforeCover;state.coverPreview=oldPreview;syncCover()}
    notify("Caricamento non riuscito: "+e.message,true);
   }
  };
  reader.onerror=()=>notify("Non riesco a leggere questo file.",true);
  reader.readAsDataURL(file);
 });
 chooser.click();
}

function editMedia(block){
 const body=S("div"),kind=block.type,initial={...block},change={...block};
 const u=["image","video","audio","button","attachment"].includes(kind)?field(body,kind==="button"?"Collegamento HTTPS":"URL o percorso del file",block.url||""):null;
 const t=["button","poll","audio","attachment"].includes(kind)?field(body,kind==="poll"?"Domanda":"Titolo / etichetta",block.text||""):null;
 const cap=["image","video","audio"].includes(kind)?field(body,"Didascalia (facoltativa)",block.caption||""):null;
 const alt=kind==="image"?field(body,"Descrizione immagine per Google",block.alt||""):null;
 const options=kind==="poll"?field(body,"Opzioni del sondaggio (una per riga)",(block.options||[]).join("\n"),"textarea"):null;
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
 modal(({image:"Modifica immagine",video:"Inserisci video YouTube",audio:"Aggiungi audio",button:"Modifica pulsante e link",attachment:"Allegato",poll:"Sondaggio"})[kind],body,()=>{
  if(u)block.url=u.value.trim();if(t)block.text=t.value.trim();if(cap)block.caption=cap.value.trim();if(alt)block.alt=alt.value.trim();
  if(options)block.options=options.value.split("\n").map(v=>v.trim()).filter(Boolean).slice(0,8);
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
 const upload=actionButton("Carica copertina dal PC",async()=>{
  closeModal();await chooseFile(null);
 });upload.className="v2-soft";body.append(upload);
 const preview=S("div","v2-modal-preview");
 const pic=S("img");preview.append(pic);body.append(preview);
 const grid=S("div","v2-modal-grid");
 const x=field(grid,"Centro X (0–100)",state.coverFocusX,"number");
 const y=field(grid,"Centro Y (0–100)",state.coverFocusY,"number");
 const zoom=field(grid,"Zoom 100–250%",state.coverZoom,"number");
 const rot=field(grid,"Rotazione -180° / 180°",state.coverRotation,"number");body.append(grid);
 function draw(){pic.src=url.value;pic.style.objectPosition=num(x.value,0,100,50)+"% "+num(y.value,0,100,50)+"%";pic.style.transform="scale("+num(zoom.value,100,250,100)/100+") rotate("+num(rot.value,-180,180,0)+"deg)"}
 [url,x,y,zoom,rot].forEach(c=>c.addEventListener("input",draw));draw();
 modal("Copertina · ritaglio e inquadratura",body,()=>{
  state.cover=url.value.trim();state.coverPreview="";state.coverFocusX=num(x.value,0,100,50);state.coverFocusY=num(y.value,0,100,50);
  state.coverZoom=num(zoom.value,100,250,100);state.coverRotation=num(rot.value,-180,180,0);syncCover();return true;
 });
}
function collect(){
 const text=id=>val(id),lines=id=>text(id).split("\n").map(v=>v.trim()).filter(Boolean);
 return {slug:state.newContent?(text("v2-slug")||slugify(text("v2-title"))):state.current.slug,
  title:text("v2-title"),category:text("v2-category"),author:text("v2-author"),
  image:state.cover,cover_focus_x:state.coverFocusX,cover_focus_y:state.coverFocusY,
  cover_zoom:state.coverZoom,cover_rotation:state.coverRotation,body:state.body,
  video_url:text("v2-video-url"),platform:text("v2-platform"),score:text("v2-score"),
  pros:lines("v2-pros"),cons:lines("v2-cons")};
}
async function save(mode){
 if(state.busy)return;
 state.busy=true;
 const buttons=[E("v2-save-draft"),E("v2-publish"),E("v2-draft-bottom"),E("v2-publish-bottom"),E("v2-preview-top"),E("v2-preview-bottom")];
 buttons.forEach(b=>b.disabled=true);
 try{
  applyEditorialFormat();
  const row=collect();
  backupNow();
  if(!row.title||!row.slug){notify("Inserisci prima titolo e indirizzo del contenuto.",true);return}
  const response=await api("v2-save",{mode,record:row,creating:state.newContent});
  notify(mode==="draft"?"Bozza salvata: nessuna modifica al sito.":"Contenuto accodato: pubblicazione al prossimo slot editoriale.");
  if(mode==="draft"){
   state.drafts[row.slug]={record:row,kind:state.newContent?"new":"edit",updated_at:new Date().toISOString()};
   E("v2-autosave-status").textContent="Bozza salvata anche su GitHub. Il sito pubblico non è stato modificato.";
  }else{
   try{localStorage.removeItem(backupKey())}catch(e){}
   E("v2-autosave-status").textContent="In coda per le 12:30 o le 19:30. Questa è l’anteprima della versione salvata; il sito online non cambia ora.";
   delete state.drafts[row.slug];
   E("v2-public-link").hidden=true; // Solo dopo la pubblicazione programmata.
   state.current={...(response.record||{}),...row,__queued:true};state.newContent=false;
   E("v2-slug").readOnly=true;
   state.rows=[state.current,...state.rows.filter(x=>x.slug!==row.slug)];
   showArticlePreview(state.current);
  }
 }catch(e){
  backupNow();
  notify(e.message,true);
  const label=E("v2-autosave-status");
  if(label)label.textContent="Pubblicazione non confermata. Il testo originale è protetto nella bozza locale.";
 }
 finally{state.busy=false;buttons.forEach(b=>b.disabled=false)}
}
async function init(){
 try{
  const session=await api("session");
  E("v2-user").textContent="GitHub · "+session.login;
  const r=await fetch("/studio-v2/catalog.json",{cache:"no-store"});
  if(!r.ok)throw Error("Catalogo Studio V2 non disponibile");
  state.rows=(await r.json()).posts||[];
  // Aggiorna la lista con articoli/modifiche confermati sul branch editoriale.
  try{
   const pending=await api("v2-pending");
   const changes=pending.overrides||{};
   state.rows=state.rows.map(x=>{
    const queued=changes[x.slug];
    if(!queued)return x;
    const same=queued.title===x.title&&queued.image===x.image&&JSON.stringify(queued.body||[])===JSON.stringify(x.body||[]);
    const alreadyReleased=x.updated_at&&queued.updated_at&&Date.parse(x.updated_at)>=Date.parse(queued.updated_at);
    return same||alreadyReleased?x:{...x,...queued,__queued:true};
   });
   for(const r of pending.posts||[]){
    if(!state.rows.some(x=>x.slug===r.slug))state.rows.unshift({...r,__queued:true});
   }
  }catch(e){notify("Coda Studio non disponibile: "+e.message,true)}
  try{const drafts=await api("v2-drafts");state.drafts=drafts.drafts||{}}catch(e){notify("Bozze non disponibili: "+e.message,true)}
  for(const [cat,label] of Object.entries(cats))E("v2-select-filter").add(new Option(label,cat));
  for(const [cat,label] of Object.entries(cats))E("v2-category").add(new Option(label,cat));
  E("v2-count-all").textContent=state.rows.length;
  E("v2-count-tech").textContent=state.rows.filter(x=>x.category==="news-tech").length;
  E("v2-count-gaming").textContent=state.rows.filter(x=>x.category==="news-gaming").length;
  E("v2-count-reviews").textContent=state.rows.filter(x=>x.category.startsWith("recensioni-")).length;
  E("v2-app").hidden=false;
  const params=new URLSearchParams(location.search);
  if(params.get("edit")){
   const row=state.rows.find(r=>r.slug===params.get("edit"));
   if(row)openExisting(row);else showHome();
  }else if(params.has("new"))startNew();else showHome();
 }catch(e){E("v2-auth").hidden=false;E("v2-app").hidden=true}
}
E("v2-home-nav").onclick=showHome;E("v2-back").onclick=showHome;E("v2-new-nav").onclick=startNew;E("v2-create-main").onclick=startNew;
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
E("v2-title").oninput=()=>{if(state.newContent)E("v2-slug").value=slugify(val("v2-title"));seoStatus()};
E("v2-modal-close").onclick=closeModal;E("v2-modal-cancel").onclick=closeModal;
E("v2-modal-apply").onclick=()=>{if(state.modalApply?.()!==false)closeModal()};
E("v2-preview-top").onclick=showArticlePreview;E("v2-preview-bottom").onclick=showArticlePreview;
E("v2-close-preview").onclick=closeArticlePreview;
E("v2-article-preview").addEventListener("click",e=>{if(e.target===E("v2-article-preview"))closeArticlePreview()});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!E("v2-article-preview").hidden)closeArticlePreview()});
E("v2-editor").addEventListener("input",scheduleBackup);
E("v2-editor").addEventListener("change",scheduleBackup);
window.addEventListener("beforeunload",backupNow);
window.addEventListener("pagehide",backupNow);
document.addEventListener("visibilitychange",()=>{if(document.hidden)backupNow()});
E("v2-save-draft").onclick=()=>save("draft");E("v2-draft-bottom").onclick=()=>save("draft");
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