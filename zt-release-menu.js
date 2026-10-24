/* Shared header sourced from the approved ZazoomTek Home section names.
   No third-party dependencies, no editing of the Home itself. */
(function(){
'use strict';
if(location.pathname==='/'||location.pathname==='/index.html')return;
var current=(location.pathname||'/').toLowerCase();
var old=document.querySelector('body > header,body > .zt-header')||document.querySelector('header');
if(!old)return;
var h=document.createElement('header');
h.className='zt-release-header';
h.setAttribute('aria-label','Navigazione principale ZazoomTek');
h.innerHTML='<div class="zt-release-inner">'+
'<a class="zt-release-brand" href="/"><img class="zt-release-logo" src="/ChatGPT.png" alt="ZazoomTek">'+
'<span class="zt-release-name"><strong>ZAZOOM<em>TEK</em></strong><small>TECH · GAMING · COMMUNITY</small></span></a>'+
'<button type="button" class="zt-release-toggle" aria-controls="ztReleaseNav" aria-expanded="false">MENU ☰</button>'+
'<nav id="ztReleaseNav" class="zt-release-nav" aria-label="Menu ZazoomTek">'+
'<a href="/">HOME</a><a href="/news.html">NEWS</a>'+
'<div class="zt-release-drop"><button type="button" aria-haspopup="true" aria-expanded="false">RECENSIONI ▾</button>'+
'<div class="zt-release-submenu"><a href="/recensioni-tech.html">TECH</a><a href="/recensioni-gaming.html">GAMING</a></div></div>'+
'<a href="/guide.html">GUIDE</a><a href="/cybercultura.html">CYBERCULTURA</a>'+
'<a href="/speciali.html">SPECIALI</a><a href="/extra.html">EXTRA</a>'+
'<a href="https://www.youtube.com/@ZazoomTek/posts" target="_blank" rel="noopener">COMMUNITY</a>'+
'<a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener">VIDEO</a></nav>'+
'<form class="zt-release-search" action="/cerca.html" method="get"><input name="q" type="search" placeholder="Cerca nel sito…" aria-label="Cerca nel sito"><button type="submit" aria-label="Avvia ricerca">⌕</button></form>'+
'</div>';
old.replaceWith(h);
document.body.classList.add('zt-release-page');
h.querySelectorAll('a[href^="/"]').forEach(function(a){
 var path=a.getAttribute('href').toLowerCase();
 if(path===current || path==='/'&&current==='/index.html')a.setAttribute('aria-current','page');
});
var toggle=h.querySelector('.zt-release-toggle'),nav=h.querySelector('.zt-release-nav');
toggle.addEventListener('click',function(){
 var open=nav.classList.toggle('open');toggle.setAttribute('aria-expanded',String(open));
});
var drop=h.querySelector('.zt-release-drop'),trigger=drop.querySelector('button');
trigger.addEventListener('click',function(){
 var open=drop.classList.toggle('open');trigger.setAttribute('aria-expanded',String(open));
});
document.addEventListener('click',function(e){
 if(!drop.contains(e.target)){drop.classList.remove('open');trigger.setAttribute('aria-expanded','false')}
});
})();
