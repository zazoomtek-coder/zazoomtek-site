/* ZazoomTek Studio - impaginazione conforme ai modelli editoriali esistenti.
 * I file sorgente sono istantanee noindex degli impaginati approvati.
 * Non modifica Home, archivi, importatori o recensioni gia' pubblicate.
 */
(function(){
"use strict";
const BASE="/studio/";
const SOURCES={news:BASE+"template-news.html",review:BASE+"template-review.html"};
const cache={};
const REVIEW=/^Recensioni /;
const SECTIONS=["Storia","Gameplay","Aspetto tecnico","Esperienza complessiva","Conclusioni","Materiali e design","Hardware e prestazioni","Uso quotidiano","Prestazioni","Design","Caratteristiche","Connettivita","Connettività","Autonomia","Qualità audio","Qualità video","Software","Test","Considerazioni finali"];
const SHORT_HEADINGS=["Pro","Contro","Vantaggi","Svantaggi"];
const enc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const normal=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase().replace(/\s+/g," ");
function categoryLabel(category){return REVIEW.test(category)?"Recensioni":(/^Speciali (Tech|Gaming)$/.test(category)?"Speciali":(category==="News Gaming"||category==="News Tech"?"News":category));}
function categoryLink(category){return REVIEW.test(category)?"/recensioni-scritte.html":category==="News Gaming"?"/gaming-today.html":category==="News Tech"?"/news.html":category==="Guide"?"/guide.html":category==="Extra"?"/extra.html":category==="Tech Impact"?"/tech-today.html":category==="Gaming Inside"?"/gaming-today.html":/^Speciali (Tech|Gaming)$/.test(category)?"/speciali.html":category==="Test"?"/test.html":category==="Unboxing"?"/unboxing.html":"/news.html";}
function canonical(url){return "https://zazoomtek.it/"+String(url||"").replace(/^\/+/,"");}
async function template(kind){
 if(!cache[kind])cache[kind]=fetch(SOURCES[kind],{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Modello grafico "+kind+" non disponibile ("+r.status+"). Pubblicazione interrotta.");return r.text();}).catch(e=>{delete cache[kind];throw e;});
 return cache[kind];
}
function extractItems(block){
 const lis=[...block.querySelectorAll("li")].map(x=>x.textContent.trim()).filter(Boolean);
 if(lis.length)return lis;
 let s=(block.textContent||"").trim().replace(/^\s*[•\-]\s*/,"");
 return s.split(/\s*(?:\n|;|•)\s*/).map(x=>x.trim().replace(/^[-•]\s*/,"")).filter(Boolean);
}
function formatBody(raw,isReview){
 const holder=document.createElement("div");holder.innerHTML=String(raw||"");
 holder.querySelectorAll("script,style,iframe").forEach(e=>e.remove());
 // L'editor puo' restituire div, p o righe non formattate: uniforma i paragrafi.
 [...holder.childNodes].forEach(n=>{
  if(n.nodeType===3&&n.textContent.trim()){const p=document.createElement("p");p.textContent=n.textContent;holder.replaceChild(p,n);}
  else if(n.nodeType===1&&n.tagName==="DIV"&&!n.classList.contains("zt-video")&&!n.classList.contains("zt-attachment")&&!n.classList.contains("inline-link")&&!n.classList.contains("insert")&&!n.querySelector("figure,ul,ol,div[data-zt-kind]")){
   const p=document.createElement("p");p.innerHTML=n.innerHTML;holder.replaceChild(p,n);
  }
 });
 let score=null,scoreComment="",positive=[],negative=[],mode="";
 const all=[...holder.children];
 for(const el of all){
  if(!el.isConnected)continue;
  const rawText=(el.textContent||"").trim();
  if(!rawText){if(["DIV","P"].includes(el.tagName))el.remove();continue;}
  const normalized=normal(rawText.replace(/[:：]\s*$/,""));
  if(isReview){
   const vote=rawText.match(/^(?:⭐\s*)?voto\s+finale\s*[:：-]?\s*(10(?:[.,]0+)?|[0-9](?:[.,][0-9]+)?)\s*\/\s*10(?:\s*[-—:]\s*(.*))?$/i);
   if(vote){const value=Number(vote[1].replace(",","."));if(value>=0&&value<=10){score=vote[1].replace(",",".");scoreComment=vote[2]||scoreComment;el.remove();continue;}}
   const comment=rawText.match(/^(?:commento\s+al\s+voto|giudizio\s+finale)\s*[:：]\s*(.+)$/i);
   if(comment){scoreComment=comment[1].trim();el.remove();continue;}
   const type=SHORT_HEADINGS.find(x=>normal(x)===normalized);
   if(type){mode=["pro","vantaggi"].includes(normal(type))?"pro":"contro";el.remove();continue;}
   const inline=rawText.match(/^(Pro|Contro)\s*[:：]\s*(.+)$/i);
   if(inline){mode=normal(inline[1])==="pro"?"pro":"contro";(mode==="pro"?positive:negative).push(...extractItems({textContent:inline[2],querySelectorAll:()=>[]}));el.remove();continue;}
   if(mode){
    const head=SECTIONS.some(x=>normal(x)===normalized)||(el.matches("h2,h3"));
    if(!head){(mode==="pro"?positive:negative).push(...extractItems(el));el.remove();continue;}
    mode="";
   }
  }
  const h=SECTIONS.find(x=>normal(x)===normalized);
  if(isReview&&normalized==="introduzione"){el.remove();continue;}
  if(h&&["P","DIV","H2","H3"].includes(el.tagName)){
    const h2=document.createElement("h2");h2.textContent=h;el.replaceWith(h2);continue;
  }
  if(el.matches("h3")&&isReview){const h2=document.createElement("h2");h2.innerHTML=el.innerHTML;el.replaceWith(h2);}
 }
 // Mantiene le immagini e i link, ma elimina gli spazi di impaginazione vuoti.
 holder.querySelectorAll("p").forEach(p=>{if(!p.textContent.trim()&&!p.querySelector("img,iframe,video"))p.remove();});
 if(isReview&&!scoreComment){
  const headings=[...holder.querySelectorAll("h2")];
  const concl=headings.find(h=>normal(h.textContent)==="conclusioni");
  if(concl){let next=concl.nextElementSibling;while(next&&next.tagName!=="H2"){if(next.matches("p")&&next.textContent.trim()){scoreComment=next.textContent.trim().slice(0,310);break;}next=next.nextElementSibling;}}
 }
 // La video-recensione va dopo il voto e i Pro/Contro, non dentro la sezione Gameplay.
 let videos=[];
 if(isReview)holder.querySelectorAll(".zt-video").forEach(v=>{videos.push(v.outerHTML);v.remove();});
 return {body:holder.innerHTML,score,scoreComment,positive,negative,videos};
}
function setMeta(doc,key,value,attr="name"){
 let e=doc.head.querySelector('meta['+attr+'="'+key+'"]');
 if(!e){e=doc.createElement("meta");e.setAttribute(attr,key);doc.head.append(e);}e.setAttribute("content",value);
}
function newElement(doc,tag,cls,txt){const e=doc.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e;}
function relatedSection(doc){
 const sec=newElement(doc,"section","zt-related-section");
 sec.setAttribute("aria-labelledby","zt-related-title");
 sec.innerHTML='<div class="zt-related-head"><h2 id="zt-related-title">Articoli correlati</h2></div><div class="zt-related-grid"></div>';
 return sec;
}
function replaceAside(doc){
 const aside=doc.querySelector("aside.article-side");
 if(!aside)return;
 aside.replaceChildren();
 aside.innerHTML='<section class="side-box zt-mix-recent"><a class="module-title" href="/news.html">Ultimi articoli</a><div class="zt-studio-side-items"></div></section><section class="side-box zt-mix-video"><a class="module-title" href="https://www.youtube.com/@ZazoomTek/videos">Ultimi video ZazoomTek</a><p class="zt-studio-video-link"><a href="https://www.youtube.com/@ZazoomTek/videos">Guarda le video recensioni e i gameplay su YouTube →</a></p></section>';
}
function appendRating(doc,article,info){
 if(info.score==null)return;
 const box=newElement(doc,"div","rating");
 box.innerHTML='<div><small>VOTO FINALE</small><strong>'+enc(info.score)+'<span>/10</span></strong></div><p>'+enc(info.scoreComment||"Valutazione finale della recensione ZazoomTek.")+'</p>';
 article.append(box);
}
function appendProsCons(doc,article,info){
 if(!info.positive.length&&!info.negative.length)return;
 const box=newElement(doc,"div","proscons");
 for(const [title,cls,items] of [["Pro","pros",info.positive],["Contro","cons",info.negative]]){
   if(!items.length)continue;
   const part=newElement(doc,"section",cls);const h=newElement(doc,"h2","",title);const ul=newElement(doc,"ul","");
   items.forEach(x=>ul.append(newElement(doc,"li","",x)));
   part.append(h,ul);box.append(part);
 }
 article.append(box);
}
function putTextArticle(doc,opt,kind){
 const review=kind==="review";const label=categoryLabel(opt.category),link=categoryLink(opt.category);
 const formatted=formatBody(opt.body,review);
 const host=review?doc.querySelector("main.content"):doc.querySelector("article.article-main");
 if(!host)throw Error("Il modello approvato non contiene la struttura attesa: "+kind);
 if(review){
   const crumb=host.querySelector(".crumb");if(crumb)crumb.innerHTML='<a href="/">Home</a> / <a href="'+enc(link)+'">Recensioni</a> / '+enc(opt.title);
   const heading=host.querySelector("h1");if(heading){
     const pieces=opt.title.split(/\s+\|\s+/);
     heading.replaceChildren(newElement(doc,"span","zt-title-main",pieces[0]),newElement(doc,"span","zt-title-subtitle",pieces.slice(1).join(" | ")));
     if(pieces.length===1)heading.querySelector(".zt-title-subtitle").remove();
   }
   const meta=host.querySelector(".meta");
   if(meta)meta.innerHTML='<span>👤 ZazoomTek</span><span>📅 '+enc(new Date(opt.date).toLocaleDateString("it-IT",{day:"numeric",month:"long",year:"numeric"}))+'</span><span>🏷 '+enc(opt.category)+'</span>';
   const cover=host.querySelector("img.hero");if(cover){cover.src=opt.cover;cover.alt=opt.title;cover.removeAttribute("width");cover.removeAttribute("height");}
   host.querySelectorAll(".hero-caption,.zt-poly-video-jump").forEach(el=>el.remove());
   const article=host.querySelector("article.article-body.article-main");
   if(!article)throw Error("Manca il corpo della recensione nel modello approvato.");
   article.innerHTML=formatted.body;
   appendRating(doc,article,formatted);
   appendProsCons(doc,article,formatted);
   formatted.videos.forEach(html=>{const holder=doc.createElement("div");holder.innerHTML=html;article.append(newElement(doc,"h2","","Video recensione / trailer"),...holder.children);});
   article.append(relatedSection(doc));
   doc.querySelectorAll("script").forEach(el=>{if(/zt-poly-play|zt-poly-video-container|cYkb8Z7JyqQ/.test(el.textContent||""))el.remove();});
 } else {
   const crumb=host.querySelector(".breadcrumbs");if(crumb)crumb.innerHTML='<a href="/">Home</a> / <a href="'+enc(link)+'">'+enc(label)+'</a> / '+enc(opt.title);
   const h1=host.querySelector("h1");if(h1)h1.textContent=opt.title;
   const meta=host.querySelector(".article-meta");if(meta)meta.innerHTML='<span>👤 ZazoomTek</span><span>📅 '+enc(new Date(opt.date).toLocaleDateString("it-IT",{day:"numeric",month:"long",year:"numeric"}))+'</span><span>🏷 '+enc(label)+'</span>';
   const cover=host.querySelector("img.article-hero");if(cover){cover.src=opt.cover;cover.alt=opt.title;}
   const body=host.querySelector(".article-body");if(!body)throw Error("Manca il corpo della news nel modello approvato.");
   body.innerHTML=formatted.body;
   host.querySelectorAll(".zt-related-section").forEach(el=>el.remove());
   body.after(relatedSection(doc));
   const topcat=doc.querySelector(".section-title strong,.section-header strong,.section-banner strong");
   if(topcat)topcat.textContent=label;
 }
 replaceAside(doc);
}
const EXTRA_CSS='.zt-studio-side-items{display:grid;gap:0}.zt-studio-side-items a{display:grid;grid-template-columns:93px 1fr;gap:10px;padding:10px 12px;border-bottom:1px solid #e8e8e8;color:#252525;text-decoration:none;align-items:center;font-size:12px;font-weight:750;line-height:1.35}.zt-studio-side-items img{width:93px;aspect-ratio:16/9;object-fit:cover}.zt-studio-video-link{padding:12px;font-size:13px}.zt-studio-video-link a{color:#b40f2a}.zt-related-grid .zt-related-card img{aspect-ratio:16/9;object-fit:cover}.zt-related-section{margin-top:24px}.article-body h2{font-weight:800}.article-body p{margin-bottom:12px}.proscons:has(section:only-child){grid-template-columns:1fr}';
const SIDEBAR_SCRIPT="(function(){var path=location.pathname;fetch('/zt-sidebar-feed.json',{cache:'no-store'}).then(function(r){if(!r.ok)throw Error('feed');return r.json()}).then(function(feed){var arr=(feed.news||[]).filter(function(x){return x&&x.title&&x.url&&x.image&&x.url!==path;});var aside=document.querySelector('.zt-studio-side-items');if(aside){arr.slice(0,9).forEach(function(x){var a=document.createElement('a'),im=document.createElement('img'),b=document.createElement('span');a.href=x.url;im.src=x.image;im.loading='lazy';im.alt='';b.textContent=x.title;a.append(im,b);aside.append(a);});}var grid=document.querySelector('.zt-related-grid');if(grid){arr.slice(0,4).forEach(function(x){var a=document.createElement('article'),ln=document.createElement('a'),im=document.createElement('img'),h=document.createElement('h3'),t=document.createElement('a');a.className='zt-related-card';ln.href=x.url;im.loading='lazy';im.src=x.image;im.alt=x.title;ln.append(im);t.href=x.url;t.textContent=x.title;h.append(t);var copy=document.createElement('div');copy.className='zt-related-copy';copy.append(h);a.append(ln,copy);grid.append(a);});}}).catch(function(){});document.addEventListener('click',function(e){var b=e.target.closest('.zt-player[data-yt] button');if(!b)return;var p=b.closest('.zt-player'),id=p.getAttribute('data-yt');if(!/^[A-Za-z0-9_-]{11}$/.test(id||''))return;var f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&rel=0';f.title='Video YouTube';f.setAttribute('allow','autoplay; encrypted-media; picture-in-picture');f.allowFullscreen=true;p.replaceChildren(f);});})();";
async function build(opt){
 const kind=REVIEW.test(opt.category)?"review":"news";
 if(!opt.title||!opt.category||!opt.cover||!opt.body)throw Error("Titolo, categoria, copertina e testo obbligatori.");
 const html=await template(kind);
 const doc=new DOMParser().parseFromString(html,"text/html");
 putTextArticle(doc,opt,kind);
 doc.title=opt.title+" | ZazoomTek";
 let canon=doc.querySelector('link[rel="canonical"]');if(!canon){canon=doc.createElement("link");canon.rel="canonical";doc.head.append(canon);}canon.href=canonical(opt.url);
 const description=String(opt.description||"").slice(0,155);
 setMeta(doc,"description",description);setMeta(doc,"robots","index,follow,max-image-preview:large");
 setMeta(doc,"og:title",opt.title,"property");setMeta(doc,"og:description",description,"property");setMeta(doc,"og:image",canonical(opt.cover),"property");setMeta(doc,"og:url",canonical(opt.url),"property");setMeta(doc,"og:type","article","property");
 setMeta(doc,"twitter:card","summary_large_image");setMeta(doc,"twitter:image",canonical(opt.cover));
 setMeta(doc,"article:published_time",opt.date,"property");setMeta(doc,"article:modified_time",opt.date,"property");
 doc.head.querySelectorAll('script[type="application/ld+json"]').forEach(el=>el.remove());
 const isReview=kind==="review";
 const schema={"@context":"https://schema.org","@type":isReview?"Review":(["News Tech","News Gaming"].includes(opt.category)?"NewsArticle":"Article"),headline:opt.title,description,image:[canonical(opt.cover)],datePublished:opt.date,dateModified:opt.date,author:{"@type":"Organization",name:"ZazoomTek"},publisher:{"@type":"Organization",name:"ZazoomTek"},mainEntityOfPage:canonical(opt.url)};
 const info=formatBody(opt.body,isReview);
 if(isReview){schema.itemReviewed={"@type":"CreativeWork",name:opt.title};if(info.score!=null)schema.reviewRating={"@type":"Rating",ratingValue:Number(info.score),bestRating:10,worstRating:0};}
 const ld=doc.createElement("script");ld.type="application/ld+json";ld.textContent=JSON.stringify(schema).replace(/</g,"\\u003c");doc.head.append(ld);
 // SEO editoriale viene applicato all'HTML definitivo senza duplicati.
 if(!window.ZTStudioSEO?.apply)throw Error("Motore SEO editoriale non caricato: pubblicazione interrotta.");
 const smart=opt.seo||window.ZTStudioSEO.analyze({title:opt.title,category:opt.category,body:opt.body,cover:opt.cover,url:opt.url});
 window.ZTStudioSEO.apply(doc,smart,{category:opt.category,body:opt.body,cover:opt.cover,url:opt.url,date:opt.date,published:opt.date});

 const style=doc.createElement("style");style.textContent=EXTRA_CSS;doc.head.append(style);
 const script=doc.createElement("script");script.textContent=SIDEBAR_SCRIPT;doc.body.append(script);
 return "<!doctype html>\n"+doc.documentElement.outerHTML;
}
function preview(){
 if(!window.ZTStudio||!window.ZTStudio.safeDoc)return;
 const title=document.getElementById("headline").value.trim();
 const category=document.getElementById("category").value;
 const cover=window.ZTStudioCover?.export?.()||document.getElementById("coverPreview").getAttribute("src");
 if(!title||!cover||!document.getElementById("editor").innerText.trim()){alert("Per l'anteprima completa inserisci titolo, testo e copertina.");return;}
 let overlay=document.getElementById("zt-exact-preview");
 if(!overlay){
  overlay=document.createElement("div");overlay.id="zt-exact-preview";
  overlay.style.cssText="position:fixed;inset:0;z-index:999999;background:#111e;padding:2vh 2vw;display:none";
  overlay.innerHTML='<div style="background:#fff;height:96vh;display:flex;flex-direction:column;border-radius:9px;overflow:hidden"><div style="display:flex;justify-content:space-between;align-items:center;padding:9px 15px;font:700 14px Arial"><span>Anteprima reale · stesso modello della pubblicazione</span><button id="zt-exact-close" type="button" style="background:#d51232;color:#fff;border:0;padding:8px 15px;border-radius:5px;cursor:pointer">Chiudi</button></div><iframe title="Anteprima impaginata del sito" sandbox="allow-scripts allow-same-origin" style="border:0;width:100%;flex:1;background:#fff"></iframe></div>';
  document.body.append(overlay);overlay.querySelector("#zt-exact-close").onclick=()=>overlay.style.display="none";
 }
 overlay.style.display="block";
 const frame=overlay.querySelector("iframe");
 frame.srcdoc='<p style="font-family:Arial;padding:35px">Caricamento del modello editoriale…</p>';
 const body=window.ZTStudio.safeDoc(),date=new Date().toISOString();
 build({title,category,cover,body,description:"",date,url:"/anteprima-studio.html",seo:window.ZTStudioSEOPrepare?.({title,category,body,cover,url:"/anteprima-studio.html"})})
 .then(html=>{if(overlay.style.display==="block")frame.srcdoc=html;})
 .catch(e=>{frame.srcdoc='<p style="font-family:Arial;padding:35px;color:#b00">'+enc(e.message)+'</p>';});
}
window.ZTStudioLayouts={build,preview,formatBody};
const previewBtn=document.getElementById("previewBtn");if(previewBtn)previewBtn.onclick=preview;
})();