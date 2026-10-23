/* ZazoomTek: additive external-press-review mounting AFTER the approved
   Tech/Gaming (30/50) + editorial rail (20) runtime layout is constructed.
   Do not alter the original Home renderer, editorial feeds or publishing. */
(function(){
"use strict";
if(!["/","/index.html"].includes(location.pathname) && location.protocol!=="file:")return;
function mount(){
 const source=document.getElementById("ztWebNewsStaging");
 if(!source)return true;
 const left=source.querySelector(".zt-webnews-followup-main");
 const right=source.querySelector(".zt-webnews-followup-rail");
 const feed=document.querySelector("#articoli.ztp-news-area .ztp-primary-feed");
 const pager=feed?.querySelector("#ztpNewsPager");
 const guide=document.getElementById("ztp-guide-extra");
 const editorialRail=document.getElementById("ztpNewsRail");
 if(!left||!feed||!pager||!guide||!editorialRail)return false;
 // Respect existing real user-facing pagination and both official GUIDE/EXTRA.
 // Never create a second guide or Extra copy.
 pager.insertAdjacentElement("afterend",left);
 left.insertAdjacentElement("afterend",guide);
 // The former three miniature black panels are explicitly retired.
 // Keep only the real top DA NON PERDERE and the single ALTRE NEWS.
 for(const extra of document.querySelectorAll(".zt-webnews-followup-rail"))extra.remove();
 source.remove();
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