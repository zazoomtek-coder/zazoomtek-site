/* ZazoomTek: approved Home graphic update Oct 16, 2026.
   Do not touch source articles, importer, automation, video shelves, or URLs. */
(function(){
 "use strict";
 if(!["/","/index.html"].includes(location.pathname))return;
 function installStyles(){
   if(document.getElementById("zt-home-graphic-approved-20261016"))return;
   const link=document.createElement("link");
   link.id="zt-home-graphic-approved-20261016";
   link.rel="stylesheet";
   link.href="/zt-home-graphic-layout-20261016.css?v=1";
   document.head.appendChild(link);
 }
 function normalizeFeatured(){
   const grid=document.getElementById("ztFeaturedGrid");
   if(!grid)return;
   const cards=[...grid.children].filter(el=>el.matches("a[href]"));
   if(cards.length>5){
     function gaming(card){
       const category=(card.dataset.featureSection||"").toLowerCase();
       if(category==="gaming"||category==="gaming-inside")return true;
       if(category==="tech"||category==="tech-impact")return false;
       const label=((card.title||"")+" "+(card.getAttribute("href")||"")).toLowerCase();
       return /gaming-inside|gta|grand theft auto|videogioch|videogam|playstation|ps5|xbox|nintendo|steam|castlevania|gameplay/.test(label);
     }
     const tech=cards.filter(card=>!gaming(card)).slice(0,4);
     const game=cards.find(gaming);
     const chosen=tech.length===4&&game?[...tech,game]:cards.slice(0,5);
     if(cards.length!==chosen.length||chosen.some((card,i)=>card!==cards[i]))grid.replaceChildren(...chosen);
   }
   grid.setAttribute("aria-label","Cinque news ZazoomTek in evidenza");
 }
 function enhanceDates(){
   function pathname(href){try{return new URL(href,location.href).pathname;}catch(_){return "";}}
   [
     {archive:"/guide.html",home:"#ztHomeGuide"},
     {archive:"/extra.html",home:"#ztHomeExtra"}
   ].forEach(function(config){
     fetch(config.archive,{cache:"no-store"}).then(function(res){
       if(!res.ok)throw Error("Archive unavailable");
       return res.text();
     }).then(function(markup){
       const doc=new DOMParser().parseFromString(markup,"text/html");
       const dates=new Map();
       doc.querySelectorAll(".news-row").forEach(function(row){
         const a=row.querySelector(".news-copy h2 a[href]");
         const meta=row.querySelector(".news-meta");
         if(a&&meta&&meta.textContent.trim())dates.set(pathname(a.getAttribute("href")),meta.textContent.trim());
       });
       const root=document.querySelector(config.home);
       if(!root)return;
       function sync(){
         root.querySelectorAll("a[href]").forEach(function(a){
           const date=dates.get(pathname(a.getAttribute("href")));
           if(!date)return;
           if(config.archive==="/guide.html"){
             const existing=a.querySelector(".zt-home-guide-next > div:last-child span");
             if(existing){existing.textContent=date;return;}
             if(a.classList.contains("zt-home-guide-primary")&&!a.querySelector(".zt-guide-published-date")){
               const label=document.createElement("small");label.className="zt-guide-published-date";label.textContent=date;a.appendChild(label);
             }
           }else if(a.classList.contains("ztp-extra-card")){
             const title=a.querySelector("strong");
             if(title&&!title.querySelector(".zt-extra-published-date")){
               const label=document.createElement("small");label.className="zt-extra-published-date";label.textContent=date;title.appendChild(label);
             }
           }
         });
       }
       sync();
       const list=root.querySelector(".ztp-extra-cards");
       if(list)new MutationObserver(sync).observe(list,{childList:true});
     }).catch(function(err){console.info("Publication dates not available:",err.message);});
   });
 }
 function relocate(){
   const area=document.getElementById("articoli");
   const panel=document.getElementById("ztp-guide-extra");
   const gamingReviews=document.getElementById("ztpGamingReviews");
   const main=area&&area.closest(".maincol");
   if(!area||!main||!panel||!gamingReviews)return false;
   if(panel.previousElementSibling!==area)area.insertAdjacentElement("afterend",panel);
   if(gamingReviews.previousElementSibling!==panel)panel.insertAdjacentElement("afterend",gamingReviews);
   document.documentElement.classList.add("zt-home-graphics-20261016");
   return true;
 }
 function init(){
   installStyles();
   normalizeFeatured();
   enhanceDates();
   const grid=document.getElementById("ztFeaturedGrid");
   if(grid)new MutationObserver(normalizeFeatured).observe(grid,{childList:true});
   if(relocate())return;
   const root=document.querySelector("main.page");
   if(!root)return;
   const obs=new MutationObserver(function(){if(relocate())obs.disconnect();});
   obs.observe(root,{childList:true,subtree:true});
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
 else init();
})();