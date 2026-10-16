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
   link.href="/zt-home-graphic-layout-20261016.css?v=3";
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
 /* Build genuine magazine boxes from the site's own Guide and Extra archives.
    First article is prominent, next up to three are compact; empty slots remain empty.
    Importers own the archives: there are no frozen article titles or fake records. */
 function renderMagazines(){
   [
     {url:"/guide.html", selector:"#ztHomeGuide", content:".zt-home-guide-content", kind:"Guida"},
     {url:"/extra.html", selector:"#ztHomeExtra", content:".ztp-extra-cards", kind:"Extra"}
   ].forEach(function(config){
     fetch(config.url,{cache:"no-store"}).then(function(response){
       if(!response.ok)throw new Error("Archive HTTP "+response.status);
       return response.text();
     }).then(function(markup){
       const doc=new DOMParser().parseFromString(markup,"text/html");
       const records=[], seen=new Set();
       doc.querySelectorAll(".news-row").forEach(function(row){
         const titleLink=row.querySelector(".news-copy h2 a[href]");
         const picture=row.querySelector("img");
         if(!titleLink||!picture)return;
         let link;
         try{link=new URL(titleLink.getAttribute("href"),location.origin);}catch(_){return;}
         if(link.origin!==location.origin || !link.pathname.endsWith(".html") || seen.has(link.pathname))return;
         seen.add(link.pathname);
         let src=picture.getAttribute("src")||"";
         try{
           const srcUrl=new URL(src,location.origin);
           if(srcUrl.protocol!=="https:" && srcUrl.origin!==location.origin)return;
           src=srcUrl.href;
         }catch(_){return;}
         records.push({
           href:link.pathname,title:titleLink.textContent.trim(),img:src,
           meta:row.querySelector(".news-meta")?.textContent.trim()||"",
           excerpt:row.querySelector(".news-copy p")?.textContent.trim()||""
         });
       });
       const target=document.querySelector(config.selector+" "+config.content);
       if(!target||!records.length)return;
       target.classList.add("zt-magazine-content");
       const feature=records[0];
       function makeImage(item){
         const image=document.createElement("img");
         image.src=item.img; image.alt=item.title;
         image.loading="lazy"; image.decoding="async";
         return image;
       }
       const primary=document.createElement("a");
       primary.className="zt-magazine-primary"; primary.href=feature.href;
       primary.appendChild(makeImage(feature));
       const primaryText=document.createElement("div");
       primaryText.className="zt-magazine-primary-copy";
       const title=document.createElement("strong");title.textContent=feature.title;
       primaryText.appendChild(title);
       if(feature.meta){
         const meta=document.createElement("small");meta.textContent=feature.meta;
         primaryText.appendChild(meta);
       }
       if(feature.excerpt){
         const excerpt=document.createElement("p");excerpt.textContent=feature.excerpt;
         primaryText.appendChild(excerpt);
       }
       primary.appendChild(primaryText);
       const side=document.createElement("div");
       side.className="zt-magazine-side";
       records.slice(1,4).forEach(function(item){
         const card=document.createElement("a");
         card.className="zt-magazine-small";card.href=item.href;
         card.appendChild(makeImage(item));
         const copy=document.createElement("span");
         copy.className="zt-magazine-small-copy";
         const heading=document.createElement("strong");heading.textContent=item.title;
         copy.appendChild(heading);
         if(item.meta){
           const date=document.createElement("small");date.textContent=item.meta;
           copy.appendChild(date);
         }
         card.appendChild(copy);side.appendChild(card);
       });
       function applyMagazineLayout(){
         // Legacy Extra loader may finish its HEAD checks after this archive fetch.
         // Keep the genuine magazine cards instead of letting that older renderer overwrite them.
         if(target.childElementCount!==2||target.firstElementChild!==primary||target.lastElementChild!==side){
           target.replaceChildren(primary,side);
         }
       }
       applyMagazineLayout();
       new MutationObserver(applyMagazineLayout).observe(target,{childList:true});
       target.dataset.archiveCount=String(Math.min(records.length,4));
       target.dataset.sourceArchive=config.url;
     }).catch(function(error){
       console.warn("ZazoomTek "+config.kind+" archive not available; preserving published cards:",error);
     });
   });
 }
 function relocate(){
   const area=document.querySelector("#articoli.ztp-news-area");
   const feed=area?.querySelector(".ztp-primary-feed");
   const pager=feed?.querySelector("#ztpNewsPager");
   const newsColumns=feed?.querySelector(".ztp-two-news-columns");
   const panel=document.getElementById("ztp-guide-extra");
   const gamingReviews=document.getElementById("ztpGamingReviews");
   const video=document.getElementById("ztpVideosAnchor");
   if(!feed||!panel||!gamingReviews||!video||(!pager&&!newsColumns))return false;
   // Final editorial order INSIDE the left 80% column: news / page numbers /
   // two side-by-side magazine boxes / three gaming reviews / Explore Videos.
   // The right-hand editorial rail remains in the SAME grid throughout.
   const preceding=(pager?.parentElement===feed)?pager:newsColumns;
   if(panel.parentElement!==feed||panel.previousElementSibling!==preceding)
     preceding.insertAdjacentElement("afterend",panel);
   if(gamingReviews.parentElement!==feed||gamingReviews.previousElementSibling!==panel)
     panel.insertAdjacentElement("afterend",gamingReviews);
   if(video.parentElement!==feed||video.previousElementSibling!==gamingReviews)
     gamingReviews.insertAdjacentElement("afterend",video);
   // Keep all three call-to-action links in Italian, even after rebuilding.
   [
     "#ztHomeGuide .zt-home-guide-heading a",
     "#ztHomeExtra .ztp-extra-head a",
     "#ztpGamingReviews .ztp-review-all"
   ].forEach(function(selector){
     const link=document.querySelector(selector);
     if(link)link.textContent="VEDI TUTTO →";
   });
   document.documentElement.classList.add("zt-home-graphics-20261016","zt-home-final-editorial-layout");
   return panel.parentElement===feed &&
     panel.previousElementSibling===preceding &&
     gamingReviews.previousElementSibling===panel &&
     video.previousElementSibling===gamingReviews;
 }
 function init(){
   installStyles();
   normalizeFeatured();
   renderMagazines();
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