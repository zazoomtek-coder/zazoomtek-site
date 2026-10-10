/* Progressive visual polish; does not replace the original editorial content. */
(function(){
 'use strict';
 function enhanceHomeSlider(){
  document.querySelectorAll('.news-slide').forEach(function(slide){
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
const ztHomeVideoFallback=[{"id":"O6VxSf8cYt0","title":"Dead Spin PC - Primo Sguardo","publishedAt":"2026-10-04T10:22:15Z","category":"gaming","short":false,"completedLive":false},{"id":"fKiuvUW5eKI","title":"🐰 WALTO | Recensione PC - Boss rush oscuro tra schivate e attacchi","publishedAt":"2026-10-05T12:28:27Z","category":"recensioni","short":false,"completedLive":false},{"id":"lmOGs9M_vhw","title":"IIFACTOR M08E AI Smart Glasses UNBOXING | Cosa c’è nella scatola?","publishedAt":"2026-09-12T12:54:11Z","category":"unboxing","short":false,"completedLive":false},{"id":"An2RZr9_Cxs","title":"Nintendo 64: il catalogo GIG del 1997 che ci faceva sognare | Retrogaming","publishedAt":"2026-09-08T09:32:22Z","category":"analogiktek","short":false,"completedLive":false},{"id":"WmIXQGZYhTc","title":"realme C100 5G Test Gaming","publishedAt":"2026-05-21T08:00:24Z","category":"test","short":false,"completedLive":false},{"id":"nQ26PED9Rgc","title":"ACE COMBAT 8 PS5 – Missione 2 NOMAD | Difendiamo la Flotta! Gameplay ITA","publishedAt":"2026-10-08T05:38:42Z","category":"gameplay","short":false,"completedLive":true}];
const ztHomeShortFallback=[{"id":"Mf8B30PKjqY","title":"Princess of the Water Lilies gameplay on PS5","publishedAt":"2026-10-02T12:29:00Z","short":true},{"id":"EaLvvrd6ysI","title":"Tomb Raider: Legacy of Atlantis – Everything changes in Egypt: mummies and supernatural creatures","publishedAt":"2026-09-29T11:05:07Z","short":true},{"id":"FOy-9dAvFMM","title":"70mai A900 Unboxing: cosa c’è nella confezione della Dash Cam 4K","publishedAt":"2026-09-28T13:07:58Z","short":true},{"id":"PV6JenVnwTo","title":"realme Buds T500 Pro Harry Potter Edition – UNBOXING 🪄🎧","publishedAt":"2026-09-22T17:30:19Z","short":true},{"id":"R2AFPqQpHaE","title":"🎮 Marvel’s Wolverine – Gameplay PS5","publishedAt":"2026-09-17T09:58:17Z","short":true},{"id":"DdzW7c0uLN0","title":"Battlefield 6 Season 4: Furious Tide is here with a FREE TRIAL","publishedAt":"2026-09-16T12:58:04Z","short":true}];
function ztHomeGallery(){
  const main=document.querySelector('main.page');
  if(!main || !document.querySelector('#ztStackList'))return;
  const existing=document.getElementById('zt-home-shelves');
  const shelves=existing || document.createElement('div');
  shelves.id='zt-home-shelves';
  shelves.className='zt-home-shelves';
  if(!existing)main.appendChild(shelves);
  const types=['gaming','recensioni','unboxing','analogiktek','test'];
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
    for(const type of types){
      const item=clean.find(x=>x.category===type && !x.short && !x.live && !x.completedLive && !used.has(x.id));
      if(item){used.add(item.id);selected.push(Object.assign({},item,{category:type}))}
    }
    // GAMEPLAY: most recent completed livestream, separate from regular GAMING uploads.
    let archive=clean.find(x=>x.completedLive && !x.short && !x.live && !used.has(x.id));
    if(!archive)archive=ztHomeVideoFallback.find(x=>x.category==='gameplay' && !used.has(x.id));
    if(archive){used.add(archive.id);selected.push(Object.assign({},archive,{category:'gameplay'}))}
    // Missing playlist data must not create fake slots.
    for(const item of ztHomeVideoFallback){
      if(selected.length>=6)break;
      if(!used.has(item.id) && item.category!=='gameplay'){used.add(item.id);selected.push(item)}
    }
    const shorts=clean.filter(x=>x.short&&!x.live).slice(0,6);
    if(shorts.length<6){for(const item of ztHomeShortFallback){if(shorts.length>=6)break;if(!shorts.some(s=>s.id===item.id))shorts.push(item)}}
    shelves.replaceChildren(group('ESPLORA VIDEO','https://www.youtube.com/@ZazoomTek/videos',selected.slice(0,6),false),group('ULTIMI SHORTS','https://www.youtube.com/@ZazoomTek/shorts',shorts.slice(0,6),true));
    document.body.classList.add('zt-home-shelves-ready');
  }
  render([...ztHomeVideoFallback,...ztHomeShortFallback]);
  fetch('/home-video-feed.json',{cache:'no-store'}).then(x=>x.ok?x.json():Promise.reject(new Error('Catalogo non disponibile'))).then(render).catch(()=>{});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ztHomeGallery,{once:true});else ztHomeGallery();
