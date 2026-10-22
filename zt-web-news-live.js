/* ZazoomTek: additive external-press-review mounting AFTER the approved
   Tech/Gaming (30/50) + editorial rail (20) runtime layout is constructed.
   Do not alter the original Home renderer, editorial feeds or publishing. */
(function(){
"use strict";
if(!["/","/index.html"].includes(location.pathname) && location.protocol!=="file:")return;
function mount(){
 const source=document.getElementById("ztWebNewsFollowup");
 if(!source)return true;
 const left=source.querySelector(".zt-webnews-followup-main");
 const right=source.querySelector(".zt-webnews-followup-rail");
 const feed=document.querySelector("#articoli.ztp-news-area .ztp-primary-feed");
 const pager=feed?.querySelector("#ztpNewsPager");
 const guide=document.getElementById("ztp-guide-extra");
 const editorialRail=document.getElementById("ztpNewsRail");
 if(!left||!right||!feed||!pager||!guide||!editorialRail)return false;
 // Respect existing real user-facing pagination and both official GUIDE/EXTRA.
 // Never create a second guide or Extra copy.
 pager.insertAdjacentElement("afterend",left);
 left.insertAdjacentElement("afterend",guide);
 // Add only local genuine ZazoomTek articles to the right 20% rail.
 editorialRail.appendChild(right);
 source.remove();
 const adjustRail=()=>{
   // The first new box starts alongside the new Web press review if space
   // permits, without modifying/shifting the previous approved editorial boxes.
   if(!left.isConnected||!right.isConnected)return;
   right.style.marginTop="0px";
   const gap=Math.round(left.getBoundingClientRect().top-right.getBoundingClientRect().top);
   if(gap>0)right.style.marginTop=Math.min(gap,2400)+"px";
 };
 requestAnimationFrame(()=>requestAnimationFrame(adjustRail));
 addEventListener("resize",()=>requestAnimationFrame(adjustRail),{passive:true});
 document.documentElement.dataset.ztWebNewsMounted="three-column";
 return true;
}
function start(){
 if(mount())return;
 const root=document.querySelector("main.page");
 if(!root)return;
 const observer=new MutationObserver(()=>{if(mount())observer.disconnect()});
 observer.observe(root,{childList:true,subtree:true});
 setTimeout(()=>{observer.disconnect();mount()},5000);
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start,{once:true});
else start();
})();