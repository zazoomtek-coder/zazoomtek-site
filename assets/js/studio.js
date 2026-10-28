"use strict";
(()=>{
 const $=id=>document.getElementById(id);
 const gate=$("studio-gate"),app=$("studio-app"),status=$("studio-status");
 const categoryNames={"news-tech":"News Tech","news-gaming":"News Gaming",
  "recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming",
  "guide":"Guide","speciali":"Speciali","extra":"Extra"};
 const categories=Object.entries(categoryNames);
 const kinds={"paragraph":"Paragrafo","heading":"Titolo sezione H2","image":"Immagine","video":"Video YouTube",
  "button":"Pulsante con link","quote":"Citazione"};
 let catalog=[],editing=null,creating=false,blocks=[],busy=false;
 const message=(v,error=false)=>{status.textContent=v;status.dataset.error=String(error)};
 const api=async(url,payload)=>{
  const args={credentials:"same-origin",cache:"no-store",redirect:"manual"};
  if(payload!==undefined){args.method="POST";args.headers={"Content-Type":"application/json"};args.body=JSON.stringify(payload)}
  const response=await fetch(url,args);
  const type=response.headers.get("content-type")||"";
  if(!type.includes("application/json"))throw Error("Sessione Access assente o scaduta: accedi nuovamente");
  const data=await response.json();
  if(!response.ok||!data.ok){
   const err=new Error(data.error||"Operazione non autorizzata");
   err.code=data.code||"";
   err.status=response.status;
   throw err;
  }
  return data;
 };
 const slugify=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase()
  .replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,120);
 const parseBlocks=row=>{
  if(row.studio_blocks&&Array.isArray(row.body))return row.body.map(b=>({...b}));
  return (Array.isArray(row.body)?row.body:[row.body||""]).filter(Boolean).map(part=>{
   const text=typeof part==="string"?part:String(part.text||part.content||"");
   if(/^#{1,3}\s/.test(text))return {type:"heading",text:text.replace(/^#{1,3}\s*/,"")};
   if(/^\*\*[^*]+\*\*$/.test(text))return {type:"heading",text:text.slice(2,-2)};
   return {type:"paragraph",text};
  });
 };
 const field=(id)=>$(id).value.trim();
 const sectionInfo=()=>{
  const cat=field("studio-category");
  $("studio-sidebar-active").textContent=categoryNames[cat]||"Contenuto";
 };
 function renderList(){
  const search=field("studio-search").toLocaleLowerCase("it");
  const filter=field("studio-filter");
  const wrap=$("studio-content-list");wrap.replaceChildren();
  const selected=catalog.filter(r=>(!filter||r.category===filter)&&(!search||
   (r.title+" "+r.category).toLocaleLowerCase("it").includes(search)));
  $("studio-counter").textContent=selected.length+" contenuti";
  for(const row of selected){
   const b=document.createElement("button");b.type="button";b.className="studio-list-item";
   if(editing&&!creating&&row.slug===editing.slug)b.classList.add("active");
   const name=document.createElement("strong");name.textContent=row.title;
   const meta=document.createElement("span");meta.textContent=(categoryNames[row.category]||row.category)+" · "+String(row.date||"");
   b.append(name,meta);b.addEventListener("click",()=>openArticle(row));
   wrap.append(b);
  }
  if(!selected.length){const p=document.createElement("p");p.className="studio-empty";p.textContent="Nessun contenuto trovato";wrap.append(p)}
 }
 const makeEl=(tag,cls,text)=>{
  const el=document.createElement(tag);
  if(cls)el.className=cls;
  if(text!==undefined)el.textContent=text;
  return el;
 };
 function addBlock(type,at=blocks.length){
  blocks.splice(at,0,{type,text:"",url:"",alt:"",caption:""});
  renderBlocks();refreshPreview();
 }
 function moveBlock(index,amount){
  const next=index+amount;
  if(next<0||next>=blocks.length)return;
  [blocks[index],blocks[next]]=[blocks[next],blocks[index]];
  renderBlocks();refreshPreview();
 }
 const textInput=(block,key,label,multiline=false)=>{
  const holder=makeEl("label","studio-block-field");
  holder.append(makeEl("span","",label));
  const input=document.createElement(multiline?"textarea":"input");
  input.value=block[key]||"";input.placeholder=label;
  if(multiline)input.rows=4;else input.type="text";
  input.addEventListener("input",()=>{block[key]=input.value;refreshPreview()});
  holder.append(input);return holder;
 };
 async function imageUpload(block=null){
  const input=document.createElement("input");
  input.type="file";input.accept="image/jpeg,image/png,image/webp";
  input.addEventListener("change",async()=>{
   const file=input.files?.[0];if(!file)return;
   if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>3200000){
    message("Usa JPEG, PNG o WebP con dimensione massima 3,2 MB",true);return;
   }
   const slug=field("studio-slug")||slugify(field("studio-title"))||"nuova-cover";
   const reader=new FileReader();
   reader.onload=async()=>{
    try{
     message("Caricamento immagine nel branch di prova...");
     const data=await api("/api/studio/upload",{slug,mime:file.type,base64:reader.result});
     if(block){block.url=data.url;renderBlocks()}else $("studio-cover").value=data.url;
     message("Immagine caricata. Salva l'articolo per pubblicarla.");
     refreshPreview();
    }catch(err){message(err.message,true)}
   };
   reader.readAsDataURL(file);
  });
  input.click();
 }
 function renderBlocks(){
  const wrap=$("studio-block-list");wrap.replaceChildren();
  blocks.forEach((block,i)=>{
   const card=makeEl("section","studio-block");
   const header=makeEl("header","studio-block-head");
   header.append(makeEl("strong","",kinds[block.type]||"Blocco"));
   const actions=makeEl("div","studio-block-actions");
   const button=(text,run,disabled=false)=>{
    const b=makeEl("button","",text);b.type="button";b.disabled=disabled;
    b.addEventListener("click",run);return b;
   };
   actions.append(button("↑",()=>moveBlock(i,-1),!i),
    button("↓",()=>moveBlock(i,1),i===blocks.length-1),
    button("×",()=>{blocks.splice(i,1);renderBlocks();refreshPreview()}));
   header.append(actions);card.append(header);
   if(["paragraph","heading","quote","button"].includes(block.type))
    card.append(textInput(block,"text",block.type==="heading"?"Sottotitolo":block.type==="button"?"Testo del pulsante":"Scrivi il testo",block.type==="paragraph"||block.type==="quote"));
   if(["button","image","video"].includes(block.type)){
    card.append(textInput(block,"url","Collegamento HTTPS o percorso locale"));
    if(block.type==="image"){
     card.append(textInput(block,"alt","Testo alternativo per SEO"),
      textInput(block,"caption","Didascalia"));
     const file=button("Carica foto",()=>imageUpload(block));file.className="studio-secondary-btn";card.append(file);
    }else if(block.type==="video")card.append(textInput(block,"caption","Didascalia video"));
   }
   const append=button("+ Inserisci sotto",()=>addBlock("paragraph",i+1));
   append.className="studio-insert-under";card.append(append);
   wrap.append(card);
  });
 }
 function refreshPreview(){
  const preview=$("studio-preview");preview.replaceChildren();
  preview.append(makeEl("h2","",field("studio-title")||"Titolo del contenuto"));
  preview.append(makeEl("small","",categoryNames[field("studio-category")]||"Categoria"));
  const cover=field("studio-cover");
  if(cover){const im=makeEl("img","studio-preview-cover");im.loading="lazy";im.src=cover;im.alt="Anteprima copertina";preview.append(im)}
  for(const b of blocks){
   const type=b.type;
   if(type==="heading")preview.append(makeEl("h3","",b.text||"Sottotitolo"));
   if(type==="paragraph")preview.append(makeEl("p","",b.text||"Paragrafo"));
   if(type==="quote")preview.append(makeEl("blockquote","",b.text||"Citazione"));
   if(type==="image"&&b.url){const im=makeEl("img","studio-preview-cover");im.src=b.url;im.alt=b.alt||"";preview.append(im)}
   if(type==="video")preview.append(makeEl("p","studio-preview-video","▶ "+(b.url||"Video YouTube")));
   if(type==="button")preview.append(makeEl("span","studio-preview-cta",b.text||"Pulsante"));
  }
  $("studio-preview-foot").textContent="Anteprima redazionale · Le modifiche saranno pubblicate solo nel branch di prova.";
 }
 function openArticle(row){
  editing=row;creating=false;
  fillEditor(row);
  renderList();
  message("Modifica: "+row.title);
 }
 function fillEditor(row){
  $("studio-title").value=row.title||"";
  $("studio-slug").value=row.slug||"";
  $("studio-slug").readOnly=!creating;
  $("studio-category").value=row.category||"news-tech";
  $("studio-cover").value=row.image||"";
  $("studio-author").value=row.author||"Redazione ZazoomTek";
  $("studio-video-url").value=row.video_url||"";
  $("studio-platform").value=row.platform||"";
  $("studio-score").value=row.score??row.rating??"";
  $("studio-pros").value=Array.isArray(row.pros)?row.pros.join("\n"):"";
  $("studio-cons").value=Array.isArray(row.cons)?row.cons.join("\n"):"";
  $("studio-mode").textContent=creating?"Nuovo contenuto":"Modifica contenuto";
  $("studio-opening").hidden=false;
  blocks=parseBlocks(row);
  renderBlocks();refreshPreview();sectionInfo();
 }
 function makeNew(){
  creating=true;editing=null;
  fillEditor({title:"",slug:"",category:"news-tech",image:"",body:[{type:"paragraph",text:""}]});
  message("Nuovo contenuto editoriale");
  renderList();
 }
 function serialize(){
  const title=field("studio-title");
  const slug=field("studio-slug")||slugify(title);
  return {title,slug,category:field("studio-category"),
   image:field("studio-cover"),author:field("studio-author"),
   video_url:field("studio-video-url"),platform:field("studio-platform"),
   score:field("studio-score"),pros:field("studio-pros").split("\n").filter(Boolean),
   cons:field("studio-cons").split("\n").filter(Boolean),body:blocks};
 }
 async function save(){
  if(busy)return;
  const record=serialize();
  if(!record.title||!record.image||!record.body.length){
   message("Titolo, copertina e contenuto sono obbligatori",true);return;
  }
  busy=true;$("studio-save").disabled=true;
  try{
   message("Salvataggio sicuro sul branch SpotNews...");
   const data=await api("/api/studio/save",{creating,record});
   message("Salvato: "+data.slug+". La nuova build Cloudflare partirà automaticamente.");
   // Catalog is a static snapshot updated by the next Cloudflare build.
   $("studio-save").disabled=true;
   $("studio-editor-note").textContent="Salvataggio riuscito. Riapri Studio dopo il nuovo deploy per rivedere la versione pubblicata.";
  }catch(err){message(err.message,true)}
  finally{busy=false}
 }
 async function boot(){
  try{
   const session=await api("/api/studio/session");
   if(!session.admin)throw Error("Non sei autorizzato a utilizzare Studio");
   const data=await fetch("/studio/catalog.json",{cache:"no-store",credentials:"same-origin"});
   if(!data.ok)throw Error("Catalogo editoriale non disponibile");
   const listing=await data.json();
   catalog=listing.posts||[];
   gate.hidden=true;app.hidden=false;
   $("studio-admin-email").textContent=session.email||"Amministratore";
   const expires=new Date(session.expires*1000);
   $("studio-auth-status").textContent="Accesso attivo sul browser fino al "+expires.toLocaleDateString("it-IT");
   for(const [id] of [["studio-filter"],["studio-category"]]){
    const control=$(id);
    categories.forEach(([value,label])=>{
     const option=document.createElement("option");option.value=value;option.textContent=label;control.append(option);
    });
   }
   $("studio-filter").insertBefore(new Option("Tutte le categorie",""),$("studio-filter").firstChild);
   $("studio-filter").value="";
   $("studio-new").addEventListener("click",makeNew);
   $("studio-search").addEventListener("input",renderList);
   $("studio-filter").addEventListener("change",renderList);
   $("studio-category").addEventListener("change",()=>{sectionInfo();refreshPreview()});
   ["studio-title","studio-cover"].forEach(id=>$(id).addEventListener("input",refreshPreview));
   $("studio-title").addEventListener("input",()=>{
    if(creating&&!$("studio-slug").dataset.customized)$("studio-slug").value=slugify(field("studio-title"));
   });
   $("studio-slug").addEventListener("input",()=>$("studio-slug").dataset.customized="true");
   $("studio-add-cover").addEventListener("click",()=>imageUpload());
   $("studio-save").addEventListener("click",save);
   for(const button of document.querySelectorAll("[data-add-block]")){
    button.addEventListener("click",()=>addBlock(button.dataset.addBlock));
   }
   renderList();
   const desired=new URLSearchParams(location.search).get("edit");
   const target=catalog.find(x=>x.slug===desired);
   if(target)openArticle(target);
   else if(catalog.length)openArticle(catalog[0]);
   else makeNew();
  }catch(err){
   gate.hidden=false;app.hidden=true;
   const unconfigured=err.code==="ACCESS_CONFIGURATION_REQUIRED"||
     /Access not configured|Invalid Access team hostname/i.test(err.message);
   $("studio-gate-setup").hidden=!unconfigured;
   $("studio-setup-link").hidden=!unconfigured;
   $("studio-retry").hidden=false;
   $("studio-gate-description").textContent=unconfigured
     ?"Studio non è ancora attivato in Cloudflare. Il link di accesso precedente portava a una pagina 404 perché non esiste un'applicazione Access configurata. Prima attiva la protezione indicata qui sotto."
     :err.status===401
     ?"La sessione amministratore non è valida. Dopo aver configurato Cloudflare Access, entra nuovamente nella pagina Studio per effettuare l'accesso protetto."
     :"Studio non è disponibile: "+err.message;
  }
 }
 $("studio-retry").addEventListener("click",()=>location.reload());
 boot();
})();