/* ZazoomTek: one accessible dropdown controller for Home, Extra, Studio pages
 * and all new static article pages. Event delegation survives header replacement.
 */
(function(){
"use strict";
const selector=".nav-drop,.zt-master-dropdown,.zt-release-drop";
function controls(drop){return drop.querySelector(":scope > button.nav-drop-trigger,:scope > button.zt-master-drop-trigger,:scope > button");}
function set(drop,opened){
 const button=controls(drop);if(!button)return;
 drop.classList.toggle("open",opened);
 button.setAttribute("aria-expanded",String(opened));
 const menu=drop.querySelector(":scope > .nav-submenu,:scope > .zt-master-sub,:scope > .zt-release-submenu");
 if(menu)menu.setAttribute("aria-hidden",String(!opened));
}
function closestDrop(node){return node&&node.closest?node.closest(selector):null;}
function install(){
 document.querySelectorAll(selector).forEach(function(drop){
  const button=controls(drop);if(!button)return;
  if(!button.id)button.id="zt-drop-"+Math.random().toString(36).slice(2,9);
  button.setAttribute("aria-haspopup","true");
  button.setAttribute("aria-expanded","false");
  const menu=drop.querySelector(":scope > .nav-submenu,:scope > .zt-master-sub,:scope > .zt-release-submenu");
  if(menu){menu.setAttribute("role","group");menu.setAttribute("aria-label",button.textContent.trim());}
 });
}
document.addEventListener("click",function(event){
 const trigger=event.target.closest(".nav-drop > button,.zt-master-dropdown > button,.zt-release-drop > button");
 if(trigger){
  const parent=closestDrop(trigger),opened=parent.classList.contains("open");
  document.querySelectorAll(selector+".open").forEach(d=>set(d,false));
  set(parent,!opened);
  event.preventDefault();
  return;
 }
 if(!closestDrop(event.target))
  document.querySelectorAll(selector+".open").forEach(d=>set(d,false));
});
document.addEventListener("keydown",function(event){
 if(event.key!=="Escape")return;
 const active=Array.from(document.querySelectorAll(selector+".open"));
 if(!active.length)return;
 active.forEach(d=>set(d,false));
 controls(active[0])?.focus();
});
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install);else install();
new MutationObserver(function(changes){
 if(changes.some(m=>Array.from(m.addedNodes).some(n=>
       n.nodeType===1&&(n.matches?.("header,#zt-unified-header")||
         n.querySelector?.(selector)))))install();
}).observe(document.documentElement,{subtree:true,childList:true});
})();
