"use strict";
(()=>{
const E=id=>document.getElementById(id),S=(tag,cls,text)=>{let e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e};
const cats={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra"};
let state={rows:[],drafts:{},current:null,body:[],mode:"home",filter:"",newContent:false,busy:false,cover:"",coverPreview:"",context:null,contextBtn:null,coverFocusX:50,coverFocusY:50,coverZoom:100,coverRotation:0,modalApply:null,at:0};
const val=id=>E(id).value.trim(),num=(v,lo,hi,def)=>Math.min(hi,Math.max(lo,Number.isFinite(+v)?+v:def));
const slugify=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,135);
function notify(msg,error=false){const t=E("v2-toast");t.hidden=false;t.textContent=msg;t.classList.toggle("error",error)}
async function api(endpoint,data){
 const opt={credentials:"same-origin",cache:"no-store",redirect:"manual"};
 if(data!==undefined){opt.method="POST";opt.headers={"Content-Type":"application/json"};opt.body=JSON.stringify(data)}
 const r=await fetch("/api/studio/"+endpoint,opt);
 if(!(r.headers.get("Content-Type")||"").includes("application/json"))throw Error("La sessione amministratore non è disponibile.");
 const j=await r.json();if(!r.ok||j.ok!==true)throw Error(j.error||"Operazione non autorizzata");
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
 const visibleSrc=state.coverPreview||state.cover||"";
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
 hideContext();
 state.mode="home";E("v2-home").hidden=false;E("v2-editor").hidden=true;E("v2-back").hidden=true;
 E("v2-crumb").textContent="Studio / Contenuti";E("v2-home-nav").classList.add("on");
 renderList();history.replaceState({}, "", "/studio-v2/");
}
function showEditor(row,newContent){
 state.current=row;state.newContent=!!newContent;state.mode="editor";
 E("v2-home").hidden=true;E("v2-editor").hidden=false;E("v2-back").hidden=false;
 E("v2-home-nav").classList.remove("on");
 E("v2-editor-heading").textContent=newContent?"Crea un nuovo contenuto":"Modifica il contenuto";
 E("v2-editor-note").textContent=newContent?"Scrivi e pubblica quando vuoi.":"Puoi cambiare tutto, senza aprire altri pannelli.";
 E("v2-crumb").textContent="Studio / "+(newContent?"Nuovo contenuto":"Modifica");
 editorFields(row);
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
  desc.append(S("b","",cats[row.category]||"Articolo"),S("span","", " · "+(row.date||"")+" · "+(state.drafts[row.slug]?"Bozza disponibile":"Pubblicato")));
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
 const sel=window.getSelection();if(!sel?.rangeCount)return;
 const r=sel.getRangeAt(0),node=document.createTextNode(e.clipboardData?.getData("text/plain")||"");
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
   editable.addEventListener("input",()=>{b.text=richValue(editable).trim();seoStatus()});
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
 const buttons=[E("v2-save-draft"),E("v2-publish"),E("v2-draft-bottom"),E("v2-publish-bottom")];
 buttons.forEach(b=>b.disabled=true);
 try{
  const row=collect();
  if(!row.title||!row.slug){notify("Inserisci prima titolo e indirizzo del contenuto.",true);return}
  const response=await api("v2-save",{mode,record:row,creating:state.newContent});
  notify(mode==="draft"?"Bozza salvata: nessuna modifica al sito.":"Contenuto accodato: pubblicazione al prossimo slot editoriale.");
  if(mode==="draft"){
   state.drafts[row.slug]={record:row,kind:state.newContent?"new":"edit"};
  }else{
   delete state.drafts[row.slug];
   E("v2-public-link").hidden=false;E("v2-public-link").href="/"+row.slug;
  }
 }catch(e){notify(e.message,true)}
 finally{state.busy=false;buttons.forEach(b=>b.disabled=false)}
}
async function init(){
 try{
  const session=await api("session");
  E("v2-user").textContent="GitHub · "+session.login;
  const r=await fetch("/studio-v2/catalog.json",{cache:"no-store"});
  if(!r.ok)throw Error("Catalogo Studio V2 non disponibile");
  state.rows=(await r.json()).posts||[];
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