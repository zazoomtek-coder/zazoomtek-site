(function editExisting() {
"use strict";
const $=id=>document.getElementById(id);
const esc=s=>String(s||"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const goodPath=raw=>{try{
 let s=decodeURIComponent(String(raw||"").trim().replace(/^https?:\/\/(?:www\.)?zazoomtek\.it\//i,"").replace(/^\/+/,"").split(/[?#]/)[0]).replace(/\/+$/,"");
 if(s&&!/\.[a-z0-9]+$/i.test(s))s+=".html";
 return (/^[\w.-]+\.html$/.test(s)||/^watch\/[\w-]{11}\.html$/.test(s))&&!s.includes("..")&&!["index.html","studio.html","watch/index.html"].includes(s)?s:null;
}catch{return null}};
const yt=raw=>{try{let u=new URL(raw,location.href);if(!["youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be","www.youtube-nocookie.com"].includes(u.hostname))return null;const id=u.hostname.includes("youtu.be")?u.pathname.slice(1):u.pathname==="/watch"?u.searchParams.get("v"):(u.pathname.match(/^\/(?:embed|shorts|live|v)\/([\w-]+)/)||[])[1];return /^[\w-]{11}$/.test(id||"")?id:null}catch{return null}};
const b64decode=s=>new TextDecoder().decode(Uint8Array.from(atob(String(s||"").replace(/\s+/g,"")),c=>c.charCodeAt(0)));
const photo=(src,alt,x=50,y=50)=>{let f=document.createElement("figure");f.className="zt-media photo";f.dataset.x=x;f.dataset.y=y;f.dataset.zoom=1;f.contentEditable="false";f.innerHTML='<img alt="'+esc(alt)+'" style="width:100%;aspect-ratio:16/9;object-fit:cover;object-position:'+x+'% '+y+'%;transform:scale(1);transform-origin:'+x+'% '+y+'%"><figcaption>Immagine · trascina per regolare l’inquadratura</figcaption>';f.querySelector("img").src=src;return f};
const video=id=>{const f=document.createElement("figure");f.className="zt-media video";f.dataset.video=id;f.contentEditable="false";f.innerHTML='<div class="zt-video-frame"><iframe title="YouTube" loading="lazy" src="https://www.youtube-nocookie.com/embed/'+id+'" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div><figcaption>Player YouTube incorporato</figcaption>';return f};
const ui=document.createElement("div");ui.id="zt-live-editor";ui.hidden=true;ui.innerHTML=`<div class="ze-head"><div><small>STUDIO PERMANENTE / MODIFICA</small><h2>Modifica un articolo pubblicato</h2><p>SEO, meta tag e layout sono gestiti dal sistema.</p></div><button id="zeClose">Chiudi</button></div>
<div class="ze-bar"><label>URL articolo<input id="zePath" placeholder="https://zazoomtek.it/nome-articolo.html"></label><button id="zeOpen">Apri articolo</button><button id="zePreview">Anteprima reale</button><button id="zeSave" class="primary">Salva modifiche</button></div>
<div id="zeStatus" role="status">Incolla il collegamento dell'articolo e premi Apri.</div>
<div class="ze-columns"><div class="ze-paper"><label>Titolo<input id="zeTitle" disabled></label><nav class="ze-tools"><button data-cmd="bold"><b>B</b></button><button data-cmd="italic"><i>I</i></button><button data-cmd="h2">H2</button><button data-cmd="p">¶</button><button id="zeLink">Link</button><button id="zeVideo">+ Video YouTube</button><button id="zePhoto">+ Foto</button><button id="zeUp">↑</button><button id="zeDown">↓</button><button id="zeDelete">Elimina selezione</button></nav><div id="zeBody" contenteditable="true" aria-label="Corpo dell'articolo"></div></div>
<aside class="ze-paper ze-aside"><h3>Posizione dell'immagine</h3><p>Seleziona la foto, trascinala con il mouse oppure usa i cursori.</p><label>Orizzontale <output id="zeXOut">50%</output></label><input type="range" id="zeX" min="0" max="100" disabled><label>Verticale <output id="zeYOut">50%</output></label><input type="range" id="zeY" min="0" max="100" disabled><button id="zeCenter">Centra foto</button><p>Il centraggio viene salvato nell'articolo e mantenuto ai successivi aggiornamenti.</p></aside></div><input id="zeFile" type="file" accept="image/jpeg,image/png,image/webp" hidden>`;
const style=document.createElement("style");style.textContent=`#zt-live-editor{position:fixed;inset:0;z-index:9998;overflow:auto;background:#f6f7fa;color:#20242b;padding:24px 3vw;font:14px/1.5 Arial,sans-serif}#zt-live-editor[hidden]{display:none!important}#zt-live-editor *{box-sizing:border-box}#zt-live-editor .ze-head{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #dadfe6;padding-bottom:15px;gap:18px}#zt-live-editor h2{font-size:24px;margin:0}#zt-live-editor h3{margin-top:0}#zt-live-editor small{color:#d51232;font-weight:800}#zt-live-editor p{margin:6px 0 14px;color:#646b76}#zt-live-editor button{background:white;border:1px solid #d1d6e0;padding:9px 13px;border-radius:7px;cursor:pointer;color:#222;font-weight:700}#zt-live-editor button.primary{color:#fff;background:#d51232;border-color:#d51232}#zt-live-editor .ze-bar{display:flex;flex-wrap:wrap;align-items:end;gap:9px;margin:18px 0}#zt-live-editor .ze-bar label{flex:1;min-width:270px}#zt-live-editor label{font-size:12px;font-weight:800}#zt-live-editor input:not([type=range]):not([type=file]){display:block;width:100%;border:1px solid #d2d6de;border-radius:7px;padding:11px;background:#fff;font-size:15px}#zeTitle{font-size:24px!important;font-weight:800;margin-bottom:20px}#zeStatus{background:white;padding:10px 15px;border:1px solid #e1e4e9;border-radius:8px;margin-bottom:17px}#zt-live-editor .ze-columns{display:grid;grid-template-columns:minmax(0,1fr) 265px;gap:20px}#zt-live-editor .ze-paper{background:white;border:1px solid #e2e5eb;border-radius:11px;padding:24px}#zt-live-editor .ze-tools{display:flex;flex-wrap:wrap;gap:6px;padding:14px 0;border-bottom:1px solid #e8e8e8}#zeBody{min-height:390px;outline:0;font-size:16px;line-height:1.75;padding-top:22px}#zeBody p{font-size:inherit;color:#252525}#zeBody h2{font-size:21px;margin:24px 0 8px}#zeBody .zt-media{margin:19px 0;cursor:pointer;border:2px solid transparent;padding:5px}#zeBody .zt-media.ze-picked{border-color:#d51232}#zeBody .zt-media img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;user-select:none}#zeBody figcaption{font-size:12px;color:#888;text-align:center}#zeBody .zt-video-frame{aspect-ratio:16/9;background:#111}#zeBody .zt-video-frame iframe{border:0;width:100%;height:100%}#zt-live-editor input[type=range]{width:100%;margin:9px 0 18px;accent-color:#d51232}#zt-live-editor .ze-aside label{display:flex;justify-content:space-between}#ze-full-preview{position:fixed;z-index:9999;inset:0;display:grid;grid-template-rows:45px 1fr;background:#000a;padding:10px}#ze-full-preview[hidden]{display:none!important}#ze-full-preview iframe{background:white;width:100%;height:100%;border:0}#ze-full-preview button{justify-self:end;cursor:pointer}@media(max-width:850px){#zt-live-editor .ze-columns{grid-template-columns:1fr}}`;
document.head.append(style);document.body.append(ui);
const leadBox=document.createElement("label");leadBox.id="zeLeadBox";leadBox.textContent="Sommario iniziale";
const leadInput=document.createElement("textarea");leadInput.id="zeLead";leadInput.rows=3;leadInput.style.cssText="display:block;width:100%;border:1px solid #d2d6de;border-radius:7px;padding:12px;margin:8px 0 18px;font:15px/1.5 Arial,sans-serif;resize:vertical";leadBox.append(leadInput);
document.getElementById("zeBody").before(leadBox);
const coverPanel=document.createElement("figure");coverPanel.id="zeCover";coverPanel.className="zt-media photo";
coverPanel.contentEditable="false";coverPanel.innerHTML='<img alt="Cover" style="width:100%;aspect-ratio:16/9;object-fit:cover;object-position:50% 50%;display:block"><figcaption>Cover · seleziona o trascina per l’inquadratura</figcaption>';
coverPanel.style.cssText="border:2px solid transparent;padding:5px;margin:7px 0 17px;cursor:pointer";
document.querySelector(".ze-aside").insertBefore(coverPanel,document.querySelector(".ze-aside h3"));
const coverUploadButton=document.createElement("button");
coverUploadButton.id="zeReplaceCover";
coverUploadButton.type="button";
coverUploadButton.textContent="Sostituisci cover · scegli una nuova foto";
coverUploadButton.style.cssText="width:100%;margin:-3px 0 18px;background:#d51232!important;color:white!important;border-color:#d51232!important";
coverPanel.insertAdjacentElement("afterend",coverUploadButton);
const coverFile=document.createElement("input");
coverFile.type="file";coverFile.id="zeCoverFile";
coverFile.accept="image/jpeg,image/png,image/webp";
coverFile.hidden=true;
coverUploadButton.insertAdjacentElement("afterend",coverFile);
coverUploadButton.onclick=()=>{if(!loaded){status("Apri prima un articolo.");return;}coverFile.click()};
coverFile.addEventListener("change",async()=>{
 const file=coverFile.files?.[0];coverFile.value="";if(!file)return;
 if(!/^image\/(?:jpeg|png|webp)$/.test(file.type)||file.size>8_000_000){
   status("Cover non valida: usa JPG, PNG o WebP fino a 8 MB.");return;
 }
 const temp=URL.createObjectURL(file);
 try{
   const bitmap=await new Promise((resolve,reject)=>{
     const image=new Image();image.onload=()=>resolve(image);
     image.onerror=()=>reject(new Error("Impossibile leggere questa foto."));
     image.src=temp;
   });
   if(bitmap.naturalWidth<320||bitmap.naturalHeight<180)throw Error("Cover troppo piccola (minimo 320 × 180).");
   const ratio=Math.min(1,1920/bitmap.naturalWidth,1920/bitmap.naturalHeight);
   const canvas=document.createElement("canvas");
   canvas.width=Math.round(bitmap.naturalWidth*ratio);
   canvas.height=Math.round(bitmap.naturalHeight*ratio);
   const context=canvas.getContext("2d");
   if(!context)throw Error("Conversione della cover non disponibile nel browser.");
   context.drawImage(bitmap,0,0,canvas.width,canvas.height);
   const newSrc=canvas.toDataURL("image/webp",0.83);
   if(!newSrc.startsWith("data:image/webp;base64,"))throw Error("Conversione in WebP non riuscita.");
   coverPanel.hidden=false;
   coverPanel.querySelector("img").src=newSrc;
   coverPanel.querySelector("img").alt=file.name;
   coverPanel.dataset.replacement="true";
   coverPanel.dataset.x="50";coverPanel.dataset.y="50";coverPanel.dataset.zoom="1";
   coverPanel.querySelector("img").style.objectPosition="50% 50%";
   coverPanel.querySelector("img").style.transform="scale(1)";
   select(coverPanel);dirty=true;
   status("Nuova cover caricata in anteprima ("+canvas.width+" × "+canvas.height+" WebP). Puoi spostarla e ingrandirla, poi premi Salva modifiche.");
 }catch(error){status("Cover non sostituita: "+error.message)}
 finally{URL.revokeObjectURL(temp)}
});
const zoomControl=document.createElement("label");
zoomControl.id="zeZoomWrap";zoomControl.innerHTML='Dimensione copertina <output id="zeZoomOut">100%</output><input id="zeZoom" type="range" min="100" max="300" step="5" value="100" disabled>';
document.getElementById("zeCenter").before(zoomControl);
coverPanel.dataset.zoom="1";coverPanel.style.aspectRatio="16 / 9";coverPanel.style.overflow="hidden";coverPanel.querySelector("img").style.height="100%";
style.textContent+="#zeBody .zt-media.photo{aspect-ratio:16/9;overflow:hidden;touch-action:none}#zeBody .zt-media.photo img{height:100%;aspect-ratio:16/9;max-height:none}#zeCover figcaption{display:none}";

coverPanel.addEventListener("click",()=>select(coverPanel));
style.textContent+="#zeCover.ze-picked{border-color:#d51232!important}#zeCover img{touch-action:none}#zeLeadBox[hidden],#zeCover[hidden]{display:none!important}";
leadInput.addEventListener("input",()=>dirty=true);
let coverDrag=null;
coverPanel.addEventListener("pointerdown",e=>{if(!e.target.closest("img"))return;select(coverPanel);coverDrag={x:e.clientX,y:e.clientY,fx:Number($("zeX").value),fy:Number($("zeY").value)};e.target.setPointerCapture?.(e.pointerId)});
coverPanel.addEventListener("pointermove",e=>{if(!coverDrag)return;if(Number($("zeZoom").value)<110)$("zeZoom").value=130;$("zeX").value=Math.min(100,Math.max(0,coverDrag.fx+(coverDrag.x-e.clientX)/3));$("zeY").value=Math.min(100,Math.max(0,coverDrag.fy+(coverDrag.y-e.clientY)/3));crop()});
coverPanel.addEventListener("pointerup",()=>coverDrag=null);coverPanel.addEventListener("pointercancel",()=>coverDrag=null);
const prev=document.createElement("section");prev.id="ze-full-preview";prev.hidden=true;prev.innerHTML='<button id="zeEndPreview">Chiudi anteprima</button><iframe title="Anteprima completa" sandbox="allow-scripts allow-forms allow-popups"></iframe>';document.body.append(prev);
let loaded=null,selected=null,dirty=false,busy=false;
const status=s=>$("zeStatus").textContent=s;
const isDemo=()=>location.protocol==="file:"&&!!window.ZTStudioDemoArticle;
const storage=path=>"zt_studio_local_edit_"+path;
function select(el){selected?.classList.remove("ze-picked");selected=el?.closest(".zt-media")||null;selected?.classList.add("ze-picked");$("zeZoom").disabled=!selected?.classList.contains("photo");$("zeZoom").value=Math.round(Number(selected?.dataset.zoom||1)*100);$("zeZoomOut").value=$("zeZoom").value+"%";for(let a of ["X","Y"]){let v=selected?.classList.contains("photo")?selected.dataset[a.toLowerCase()]:"50";$("ze"+a).disabled=!selected?.classList.contains("photo");$("ze"+a).value=v||50;$("ze"+a+"Out").value=(v||50)+"%"}}
function crop(){if(!selected?.classList.contains("photo"))return;let x=Number($("zeX").value),y=Number($("zeY").value);selected.dataset.x=x;selected.dataset.y=y;const img=selected.querySelector("img"),zoom=Math.max(1,Math.min(3,Number($("zeZoom").value)/100));selected.dataset.zoom=String(zoom);img.style.objectPosition=x+"% "+y+"%";img.style.transform="scale("+zoom+")";img.style.transformOrigin=x+"% "+y+"%";$("zeZoomOut").value=Math.round(zoom*100)+"%";$("zeXOut").value=x+"%";$("zeYOut").value=y+"%";dirty=true}
["X","Y"].forEach(a=>$("ze"+a).addEventListener("input",crop));$("zeZoom").addEventListener("input",crop);
$("zeCenter").onclick=()=>{if(!selected)return;$("zeX").value=50;$("zeY").value=50;$("zeZoom").value=100;crop()};
let drag=null;const body=$("zeBody");
/* SEO editoriale: same analyzer for new and existing published articles. */
const seoAPI=window.ZTStudioSEO;
const seoMount=document.createElement("section");
seoMount.className="ze-seo-aside";
document.querySelector(".ze-aside").appendChild(seoMount);
const seoPanel=seoAPI?.panel(seoMount);
let seoCategory="Article",seoSourceDate="",seoTimer=0;
const categoryFromDoc=doc=>{
 const section=(doc.querySelector('meta[property="article:section"]')?.content||
   doc.querySelector(".tag,.article-category,.breadcrumbs,.crumb")?.textContent||"").trim();
 const canon=(doc.querySelector('link[rel="canonical"]')?.href||"").toLowerCase();
 const text=(doc.querySelector("h1")?.textContent||"").toLowerCase();
 let reviewed=null;
 for(const node of doc.querySelectorAll('script[type="application/ld+json"]')){
   try{
     const data=JSON.parse(node.textContent||"{}");
     const arr=Array.isArray(data?.["@graph"])?data["@graph"]:[data];
     for(const item of arr){
       if(item["@type"]==="Review")reviewed=item.itemReviewed?.["@type"]||"Review";
     }
   }catch(_){}
 }
 if(reviewed){
   if(reviewed==="VideoGame"||/gaming|ps[45]|videogiochi|xbox|nintendo/.test(section.toLowerCase()))return "Recensioni Gaming";
   if(reviewed==="Product"||/tech|hi-tech|tecnologia/.test(section.toLowerCase()))return "Recensioni Hi-Tech";
   return "Recensioni";
 }
 if(/news gaming/i.test(section)||/gaming-today/.test(canon))return "News Gaming";
 if(/news tech/i.test(section)||/news\.html/.test(canon))return "News Tech";
 if(/speciali/i.test(section))return "Speciali Tech";
 if(/recension/.test(section)||/recensione/.test(canon+" "+text)){
   return /gaming|videogiochi/i.test(section)?"Recensioni Gaming":/tech/i.test(section)?"Recensioni Hi-Tech":"Recensioni";
 }
 return /news/i.test(section)?"News Tech":section||"Article";
};
const editSEOInput=()=>({
 title:$("zeTitle")?.value?.trim()||"",
 category:seoCategory,body:body.innerText||"",
 cover:coverPanel.querySelector("img")?.getAttribute("src")||"",
 url:loaded?"/"+loaded.path:""
});
seoPanel?.attach(editSEOInput);
const refreshEditSEO=()=>{
 clearTimeout(seoTimer);
 seoTimer=setTimeout(()=>{if(loaded)seoPanel?.update(editSEOInput())},400);
};
$("zeTitle").addEventListener("input",refreshEditSEO);
body.addEventListener("input",refreshEditSEO);
coverPanel.querySelector("img").addEventListener("load",refreshEditSEO);

body.addEventListener("pointerdown",e=>{const im=e.target.closest(".photo img");if(!im)return;select(im.parentElement);drag={x:e.clientX,y:e.clientY,fx:Number($("zeX").value),fy:Number($("zeY").value)};im.setPointerCapture?.(e.pointerId)});
body.addEventListener("pointermove",e=>{if(!drag||!selected)return;if(Number($("zeZoom").value)<110)$("zeZoom").value=130;$("zeX").value=Math.min(100,Math.max(0,drag.fx+(drag.x-e.clientX)/3));$("zeY").value=Math.min(100,Math.max(0,drag.fy+(drag.y-e.clientY)/3));crop()});
body.addEventListener("pointerup",()=>drag=null);body.addEventListener("pointercancel",()=>drag=null);
body.onclick=e=>select(e.target.closest(".zt-media"));body.addEventListener("input",()=>dirty=true);$("zeTitle").addEventListener("input",()=>dirty=true);
for(let b of ui.querySelectorAll("[data-cmd]"))b.onclick=()=>{body.focus();const c=b.dataset.cmd;document.execCommand(c==="h2"||c==="p"?"formatBlock":c,false,c==="h2"?"H2":c==="p"?"P":null);dirty=true};
function insert(el){if(selected)selected.insertAdjacentElement("afterend",el);else body.append(el);select(el);dirty=true}
$("zeVideo").onclick=()=>{const raw=prompt("Inserisci il link YouTube");if(!raw)return;const id=yt(raw);if(!id){status("Link YouTube non valido.");return}insert(video(id))};
$("zeLink").onclick=()=>{const raw=prompt("Collegamento web");if(!raw)return;const id=yt(raw);if(id){insert(video(id));return}try{let u=new URL(raw);if(!["https:","http:"].includes(u.protocol))throw Error();body.focus();document.execCommand("createLink",false,u.href);dirty=true}catch{status("Link non valido.")}};
$("zePhoto").onclick=()=>$("zeFile").click();
$("zeFile").onchange=e=>{const file=e.target.files?.[0];e.target.value="";if(!file)return;if(!/^image\/(?:png|jpeg|webp)$/.test(file.type)||file.size>8e6){status("Usa JPG, PNG o WebP fino a 8 MB.");return}let reader=new FileReader();reader.onload=()=>insert(photo(reader.result,file.name));reader.readAsDataURL(file)};
$("zeUp").onclick=()=>{if(selected?.previousElementSibling){selected.previousElementSibling.before(selected);dirty=true}};
$("zeDown").onclick=()=>{if(selected?.nextElementSibling){selected.nextElementSibling.after(selected);dirty=true}};
$("zeDelete").onclick=()=>{if(selected&&confirm("Eliminare l'elemento selezionato?")){selected.remove();select(null);dirty=true}};
body.addEventListener("paste",e=>{const t=e.clipboardData?.getData("text/plain")?.trim(),id=yt(t);if(id){e.preventDefault();insert(video(id));status("Link YouTube trasformato automaticamente in player.")}});
function prepare(html){const doc=new DOMParser().parseFromString(html,"text/html"),article=doc.querySelector("article.article-main,article.story,article.zt-main.zt-article,article.zt-main,article.zt-article,main.content article.article-body,main.content article,article.zt-watch-article")||[...doc.querySelectorAll("main")].find(main=>main.querySelector("h1")&&main.querySelector(".article-copy"));if(!article)throw Error("Non è una pagina editoriale supportata.");
let holder=article.querySelector(":scope > .article-body, :scope > .body, :scope > .article-copy"), nodes=[],type="";
if(holder){type="holder";nodes=[holder]}
else if(article.matches(".zt-watch-article")){type="watch";nodes=[...article.children].filter(el=>!el.matches("h1"))}
else if(article.matches(".article-body")){type="self";for(const el of [...article.children]){if(el.matches(".zt-related-section,.zt-community-banner,.zt-community-area,.zt-subscribe-cta,.related,[data-zt-auto]"))break;nodes.push(el)}}
else{const cover=article.querySelector(":scope > figure.hero, :scope > img.article-hero, :scope > img.cover, :scope > img, :scope > .zt-studio-cover-viewport, :scope > figure:has(.zt-studio-cover-viewport), :scope > figure:has(> img)");let found=false;for(const el of [...article.children]){if(el===cover){found=true;continue}if(!found)continue;if(el.matches(".zt-related-section,.zt-community-banner,.zt-community-area,.zt-subscribe-cta,.related,.end,.zt-community,.zt-related,[data-zt-auto],script"))break;nodes.push(el)}type="children"}
if(!nodes.length)throw Error("Corpo articolo non individuato: salvataggio bloccato per sicurezza.");
let div=document.createElement("div");if(holder)div.innerHTML=holder.innerHTML;else nodes.forEach(n=>div.append(n.cloneNode(true)));
div.querySelectorAll("script,style,form,object,embed").forEach(x=>x.remove());
div.querySelectorAll("iframe").forEach(x=>{let id=yt(x.src);if(id)x.replaceWith(video(id));else x.remove()});
div.querySelectorAll(".zt-player[data-yt]").forEach(x=>{if(/^[\w-]{11}$/.test(x.dataset.yt))x.replaceWith(video(x.dataset.yt))});
div.querySelectorAll("img").forEach(img=>{if(img.closest("figure.zt-media"))return;let po=(img.style.objectPosition||"").match(/(\d+)%\s+(\d+)%/),f=photo(img.getAttribute("src")||"",img.alt,+((po||[])[1]||50),+((po||[])[2]||50));f.dataset.zoom=String(Math.max(1,Math.min(3,Number(img.dataset.ztZoom||1))));f.querySelector("img").style.transform="scale("+f.dataset.zoom+")";let old=img.closest("figure");if(old&&old.querySelectorAll("img").length===1)old.replaceWith(f);else img.replaceWith(f)});
return {doc,article,nodes,type,div};
}
function show(path,html,sha){let p=prepare(html);loaded={path,html,sha};$("zePath").value=path;
const lead=p.article.querySelector(".lead");leadBox.hidden=!lead;leadInput.value=lead?.textContent?.trim()||"";
const hero=p.doc.querySelector(".zt-studio-cover-viewport > img, main.content img.hero") || p.article.querySelector(":scope > figure.hero img,:scope > img.article-hero,:scope > img.cover,:scope > img, :scope > figure:has(> img) img");
coverPanel.hidden=false;coverPanel.dataset.replacement="false";if(!hero){coverPanel.querySelector("img").removeAttribute("src");coverPanel.dataset.x="50";coverPanel.dataset.y="50";coverPanel.dataset.zoom="1";}if(hero){coverPanel.querySelector("img").src=hero.getAttribute("src")||"";const point=(hero.style.objectPosition||"50% 50%").match(/(\d+)%\s+(\d+)%/);coverPanel.dataset.x=point?.[1]||50;coverPanel.dataset.y=point?.[2]||50;coverPanel.dataset.zoom=String(Number(hero.getAttribute("data-zt-zoom")||1));coverPanel.querySelector("img").style.objectPosition=coverPanel.dataset.x+"% "+coverPanel.dataset.y+"%";coverPanel.querySelector("img").style.transform="scale("+coverPanel.dataset.zoom+")";coverPanel.querySelector("img").style.transformOrigin=coverPanel.dataset.x+"% "+coverPanel.dataset.y+"%";}$("zeTitle").disabled=false;$("zeTitle").value=(p.article.querySelector("h1")||p.doc.querySelector("main.content h1"))?.textContent?.trim()||"";body.replaceChildren(...[...p.div.childNodes]);seoCategory=categoryFromDoc(p.doc);seoSourceDate=p.doc.querySelector('meta[property="article:published_time"]')?.content||"";seoPanel?.update(editSEOInput(),true);select(null);dirty=false;ui.hidden=false;status("Articolo originale caricato: "+path+". Modifica testo, foto, link e video. SEO controllabile prima del salvataggio.");}
async function open(raw){const path=goodPath(raw);if(!path){status("Inserisci un link articolo valido.");return}if(dirty&&!confirm("Scartare le modifiche non salvate?"))return;try{let html,sha;if(isDemo()){html=localStorage.getItem(storage(path))||window.ZTStudioDemoArticle.html;sha="locale"}else{let api=window.ZTStudioGitHub;if(!api?.isAuthenticated())throw Error("Collega prima GitHub nello Studio.");let r=await api.read(path);if(r?.content){html=b64decode(r.content);sha=r.sha}else{const live=await fetch("/"+path,{cache:"no-store"});if(!live.ok)throw Error("Articolo non presente né su GitHub né sul sito.");html=await live.text();sha=null}}show(path,html,sha)}catch(e){status("Apertura non riuscita: "+e.message)}}
function build(){if(!loaded)throw Error("Apri prima un articolo.");let p=prepare(loaded.html),out=document.createElement("div");out.innerHTML=body.innerHTML;
out.querySelectorAll("script,style,object,form").forEach(x=>x.remove());out.querySelectorAll("*").forEach(el=>[...el.attributes].forEach(a=>{if(/^on/i.test(a.name))el.removeAttribute(a.name)}));
out.querySelectorAll(".ze-picked").forEach(x=>x.classList.remove("ze-picked"));
out.querySelectorAll("figure.zt-media.video").forEach(f=>{const id=f.dataset.video;if(!/^[\w-]{11}$/.test(id||""))throw Error("ID video non valido");f.className="zt-studio-video";f.removeAttribute("contenteditable");f.innerHTML='<div class="zt-player" style="width:100%;max-width:850px;aspect-ratio:16/9;background:#111" data-yt="'+id+'"><iframe style="display:block;width:100%;height:100%;aspect-ratio:16/9;border:0" src="https://www.youtube-nocookie.com/embed/'+id+'" title="YouTube" loading="lazy" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe></div>'});
out.querySelectorAll("figure.zt-media.photo").forEach(f=>{const img=f.querySelector("img"),src=img?.getAttribute("src")||"";if(!(/^(https:\/\/|\/(?!\/)|data:image\/(?:png|jpeg|webp);base64,)/i.test(src)))throw Error("Immagine non sicura");const x=Math.max(0,Math.min(100,Number(f.dataset.x)||0)),y=Math.max(0,Math.min(100,Number(f.dataset.y)||0));f.className="zt-studio-photo";f.removeAttribute("contenteditable");f.removeAttribute("data-x");f.removeAttribute("data-y");img.style.setProperty("object-position",x+"% "+y+"%","important");img.style.aspectRatio="16/9";img.style.width="100%";img.style.objectFit="cover";img.style.setProperty("transform","scale("+Math.max(1,Math.min(3,+f.dataset.zoom||1))+")","important");img.style.transformOrigin=x+"% "+y+"%";img.setAttribute("data-zt-crop",x+","+y);img.setAttribute("data-zt-zoom",f.dataset.zoom||"1");f.style.aspectRatio="16/9";f.style.overflow="hidden";f.querySelector("figcaption")?.remove()});
if(p.type==="holder")p.nodes[0].innerHTML=out.innerHTML;else{const before=p.nodes[0];for(const n of [...out.childNodes])before.before(n);for(const n of p.nodes)n.remove()}
let title=$("zeTitle").value.trim();if(!title)throw Error("Titolo obbligatorio");const titleNode=p.article.querySelector("h1")||p.doc.querySelector("main.content h1");if(!titleNode)throw Error("Titolo originale mancante");titleNode.textContent=title;
const leadNode=p.article.querySelector(".lead");if(leadNode)leadNode.textContent=leadInput.value.trim();
let hero=p.doc.querySelector(".zt-studio-cover-viewport > img, main.content img.hero") || p.article.querySelector(":scope > figure.hero img,:scope > img.article-hero,:scope > img.cover,:scope > img, :scope > figure:has(> img) img");
if(!hero&&coverPanel.dataset.replacement==="true"){
  const insertAfter=p.article.querySelector("h1")||p.doc.querySelector("main h1");
  if(!insertAfter)throw Error("Titolo mancante: impossibile inserire una cover.");
  hero=p.doc.createElement("img");hero.className="article-hero";
  hero.alt=title;insertAfter.insertAdjacentElement("afterend",hero);
}
if(hero&&!coverPanel.hidden){if(coverPanel.dataset.replacement==="true"){hero.setAttribute("src",coverPanel.querySelector("img").getAttribute("src")||"");hero.setAttribute("alt",title);hero.removeAttribute("srcset");hero.removeAttribute("sizes");hero.removeAttribute("data-src");hero.removeAttribute("width");hero.removeAttribute("height");}const x=Math.max(0,Math.min(100,+coverPanel.dataset.x||0)),y=Math.max(0,Math.min(100,+coverPanel.dataset.y||0));hero.style.objectFit="cover";hero.style.setProperty("object-position",x+"% "+y+"%","important");hero.setAttribute("data-zt-crop",x+","+y);const zoom=Math.max(1,Math.min(3,+coverPanel.dataset.zoom||1));hero.setAttribute("data-zt-zoom",String(zoom));let frame=hero.parentElement?.classList.contains("zt-studio-cover-viewport")?hero.parentElement:null;if(!frame){frame=p.doc.createElement("div");frame.className="zt-studio-cover-viewport";hero.replaceWith(frame);frame.append(hero)}frame.style.cssText="position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;margin:0 0 24px";hero.style.setProperty("width","100%","important");hero.style.setProperty("height","100%","important");hero.style.setProperty("aspect-ratio","auto","important");hero.style.setProperty("max-height","none","important");hero.style.setProperty("transform","scale("+zoom+")","important");hero.style.setProperty("transform-origin",x+"% "+y+"%","important")}
const summary=out.textContent.replace(/\s+/g," ").trim().slice(0,158)||title,doc=p.doc;
doc.title=title+" | ZazoomTek";for(const [sel,val] of [['meta[name="description"]',summary],['meta[property="og:title"]',title],['meta[property="og:description"]',summary]]){let m=doc.head.querySelector(sel);if(m)m.content=val}
doc.querySelectorAll('script[type="application/ld+json"]').forEach(s=>{try{let o=JSON.parse(s.textContent);if(["Article","NewsArticle","Review","BlogPosting"].includes(o["@type"])){o.headline=title;o.description=summary;o.dateModified=new Date().toISOString();s.textContent=JSON.stringify(o).replace(/</g,"\\u003c")}}catch{}});
return "<!doctype html>\n"+doc.documentElement.outerHTML;
}
async function save(){if(!loaded||busy)return;busy=true;$("zeSave").disabled=true;try{status("Analisi SEO e verifica prima del salvataggio…");if(!seoPanel||!seoAPI?.apply)throw Error("Motore SEO editoriale non disponibile: nessun salvataggio.");const seo=seoPanel.prepare(editSEOInput());let html=build(),path=loaded.path,doc=new DOMParser().parseFromString(html,"text/html"),counter=0,api=window.ZTStudioGitHub;

const savedHero=doc.querySelector(".zt-studio-cover-viewport > img, main.content img.hero")||doc.querySelector("article.article-main > img.article-hero,article.article-main > .zt-studio-cover-viewport > img");
let newCoverSrc=savedHero?.getAttribute("src")||"";
if(coverPanel.dataset.replacement==="true"&&newCoverSrc.startsWith("data:image/webp;base64,")){
 if(!isDemo()){
   if(!api?.isAuthenticated())throw Error("Collega GitHub prima di salvare la nuova cover.");
   const key=path.replace(/\.html$/,"").replace(/[^a-zA-Z0-9_.-]/g,"-").slice(0,90);
   const dest="assets/studio/"+key+"-cover-"+Date.now()+"-"+Math.random().toString(36).slice(2,8)+".webp";
   await api.create(dest,newCoverSrc.slice("data:image/webp;base64,".length),"studio: sostituisce cover di "+path);
   newCoverSrc="/"+dest;
   savedHero.setAttribute("src",newCoverSrc);
 }
 const canonicalCover=newCoverSrc.startsWith("/")?"https://zazoomtek.it"+newCoverSrc:newCoverSrc;
 for(const sel of ['meta[property="og:image"]','meta[name="twitter:image"]']){
   let tag=doc.head.querySelector(sel);
   if(!tag){tag=doc.createElement("meta");tag.setAttribute(sel.includes("twitter:")?"name":"property",sel.includes("twitter:")?"twitter:image":"og:image");doc.head.appendChild(tag)}
   tag.content=canonicalCover;
 }
 const metaAlt=doc.head.querySelector('meta[property="og:image:alt"]');
 if(metaAlt)metaAlt.content=doc.querySelector("h1")?.textContent?.trim()||"ZazoomTek";
 doc.querySelectorAll('script[type="application/ld+json"]').forEach(script=>{
   try{
     const schema=JSON.parse(script.textContent);
     const update=(entry)=>{
       if(!entry||typeof entry!=="object")return;
       if(Array.isArray(entry)){entry.forEach(update);return;}
       if(["Article","NewsArticle","Review","BlogPosting"].some(t=>[entry["@type"]].flat().includes(t))){
         entry.image=canonicalCover;
       }
       if(entry["@graph"])update(entry["@graph"]);
     };
     update(schema);script.textContent=JSON.stringify(schema).replace(/</g,"\\u003c");
   }catch(_){}
 });
}

for(const im of doc.querySelectorAll(".zt-studio-photo img")){let src=im.getAttribute("src")||"",match=/^data:image\/(jpeg|png|webp);base64,([A-Za-z0-9+/=]+)$/i.exec(src);if(!match||isDemo())continue;const dest="assets/studio/"+path.replace(/\.html$/,"")+"-"+Date.now()+"-"+(++counter)+"."+({jpeg:"jpg",png:"png",webp:"webp"}[match[1]]);await api.create(dest,match[2],"studio: foto per "+path);im.setAttribute("src","/"+dest)}
// Apply metadata after cover replacement/upload so OG/JSON-LD use the FINAL URL.
const seoFinalCover=(doc.querySelector(".zt-studio-cover-viewport > img,main.content img.hero,img.article-hero,img.cover")?.getAttribute("src")||"");
const seoFinalDate=new Date().toISOString();
seoAPI.apply(doc,seo,{
 category:seoCategory,body:body.innerText,
 cover:seoFinalCover.startsWith("/")?seoFinalCover:undefined,
 url:"/"+path,published:seoSourceDate||undefined,date:seoFinalDate
});
html="<!doctype html>\n"+doc.documentElement.outerHTML;
if(isDemo()){localStorage.setItem(storage(path),html);show(path,html,"locale");status("Modifiche salvate localmente. Riapri l’articolo: sono persistenti. Nessuna pubblicazione.");return}
if(!api?.isAuthenticated())throw Error("Accesso GitHub non verificato.");let override="editorial/studio-overrides/"+path.replace(/\.html$/,".json"),old=await api.read(override),data=JSON.stringify({version:1,path,html,owner_edited:true},null,2)+"\n";
await api.write(override,data,old?.sha||null,"studio: proteggi revisione "+path);
let result=await api.write(path,html,loaded.sha,"studio: modifica articolo originale "+path);
show(path,html,result.content?.sha||loaded.sha);status("Salvato su GitHub e protetto dagli import successivi. Pubblicazione solo con Master.");
}catch(e){status("Nessuna conferma di salvataggio: "+e.message)}finally{busy=false;$("zeSave").disabled=false}}
$("zeClose").onclick=()=>{if(dirty&&!confirm("Chiudere senza salvare?"))return;ui.hidden=true};
$("zeOpen").onclick=()=>open($("zePath").value);$("zePath").onkeydown=e=>{if(e.key==="Enter")open($("zePath").value)};
$("zeSave").onclick=save;
$("zePreview").onclick=()=>{try{
 const doc=new DOMParser().parseFromString(build(),"text/html");
 if(!seoPanel||!seoAPI)throw Error("Motore SEO non disponibile.");
 const seo=seoPanel.prepare(editSEOInput());
 seoAPI.apply(doc,seo,{category:seoCategory,body:body.innerText,url:"/"+loaded.path,published:seoSourceDate||undefined});
 prev.querySelector("iframe").srcdoc="<!doctype html>\n"+doc.documentElement.outerHTML;
 prev.hidden=false;
}catch(e){status("Anteprima SEO non disponibile: "+e.message)}};$("zeEndPreview").onclick=()=>prev.hidden=true;
const sidebar=document.querySelector(".sidebar");if(sidebar){const b=document.createElement("button");b.className="navbtn";b.id="zeNav";b.textContent="✎  Modifica articoli";(document.getElementById("navDraft")||sidebar.firstElementChild).insertAdjacentElement("afterend",b);b.onclick=()=>ui.hidden=false}
const query=new URLSearchParams(location.search).get("edit");if(query){ui.hidden=false;$("zePath").value=query;let attempts=0;const autoOpen=()=>{if(isDemo()||window.ZTStudioGitHub?.isAuthenticated?.()){open(query);return}if(++attempts<=40){setTimeout(autoOpen,250);return}status("Collega GitHub con l’accesso permanente dello Studio, quindi premi Apri articolo.")};setTimeout(autoOpen,200)}
if(isDemo()){ui.hidden=false;$("zePath").value=window.ZTStudioDemoArticle.path;setTimeout(()=>open(window.ZTStudioDemoArticle.path),80)}
})();
