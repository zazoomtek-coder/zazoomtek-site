"use strict";
(()=>{
const E=id=>document.getElementById(id), T=(tag,cls,text)=>{
 const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=String(text);return e;
};
const C={"news-tech":"News Tech","news-gaming":"News Gaming","recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming","guide":"Guide","speciali":"Speciali","extra":"Extra"};
const N={paragraph:"Paragrafo",heading:"Sottotitolo H2",image:"Foto nell'articolo",video:"Video YouTube",button:"Pulsante con link",quote:"Citazione"};
const state={articles:[],current:null,isNew:false,blocks:[],busy:false,admin:false};
const V=id=>E(id).value.trim();
const slugify=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-+|-+$/g,"").slice(0,130);
const button=(label,onClick,cls="",disabled=false)=>{
 const b=T("button",cls,label);b.type="button";b.disabled=disabled;b.addEventListener("click",onClick);return b;
};
function feedback(msg,bad=false){
 const x=E("studio-status");x.textContent=msg;x.dataset.error=String(bad);
}
function authFeedback(msg,bad=false){
 const x=E("studio-login-status");x.textContent=msg;x.dataset.error=String(bad);
}
async function api(path,body){
 const opt={credentials:"same-origin",cache:"no-store",redirect:"manual"};
 if(body!==undefined){opt.method="POST";opt.headers={"Content-Type":"application/json"};opt.body=JSON.stringify(body)}
 const response=await fetch("/api/studio/"+path,opt);
 const type=response.headers.get("Content-Type")||"";
 if(!type.includes("application/json")){
  const err=new Error("L'API Studio non risponde correttamente.");err.status=response.status;throw err;
 }
 const data=await response.json();
 if(!response.ok||data.ok!==true){
  const err=new Error(data.error||"Operazione non autorizzata");
  err.code=data.code;err.status=response.status;throw err;
 }
 return data;
}
function showLogin(error){
 E("studio-app").hidden=true;E("studio-auth").hidden=false;
 const setup=error?.code==="SETUP_REQUIRED";
 E("studio-setup").hidden=!setup;
 E("studio-login-form").hidden=setup;
 E("studio-check-again").hidden=!setup;
 if(setup)authFeedback("Per attivare Studio serve solo una chiave di sessione nel progetto Cloudflare Pages.",true);
 else if(error?.status===401||!error)authFeedback("Inserisci il token GitHub soltanto al primo accesso.");
 else authFeedback(error?.message||"Connessione non disponibile. Riprova.",true);
}
async function loadCatalog(){
 const res=await fetch("/studio/catalog.json",{cache:"no-store",credentials:"same-origin"});
 if(!res.ok)throw new Error("Catalogo Studio non disponibile.");
 const data=await res.json();
 state.articles=Array.isArray(data.posts)?data.posts:[];
}
function makeOptions(){
 const a=E("studio-filter"),b=E("studio-category");
 a.replaceChildren(new Option("Tutte le categorie",""));b.replaceChildren();
 for(const [k,v] of Object.entries(C)){a.add(new Option(v,k));b.add(new Option(v,k))}
}
function repaintList(){
 const q=V("studio-search").toLocaleLowerCase("it"),cat=V("studio-filter");
 const found=state.articles.filter(r=>(!cat||cat===r.category)&&(!q||String(r.title||"").toLocaleLowerCase("it").includes(q)));
 E("studio-count").textContent=found.length+" contenuti";
 const host=E("studio-list");host.replaceChildren();
 for(const article of found){
  const box=button("",()=>selectArticle(article),"studio-article-select");
  if(!state.isNew&&state.current?.slug===article.slug)box.classList.add("selected");
  box.append(T("strong","",article.title),T("span","",C[article.category]||article.category),T("small","",article.date||""));
  host.append(box);
 }
 if(!found.length)host.append(T("p","studio-no-content","Nessun articolo corrispondente."));
}
function originalBlocks(row){
 if(row.studio_blocks&&Array.isArray(row.body))return row.body.map(b=>({...b}));
 const input=Array.isArray(row.body)?row.body:[row.body||""];
 const output=[];
 for(const item of input){
  const t=typeof item==="string"?item:String(item?.text||item?.content||"");
  for(let s of t.split(/\n\s*\n/)){
   s=s.trim();if(!s)continue;
   if(/^#{1,3}\s/.test(s))output.push({type:"heading",text:s.replace(/^#{1,3}\s+/,"")});
   else if(/^\*\*[^*]+\*\*$/.test(s))output.push({type:"heading",text:s.slice(2,-2)});
   else output.push({type:"paragraph",text:s});
  }
 }
 return output.length?output:[{type:"paragraph",text:""}];
}
function setArticle(row){
 const values={"studio-title":row.title||"","studio-slug":row.slug||"","studio-cover":row.image||"",
 "studio-author":row.author||"Redazione ZazoomTek","studio-video":row.video_url||"",
 "studio-platform":row.platform||"","studio-score":row.score??"",
 "studio-pros":Array.isArray(row.pros)?row.pros.join("\n"):"",
 "studio-cons":Array.isArray(row.cons)?row.cons.join("\n"):""};
 for(const [id,value] of Object.entries(values))E(id).value=value;
 E("studio-slug").readOnly=!state.isNew;
 E("studio-category").value=row.category||"news-tech";
 E("studio-current-mode").textContent=state.isNew?"Crea un contenuto":"Modifica contenuto";
 E("studio-current-category").textContent=C[row.category]||"News Tech";
 E("studio-save").disabled=E("studio-save-bottom").disabled=false;
 E("studio-save-detail").textContent="Le modifiche saranno pubblicate soltanto nella preview SpotNews.";
 state.blocks=originalBlocks(row);
 renderBlocks();renderPreview();
}
function selectArticle(row){
 if(state.busy)return;
 state.current=row;state.isNew=false;
 setArticle(row);repaintList();
 feedback("Modifica: "+row.title);
}
function createArticle(){
 if(state.busy)return;
 state.current=null;state.isNew=true;
 setArticle({title:"",slug:"",category:"news-tech",image:"",body:[{type:"paragraph",text:""}]});
 repaintList();feedback("Nuovo contenuto editoriale.");
}
function move(i,amount){
 const j=i+amount;
 if(j<0||j>=state.blocks.length)return;
 [state.blocks[i],state.blocks[j]]=[state.blocks[j],state.blocks[i]];
 renderBlocks();renderPreview();
}
function add(type,where=state.blocks.length){
 state.blocks.splice(where,0,{type,text:"",url:"",alt:"",caption:""});
 renderBlocks();renderPreview();
}
function blockField(b,key,label,multiline=false){
 const wrap=T("label","studio-block-input");
 wrap.append(T("span","",label));
 const control=document.createElement(multiline?"textarea":"input");
 if(multiline)control.rows=5;
 else control.type="text";
 control.value=b[key]||"";control.placeholder=label;
 control.addEventListener("input",()=>{b[key]=control.value;renderPreview()});
 wrap.append(control);return wrap;
}
function renderBlocks(){
 const target=E("studio-blocks");target.replaceChildren();
 state.blocks.forEach((b,i)=>{
  const section=T("section","studio-block");
  const head=T("header","studio-block-bar");
  head.append(T("b","",N[b.type]||"Blocco"));
  const controls=T("div","studio-block-buttons");
  controls.append(button("↑",()=>move(i,-1),"",i===0),
   button("↓",()=>move(i,1),"",i===state.blocks.length-1),
   button("×",()=>{state.blocks.splice(i,1);renderBlocks();renderPreview()}));
  head.append(controls);section.append(head);
  if(["heading","paragraph","quote","button"].includes(b.type))
   section.append(blockField(b,"text",
    b.type==="heading"?"Sottotitolo":b.type==="button"?"Scritta sul pulsante":"Scrivi il testo",
    ["paragraph","quote"].includes(b.type)));
  if(["button","image","video"].includes(b.type)){
   section.append(blockField(b,"url",b.type==="video"?"Link YouTube":"Link o indirizzo immagine"));
   if(b.type==="image"){
    section.append(blockField(b,"alt","Descrizione immagine per SEO"),
     blockField(b,"caption","Didascalia"));
    section.append(button("Carica foto",()=>upload(b),"studio-outline"));
   }else if(b.type==="video")section.append(blockField(b,"caption","Didascalia video"));
  }
  section.append(button("＋ Inserisci un blocco sotto",()=>add("paragraph",i+1),"studio-add-under"));
  target.append(section);
 });
}
function renderPreview(){
 const content=E("studio-preview");content.replaceChildren();
 content.append(T("h3","studio-preview-title",V("studio-title")||"Titolo dell'articolo"));
 content.append(T("small","studio-preview-category",C[V("studio-category")]||"News Tech"));
 const image=V("studio-cover");
 if(image){const img=T("img","studio-preview-cover");img.src=image;img.alt="Copertina";img.loading="lazy";content.append(img)}
 for(const b of state.blocks){
  const t=b.text||"",url=b.url||"";
  if(b.type==="heading")content.append(T("h4","",t||"Sottotitolo"));
  if(b.type==="paragraph")content.append(T("p","",t||"Paragrafo"));
  if(b.type==="quote")content.append(T("blockquote","",t||"Citazione"));
  if(b.type==="image"&&url){
   const img=T("img","studio-preview-cover");img.src=url;img.alt=b.alt||"Immagine";img.loading="lazy";content.append(img);
   if(b.caption)content.append(T("small","",b.caption));
  }
  if(b.type==="video")content.append(T("p","studio-video-placeholder","▶ "+(url||"Video YouTube")));
  if(b.type==="button")content.append(T("span","studio-preview-button",t||"Pulsante"));
 }
}
function readArticle(){
 const v=k=>V(k), lines=id=>V(id).split("\n").map(x=>x.trim()).filter(Boolean);
 return {slug:v("studio-slug")||slugify(v("studio-title")),title:v("studio-title"),
  category:v("studio-category"),image:v("studio-cover"),author:v("studio-author"),
  video_url:v("studio-video"),platform:v("studio-platform"),
  score:v("studio-score"),pros:lines("studio-pros"),cons:lines("studio-cons"),body:state.blocks};
}
async function save(){
 if(state.busy)return;
 state.busy=true;E("studio-save").disabled=E("studio-save-bottom").disabled=true;
 try{
  feedback("Salvataggio sul branch di prova...");
  const result=await api("save",{creating:state.isNew,record:readArticle()});
  feedback("Salvato: "+result.slug+". Nuova build Cloudflare attivata.");
  E("studio-save-detail").textContent="Modifica salvata. Riapri la preview dopo l'aggiornamento per visualizzarla.";
 }catch(e){feedback(e.message,true)}
 finally{state.busy=false;E("studio-save").disabled=E("studio-save-bottom").disabled=false}
}
function upload(block){
 const choose=document.createElement("input");choose.type="file";choose.accept="image/jpeg,image/png,image/webp";
 choose.addEventListener("change",()=>{
  const file=choose.files?.[0];if(!file)return;
  if(!["image/jpeg","image/png","image/webp"].includes(file.type)||file.size>3200000){
   feedback("Sono consentite immagini JPEG, PNG e WebP fino a 3,2 MB.",true);return;
  }
  const reader=new FileReader();
  reader.addEventListener("load",async()=>{
   try{
    feedback("Caricamento della foto nel branch SpotNews...");
    const result=await api("upload",{slug:V("studio-slug")||slugify(V("studio-title"))||"contenuto",
     mime:file.type,base64:reader.result});
    if(block){block.url=result.url;renderBlocks()}
    else E("studio-cover").value=result.url;
    renderPreview();feedback("Immagine caricata. Salva l'articolo per completare.");
   }catch(e){feedback(e.message,true)}
  });reader.readAsDataURL(file);
 });choose.click();
}
async function authenticated(session){
 state.admin=true;await loadCatalog();
 E("studio-auth").hidden=true;E("studio-app").hidden=false;
 E("studio-account-name").textContent="Account GitHub: "+session.login;
 E("studio-session-expiry").textContent="Accesso persistente con rinnovo automatico. Nessuna scadenza periodica di Studio.";
 makeOptions();repaintList();
 const desired=new URLSearchParams(location.search).get("edit");
 const row=state.articles.find(r=>r.slug===desired);
 if(row)selectArticle(row);else if(state.articles.length)selectArticle(state.articles[0]);else createArticle();
}
async function firstLogin(event){
 event.preventDefault();
 const token=E("studio-token").value.trim();
 if(!token){authFeedback("Inserisci il token GitHub.",true);return}
 const submit=E("studio-login-submit");submit.disabled=true;
 try{
  authFeedback("Verifica del token e dei permessi GitHub in corso...");
  const result=await api("login",{token});
  E("studio-token").value="";
  await authenticated(result);
 }catch(e){authFeedback(e.message,true)}
 finally{submit.disabled=false}
}
async function boot(){
 try{await authenticated(await api("session"))}
 catch(e){showLogin(e)}
}
E("studio-login-form").addEventListener("submit",firstLogin);
E("studio-check-again").addEventListener("click",()=>location.reload());
E("studio-new").addEventListener("click",createArticle);
E("studio-search").addEventListener("input",repaintList);
E("studio-filter").addEventListener("change",repaintList);
E("studio-cover-upload").addEventListener("click",()=>upload());
E("studio-save").addEventListener("click",save);
E("studio-save-bottom").addEventListener("click",save);
E("studio-logout").addEventListener("click",async()=>{
 try{await api("logout",{})}catch(_){}
 location.reload();
});
E("studio-title").addEventListener("input",()=>{
 if(state.isNew)E("studio-slug").value=slugify(V("studio-title"));
 renderPreview();
});
E("studio-cover").addEventListener("input",renderPreview);
E("studio-category").addEventListener("change",()=>{
 E("studio-current-category").textContent=C[V("studio-category")]||"News Tech";
 renderPreview();
});
E("studio-preview-toggle").addEventListener("click",()=>{
 const el=E("studio-preview-column");
 el.classList.toggle("studio-preview-mobile-expanded");
 if(window.innerWidth<1200)el.scrollIntoView({behavior:"smooth"});
});
for(const b of document.querySelectorAll("[data-block]"))
 b.addEventListener("click",()=>add(b.dataset.block));
boot();
})();