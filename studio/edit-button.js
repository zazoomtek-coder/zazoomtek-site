/* Display is conditional; write authorization is always enforced independently by GitHub. */
(()=>{
"use strict";
let authorized=false;
try{authorized=Number(localStorage.getItem("zt_studio_verified_until")||0)>Date.now()}catch{}
if(!authorized)return;
const root=document.querySelector("article.article-main,article.story,article.zt-main.zt-article");
const title=root?.querySelector("h1");
if(!root||!title||document.getElementById("zt-studio-edit-title"))return;
const path=location.pathname.replace(/^\//,"");
if(!/^[a-zA-Z0-9_.-]+\.html$/.test(path)||path==="index.html")return;
const b=document.createElement("a");b.id="zt-studio-edit-title";b.textContent="✎ Modifica";
b.href="/studio/?edit="+encodeURIComponent(path);
b.style.cssText="display:inline-flex;align-items:center;margin:8px 0 16px;padding:9px 13px;background:#222;color:#fff;border-left:4px solid #d51232;text-decoration:none;font:800 12px/1 Arial,sans-serif";
b.setAttribute("aria-label","Apri questo articolo nello Studio per modificarlo");
title.insertAdjacentElement("afterend",b);
})();