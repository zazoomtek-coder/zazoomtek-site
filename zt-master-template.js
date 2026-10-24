/* One shared navigation + sidebar runtime for every ZazoomTek article.
 * Static page output is authored by services10/15-master-structural.py;
 * Studio uses the same components before first scheduled rebuild.
 */
(function(){
"use strict";
function mount(){
 // A missing or blocked image never leaves a blank editorial/card position.
 document.addEventListener("error",function(event){
  var img=event.target;
  if(!img||img.tagName!=="IMG")return;
  if(!img.closest(".zt-master-card,.zt-feature-card,.news-row,.article-row,.article-main,.zt-master-article-related,.zt-master-rail"))return;
  var fallback="/assets/zt-editorial-fallback.svg";
  if(img.getAttribute("src")===fallback)return;
  img.src=fallback;
 },true);
 document.querySelectorAll(".zt-master-card img,.zt-master-rail img,.zt-master-article-related img").forEach(function(img){
  if(!img.getAttribute("src"))img.setAttribute("src","/assets/zt-editorial-fallback.svg");
 });
 var body=document.body;
 if(!body||!body.classList.contains("zt-master-page"))return;
 var header=document.querySelector(".zt-master-header");
 if(header){
  var toggle=header.querySelector(".zt-master-toggle"),nav=header.querySelector(".zt-master-nav,.nav"),drop=header.querySelector(".zt-master-dropdown,.nav-drop"),btn=drop&&drop.querySelector("button");
  if(toggle&&nav)toggle.addEventListener("click",function(){var open=nav.classList.toggle("open");toggle.setAttribute("aria-expanded",String(open));});
  if(btn&&drop)btn.addEventListener("click",function(){var open=drop.classList.toggle("open");btn.setAttribute("aria-expanded",String(open));});
  document.addEventListener("click",function(e){if(drop&&btn&&!drop.contains(e.target)){drop.classList.remove("open");btn.setAttribute("aria-expanded","false");}});
  var current=location.pathname.replace(/\/$/,"/index.html");
  header.querySelectorAll('a[href^="/"]').forEach(function(link){
   if(link.getAttribute("href")===current||current==="/index.html"&&link.getAttribute("href")==="/")link.setAttribute("aria-current","page");
  });
 }
 var rail=document.querySelector(".zt-master-rail");
 if(!rail)return;
 var grid=rail.querySelector(".zt-master-grid");
 if(!grid||grid.children.length)return; // Snapshot already populated server-side.
 fetch("/zt-sidebar-feed.json",{cache:"no-store"}).then(function(r){if(!r.ok)throw Error("feed unavailable");return r.json();}).then(function(feed){
  var pool=Array.isArray(feed.news)?feed.news:[];
  var path=location.pathname.toLowerCase();
  var seenUrls=new Set();
  pool=pool.filter(function(item){
   if(!item||!item.url||!item.title)return false;
   var url=String(item.url).split("?")[0].toLowerCase(),title=String(item.title).toLowerCase().trim();
   if(url===path||seenUrls.has(url))return false;
   seenUrls.add(url);return true;
  });
  pool.sort(function(a,b){return String(b.published||"").localeCompare(String(a.published||""));});
  var article=document.querySelector(".zt-master-content,.article-main,.article-body,main");
  var text=article?article.textContent.length:3000;
  var count=Math.max(8,Math.min(Math.ceil(text/220),Math.max(0,pool.length-4)));
  var current=pool.slice(0,count),related=pool.slice(count,count+4);
  function draw(items,target){
   if(!target)return;
   target.replaceChildren();
   items.forEach(function(item){
    var link=document.createElement("a"),img=document.createElement("img"),label=document.createElement("span");
    link.className="zt-master-card";link.href=item.url;
    img.src=item.image||"/assets/zt-editorial-fallback.svg";img.loading="lazy";img.alt=item.title;
    label.textContent=item.title;link.append(img,label);target.append(link);
   });
  }
  draw(current,rail.querySelector(".zt-master-group .zt-master-grid"));
  draw(related,document.querySelector(".zt-master-article-related .zt-master-related-list"));
 }).catch(function(){ /* Existing content stays visible if external feed is unavailable. */ });
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",mount);else mount();
})();
