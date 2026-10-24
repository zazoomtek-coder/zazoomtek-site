/* Deduplicate actual Gaming review rows. Prefer the linked article's own
   image before displaying the explicit branded fallback for a broken URL. */
(()=>{
"use strict";
const norm=s=>String(s||"").normalize("NFKC").toLocaleLowerCase("it").replace(/\s+/g," ").trim();
async function getCover(href){
 if(!/^\/[A-Za-z0-9._-]+\.html$/.test(href))return "";
 try{const res=await fetch(href,{cache:"force-cache"});if(!res.ok)return "";
 const page=new DOMParser().parseFromString(await res.text(),"text/html");
 const src=page.querySelector('meta[property="og:image"]')?.content ||
  page.querySelector("main img.article-hero,main img.hero")?.getAttribute("src")||"";
 return /^(https:\/\/|\/assets\/)/.test(src)?src:"";
 }catch{return ""}
}
function run(){
 const list=document.getElementById("reviewList");if(!list)return;
 const urls=new Set(),names=new Set();
 list.querySelectorAll(":scope>.news-row").forEach(row=>{
   const a=row.querySelector(".news-copy h2 a[href]");if(!a)return;
   const title=a.textContent.trim(),name=norm(title),url=(a.getAttribute("href")||"").split(/[?#]/)[0];
   if(urls.has(url)||names.has(name)){row.remove();return;}
   urls.add(url);names.add(name);
   let img=row.querySelector(":scope>a img");
   if(!img){const anchor=document.createElement("a");anchor.href=url;
     img=document.createElement("img");anchor.append(img);row.prepend(anchor)}
   img.alt=title;img.loading="lazy";img.decoding="async";
   let attempted=false;
   const logo=()=>{img.src="/ChatGPT.png";img.style.objectFit="contain";img.style.background="#151515"};
   img.addEventListener("error",async()=>{
     if(attempted){logo();return}attempted=true;
     const next=await getCover(url);
     if(next && next!==img.getAttribute("src"))img.src=next;else logo();
   });
   if(!img.getAttribute("src")){void getCover(url).then(src=>{if(src)img.src=src;else logo()})}
 });
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",run,{once:true});else run();
})();
