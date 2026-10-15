/* ZazoomTek HOME 45/35/20: approved interactive layout.
   Keep canonical article feed markers in index.html for all importers.
   Reuse real cards, reviews, menus, guides, videos and Shorts. */
(function() {
 "use strict";
 const path=window.location.pathname;
 if(!["/","/index.html","/anteprima-home-produzione-validazione-20261013.html"].includes(path)) return;
 // HOME_TOPIC_CLASSIFIER_START
 // The canonical feed uses generic "News" for both categories. Classify the
 // article subject, not the YouTube post type and not the closing subscribe CTA.
 // Distinguish actual VIDEO GAMES from gaming-branded hardware and physical toys.
 function categorizeHomeArticle(title, excerpt="", imageAlt="", imageUrl="") {
   const normalize=s=>String(s||"").normalize("NFKD")
     .replace(/[\u0300-\u036f]/g,"").replace(/[’‘]/g,"'").toLowerCase();
   const heading=normalize(title);
   const body=normalize(excerpt).slice(0,550);
   const artwork=normalize(imageAlt+" "+imageUrl);
   const physicalNonDigital=/\b(senza schermo|senza connessione|giocattol|giochi educativi fisici|giocattoli in legno|giochi da tavolo tradizionali)\b/;
   const technologyProduct=/\b(smartphone|tablet|smartwatch|notebook|laptop|mini pc|stampant\w*|multifunzion\w*|router|modem|wifi|wi-fi|processore|chip ai|gpu|scheda video|periferiche|mouse|tastier|cuffie|auricolari|monitor|televis|videoproiett|forno|smart home|domotica|fotocamer|videocamer|firmware|sistema operativo|coloros|wear os|fotovoltaic|server|cloud|cybersecurity|sicurezza informatica|governance ai)\b/;
   const namedVideogame=/\b(pubg|fortnite|minecraft|roblox|battlefield|call of duty|dead space|ace combat|spongebob|titans of the tide|dragon'?s dogma|the talos principle|ea sports fc|fc 2[5-9]|fifa|gta|grand theft auto|crazy taxi|rockbeasts|tower tactics|total war|shogun|witcher|zelda|monster hunter|assassin'?s creed|tekken|street fighter|gran turismo|tomb raider|poly fighter|walto|chivalware|skate\.|mario kart|elden ring|diablo|halo|god of war|forza horizon|final fantasy)\b/;
   const gamingIndustry=/\b(videogioch|videogame|video game|gaming|esport|e-sport|cosplay|gameplay|steam|epic games|playstation|ps5|ps4|xbox|nintendo|switch 2|unity|unreal engine|ps store|steam next fest|demo gratuita|action rpg|roguelike|deckbuilding|gdr|game show|gioco digitale|giochi digitali|gioco di carte digitale|giochi di carte digitali|giocatori|videoludic)\b/;
   const explicitGamingCollection=/\b(hasbro games junior collection|monopoly junior|cluedo junior|lucca comics.*card collection|lc&g card collection|be comics|be games|players al m9)\b/;
   // A product stays in Tech even when its use case mentions gaming.
   if(technologyProduct.test(heading) && !namedVideogame.test(heading) && !explicitGamingCollection.test(heading))return "tech";
   if(physicalNonDigital.test(heading) && !/digitale|digitali|videogiochi/.test(heading))return "tech";
   if(namedVideogame.test(heading)||explicitGamingCollection.test(heading))return "gaming";
   if(/\b(esport|e-sport|videogioch|videogame|videoludic|gameplay|playstation|ps5|xbox|nintendo|steam|gaming|cosplay)\b/.test(heading))return "gaming";
   if(/\b(gioco di carte digital|giochi di carte digital|gioco digitale|giochi digitali|videogioco|demo di gioco|gioco per pc|titolo in accesso anticipato)\b/.test(heading))return "gaming";
   // The real article lead is a secondary signal for new and unfamiliar games.
   // Avoid using the full data-search field: it contains generic sign-off tags.
   if(/\b(videogioco|videogiochi|video game|gioco per pc|gioco per ps5|gioco per xbox|gioco per switch|titolo videoludico|gioco sviluppato|gioco pubblicato|demo su steam|rpg narrativo|gioco multiplayer|studio di sviluppo videoludico)\b/.test(body))return "gaming";
   if(gamingIndustry.test(body) && /\b(gioco|titolo|videogioco|videogiochi|avventura|giocatori|campagna|sviluppato|lancio)\b/.test(body) && !technologyProduct.test(heading))return "gaming";
   // Image filename or genuinely independent alt text can help when available.
   // There is no claim of visual recognition from opaque CDN image identifiers.
   if(!technologyProduct.test(heading) && /(?:^|[/._\s-])(gaming|videogame|gameplay|esports|video-game)(?:[/._\s-]|$)/.test(artwork))return "gaming";
   return "tech";
 }
 // HOME_TOPIC_CLASSIFIER_END

 // HOME_PUBLICATION_ORDER_START
 // Publication date is authoritative. This parser is independent from fetch
 // order, article category, homepage rebuild time, and image upload time.
 function homePublicationTime(rawValue){
  const raw=String(rawValue||"").toLowerCase().trim();
  if(!raw)return -Infinity;
  const iso=raw.match(/\b20\d\d-(?:0?[1-9]|1[0-2])-(?:[0-2]?\d|3[01])(?:[t\s]\d\d:\d\d(?::\d\d)?(?:z|[+-]\d\d:?\d\d)?)?/i);
  if(iso){const ms=Date.parse(iso[0]);if(Number.isFinite(ms))return ms;}
  const months={gennaio:0,febbraio:1,marzo:2,aprile:3,maggio:4,giugno:5,luglio:6,agosto:7,settembre:8,ottobre:9,novembre:10,dicembre:11};
  const date=raw.match(/\b([0-3]?\d)\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})\b/);
  if(date)return Date.UTC(+date[3],months[date[2]],+date[1]);
  const slash=raw.match(/\b([0-3]?\d)[\/-](0?\d|1[0-2])[\/-](20\d{2})\b/);
  if(slash)return Date.UTC(+slash[3],+slash[2]-1,+slash[1]);
  // Legacy imports can contain Italian relative labels.
  const todayParts=new Intl.DateTimeFormat("en-GB",{timeZone:"Europe/Rome",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(new Date());
  const value=k=>Number(todayParts.find(p=>p.type===k)?.value||0);
  const today=Date.UTC(value("year"),value("month")-1,value("day"));
  if(/\boggi\b/.test(raw))return today;
  if(/\bieri\b/.test(raw))return today-86400000;
  const ago=raw.match(/\b(\d{1,3})\s+giorni?\s+fa\b/);
  if(ago)return today-(+ago[1])*86400000;
  return -Infinity;
 }
 function orderHomeColumn(column){
  const cards=[...column.children].filter(node=>node.matches("article.article-row"));
  const ranked=cards.map((node,index)=>({node,index,
    date:homePublicationTime(node.getAttribute("data-published-at")||
       node.querySelector(".article-meta")?.textContent||"")}));
  ranked.sort((a,b)=>b.date-a.date || a.index-b.index);
  for(const entry of ranked)column.appendChild(entry.node);
  return ranked.map(x=>x.node);
 }
 // HOME_PUBLICATION_ORDER_END

 function setup(){
  const layout=document.querySelector('main.page .layout');
  const main=layout&&layout.querySelector(':scope > .maincol');
  const side=layout&&layout.querySelector(':scope > aside.sidebar');
  const original=document.querySelector('section.module#articoli');
  const latest=main&&main.querySelector(".latest-reviews-module");
  const guide=main&&main.querySelector("#ztHomeGuide");
  if(!main||!side||!original||!latest||!guide)return;
  if(document.querySelector(".ztp-final-three"))return;
  const rows=[...original.querySelectorAll('.article-list > article.article-row')];
  if(rows.length<10)return;
  const fragmentHTML="<section class=\"ztp-news-area\" id=\"articoli\" aria-label=\"Ultimi articoli suddivisi tra Tech e Gaming\">\n<div class=\"ztp-split-heading\"><div><span class=\"ztp-kicker\"></span><h2>Le ultime notizie di ZazoomTek</h2></div><span class=\"ztp-count\">15 news · Tech e Gaming</span></div>\n<div class=\"ztp-three-columns ztp-final-three\" id=\"articleList\">\n<div class=\"ztp-primary-feed\">\n<div class=\"ztp-two-news-columns\">\n<section class=\"ztp-news-column ztp-news-tech\" aria-labelledby=\"ztp-tech-heading\"><header class=\"ztp-news-head\"><h2 id=\"ztp-tech-heading\"><span>ULTIMI ARTICOLI</span><b>TECH</b></h2><small>8 news</small></header><div class=\"ztp-news-items\">\n\n\n\n\n\n\n</div></section>\n<section class=\"ztp-news-column ztp-news-gaming\" aria-labelledby=\"ztp-gaming-heading\"><header class=\"ztp-news-head\"><h2 id=\"ztp-gaming-heading\"><span>ULTIMI ARTICOLI</span><b>GAMING</b></h2><small>7 news</small></header><div class=\"ztp-news-items\">\n\n\n\n\n\n</div></section>\n</div>\n<div class=\"ztp-videos-anchor\" id=\"ztpVideosAnchor\" aria-label=\"Esplora Ultimi Video del canale ZazoomTek\"></div>\n<div class=\"ztp-news-pagination-internal\" id=\"ztpNewsPager\"></div>\n</div>\n<aside class=\"ztp-news-rail\" id=\"ztpNewsRail\" aria-label=\"Box editoriali, articoli più letti, Tech Impact e Gaming Inside\"></aside>\n</div>\n\n</section>";
  const wrapper=document.createElement("div");
  wrapper.innerHTML=fragmentHTML;
  const area=wrapper.querySelector(".ztp-news-area");
  if(!area) return;
  // The approved Home has no preview caption, layout percentages or debug counter.
  const redundantPreviewHeading=area.querySelector(".ztp-split-heading");
  if(redundantPreviewHeading)redundantPreviewHeading.remove();
  // Defense in depth if older templates still ship a preview-only side header.
  const editorialPreviewBar=area.querySelector(".ztp-editorial-heading");
  if(editorialPreviewBar)editorialPreviewBar.remove();
  const tech=area.querySelector(".ztp-news-tech .ztp-news-items");
  const gaming=area.querySelector(".ztp-news-gaming .ztp-news-items");
  const rail=area.querySelector(".ztp-news-rail");
  if(!tech||!gaming||!rail)return;
  // Build directly from the fifteen canonical, auto-updated Community news.
  // Nothing is retyped or guessed; same image, excerpt, title and actual link.
  // Classify from the headline plus actual article lead and artwork metadata.
  let techCount=0,gamingCount=0;
  for(const row of rows){
   const title=row.querySelector('h3 a')?.textContent||"";
   const category=(row.dataset.postCategory||"").toLowerCase();
   // HARD EXCLUSION: EXTRA stays in /extra.html, even when its headline
   // mentions computers, gaming or technology incidentally.
   if(category==="extra"||/^news\s+extra\s*:/i.test(title)){
    row.hidden=true;
    continue;
   }
   const lead=row.querySelector(".article-copy p")?.textContent||"";
   const image=row.querySelector("img.article-image");
   const route=(category==="tech"||category==="gaming")?category:null;
   const isGaming=(route||categorizeHomeArticle(title,lead,image?.alt||"",image?.getAttribute("src")||""))==="gaming";
   row.classList.add("ztp-news-item");
   if(isGaming){
    const i=gamingCount++;
    if(i===0||i===3)row.classList.add("ztp-gaming-feature");
    else row.classList.remove("ztp-gaming-feature");
    const copy=row.querySelector(".article-copy");
    if(copy&&!copy.querySelector(".ztp-gaming-kind")){
      const label=document.createElement("span");
      label.className="ztp-gaming-kind";
      label.textContent=/sport|fc 27|racing/i.test(title)?"SPORT & CORSE":
        /tekken|street fighter/i.test(title)?"PICCHIADURO":
        /indie|chivalware/i.test(title)?"INDIE & NOVITÀ":"GAMING";
      copy.prepend(label);
    }
    gaming.appendChild(row);
   }else{techCount++;tech.appendChild(row);}
  }

  // Featured stories live ONLY in the six-card mosaic while selected.
  // Remove them from the homepage feeds (archive pages remain chronological).
  const featuredUrls=new Set([...document.querySelectorAll('#ztFeaturedGrid > a[href]')].map(a=>new URL(a.getAttribute('href'),location.href).pathname));
  function suppressFeaturedDuplicates(){
    const cards=[...tech.querySelectorAll('article.article-row'),...gaming.querySelectorAll('article.article-row')];
    for(const card of cards){
      const href=card.querySelector('h3 a[href]')?.getAttribute('href');
      if(!href)continue;
      const isFeatured=featuredUrls.has(new URL(href,location.href).pathname);
      card.hidden=isFeatured;
      card.style.display=isFeatured?'none':'';
    }
  }
  suppressFeaturedDuplicates();
  const featuredGrid=document.getElementById('ztFeaturedGrid');
  if(featuredGrid)new MutationObserver(function(){
    featuredUrls.clear();
    featuredGrid.querySelectorAll('a[href]').forEach(a=>featuredUrls.add(new URL(a.getAttribute('href'),location.href).pathname));
    suppressFeaturedDuplicates();
  }).observe(featuredGrid,{childList:true});
  // Live Tech and Gaming are derived exclusively from the latest canonical Community feed.
  // Never reinsert a static Gaming archive above new articles.
  orderHomeColumn(tech);
  const orderedGaming=orderHomeColumn(gaming);
  let currentOrder=0;
  for(const item of orderedGaming){
   const extra=item.classList.contains("ztp-gaming-extra");
   item.classList.toggle("ztp-gaming-feature",!extra&&(currentOrder===0||currentOrder===3));
   if(!extra)currentOrder++;
  }
  const previewCounter=area.querySelector('.ztp-count');
  if(previewCounter)previewCounter.textContent=rows.length+' news · Tech e Gaming';
  area.querySelector(".ztp-news-tech .ztp-news-head small").textContent=techCount+" news";
  area.querySelector(".ztp-news-gaming .ztp-news-head small").textContent=gamingCount+" news";
  // Hide only the canonical shell, not its imported content (now moved).
  original.id="ztCanonicalNews";
  original.style.display="none";
  const originalList=original.querySelector("#articleList");
  if(originalList)originalList.id="ztCanonicalArticleList";
  area.id="articoli";
  original.insertAdjacentElement("afterend",area);
  // Move live pagination: still updated by scripts and fully clickable.
  const pagination=original.querySelector("nav.pagination");
  if(pagination)area.querySelector("#ztpNewsPager").appendChild(pagination);
  // Small pagination belongs directly after the Tech/Gaming news, not after videos.
  const pager=area.querySelector("#ztpNewsPager");
  const newsColumns=area.querySelector(".ztp-primary-feed .ztp-two-news-columns");
  if(pager&&newsColumns)newsColumns.insertAdjacentElement("afterend",pager);
  layout.classList.add("ztp-three-home");
  const top=document.createElement("div");top.className="ztp-top";
  const topMain=document.createElement("div");topMain.className="ztp-top-main";
  const video=document.createElement("section");
  video.className="ztp-review-videos ztp-top-videos";
  video.setAttribute("aria-label","Ultime video recensioni ZazoomTek");
  video.innerHTML='<h2>ULTIME VIDEO RECENSIONI</h2><div class="ztp-review-list" id="ztpReviewVideoList"></div><div class="ztp-review-footer"><a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener noreferrer">TUTTE LE VIDEO RECENSIONI →</a></div>';
  topMain.append(latest,guide);top.append(topMain);main.insertBefore(top,area);
  const list=video.querySelector("#ztpReviewVideoList");
  // Selected dynamically from the actual authenticated channel JSON.
  const fallbackReviewIDs=["WwGAaKGfoGY","tb1CAHc1QoM","6Zz4E1FhAY4"];
  function renderReviews(items){
   if(!Array.isArray(items)||items.length<3)return;
   const chosen=items.filter(x=>x&&/^[A-Za-z0-9_-]{11}$/.test(String(x.id||""))).slice(0,3);
   if(chosen.length!==3)return;
   list.replaceChildren();
   for(const item of chosen){
    const id=String(item.id);
    const card=document.createElement("article");card.className="ztp-review-card";
    const link=document.createElement("a");
    link.href="https://www.youtube.com/watch?v="+encodeURIComponent(id);link.target="_blank";link.rel="noopener noreferrer";
    const imageBox=document.createElement("span");imageBox.className="ztp-review-thumb";
    const image=document.createElement("img");image.src="https://i.ytimg.com/vi/"+id+"/hqdefault.jpg";image.alt=item.title||"Recensione ZazoomTek";image.loading="lazy";
    const play=document.createElement("span");play.className="ztp-review-play";play.textContent="▶";play.setAttribute("aria-hidden","true");
    imageBox.append(image,play);
    const copy=document.createElement("span");copy.className="ztp-review-copy";
    const name=document.createElement("strong");name.textContent=item.title||"Recensione";
    const date=document.createElement("small");
    try{date.textContent=new Intl.DateTimeFormat("it-IT",{day:"numeric",month:"long",year:"numeric",timeZone:"Europe/Rome"}).format(new Date(item.publishedAt));}catch(_){date.textContent="ZazoomTek";}
    copy.append(name,date);link.append(imageBox,copy);card.append(link);list.appendChild(card);
   }
  }
  const originalStack=side.querySelector(".zt-video-stack");
  const pop=side.querySelector("#zt-popular-box");
  const impact=side.querySelector('.zt-special-box[data-special-section="tech"]');
  const inside=side.querySelector('.zt-special-box[data-special-section="gaming"]');
  if(pop)rail.appendChild(pop);
  if(impact)rail.appendChild(impact);
  if(inside)rail.appendChild(inside);
  if(originalStack)originalStack.remove();
  while(side.firstElementChild)rail.appendChild(side.firstElementChild);
  side.remove();
  const videoShelfTarget=area.querySelector("#ztpVideosAnchor");
  // Shorts stay in the 20% editorial rail, beneath Dalla Redazione;
  // Explore Video retains its full original width.
  const shortsSlot=document.createElement("aside");
  shortsSlot.className="ztp-shorts-companion";
  shortsSlot.setAttribute("aria-label","Ultimi Shorts ZazoomTek");
  const root=document.querySelector("main.page");
  function mountShelves(){
   const shelves=document.getElementById("zt-home-shelves");
   if(!shelves||!videoShelfTarget)return false;
   if(shelves.parentElement!==videoShelfTarget)videoShelfTarget.appendChild(shelves);
   const sync=()=>{
     const full=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&!el.querySelector(".zt-shelf-shorts"));
     if(full){const h=full.querySelector(".zt-shelf-head h2");if(h&&h.textContent!=="ESPLORA ULTIMI VIDEO")h.textContent="ESPLORA ULTIMI VIDEO";}
     const shorts=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&el.querySelector(".zt-shelf-shorts")) || rail.querySelector(".ztp-rail-shorts") || shortsSlot.querySelector(".ztp-rail-shorts");
     if(!shorts)return;
     shorts.classList.add("ztp-rail-shorts");
     const heading=shorts.querySelector(".zt-shelf-head h2");
     if(heading)heading.textContent="ULTIMI SHORTS";
     const prev=shortsSlot.querySelector(".ztp-rail-shorts");
     if(prev&&prev!==shorts)prev.replaceWith(shorts);
     else if(shorts.parentElement!==shortsSlot)shortsSlot.appendChild(shorts);
     requestAnimationFrame(reconcileRight);
   };
   sync();
   requestAnimationFrame(reconcileRight);
   if(!shelves.dataset.ztpShortsObserved){
     shelves.dataset.ztpShortsObserved="yes";
     new MutationObserver(sync).observe(shelves,{childList:true});
   }
   return true;
  }
  if(!mountShelves()&&root){
   const obs=new MutationObserver(()=>{if(mountShelves())obs.disconnect();});
   obs.observe(root,{childList:true});
  }
  // Only distinct real archive articles may expand Gaming. A static hidden
  // cache is never shown twice, and card balancing avoids creating new gaps.
  // Keep category columns aligned without injecting stale, prewritten Gaming news.
  // Match their rendered heights by distributing spare space BETWEEN real cards.
  // Mobile/tablet stacks remain untouched.
  // Eliminate inline height/space-between that artificially spread Gaming articles.
  function balance(){
    [area.querySelector(".ztp-news-tech .ztp-news-items"),area.querySelector(".ztp-news-gaming .ztp-news-items")].forEach(function(col){
      if(!col)return;
      ["min-height","height","display","flex-direction","justify-content"].forEach(function(p){col.style.removeProperty(p);});
    });
  }

  // Fill remaining vertical space with published articles, never blank padding.
  // Entries come from real, distinct archived news URLs on ZazoomTek.
  const sidebarEditorials=[{"title":"Invincible VS, la Stagione 2 introduce Angstrom Levy e anticipa Agent Spider per la Stagione 3","url":"/news-UgkxXceRhhYmqSVnSCYUnBmmGOoUEExn5Fza.html","image":"https://yt3.ggpht.com/EoKOEVjA0Gx455lYDry-3KyVbbe1TxA5Dj3gNRquLiJQWKjo1XT0AGUZzOWQL6HQVU9HIljvqASgFQ=s1600-rw-nd-v1"},{"title":"Sony premiata con il Technology & Engineering Emmy Award per il contributo alle specifiche NMOS","url":"/news-Ugkxo5QI5Efk3Q7DxPZMMGveZ4DWlrfsrdDZ.html","image":"https://yt3.ggpht.com/pfG4zfQsycErlklS-LG5nUfVjctrMKT6H0eU1OfcVzbm4GONidmrSZWup1VnlbVRGHT4dM4L9X0mHw=s1600-rw-nd-v1"},{"title":"Hisense presenta Speed Oven, il forno 7-in-1 che raggiunge 230 °C in soli 60 secondi","url":"/news-UgkxkZg10OhFGxe-d-bQ_gj4zino-VF-ER5K.html","image":"https://yt3.ggpht.com/OIMvcjBOepuvTEVDOs7xTOfsC3l6RwqjdycDx0YJOlQU41ArFoRkgc4HjTI0FFsaqARtrHVyBkABLw=s1600-rw-nd-v1"},{"title":"AI e governance, per Veeam senza visibilità non può esistere un vero controllo","url":"/news-Ugkx421MOc98LGwAzu85c136vEAf5r_50wfO.html","image":"https://yt3.ggpht.com/caAAYlybmsmVmX8jAK2JH3BzkDRDq8aW1R1AibgdGiY5RAm5cbB6gZf9jEFhfsN1iulP010cBRqV=s1600-rw-nd-v1"},{"title":"Huawei lancia in Italia WATCH 6 Series e MatePad Pro 12\", tra benessere, produttività e design premium","url":"/news-UgkxbcoXD_25p4VIR7kWs-B0XEppXkXv9j2h.html","image":"https://yt3.ggpht.com/2PV-epMqjxmtEPMBhw0wCcPQY2w1qd0GxVcthNzmq0ALW9masWhyj-gbgl0Ytg2a-lax81wD4Ia3tg=s1600-rw-nd-v1"},{"title":"Be Comics! Be Games! Be XMAS! arriva a Torino il 12 e 13 dicembre con gaming, cosplay e cultura pop","url":"/news-UgkxilSWumVWHCrchRnCxRIn-wDLxZ7zAOYa.html","image":"https://yt3.ggpht.com/eE-6hFhgCW3xuGRcbwlL6zsHhLra8V0U7FpVFOGV54VAguRLNz0AOkLztPgJnP1NpMS8xJ60QVDM=s1600-rw-nd-v1"}];
  const editorialBox=document.createElement("section");
  editorialBox.className="ztp-editorial-archive";
  const editorialHead=document.createElement("h2");editorialHead.textContent="DALLA REDAZIONE";
  editorialBox.append(editorialHead);
  const editorialCards=[];
  for(const item of sidebarEditorials){
    const article=document.createElement("a");article.className="ztp-editorial-story";
    article.href=item.url;article.hidden=true;
    const pic=document.createElement("img");pic.src=item.image;pic.alt=item.title;pic.loading="lazy";
    const title=document.createElement("strong");title.textContent=item.title;
    article.append(pic,title);editorialBox.append(article);editorialCards.push(article);
  }
  const ytFollow=rail.querySelector(".zt-youtube-follow");
  if(ytFollow)ytFollow.insertAdjacentElement("afterend",editorialBox);
  else rail.appendChild(editorialBox);
  editorialBox.insertAdjacentElement("afterend",shortsSlot);
  // Three large and real editorial images; keep article links, never inject placeholders.
  function reconcileRight(){
    if(!document.documentElement.classList.contains("ztp-home-live-ready"))return;
    const linked=new Set([...area.querySelectorAll(".ztp-news-item h3 a")].map(a=>{
      try{return new URL(a.getAttribute("href"),location.origin).pathname;}catch(_){return "";}
    }));
    const eligible=editorialCards.filter(card=>!linked.has(new URL(card.href).pathname));
    const selected=new Set(eligible.slice(0,3));
    editorialCards.forEach(card=>{card.hidden=!selected.has(card);});
    editorialBox.style.display=selected.size?"block":"none";
  }

  balance();
  window.addEventListener("load",()=>{balance();requestAnimationFrame(reconcileRight)},{once:true});
  window.addEventListener("resize",()=>requestAnimationFrame(()=>{balance();reconcileRight()}),{passive:true});
  // Channel JSON is authoritative and refreshes all three video review cards.
  fetch("/home-video-feed.json",{cache:"no-store"}).then(r=>{
    if(!r.ok)throw Error("video catalog unavailable");return r.json();
  }).then(items=>{
    const v=items.filter(x=>x&&x.category==="recensioni"&&!x.short&&!x.live)
       .sort((a,b)=>String(b.publishedAt||"").localeCompare(String(a.publishedAt||""))).slice(0,3);
    renderReviews(v);
  }).catch(()=>{});
  document.documentElement.classList.add("ztp-home-live-ready");
  requestAnimationFrame(reconcileRight);
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",setup,{once:true});
 else setup();
})();


