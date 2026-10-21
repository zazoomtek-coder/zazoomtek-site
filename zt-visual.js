/* Progressive visual polish; does not replace the original editorial content. */
(function(){
 'use strict';
 function enhanceHomeSlider(){
  document.querySelectorAll('.news-slide').forEach(function(slide){
   // Il carosello News in evidenza gestisce da solo le cover: mai duplicare testi.
   if(slide.closest('#newsSlider'))return;
   if(slide.querySelector('.zt-slide-overlay,.news-slide-copy'))return;
   var img=slide.querySelector('img[alt]');
   if(!img || !img.alt.trim())return;
   var holder=slide.querySelector('a')||slide;
   var box=document.createElement('div');box.className='zt-slide-overlay';
   var label=document.createElement('span');label.className='zt-kicker';label.textContent='IN EVIDENZA';
   var title=document.createElement('h3');title.textContent=img.alt;
   var cta=document.createElement('span');cta.className='zt-slide-read';cta.textContent='Leggi la notizia completa ›';
   box.append(label,title,cta);
   holder.appendChild(box);
  });
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',enhanceHomeSlider,{once:true});else enhanceHomeSlider();
})();


/* Homepage video and Shorts collections. Uses only videos actually published by ZazoomTek.
   Safely falls back to the last verified six videos/shorts if the feed is unavailable. */
const ztHomeVideoFallback=[{"id":"O6VxSf8cYt0","title":"Dead Spin PC - Primo Sguardo","publishedAt":"2026-10-04T10:22:15Z","category":"gaming","short":false,"completedLive":false},{"id":"fKiuvUW5eKI","title":"🐰 WALTO | Recensione PC - Boss rush oscuro tra schivate e attacchi","publishedAt":"2026-10-05T12:28:27Z","category":"recensioni","short":false,"completedLive":false},{"id":"lmOGs9M_vhw","title":"IIFACTOR M08E AI Smart Glasses UNBOXING | Cosa c’è nella scatola?","publishedAt":"2026-09-12T12:54:11Z","category":"unboxing","short":false,"completedLive":false},{"id":"An2RZr9_Cxs","title":"Nintendo 64: il catalogo GIG del 1997 che ci faceva sognare | Retrogaming","publishedAt":"2026-09-08T09:32:22Z","category":"analogiktek","short":false,"completedLive":false},{"id":"WmIXQGZYhTc","title":"realme C100 5G Test Gaming","publishedAt":"2026-05-21T08:00:24Z","category":"test","short":false,"completedLive":false},{"id":"tEkXOj7XOwA","title":"Sesame Street: Amici e risate PS5 - lungo gameplay","publishedAt":"2026-10-13T08:39:35Z","category":"gameplay","short":false,"completedLive":false}];
const ztHomeShortFallback=[{"id":"Mf8B30PKjqY","title":"Princess of the Water Lilies gameplay on PS5","publishedAt":"2026-10-02T12:29:00Z","short":true},{"id":"EaLvvrd6ysI","title":"Tomb Raider: Legacy of Atlantis – Everything changes in Egypt: mummies and supernatural creatures","publishedAt":"2026-09-29T11:05:07Z","short":true},{"id":"FOy-9dAvFMM","title":"70mai A900 Unboxing: cosa c’è nella confezione della Dash Cam 4K","publishedAt":"2026-09-28T13:07:58Z","short":true},{"id":"PV6JenVnwTo","title":"realme Buds T500 Pro Harry Potter Edition – UNBOXING 🪄🎧","publishedAt":"2026-09-22T17:30:19Z","short":true},{"id":"R2AFPqQpHaE","title":"🎮 Marvel’s Wolverine – Gameplay PS5","publishedAt":"2026-09-17T09:58:17Z","short":true},{"id":"DdzW7c0uLN0","title":"Battlefield 6 Season 4: Furious Tide is here with a FREE TRIAL","publishedAt":"2026-09-16T12:58:04Z","short":true}];
function ztHomeGallery(){
  const main=document.querySelector('main.page');
  if(!main || !document.querySelector('#ztStackList'))return;
  const existing=document.getElementById('zt-home-shelves');
  const shelves=existing || document.createElement('div');
  shelves.id='zt-home-shelves';
  shelves.className='zt-home-shelves';
  if(!existing)main.appendChild(shelves);
  const types=['recensioni','test','unboxing','gaming','analogiktek'];
  const labels={gaming:'GAMING',recensioni:'RECENSIONI',unboxing:'UNBOXING',analogiktek:'ANALOGIKTEK',test:'TEST',gameplay:'GAMEPLAY'};
  function card(video,short){
    const article=document.createElement('article');
    article.className='zt-shelf-card'+(short?' zt-shelf-short':'');
    const button=document.createElement('button');
    button.type='button';button.className='zt-shelf-thumbnail';
    button.setAttribute('aria-label','Riproduci '+video.title);
    const img=document.createElement('img');
    img.src='https://i.ytimg.com/vi/'+video.id+'/maxresdefault.jpg';
    img.loading='lazy';img.decoding='async';img.alt=video.title;
    img.onerror=function(){img.onerror=null;img.src='https://i.ytimg.com/vi/'+video.id+'/hqdefault.jpg'};
    const play=document.createElement('span');play.className='zt-shelf-play';play.textContent='▶';play.setAttribute('aria-hidden','true');
    button.append(img,play);
    button.addEventListener('click',function(){
      const iframe=document.createElement('iframe');
      iframe.src='https://www.youtube-nocookie.com/embed/'+encodeURIComponent(video.id)+'?autoplay=1&playsinline=1&rel=0';
      iframe.title=video.title;
      iframe.setAttribute('allow','accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share');
      iframe.allowFullscreen=true;
      iframe.className='zt-shelf-iframe';
      button.replaceWith(iframe);
    });
    const copy=document.createElement('div');copy.className='zt-shelf-copy';
    const heading=document.createElement('h3');heading.textContent=video.title;
    const tag=document.createElement('span');tag.className='zt-shelf-label';tag.textContent=short?'SHORT':(labels[video.category]||'VIDEO');
    copy.append(heading,tag);
    article.append(button,copy);
    return article;
  }
  function group(title,url,data,short){
    const section=document.createElement('section');section.className='zt-shelf';
    const header=document.createElement('div');header.className='zt-shelf-head';
    const heading=document.createElement('h2');heading.textContent=title;
    const more=document.createElement('a');more.href=url;more.textContent=short?'Tutti gli Shorts →':'Tutti i video →';more.target='_blank';more.rel='noopener noreferrer';
    header.append(heading,more);
    const grid=document.createElement('div');grid.className='zt-shelf-grid'+(short?' zt-shelf-shorts':'');
    data.forEach(function(item){grid.appendChild(card(item,short))});
    section.append(header,grid);
    return section;
  }
  function render(source){
    if(!Array.isArray(source)||!source.length)return;
    const clean=source.filter(x=>x && /^[A-Za-z0-9_-]{11}$/.test(x.id||'') && typeof x.title==='string' && x.title.trim());
    clean.sort((a,b)=>(b.publishedAt||'').localeCompare(a.publishedAt||''));
    const selected=[];const used=new Set();
    // Fixed category order: the same as the channel playlists, no sorting by upload date.
    // Missing categories use their own last verified video without moving GAMEPLAY.
    for(const type of types){
      const item=clean.find(x=>x.category===type && !x.short && !x.live && !x.completedLive && !used.has(x.id))
        || ztHomeVideoFallback.find(x=>x.category===type && !used.has(x.id));
      if(item){used.add(item.id);selected.push(Object.assign({},item,{category:type}))}
    }
    // GAMEPLAY always occupies the last tile, but selects the most recent
    // real, creator-approved gameplay session. A completed livestream alone
    // does NOT make a video gameplay; edited/commented clips remain GAMING.
    // Compare fresh verified videos and the last verified original backup.
    // A stale feed must never replace a newer, verified full session with
    // an old completed live recording; choose by actual upload timestamp.
    const authenticGameplay=clean.filter(x=>x.category==='gameplay' && !x.short && !x.live && !used.has(x.id));
    const backupGameplay=ztHomeVideoFallback.filter(x=>x.category==='gameplay' && !x.short && !used.has(x.id));
    const gameplay=[...authenticGameplay,...backupGameplay].sort((a,b)=>(b.publishedAt||'').localeCompare(a.publishedAt||''))[0];
    if(gameplay){used.add(gameplay.id);selected.push(Object.assign({},gameplay,{category:'gameplay'}))}
    const shorts=clean.filter(x=>x.short&&!x.live).slice(0,6);
    if(shorts.length<6){for(const item of ztHomeShortFallback){if(shorts.length>=6)break;if(!shorts.some(s=>s.id===item.id))shorts.push(item)}}
    shelves.replaceChildren(group('ESPLORA VIDEO','https://www.youtube.com/@ZazoomTek/videos',selected.slice(0,6),false),group('ULTIMI SHORTS','https://www.youtube.com/@ZazoomTek/shorts',shorts.slice(0,6),true));
    document.body.classList.add('zt-home-shelves-ready');
  }
  render([...ztHomeVideoFallback,...ztHomeShortFallback]);
  fetch('/home-video-feed.json',{cache:'no-store'}).then(x=>x.ok?x.json():Promise.reject(new Error('Catalogo non disponibile'))).then(render).catch(()=>{});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ztHomeGallery,{once:true});else ztHomeGallery();


/* Refresh the 3 Tech Impact + 2 Gaming Inside entries from the site's
   own approved editorial manifest. Static HTML above provides a safe fallback. */
(function(){
  'use strict';
  function refreshSpecials(){
    if(!document.getElementById('zt-special-tech'))return;
    fetch('/special-featured.json',{cache:'no-store'}).then(function(r){
      if(!r.ok)throw new Error('Special featured feed unavailable');
      return r.json();
    }).then(function(data){
      if(!data||!Array.isArray(data.items))return;
      [
        {section:'tech',limit:3},
        {section:'gaming',limit:2}
      ].forEach(function(setting){
        const items=data.items.filter(function(x){
          return x && x.section===setting.section && typeof x.title==='string' &&
            typeof x.slug==='string' && /^(tech-impact|gaming-inside)-[a-z0-9-]+\.html$/.test(x.slug) &&
            typeof x.image==='string' && x.image.startsWith('/assets/special/');
        }).slice(0,setting.limit);
        if(items.length!==setting.limit)return;
        const list=document.getElementById('zt-special-'+setting.section);
        if(!list)return;
        const fragment=document.createDocumentFragment();
        items.forEach(function(item){
          const article=document.createElement('article');
          article.className='zt-special-item';
          const thumb=document.createElement('a');
          thumb.className='zt-special-thumb';thumb.href='/'+item.slug;
          thumb.setAttribute('aria-label',item.title);
          const img=document.createElement('img');
          img.src=item.image;img.alt=item.title;img.loading='lazy';
          thumb.append(img);
          const h3=document.createElement('h3');
          const link=document.createElement('a');link.href='/'+item.slug;link.textContent=item.title;
          h3.append(link);
          article.append(thumb,h3);
          fragment.append(article);
        });
        list.replaceChildren(fragment);
      });
    }).catch(function(){/* Preserve server-rendered validated content. */});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',refreshSpecials,{once:true});
  else refreshSpecials();
})();

/* ZT editorial SMART STICKY: page-linked scroll with every box 100% visible.
   The previous nested scroll cut modules at the viewport boundary. Each right
   column now has natural height; a negative sticky top keeps the LAST card
   reachable as the user scrolls the main article. ResizeObserver handles
   lazy-loaded pictures and any new editorial cards. */
(function(){
  'use strict';
  function init(){
    var sides=document.querySelectorAll('aside.zt-side-mix');
    if(!sides.length)return;
    var query=window.matchMedia('(min-width:1001px)');
    var frame=0;
    function refresh(){
      frame=0;
      sides.forEach(function(side){
        // Mobile/tablet: the sidebar is simply part of the document.
        if(!query.matches){
          side.style.removeProperty('--zt-side-smart-top');
          return;
        }
        // getBoundingClientRect observes the natural height, never a clipped
        // scrolling window; large modules remain whole in the DOM.
        var fullHeight=side.getBoundingClientRect().height;
        var viewport=window.visualViewport
          ?window.visualViewport.height:window.innerHeight;
        var top=Math.min(16,Math.floor(viewport-fullHeight-16));
        var old=side.style.getPropertyValue('--zt-side-smart-top');
        var next=top+'px';
        if(old!==next)side.style.setProperty('--zt-side-smart-top',next);
      });
    }
    function schedule(){
      if(frame)return;
      frame=window.requestAnimationFrame(refresh);
    }
    if(typeof ResizeObserver==='function'){
      var observer=new ResizeObserver(schedule);
      sides.forEach(function(side){observer.observe(side)});
    }
    window.addEventListener('resize',schedule,{passive:true});
    if(window.visualViewport){
      window.visualViewport.addEventListener('resize',schedule,{passive:true});
    }
    window.addEventListener('load',schedule,{once:true});
    schedule();
  }
  if(document.readyState==='loading')
    document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();


/* ZT_SITE_BACK_TO_TOP_20261014 — accessible button on every public page. */
(function(){
 "use strict";
 function install(){
  if(document.getElementById("ztBackToTop"))return;
  const sheet=document.createElement("style");sheet.id="zt-backtop-style";
  sheet.textContent=".zt-backtop{position:fixed;right:clamp(16px,2vw,28px);bottom:calc(21px + env(safe-area-inset-bottom,0px));z-index:9000;width:54px;height:54px;display:grid;place-items:center;background:#df0935;color:#fff;border:0;border-radius:50%;font:900 29px/1 Arial,Helvetica,sans-serif;cursor:pointer;box-shadow:0 5px 14px #0003;opacity:0;visibility:hidden;pointer-events:none;transform:translateY(10px);transition:opacity .18s ease,transform .18s ease,visibility .18s}.zt-backtop.zt-backtop-visible{opacity:1;visibility:visible;pointer-events:auto;transform:translateY(0)}.zt-backtop:hover{background:#bd1230;box-shadow:0 7px 17px #0004}.zt-backtop:focus-visible{outline:3px solid #2185ff;outline-offset:3px}@media(max-width:620px){.zt-backtop{width:48px;height:48px;right:14px;bottom:calc(14px + env(safe-area-inset-bottom,0px));font-size:26px}}@media(prefers-reduced-motion:reduce){.zt-backtop{transition:none}}";
  document.head.appendChild(sheet);
  const button=document.createElement("button");button.type="button";button.id="ztBackToTop";
  button.className="zt-backtop";button.setAttribute("aria-label","Torna in alto");button.title="Torna in alto";
  button.textContent="↑";
  button.addEventListener("click",function(){
    const reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({top:0,behavior:reduce?"auto":"smooth"});
  });
  document.body.appendChild(button);
  let ticking=false;
  function sync(){
    ticking=false;
    const visible=window.scrollY>300;
    button.classList.toggle("zt-backtop-visible",visible);
    button.setAttribute("aria-hidden",visible?"false":"true");
  }
  window.addEventListener("scroll",function(){if(!ticking){ticking=true;requestAnimationFrame(sync);}},{passive:true});
  sync();
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install,{once:true});else install();
})();

/* ZT_REVIEW_SUBMENU_20261019 — one visible Recensioni button,
   accessible Tech/Gaming choices, no alteration to protected Home nav HTML. */
(function(){
  'use strict';
  function ready(){
    const links=Array.from(document.querySelectorAll('header .topbar nav.nav > a, header .zt-headrow nav.zt-nav > a'))
      .filter(a=>a.textContent.trim().toLowerCase()==='recensioni');
    if(!links.length||document.getElementById('zt-review-dropdown'))return;
    const menu=document.createElement('div');
    menu.id='zt-review-dropdown';
    menu.setAttribute('aria-label','Scegli le recensioni');
    menu.innerHTML='<a href="/recensioni-tech.html">TECH</a><a href="/recensioni-gaming.html">GAMING</a>';
    document.body.appendChild(menu);
    let active=null, timer=null;
    const cancel=()=>{if(timer!==null){clearTimeout(timer);timer=null;}};
    const close=()=>{
      cancel();
      menu.classList.remove('is-open');
      links.forEach(a=>a.setAttribute('aria-expanded','false'));
      active=null;
    };
    const position=()=>{
      if(!active)return;
      const b=active.getBoundingClientRect();
      if(b.bottom<0||b.top>innerHeight){close();return;}
      const width=menu.offsetWidth||176;
      menu.style.left=Math.round(Math.max(8,Math.min(b.left,innerWidth-width-8)))+'px';
      menu.style.top=Math.round(b.bottom+2)+'px';
    };
    const open=(link)=>{
      cancel();
      active=link;
      links.forEach(a=>a.setAttribute('aria-expanded',a===link?'true':'false'));
      menu.classList.add('is-open');
      position();
    };
    const delayedClose=()=>{cancel();timer=setTimeout(close,170);};
    links.forEach(a=>{
      a.setAttribute('aria-haspopup','true');
      a.setAttribute('aria-expanded','false');
      a.addEventListener('mouseenter',()=>{if(matchMedia('(hover: hover)').matches)open(a);});
      a.addEventListener('mouseleave',delayedClose);
      a.addEventListener('focus',()=>{if(matchMedia('(hover: hover)').matches)open(a);});
      a.addEventListener('keydown',e=>{
        if(e.key==='ArrowDown'||e.key===' '){e.preventDefault();open(a);menu.querySelector('a')?.focus();}
      });
      a.addEventListener('click',e=>{
        if(matchMedia('(hover: none)').matches){
          e.preventDefault();
          if(active===a&&menu.classList.contains('is-open'))close();else open(a);
        }
      });
    });
    menu.addEventListener('mouseenter',cancel);
    menu.addEventListener('mouseleave',delayedClose);
    menu.addEventListener('focusin',cancel);
    menu.addEventListener('focusout',e=>{if(!menu.contains(e.relatedTarget))delayedClose();});
    document.addEventListener('pointerdown',e=>{
      if(!menu.contains(e.target)&&!links.includes(e.target))close();
    });
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape'&&active){const old=active;close();old.focus();}
    });
    addEventListener('resize',position,{passive:true});
    addEventListener('scroll',()=>{if(active)position();},{passive:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});
  else ready();
})();


/* CYBERCULTURA_20261021: menu is a direct, accessible link.
   The obsolete Insights flyout was removed to avoid altering editorial routes. */

/* ZT_SITE_MENU_FLYOUT_20261019
   The existing Home menu is the only source of routes. Render its exact
   dropdown links as a fixed, keyboard/touch-accessible flyout everywhere. */
(function(){
  'use strict';
  function ready(){
    const drops=Array.from(document.querySelectorAll('header nav.nav > .nav-drop'));
    if(!drops.length||document.getElementById('zt-site-menu-flyout'))return;
    const flyout=document.createElement('nav');
    flyout.id='zt-site-menu-flyout';
    flyout.setAttribute('aria-label','Sottomenu del sito');
    document.body.appendChild(flyout);
    let active=null;
    let closeTimer=null;
    function cancel(){
      if(closeTimer!==null){clearTimeout(closeTimer);closeTimer=null;}
    }
    function close(){
      cancel();active=null;flyout.classList.remove('is-open');
      drops.forEach(drop=>{
        drop.classList.remove('zt-nav-open');
        const button=drop.querySelector(':scope > .nav-drop-trigger');
        if(button)button.setAttribute('aria-expanded','false');
      });
    }
    function position(){
      if(!active)return;
      const btn=active.querySelector(':scope > .nav-drop-trigger');
      if(!btn)return close();
      const rect=btn.getBoundingClientRect();
      if(rect.bottom<0||rect.top>innerHeight)return close();
      const width=flyout.offsetWidth||215;
      flyout.style.left=Math.max(8,Math.min(Math.round(rect.left),innerWidth-width-8))+'px';
      flyout.style.top=Math.min(innerHeight-8,Math.round(rect.bottom))+'px';
    }
    function open(drop){
      cancel();
      const source=drop.querySelectorAll(':scope > .nav-submenu a[href]');
      if(!source.length)return;
      flyout.replaceChildren(...Array.from(source,link=>link.cloneNode(true)));
      active=drop;
      drops.forEach(item=>{
        item.classList.toggle('zt-nav-open',item===drop);
        const button=item.querySelector(':scope > .nav-drop-trigger');
        if(button)button.setAttribute('aria-expanded',item===drop?'true':'false');
      });
      flyout.classList.add('is-open');
      position();
    }
    function delayedClose(){cancel();closeTimer=setTimeout(close,230);}
    drops.forEach(drop=>{
      const btn=drop.querySelector(':scope > .nav-drop-trigger');
      if(!btn)return;
      btn.setAttribute('aria-haspopup','true');
      btn.setAttribute('aria-expanded','false');
      btn.setAttribute('aria-controls','zt-site-menu-flyout');
      drop.addEventListener('mouseenter',()=>{if(matchMedia('(hover:hover)').matches)open(drop);});
      drop.addEventListener('mouseleave',delayedClose);
      btn.addEventListener('click',event=>{
        event.preventDefault();
        event.stopPropagation();
        if(active===drop&&flyout.classList.contains('is-open'))close();
        else open(drop);
      });
      btn.addEventListener('keydown',event=>{
        if(event.key==='ArrowDown'||event.key===' '){
          event.preventDefault();open(drop);
          flyout.querySelector('a')?.focus();
        }
      });
      btn.addEventListener('focus',()=>{if(matchMedia('(hover:hover)').matches)open(drop);});
    });
    flyout.addEventListener('mouseenter',cancel);
    flyout.addEventListener('mouseleave',delayedClose);
    flyout.addEventListener('focusin',cancel);
    flyout.addEventListener('focusout',event=>{
      if(!flyout.contains(event.relatedTarget))delayedClose();
    });
    document.addEventListener('pointerdown',event=>{
      if(active&&!flyout.contains(event.target)&&!active.contains(event.target))close();
    });
    document.addEventListener('keydown',event=>{
      if(event.key==='Escape'&&active){
        const btn=active.querySelector(':scope > .nav-drop-trigger');
        close();btn?.focus();
      }
    });
    addEventListener('resize',position,{passive:true});
    addEventListener('scroll',position,{passive:true});
    document.documentElement.classList.add('zt-site-menu-enhanced');
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});
  else ready();
})();
