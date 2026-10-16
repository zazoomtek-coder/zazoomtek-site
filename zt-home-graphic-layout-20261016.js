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