/* ZT_HOME_MAGAZINE_10X10_20261014
   Home-only progressive enhancement. Existing import, SEO, dates and routes remain authoritative.
   Featured articles are enlarged using existing editorial selection, never invented view counts. */
(function () {
  "use strict";
  if (!["/","/index.html"].includes(window.location.pathname)) return;

  function enhance() {
    var area=document.querySelector("#articoli.ztp-news-area");
    if (!area || area.dataset.ztMagazine1010==="yes") return;
    var tech=area.querySelector(".ztp-news-tech .ztp-news-items");
    var gaming=area.querySelector(".ztp-news-gaming .ztp-news-items");
    if (!tech || !gaming) return;
    area.dataset.ztMagazine1010="yes";

    var css=[
      "#articoli.ztp-news-area{--zt-mag-border:#dfe6ef;--zt-mag-radius:15px}",
      "#articoli .ztp-news-column,#articoli .ztp-news-rail>section{border:1.5px solid var(--zt-mag-border)!important;border-radius:var(--zt-mag-radius)!important;overflow:hidden!important;box-shadow:none!important}",
      "#articoli .ztp-news-head small{display:none!important}",
      "#articoli .ztp-news-items{padding:6px 11px 10px!important}",
      "#articoli .ztp-news-items>.article-row{display:grid!important;grid-template-columns:minmax(0,46%) minmax(0,1fr)!important;gap:10px!important;align-items:center!important;padding:12px 0!important;min-height:0!important;margin:0!important}",
      "#articoli .ztp-news-items>.article-row[hidden]{display:none!important}",
      "#articoli .ztp-news-items>.article-row.zt-mag-big{display:block!important;padding:12px 0 16px!important;grid-template-columns:none!important}",
      "#articoli .ztp-news-items>.article-row>a:first-child{margin:0!important;display:block!important;overflow:hidden!important}",
      "#articoli .ztp-news-items>.article-row .article-image{width:100%!important;height:auto!important;aspect-ratio:16/9!important;max-height:none!important;object-fit:contain!important;object-position:center center!important;border-radius:9px!important;background:#131b29!important}",
      "#articoli .ztp-news-items>.article-row.zt-mag-big>a:first-child{margin:0 0 9px!important}",
      "#articoli .ztp-news-items>.article-row.zt-mag-big .article-image{aspect-ratio:16/9!important}",
      "#articoli .ztp-news-items>.article-row .article-copy h3{font-size:clamp(11px,.84vw,13px)!important;line-height:1.29!important;margin:2px 0 5px!important}",
      "#articoli .ztp-news-items>.article-row.zt-mag-big .article-copy h3{font-size:clamp(14px,1.15vw,18px)!important;line-height:1.23!important}",
      "#articoli .ztp-news-items>.article-row:not(.zt-mag-big) .article-copy p{display:none!important}",
      "#articoli .ztp-news-items>.article-row.zt-mag-big .article-copy p{display:-webkit-box!important;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden!important;font-size:11px!important;line-height:1.4!important}",
      "#articoli .ztp-news-items>.article-row .article-copy .read-more{font-size:9px!important;padding:5px 7px!important}",
      "#articoli .ztp-news-rail .zt-special-item{display:block!important;grid-template-columns:none!important;padding:10px 11px!important;margin:0!important;min-height:0!important}",
      "#articoli .ztp-news-rail .zt-special-item:nth-child(n+3){display:none!important}",
      "#articoli .ztp-news-rail .zt-special-thumb{display:block!important;width:100%!important}",
      "#articoli .ztp-news-rail .zt-special-thumb img{width:100%!important;max-height:none!important;height:auto!important;aspect-ratio:16/9!important;object-fit:contain!important;object-position:center center!important;border-radius:9px!important;background:#172131!important}",
      "#articoli .ztp-news-rail .zt-special-item h3{font-size:11px!important;line-height:1.3!important;margin:7px 0 3px!important}",
      "#articoli .ztp-news-rail #zt-popular-box .zt-popular-article{display:block!important;padding:10px 11px!important;grid-template-columns:none!important}",
      "#articoli .ztp-news-rail #zt-popular-box .zt-popular-list>.zt-popular-article:nth-of-type(n+3){display:none!important}",
      "#articoli .ztp-news-rail #zt-popular-box .zt-popular-article img{width:100%!important;height:auto!important;aspect-ratio:16/9!important;object-fit:contain!important;object-position:center!important;border-radius:9px!important;background:#141923!important}",
      "#articoli .ztp-news-rail #zt-popular-box .zt-popular-copy{display:block!important;margin-top:6px!important}",
      "#articoli .ztp-news-rail #zt-popular-box .zt-popular-copy strong{font-size:11px!important;line-height:1.32!important}",
      "#articoli .ztp-news-rail .zt-special-footer{display:block!important}",
      "#articoli .ztp-news-rail .zt-special-box,#articoli .ztp-news-rail #zt-popular-box{min-width:0!important}",
      "#articoli .ztp-news-rail img{object-position:center center!important}",
      "@media(min-width:1150px){#articoli .ztp-final-three{grid-template-columns:minmax(0,4fr) minmax(0,1fr)!important;gap:13px!important}#articoli .ztp-final-three .ztp-primary-feed{grid-column:1!important;grid-row:1!important}#articoli .ztp-final-three .ztp-news-rail{grid-column:2!important;grid-row:1!important;display:flex!important;gap:13px!important;flex-direction:column!important}#articoli .ztp-final-three .ztp-two-news-columns{grid-template-columns:minmax(0,5fr) minmax(0,3fr)!important;gap:12px!important}}",
      "@media(min-width:821px) and (max-width:1149px){#articoli .ztp-final-three{grid-template-columns:1fr!important}#articoli .ztp-final-three .ztp-primary-feed{grid-column:1!important;grid-row:1!important}#articoli .ztp-final-three .ztp-two-news-columns{grid-template-columns:minmax(0,5fr) minmax(0,3fr)!important}#articoli .ztp-final-three .ztp-news-rail{grid-column:1!important;grid-row:2!important;display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important}}",
      "@media(max-width:820px){#articoli .ztp-final-three{grid-template-columns:1fr!important}#articoli .ztp-final-three .ztp-two-news-columns{grid-template-columns:1fr!important}#articoli .ztp-news-items>.article-row .article-copy h3{font-size:12px!important}#articoli .ztp-news-items>.article-row.zt-mag-big .article-copy h3{font-size:17px!important}}",
      "@media(max-width:420px){#articoli .ztp-news-items>.article-row:not(.zt-mag-big){grid-template-columns:43% minmax(0,1fr)!important;gap:8px!important}#articoli .ztp-news-rail .zt-special-item h3{font-size:12px!important}}",
      "@media(prefers-reduced-motion:reduce){#articoli .ztp-news-items>.article-row{transition:none!important}}"
    ].join("\n");
    var sty=document.createElement("style");sty.id="zt-home-magazine-1010";sty.textContent=css;document.head.appendChild(sty);

    function hrefOf(node) {
      var a=node.querySelector(".article-copy h3 a");
      if (!a) return "";
      try { return new URL(a.getAttribute("href"),window.location.origin).pathname; }
      catch(e) { return ""; }
    }
    var seen=new Set([].concat([].slice.call(tech.querySelectorAll("article.article-row")),[].slice.call(gaming.querySelectorAll("article.article-row"))).map(hrefOf).filter(Boolean));
    function classify(title) {
      var t=String(title||"").toLowerCase();
      if (/^news\s+gaming\s*:|^gaming\s*:/.test(t)) return "gaming";
      if (/^news\s+tech\s*:|^tech\s*:/.test(t)) return "tech";
      if (/\b(pubg|playstation|ps5|xbox|nintendo|gaming|videogioch|videogame|fortnite|minecraft|steam|shogun|tekken|warhammer|enshrouded|lucca comics|cluedo|monopoly|just dance|battlefield|rpg|gameplay|wolverine|diablo|total war|ubisoft|spongebob|game ground|ace combat)\b/.test(t)) return "gaming";
      return "tech";
    }
    function makeArticle(from) {
      var link=from.querySelector(".news-copy h2 a");
      var img=from.querySelector("img");
      if (!link||!img) return null;
      var title=String(link.textContent||"").trim();
      if(/^news\s+extra\s*:/i.test(title)||from.getAttribute("data-post-category")==="extra")return null;
      var url=link.getAttribute("href");
      if (!url||!/^\/(news-|tech-impact-|gaming-inside-)[\w-]+\.html$/.test(url)||seen.has(url)) return null;
      seen.add(url);
      var article=document.createElement("article");
      article.className="article-row ztp-news-item zt-mag-archive";
      var imageLink=document.createElement("a");imageLink.href=url;
      var photo=document.createElement("img");photo.className="article-image";
      photo.src=img.getAttribute("src");photo.alt=img.alt||link.textContent.trim();
      photo.loading="lazy";photo.decoding="async";
      imageLink.appendChild(photo);
      var copy=document.createElement("div");copy.className="article-copy";
      var h3=document.createElement("h3"), title=document.createElement("a");
      title.href=url;title.textContent=link.textContent.trim();h3.appendChild(title);
      var date=document.createElement("div");date.className="article-meta";
      date.textContent=(from.querySelector(".news-meta")||{}).textContent||"ZazoomTek";
      var p=document.createElement("p");p.textContent=(from.querySelector(".news-copy p")||{}).textContent||"";
      var read=document.createElement("a");read.className="read-more";read.href=url;read.textContent="LEGGI TUTTO ›";
      copy.append(h3,date,p,read);article.append(imageLink,copy);
      return article;
    }
    function rebalance() {
      var featured=new Set([].slice.call(document.querySelectorAll("#ztFeaturedGrid a[href]"))
        .map(function(a){try{return new URL(a.getAttribute("href"),location.origin).pathname;}catch(e){return "";}}));
      [[tech,3],[gaming,4]].forEach(function(pair){
        var col=pair[0],maxBig=pair[1];
        var rows=[].slice.call(col.querySelectorAll(":scope > article.article-row"));
        rows.forEach(function(r,i){r.hidden=i>=10;r.classList.remove("zt-mag-big","ztp-gaming-feature");});
        var firstTen=rows.slice(0,10);
        var chosen=firstTen.map(function(r,i){return featured.has(hrefOf(r))?i:-1;}).filter(function(i){return i>=0;}).slice(0,maxBig);
        var fallback=maxBig===3?[0,4,8]:[0,3,6,9];
        fallback.forEach(function(i){if(chosen.length<maxBig&&i<firstTen.length&&!chosen.includes(i))chosen.push(i);});
        firstTen.forEach(function(r,i){r.classList.toggle("zt-mag-big",chosen.includes(i));});
        var n=col.closest(".ztp-news-column").querySelector(".ztp-news-head small");
        if(n) n.textContent=Math.min(10,firstTen.length)+" news";
      });
    }
    rebalance();
    // The canonical 15 home articles remain untouched. Only published archive cards may fill missing slots.
    function fillArchive(path) {
      return fetch(path,{cache:"force-cache",credentials:"same-origin"})
      .then(function(resp){if(!resp.ok)throw new Error("Archive unavailable");return resp.text();})
      .then(function(html){
        var doc=new DOMParser().parseFromString(html,"text/html");
        [].slice.call(doc.querySelectorAll(".news-list article.news-row")).forEach(function(src){
          var link=src.querySelector(".news-copy h2 a");
          if(!link) return;
          var name=link.textContent.trim();
          var section=classify(name)==="gaming"?gaming:tech;
          if(section.querySelectorAll(":scope > article.article-row").length>=10)return;
          var row=makeArticle(src);
          if(row)section.appendChild(row);
        });
        rebalance();
        return tech.querySelectorAll(":scope > article.article-row").length>=10 &&
               gaming.querySelectorAll(":scope > article.article-row").length>=10;
      });
    }
    fillArchive("/news.html").then(function(full){
      if(!full)return fillArchive("/news-2.html");
      return true;
    }).catch(function(){rebalance();});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",enhance,{once:true});
  else enhance();
})();


/* ZT_HOME_RESTORE_REVIEWS_GUIDE_EXTRA_20261014
   Runtime-only enhancement: canonical news URLs and imports remain unchanged. */
(function(){
 "use strict";
 if(!["/","/index.html"].includes(location.pathname))return;
 function run(){
   const area=document.querySelector("#articoli.ztp-news-area");
   const top=document.querySelector(".ztp-top");
   const review=document.querySelector(".ztp-top-main .latest-reviews-module");
   const guide=document.querySelector(".ztp-top-main #ztHomeGuide");
   if(!area||!top||!review||!guide||document.getElementById("ztp-guide-extra"))return;
   const stylesheet=document.createElement("link");stylesheet.rel="stylesheet";
   stylesheet.href="/zt-home-gap-fix-20261014.css?v=9";document.head.appendChild(stylesheet);
   area.querySelectorAll(".ztp-news-items").forEach(function(col){
     ["min-height","height","display","flex-direction","justify-content"].forEach(function(p){col.style.removeProperty(p);});
   });
   const track=review.querySelector("#latestVideos");
   const olderCards=track?[...track.querySelectorAll("article.video-card")]:[];
   const gamingCards=olderCards.filter(function(card){
     const url=card.querySelector("h3 a")?.getAttribute("href")||"";
     return /poly-fighter|sesame-street|transport-fever|recensione-Ugkxvpi|walto|recensione-Ugkx1Mz|ace-combat|recensione-UgkxPQV/i.test(url);
   }).slice(0,3);
   function reviewCard(data){
     const c=document.createElement("article");c.className="video-card zt-review-card";
     const imageLink=document.createElement("a");imageLink.className="video-thumb zt-review-thumb";imageLink.href=data.href;
     const image=document.createElement("img");image.src=data.img;image.alt=data.title;image.loading="lazy";image.decoding="async";imageLink.appendChild(image);
     const heading=document.createElement("h3"),anchor=document.createElement("a");anchor.href=data.href;anchor.textContent=data.title;heading.appendChild(anchor);
     if(data.href.startsWith("https://")){imageLink.target="_blank";imageLink.rel="noopener noreferrer";anchor.target="_blank";anchor.rel="noopener noreferrer";}
     c.append(imageLink,heading);
     if(data.kind){const small=document.createElement("small");small.textContent=data.kind;c.appendChild(small);}
     return c;
   }
   if(track){
     track.replaceChildren(
       reviewCard({href:"/recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html",title:"70mai Dash Cam 4K A900 | Recensione",img:"https://yt3.ggpht.com/_Dt3qOg45HgYDTfEAyPaMIcIFyrOaQLiH8WoY2GfoAvX7uaU1uc9OUTBBBqKuTgWNnWAGeV-aoFx4Ug=s1600-rw-nd-v1",kind:"Recensione scritta"}),
       reviewCard({href:"/recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html",title:"IIFACTOR M08E AI Smart Glasses | Recensione",img:"https://yt3.ggpht.com/g9pYihIxSd_5JUYmWF3t8PVGJAEsueYJmPZoCfl_hiYkrBhnn-37gOzbY-09frAt_xG23eBgmQLUMA=s1600-rw-nd-v1",kind:"Recensione scritta"}),
       reviewCard({href:"https://www.youtube.com/watch?v=6hLJq9njq5o",title:"realme Buds T500 Pro Harry Potter Edition | Recensione",img:"https://i.ytimg.com/vi/6hLJq9njq5o/hqdefault.jpg",kind:"Video recensione"})
     );
   }
   const h=review.querySelector(".module-head h2");if(h)h.textContent="RECENSIONI TECH";
   const label=review.querySelector(".module-head span");if(label)label.textContent="Tre recensioni Tech";

   // Attach the approved Extra section next to Guides, using real article URLs.
   const panel=document.createElement("div");panel.id="ztp-guide-extra";guide.parentNode.insertBefore(panel,guide);panel.appendChild(guide);
   const extra=document.createElement("section");extra.id="ztHomeExtra";extra.className="ztp-extra";
   const exHead=document.createElement("div");exHead.className="ztp-extra-head";
   const exTitle=document.createElement("h2");exTitle.textContent="EXTRA";
   const all=document.createElement("a");all.href="/extra.html";all.textContent="VEDI LE NEWS →";exHead.append(exTitle,all);
   const extraCards=document.createElement("div");extraCards.className="ztp-extra-cards";
   // Always read the newest two Extra articles from their canonical archive.
   // Do not freeze article names in the homepage script.
   const renderExtraCards=function(items){
     extraCards.replaceChildren();
     items.slice(0,2).forEach(function(item){
       if(!item.href || !item.title)return;
       const a=document.createElement("a");a.className="ztp-extra-card";a.href=item.href;
       const img=document.createElement("img");img.src=item.img||"/ChatGPT.png";img.alt=item.title;img.loading="lazy";img.decoding="async";
       const name=document.createElement("strong");name.textContent=item.title;
       a.append(img,name);extraCards.appendChild(a);
     });
   };
   const readExtraArchive=function(){
     return fetch("/extra.html",{cache:"no-store"}).then(function(response){
       if(!response.ok)throw Error("Extra archive HTTP "+response.status);
       return response.text();
     }).then(function(markup){
       const doc=new DOMParser().parseFromString(markup,"text/html");
       const rows=Array.from(doc.querySelectorAll("#extraList .news-row"));
       const seen=new Set();
       const items=rows.map(function(row){
         const link=row.querySelector(".news-copy h2 a") || row.querySelector("h2 a");
         const img=row.querySelector("img");
         if(!link)return null;
         const href=link.getAttribute("href");
         if(!href||seen.has(href))return null;
         seen.add(href);
         return {title:link.textContent.trim(),href:href,img:img?.getAttribute("src")||""};
       }).filter(Boolean);
       if(!items.length)throw Error("Empty Extra archive");
       return items;
     });
   };
   readExtraArchive().then(renderExtraCards).catch(function(error){
     console.warn("Extra homepage feed unavailable:",error);
     // The archive is still accessible through the section heading.
     const link=document.createElement("a");link.className="ztp-extra-card";
     link.href="/extra.html";link.textContent="Scopri le ultime news Extra →";
     extraCards.replaceChildren(link);
   });
   extra.append(exHead,extraCards);panel.appendChild(extra);

   // Move three real Gaming reviews to after the news grid, not at the very bottom.
   if(!document.getElementById("ztpGamingReviews")){
     const section=document.createElement("section");section.className="module ztp-gaming-reviews";section.id="ztpGamingReviews";
     const head=document.createElement("div");head.className="module-head";
     const title=document.createElement("h2");title.textContent="RECENSIONI GAMING";
     const more=document.createElement("a");more.href="/recensioni-scritte.html";more.className="ztp-review-all";more.textContent="VEDI TUTTE →";head.append(title,more);
     const cards=document.createElement("div");cards.className="ztp-gaming-review-cards";
     if(gamingCards.length===3){gamingCards.forEach(card=>cards.appendChild(card.cloneNode(true)));}
     else {
       [
         {title:"Poly Fighter | Recensione PC",href:"/poly-fighter-recensione-pc.html",img:"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/3977340/472302f24d5fcb52f0a111fd532d0ec1dd429810/capsule_616x353.jpg"},
         {title:"Sesame Street: Amici e risate | Recensione PS5",href:"/sesame-street-amici-e-risate-recensione-ps5.html",img:"/assets/recensioni/sesame-street/cover.webp"},
         {title:"Transport Fever 3 | Recensione PS5",href:"/recensione-Ugkxvpi4bKV_hiuDy7XJQb0-qw7CTJc5Is33.html",img:"https://yt3.ggpht.com/kI8EIbI2faK9m5NvmrggFQ_OdgW14-sL-iUXXwOFarZ_VX71Sne7FtDadwv0UmPwZ0eWOMhqxJg7eRQ=s1600-rw-nd-v1"}
       ].forEach(item=>cards.appendChild(reviewCard(item)));
     }
     section.append(head,cards);
     // Gaming reviews belong immediately after the Tech/Gaming news grid,
     // inside the primary feed, before Explore Videos and pagination.
     const videoAnchor=area.querySelector("#ztpVideosAnchor");
     const newsColumns=area.querySelector(".ztp-primary-feed .ztp-two-news-columns");
     const videoPair=videoAnchor?.closest(".ztp-video-shorts-pair");
     if(videoPair)videoPair.insertAdjacentElement("beforebegin",section);
     else if(videoAnchor)videoAnchor.insertAdjacentElement("beforebegin",section);
     else if(newsColumns)newsColumns.insertAdjacentElement("afterend",section);
     else area.querySelector(".ztp-primary-feed")?.appendChild(section);
   }
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",run,{once:true});else run();
})();

/* ZT_HOME_GAMING_THREE_EXTRA_20261014
   Keep the ten canonical Gaming articles. Add at most three linked, real archive
   articles to the empty space (the existing story plus two more). No placeholders. */
(function(){
 "use strict";
 if(!["/","/index.html"].includes(location.pathname))return;
 function init(){
  const root=document.querySelector("#articoli.ztp-news-area");
  const tech=root?.querySelector(".ztp-news-tech .ztp-news-items");
  const gaming=root?.querySelector(".ztp-news-gaming .ztp-news-items");
  if(!root||!tech||!gaming)return;
  const verified=[
   {href:"/news-Ugkxjafwnrw9O14Zgh1LkgQ-Qz61uHxbVzsr.html",title:"TEKKEN 8: Roger Jr. mostrato a EVO France, gameplay e data di uscita",img:"https://yt3.ggpht.com/CYkB_BV0hfpkrJptq3XgtBqqAcQiAJCTuOm9km7zzxQP9X9QCOT5VpqhVD5oVvZiOyRLHchgZ-Ow=s1600-rw-nd-v1"},
   {href:"/news-UgkxnLATplzUfYdizRa8iHxQEbXjxXQtWNTO.html",title:"Game Ground 2026 celebra i 40 anni di Castlevania con Michiru Yamane",img:"https://yt3.ggpht.com/snQpfRxzG3mI7g-r-wuX8OgCKR2pJp4La95d3wh6hmgf0PLRlKdlZKCBJUOzr-RjXM_4qevUl5rC-6w=s1600-rw-nd-v1"},
   {href:"/news-UgkxoPvqPweD4Q959Hlr2MgIasRETc4ISSua.html",title:"Street Fighter 6: Arjun arriva con Yoga Breathing e nuove trappole",img:"https://yt3.ggpht.com/nzdrx4GuLtp478BpnSld8kmWdQ_JuS_LLjsFEsqTprxa3dZ6UMYCNSNHyNaB8GosyfBNa2_sNds=s1600-rw-nd-v1"},
   {href:"/news-Ugkxi-JLntnVeff9hYO0L1UTscTuSEVSgl3a.html",title:"Sonic Racing: CrossWorlds, campione mondiale e novità dell'Anno 2",img:"https://yt3.ggpht.com/En_bo_SxmwM82TlOVYa1Wucu4jzNsDUgG0uO6GlsAG2G0MZCEA_WP3GSnprZv-ssibweCCKRVkNJCOg=s1600-rw-nd-v1"},
   {href:"/news-Ugkxa3g7XI5HXDvwAHFN4InsegWz1CbulplP.html",title:"Chivalware arriva su PC e Nintendo Switch 2: disponibile la demo",img:"https://yt3.ggpht.com/AhZN49_Z1SvI-SzvlzB_HkK-hq44BUgAFNjHbezXLrFUjobQsV79_IOBNijyDxCirlW0jzwDheNnHw=s1600-rw-nd-v1"}
  ];
  const pathOf=url=>{try{return new URL(url,location.origin).pathname;}catch(_){return "";}};
  let queued=false,lastSignature="";
  function render(){
   queued=false;
   const old=[...gaming.querySelectorAll(":scope > .ztp-gaming-bottom-fill")];
   if(window.innerWidth<1150){old.forEach(e=>e.hidden=true);return;}
   const techRows=[...tech.querySelectorAll(":scope > article.article-row:not([hidden])")];
   const gamingRows=[...gaming.querySelectorAll(":scope > article.article-row:not([hidden])")];
   if(techRows.length<10||gamingRows.length<10)return;
   const available=Math.max(0,techRows[techRows.length-1].getBoundingClientRect().bottom-
                           gamingRows[gamingRows.length-1].getBoundingClientRect().bottom);
   // Each compact row is approximately 120px; never create another white block.
   const needed=Math.min(3,Math.max(0,Math.floor((available+8)/112)));
   const used=new Set([...root.querySelectorAll(".ztp-news-item h3 a, .ztp-editorial-story:not([hidden])")].map(a=>pathOf(a.href)));
   const chosen=verified.filter(item=>!used.has(item.href)).slice(0,needed);
   const signature=chosen.map(i=>i.href).join("|");
   if(lastSignature===signature && old.length===chosen.length){
     old.forEach(e=>e.hidden=false);
     return;
   }
   lastSignature=signature;
   old.forEach(el=>el.remove());
   chosen.forEach((item,index)=>{
      const card=document.createElement("article");
      card.className="ztp-gaming-bottom-fill";
      card.dataset.extraGaming="yes";
      card.id="ztpGamingGapFiller"+(index+1);
      const thumb=document.createElement("a");thumb.href=item.href;thumb.className="ztp-gaming-bottom-thumb";
      const img=document.createElement("img");img.src=item.img;img.alt=item.title;img.loading="lazy";img.decoding="async";thumb.appendChild(img);
      const copy=document.createElement("div");copy.className="ztp-gaming-bottom-copy";
      const category=document.createElement("span");category.textContent="GAMING";
      const heading=document.createElement("a");heading.href=item.href;heading.textContent=item.title;
      copy.append(category,heading);card.append(thumb,copy);gaming.appendChild(card);
   });
  }
  function schedule(){if(!queued){queued=true;requestAnimationFrame(render);}}
  new MutationObserver(schedule).observe(tech,{childList:true});
  new MutationObserver(schedule).observe(gaming,{childList:true});
  window.addEventListener("resize",schedule,{passive:true});
  window.addEventListener("load",schedule,{once:true});
  schedule();
 }
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();

/* ZT_REVIEW_TECH_ARTWORK_16_9_20261014
   Make review covers readable as complete art in a wide frame with natural-color
   side extensions; landscape covers keep their original full-bleed shape. */
(function(){
  "use strict";
  if(!["/","/index.html"].includes(location.pathname))return;
  function init(){
    const track=document.querySelector(".ztp-top-main .latest-reviews-module #latestVideos");
    if(!track)return;
    function apply(){
      [...track.querySelectorAll(".zt-review-thumb > img")].forEach(function(img){
        const thumb=img.closest(".zt-review-thumb");
        if(!thumb)return;
        const url=img.currentSrc||img.src;
        if(url && thumb.dataset.ztReviewArtUrl!==url){
          // Use the same original cover for both layers, never invent a product image.
          thumb.style.setProperty("--zt-thumb-artwork","url("+JSON.stringify(url)+")");
          thumb.dataset.ztReviewArtUrl=url;
        }
        thumb.classList.add("zt-review-adapted");
        if(img.complete && img.naturalWidth>0 && img.naturalHeight>0){
          const ratio=img.naturalWidth/img.naturalHeight;
          thumb.classList.toggle("zt-cover-landscape",ratio>=1.64);
        }
        if(!img.dataset.ztRatioListener){
          img.dataset.ztRatioListener="yes";
          img.addEventListener("load",apply,{passive:true});
        }
      });
    }
    apply();
    const observer=new MutationObserver(function(records){
      if(records.some(rec=>rec.addedNodes.length || rec.removedNodes.length))apply();
    });
    observer.observe(track,{childList:true,subtree:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});else init();
})();
