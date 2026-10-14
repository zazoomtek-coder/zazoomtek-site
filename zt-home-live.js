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
   const lead=row.querySelector(".article-copy p")?.textContent||"";
   const image=row.querySelector("img.article-image");
   const isGaming=categorizeHomeArticle(title,lead,image?.alt||"",image?.getAttribute("src")||"")==="gaming";
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
  layout.classList.add("ztp-three-home");
  const top=document.createElement("div");top.className="ztp-top";
  const topMain=document.createElement("div");topMain.className="ztp-top-main";
  const video=document.createElement("section");
  video.className="ztp-review-videos ztp-top-videos";
  video.setAttribute("aria-label","Ultime video recensioni ZazoomTek");
  video.innerHTML='<h2>ULTIME VIDEO RECENSIONI</h2><div class="ztp-review-list" id="ztpReviewVideoList"></div><div class="ztp-review-footer"><a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener noreferrer">TUTTE LE VIDEO RECENSIONI →</a></div>';
  topMain.append(latest,guide);top.append(topMain,video);main.insertBefore(top,area);
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
  const root=document.querySelector("main.page");
  function mountShelves(){
   const shelves=document.getElementById("zt-home-shelves");
   if(!shelves||!videoShelfTarget)return false;
   if(shelves.parentElement!==videoShelfTarget)videoShelfTarget.appendChild(shelves);
   const sync=()=>{
     const full=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&!el.querySelector(".zt-shelf-shorts"));
     if(full){const h=full.querySelector(".zt-shelf-head h2");if(h&&h.textContent!=="ESPLORA ULTIMI VIDEO")h.textContent="ESPLORA ULTIMI VIDEO";}
     const shorts=[...shelves.children].find(el=>el.classList.contains("zt-shelf")&&el.querySelector(".zt-shelf-shorts"));
     if(!shorts)return;
     shorts.classList.add("ztp-rail-shorts");
     const heading=shorts.querySelector(".zt-shelf-head h2");
     if(heading)heading.textContent="ULTIMI SHORTS";
     const prev=rail.querySelector(".ztp-rail-shorts");
     if(prev&&prev!==shorts)prev.replaceWith(shorts);
     else if(!prev){if(inside)inside.insertAdjacentElement("afterend",shorts);else rail.appendChild(shorts);}
     if(inside&&shorts.previousElementSibling!==inside)inside.insertAdjacentElement("afterend",shorts);
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
  function balance(){
   const techItems=area.querySelector(".ztp-news-tech .ztp-news-items");
   const gamingItems=area.querySelector(".ztp-news-gaming .ztp-news-items");
   if(!techItems||!gamingItems)return;
   const cols=[techItems,gamingItems];
   for(const col of cols){
    col.style.removeProperty("min-height");
    col.style.removeProperty("display");
    col.style.removeProperty("flex-direction");
    col.style.removeProperty("justify-content");
   }
   if(window.innerWidth<=820)return;
   const heights=cols.map(col=>col.getBoundingClientRect().height);
   const maxHeight=Math.max(...heights);
   for(let n=0;n<cols.length;n++){
    if(maxHeight-heights[n]<5)continue;
    const col=cols[n];
    col.style.display="flex";
    col.style.flexDirection="column";
    col.style.justifyContent="space-between";
    col.style.minHeight=Math.ceil(maxHeight)+"px";
   }
  }

  // Fill remaining vertical space with published articles, never blank padding.
  // Entries come from real, distinct archived news URLs on ZazoomTek.
  const sidebarEditorials=[{"title":"News: Totem arriva nei negozi Città del Sole, 160 giochi senza schermo né connessione","url":"/news-UgkxBGaXbwgP0ASm6MzyOwrF9mLqjBPwqdrv.html","image":"https://yt3.ggpht.com/wTV9oR-jX2J2Cgq0a0FVOjGscLX8NsUG5faWPP38JP9YxnPvsGul_5ySB0DWXv73RA4JwKCmVbAOqA=s1600-rw-nd-v1"},{"title":"News: realme passa a ColorOS 17 basato su Android 17, rollout da ottobre sui primi smartphone","url":"/news-UgkxJtnjr69lRe_UU0p4peoueh64NfWSi1zF.html","image":"https://yt3.ggpht.com/3c5f_5ssRd3cdl2SMa68ugboaW64GvTrsQC6LrVMBOLeiiX1E5IEBCnCJ63D60BtnDYJQYPBwjvEJQ=s1600-rw-nd-v1"},{"title":"GRAZIE A TUTTI VOI! ZAZOOMTEK CRESCE ANCORA!","url":"/news-Ugkx8FpJmRlS3S7_ZcqmirDiYmcCbg7dSjyt.html","image":"https://yt3.ggpht.com/hKSuXxh43cNqAOVKoPTMc4BBdc8gY_ZV2ZjNRU4BQ0yv88djq-XmETg_ka6uBZk_JFWtWUETNpklhQ=s1600-rw-nd-v1"},{"title":"News: EA SPORTS FC 27, tornano le Stelle del Futuro con Rio Ngumoha protagonista del Team 1","url":"/news-UgkxSZwRsjwa-UE_dTpIcqSMfUbFwtkh3Jn5.html","image":"https://yt3.ggpht.com/pY0m2L6tOuYQRHdka4YMSiuhPg84FdSbOUUrhlcXCkNe3xOwjfshTHz0QE0M6OIZVTIaEwAbe-9p=s1600-rw-nd-v1"},{"title":"News: Call of Duty Modern Warfare 4, DMZ Deep Dive Parte 2 svela FOB, crafting, armi e accesso anticipato","url":"/news-UgkxFcKuOM5B9s3C-I_wnL7Y-0E4nj3h7bXb.html","image":"https://yt3.ggpht.com/q14FYSA6R5xDB4mMIZDhHGXz272eXMpB9lwIbLE5wvuK6C87KEULSTTIpf1Sxv75SUmbzuMDTSCK=s1600-rw-nd-v1"},{"title":"News: Crazy Taxi: World Tour corre in Brasile, SEGA svela la quarta mappa della campagna","url":"/news-UgkxHwO-OKR3z-qEkJL0MBsZS_tMU0R5Q0fi.html","image":"https://yt3.ggpht.com/PdcP0LGfc9LCO05zLQnPdX_jLsp3pxHl_vMGM7x_MsuJgjNeJ_knp1FEP1fvcldjqT7DFnFb09J3dg=s1600-rw-nd-v1"}];
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
  function reconcileRight(){
    if(!document.documentElement.classList.contains("ztp-home-live-ready"))return;
    editorialCards.forEach(card=>card.hidden=true);
    editorialBox.style.display="none";
    if(window.innerWidth<=1380)return;
    const primary=area.querySelector(".ztp-primary-feed");
    if(!primary)return;
    if(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom<90)return;
    const alreadyLinked=new Set([...area.querySelectorAll(".ztp-news-item h3 a")].map(a=>a.getAttribute("href")));
    editorialBox.style.display="block";
    for(const card of editorialCards){
      if(alreadyLinked.has(card.getAttribute("href")))continue;
      const before=Math.abs(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom);
      card.hidden=false;
      const after=Math.abs(primary.getBoundingClientRect().bottom-rail.getBoundingClientRect().bottom);
      if(after>=before){card.hidden=true;break;}
    }
    if(!editorialCards.some(card=>!card.hidden))editorialBox.style.display="none";
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
