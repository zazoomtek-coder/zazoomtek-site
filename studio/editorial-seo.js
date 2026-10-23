/* Studio SEO editoriale: offline, deterministico, solo contenuti effettivamente scritti. */
(function(){
"use strict";
const stop=new Set("a ad ai al alla alle anche altro come con cosa da dai dal della dello degli dei del delle dopo e ed è gli ha hanno i il in la le lo ma nei nel nella non o per più piu prima primo quando questa questo questi queste si sono su sul sulla tra un una uno che cui sarà del tutti tutte tutto nuovo nuova notizia news articolo recensione review guida scopri test video".split(" "));
const strip=s=>String(s||"").replace(/<[^>]*>/g," ").replace(/&nbsp;/g," ").replace(/&amp;/g,"&").replace(/\s+/g," ").trim();
const norm=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const words=s=>strip(s).match(/[\p{L}\p{N}]+/gu)||[];
const significant=s=>words(s).filter(x=>x.length>2&&!stop.has(norm(x)));
const unique=a=>[...new Set(a.filter(Boolean))];
const trim=(s,max)=>{s=String(s||"").replace(/\s+/g," ").trim();if(s.length<=max)return s;const p=s.slice(0,max+1),j=p.lastIndexOf(" ");return (j>max*.6?p.slice(0,j):p.slice(0,max)).replace(/[\s,;:–-]+$/,"").replace(/\s+(?:e|di|da|del|della|con|per|in|su|a|un|una|il|la|che|tra)$/i,"")};
const abs=s=>{try{const u=new URL(s,"https://zazoomtek.it/");return u.hostname==="zazoomtek.it"&&u.protocol==="https:"?u.href:null}catch{return null}};
const rating=s=>{const m=String(s||"").match(/\bvoto\s+finale\s*[:：-]?\s*(10(?:[.,]0+)?|[0-9](?:[.,]\d+)?)\s*\/\s*10\b/i);return m?Number(m[1].replace(",",".")):null};
const typeFor=category=>/^Recensioni\b/i.test(category)?"Review":/^News\b/i.test(category)?"NewsArticle":"Article";
function analyze(data){
 const title=strip(data.title),category=String(data.category||"").trim(),body=strip(data.body);
 if(title.length<10||!category||words(body).length<35)throw Error("SEO non generato: servono categoria, titolo e almeno 35 parole di testo concreto.");
 const titleTerms=new Set(significant(title).map(norm));
 const chunks=(body.match(/[^.!?;\n]+(?:[.!?;]|$)/g)||[]).map((text,index)=>({text:text.trim(),index})).filter(x=>words(x.text).length>=7);
 if(!chunks.length)throw Error("SEO non generato: non trovo frasi informative sufficienti.");
 const ranked=chunks.map(x=>({...x,score:significant(x.text).filter(w=>titleTerms.has(norm(w))).length*3+(x.text.length>=70&&x.text.length<=180?2:0)+(x.index>0?1:0)})).sort((a,b)=>b.score-a.score);
 const evidence=ranked.slice(0,3).map(x=>x.text.replace(/[.!?;]+$/,""));
 const description=trim(title+": "+evidence.join(" · "),155);
 if(description.length<100)throw Error("SEO non generato: la meta description sarebbe troppo generica. Aggiungi dettagli verificabili.");
 const freq=new Map(),terms=significant(body);
 for(let i=0;i<terms.length;i++)for(let n=1;n<=3&&i+n<=terms.length;n++){
   const value=terms.slice(i,i+n).join(" "),key=norm(value);if(value.length>54||value.length<4)continue;
   const old=freq.get(key)||{text:value,count:0,match:0,n};old.count++;old.match=terms.slice(i,i+n).filter(t=>titleTerms.has(norm(t))).length;freq.set(key,old);
 }
 const candidates=[...freq.values()].sort((a,b)=>(b.match*3+b.n+b.count)-(a.match*3+a.n+a.count)).map(x=>x.text);
 const subject=title.split(/\s*[|–—:]\s*/)[0].replace(/\s+\b(?:recensione|review|guida|test)\b.*$/i,"").trim();
 const primary=trim(subject.length>=7&&subject.length<=65?subject:title,65);
 const secondary=unique(candidates.filter(x=>norm(x)!==norm(primary)&&x.split(" ").length>=2)).slice(0,6);
 const tags=unique([category,...secondary.slice(0,5),...significant(title).filter(x=>/\d/.test(x))]).slice(0,10);
 const score=typeFor(category)==="Review"?rating(body):null;
 const image=abs(data.cover||data.image),url=abs(data.url);
 const hashtags=tags.slice(0,5).map(x=>"#"+norm(x).replace(/[^a-z0-9]/g,"")).filter(x=>x.length>2);
 return {title:trim(title,67),description,primary,secondary,tags,schemaType:typeFor(category),
 reviewType:/Gaming/i.test(category)?"VideoGame":/Tech/i.test(category)?"Product":"CreativeWork",rating:score,alt:trim("Copertina: "+title,135),image,canonical:url,
 socialFacebook:trim(title+". "+description,350),socialTikTok:trim(title+". "+description,200)+"\n"+hashtags.join(" "),
 warnings:unique([description.length<135?"Descrizione sotto 135 caratteri; valuta di aggiungere informazioni reali.":"",!image?"Cover non presente: nessuna immagine social inventata.":"",!url?"Canonical non ancora disponibile.":""])};
}
function apply(doc,seo,ctx={}){
 if(!doc?.head||!doc.querySelector("h1")||!seo?.description||!seo?.primary)throw Error("SEO incompleto: salvataggio annullato");
 const url=abs(ctx.url||seo.canonical||doc.querySelector('link[rel="canonical"]')?.href);
 if(!url)throw Error("URL canonical non valido");
 const image=abs(ctx.cover||seo.image||doc.querySelector('meta[property="og:image"]')?.content);
 const category=ctx.category||"Article",kind=typeFor(category),title=doc.querySelector("h1").textContent.trim();
 doc.title=seo.title+" | ZazoomTek";
 const canonical=[...doc.head.querySelectorAll('link[rel="canonical"]')];const link=canonical.shift()||doc.createElement("link");link.rel="canonical";link.href=url;if(!link.parentNode)doc.head.append(link);canonical.forEach(x=>x.remove());
 function meta(attr,key,val){const list=[...doc.head.querySelectorAll('meta['+attr+'="'+key+'"]')];const first=list.shift()||doc.createElement("meta");list.forEach(x=>x.remove());if(!val){first.remove();return}first.setAttribute(attr,key);first.content=val;if(!first.parentNode)doc.head.append(first)}
 const props={"og:type":"article","og:site_name":"ZazoomTek","og:title":seo.title,"og:description":seo.description,"og:url":url,"og:image":image,"og:image:alt":image?seo.alt:null};
 Object.entries(props).forEach(([k,v])=>meta("property",k,v));
 const names={"description":seo.description,"robots":"index,follow,max-image-preview:large","twitter:card":"summary_large_image","twitter:title":seo.title,"twitter:description":seo.description,"twitter:image":image,"keywords":unique([seo.primary,...seo.secondary]).join(", ")};
 Object.entries(names).forEach(([k,v])=>meta("name",k,v));
 doc.head.querySelectorAll('meta[property="article:tag"]').forEach(x=>x.remove());
 seo.tags.slice(0,12).forEach(tag=>{const x=doc.createElement("meta");x.setAttribute("property","article:tag");x.content=tag;doc.head.append(x)});
 const hero=doc.querySelector(".zt-studio-cover-viewport > img, main.content img.hero,img.article-hero,img.cover");
 if(hero){hero.alt=seo.alt;if(ctx.cover&&image)hero.src=new URL(image).pathname}
 // Image ALT: reuse captions or article subject; never guess image contents.
 doc.querySelectorAll("article img,.article-body img,.body img").forEach(img=>{
   if(img===hero||img.closest(".zt-player"))return;
   const previous=(img.getAttribute("alt")||"").trim();
   if(previous&&!/^(?:foto(?:grafia)? articolo zazoomtek|immagine|image|foto)$/i.test(previous))return;
   const caption=img.closest("figure")?.querySelector("figcaption")?.textContent?.trim();
   if(caption)img.setAttribute("alt",trim(caption,145));
   else img.setAttribute("alt",trim("Immagine nell'articolo: "+title,145));
 });
 for(const el of [...doc.head.querySelectorAll('script[type="application/ld+json"]')]){
  try{const old=JSON.parse(el.textContent);const matches=x=>["Article","NewsArticle","Review","BlogPosting"].includes(x?.["@type"]);if(matches(old)){el.remove();continue}if(Array.isArray(old["@graph"])){old["@graph"]=old["@graph"].filter(x=>!matches(x));if(!old["@graph"].length)el.remove();else el.textContent=JSON.stringify(old).replace(/</g,"\\u003c")}}catch(_){} 
 }
 const now=ctx.date||new Date().toISOString();
 const published=ctx.published||doc.querySelector('meta[property="article:published_time"]')?.content||now;
 const schema={"@context":"https://schema.org","@type":kind,headline:title,description:seo.description,datePublished:published,dateModified:now,
  mainEntityOfPage:url,author:{"@type":"Organization",name:"ZazoomTek"},publisher:{"@type":"Organization",name:"ZazoomTek"}};
 if(image)schema.image=[image];
 if(kind==="Review"){
  const itemName=trim(title.replace(/\s*(?:\||–|-)?\s*recensione\b.*$/i,""),95)||title;
  schema.itemReviewed={"@type":/Gaming/i.test(category)?"VideoGame":/Tech/i.test(category)?"Product":"CreativeWork",name:itemName};
  const value=rating(ctx.body||doc.body.textContent);
  if(value!==null&&value>=0&&value<=10)schema.reviewRating={"@type":"Rating",ratingValue:value,bestRating:10,worstRating:0};
 }
 const node=doc.createElement("script");node.type="application/ld+json";node.textContent=JSON.stringify(schema).replace(/</g,"\\u003c");doc.head.append(node);
 return doc;
}
function panel(container){
 const root=document.createElement("section");root.className="zt-seo-panel";root.setAttribute("aria-label","SEO editoriale");
 root.innerHTML='<h3>SEO editoriale automatico</h3><p class="zt-seo-state" role="status">Analisi del contenuto disponibile dopo la scrittura.</p><div class="zt-seo-fields"></div><button type="button" class="zt-seo-refresh">Rigenera SEO</button><p class="zt-seo-alert" role="status"></p><details><summary>Bozze social · non pubblicate</summary><div class="zt-seo-social"></div></details>';
 const spec=[["title","Titolo SEO"],["description","Meta description"],["primary","Keyword principale"],["secondary","Keyword secondarie"],["tags","Tag editoriali"],["alt","ALT descrittivo cover"],["socialFacebook","Facebook"],["socialTikTok","TikTok"]];
 const inputs={};spec.forEach(([key,label])=>{const field=document.createElement("label");field.textContent=label;const node=document.createElement(["description","socialFacebook","socialTikTok"].includes(key)?"textarea":"input");node.dataset.field=key;if(node.tagName==="TEXTAREA")node.rows=2;field.append(node);root.querySelector(key.startsWith("social")?".zt-seo-social":".zt-seo-fields").append(field);inputs[key]=node});
 container.append(root);
 let result=null,source=null,last="",manual=false,problem=null;
 const state=root.querySelector(".zt-seo-state"),alert=root.querySelector(".zt-seo-alert");
 const signature=x=>JSON.stringify([x.title,x.category,x.body,x.cover,x.url]);
 function update(x,force=false){
  const key=signature(x);if(!force&&key===last)return;last=key;
  if(manual&&!force){state.textContent="Testo cambiato. Rigenera per aggiornare il SEO senza perdere le tue correzioni.";return}
  try{result=analyze(x);problem=null;manual=false;
   spec.forEach(([k])=>inputs[k].value=Array.isArray(result[k])?result[k].join(", "):String(result[k]||""));
   state.textContent="SEO specifico generato · "+result.schemaType+(result.rating!==null?" · voto "+result.rating+"/10":"");
   alert.textContent=result.warnings.join(" ");}catch(e){result=null;problem=e;state.textContent="Analisi non completata: "+e.message;alert.textContent=e.message}
 }
 spec.forEach(([k])=>inputs[k].addEventListener("input",()=>{manual=true;state.textContent="SEO personalizzato manualmente."}));
 root.querySelector(".zt-seo-refresh").onclick=()=>{if(source)update(source(),true)};
 return {root,attach(fn){source=fn;return this},update,prepare(data){
  update(data);if(!result)throw problem||new Error("SEO non generato");
  const seo={...result};spec.forEach(([k])=>seo[k]=["secondary","tags"].includes(k)?unique(inputs[k].value.split(",").map(x=>x.trim())):inputs[k].value.trim());
  if(seo.title.length<12||seo.title.length>90||seo.description.length<100||seo.description.length>170||!seo.primary||!seo.alt)throw Error("Controlla Titolo SEO (12–90 caratteri), Meta description (100–170) e keyword principale.");
  return seo;
 }};
}
if(typeof document!=="undefined"){
 const style=document.createElement("style");
 style.textContent=".zt-seo-panel{background:#fff;border:1px solid #dbe0e8;padding:15px;margin:14px 0;color:#272d35;font:12px/1.5 Arial,sans-serif}.zt-seo-panel h3{margin:0 0 8px;font-size:15px}.zt-seo-panel label{display:block;margin:9px 0;font-weight:800;font-size:11px}.zt-seo-panel input,.zt-seo-panel textarea{display:block;width:100%;box-sizing:border-box;border:1px solid #dbe0e8;padding:8px;border-radius:4px;color:#252a31;background:white;font:12px Arial,sans-serif}.zt-seo-panel button{background:#222;color:#fff;border:0;padding:8px 12px;font-weight:800}.zt-seo-panel .zt-seo-alert{color:#a91a34}.zt-seo-panel details{margin-top:10px}";document.head.append(style);
}
window.ZTStudioSEO={analyze,apply,panel,rating,version:1};
})();
