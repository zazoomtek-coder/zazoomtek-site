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
 // Reuse the already approved text classifier ONLY for legacy general NEWS
 // in the Tech/Gaming column backfill; editorial labels always win.
 window.ztHomeTopicClassifier=categorizeHomeArticle;
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
  // Carousel owns these exact article URLs while they are featured.
  // The canonical feed and its original timestamps stay untouched.
  const featuredOnHome=new Set([...document.querySelectorAll("#ztFeaturedGrid > a[href]")].map(a=>{
    try{return new URL(a.getAttribute("href"),location.origin).pathname;}catch(_){return "";}
  }).filter(Boolean));
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
   // Only the importer's explicit editorial category may enter a regular column.
   // Unknown/Impact/Inside items remain in their dedicated editorial sections.
   const route=(category==="tech"||category==="gaming")?category:null;
   if(!route || /^news\s+(?:tech\s+impact|gaming\s+inside)\s*:/i.test(title)){
     row.hidden=true;
     continue;
   }
   const articleLink=row.querySelector(".article-copy h3 a[href]");
   let articlePath="";
   try{articlePath=new URL(articleLink?.getAttribute("href")||"",location.origin).pathname;}catch(_){}
   // Guide articles belong only in Guide shelves, not regular news columns.
   if(/^\/guida[-/]/i.test(articlePath) || /10 giochi PS5 a meno di 20 euro/i.test(title)){row.hidden=true;continue;}
   if(!articlePath || featuredOnHome.has(articlePath))continue;
   const isGaming=route==="gaming";
   row.classList.add("ztp-news-item");
   if(isGaming){
    const i=gamingCount++;
    if(i===0||i===3)row.classList.add("ztp-gaming-feature");
    else row.classList.remove("ztp-gaming-feature");
    row.querySelectorAll(".ztp-gaming-kind").forEach(label=>label.remove());
    gaming.appendChild(row);
   }else{techCount++;tech.appendChild(row);}
  }

  // Only non-featured articles appear in the columns. Once the independent
  // featured curator replaces an item, the next public build automatically
  // restores the old article to its category at its ORIGINAL publication time.
  // Keep its full canonical news entry and URL so no article gets deleted.
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
  const sidebarEditorials=[{"title":"Tales of Eternia Remastered è disponibile ora su PC e console","url":"/news-UgkxHKjqDM_6w4x_d1JfWv0MwO8uWY5mvxdT.html","image":"https://yt3.ggpht.com/NSskrfq9i9pljVhldYWumZrovdtp82LmvZfIW8rtDikqxnb4uoolWuacle8xv6glmVcqWcLjw0NEzg=s1600-rw-nd-v1"},{"title":"Galaxies Autumn Showcase 2026 presenta oltre 50 giochi tra Castlevania, THE FINALS, inZOI e Planet Zoo 2","url":"/news-UgkxmeHWU7RwhPehvkplGPHZSjz6XYDe4E4O.html","image":"https://yt3.ggpht.com/gSeRUTW_RIWbq87H9LzOZpXej9mDPHi_0HzFf_cKL5tS_4j4u3rx3hkp06GgNUrIq9_GZZrX_PAxVw=s1600-rw-nd-v1"},{"title":"PEAK arriva su console quest’autunno, edizione fisica PS5 il 9 dicembre con Buddy Code","url":"/news-Ugkx-OXj6pKP_zwDIxvYCYT3NmR331k4FNzI.html","image":"https://yt3.ggpht.com/ogtzPVCaC-4zyiiRaFxwo61JyFQIAmvUsHG06LOoOivOrrj7yfMtjaRsBdFvhPsaOOXw7f__iTfq=s1600-rw-nd-v1"},{"title":"Star Wars Zero Company, la Patch 1.2 introduce i Modificatori della campagna e nuove opzioni di difficoltà","url":"/news-UgkxfPFvMsM74hTZC1vCygxkY4P6ZVEVd3rz.html","image":"https://yt3.ggpht.com/STsF27-F5OGSpk1-DSrn_oRI6B0h9bqRxY-jzo0mUbH8w3LMeQ3lqM9ojtjMRa_Ep5klArdrcwUfCQ=s1600-rw-nd-v1"},{"title":"Acts of Blood arriva su PC il 4 dicembre, versioni PS5 e Xbox Series X|S nel 2027","url":"/news-UgkxanA_bg3ewHe8h6QlwNX-x68h4g3KFnJl.html","image":"https://yt3.ggpht.com/ecd6waU4I99z3DspUmPeHk0uRpu85SRaH2Y62whLuJ6ccAG4gk-al2PqPV6ZBPA8TNrEndVRLt0lYQ=s1600-rw-nd-v1"},{"title":"Wreckfest 2, l’aggiornamento 9 aggiunge Deathloop 2, nuove auto e modalità","url":"/news-UgkxnO7wMKAA5-asrOgA4z9nFwqxPBaShPTz.html","image":"https://yt3.ggpht.com/mj2HgBiZLuzl-NVQjYD67e4tY3EplPVGrj2gLMjOoRAQJJdZcIQoiMSx-zSyjFhMqpStFah17ENmdi4=s1600-rw-nd-v1"},{"title":"Forge of the Fae arriva a marzo 2027 con un JRPG ispirato all’Irlanda del XIX secolo","url":"/news-Ugkx5hB09T4oM2Oph87ieWwY9aaVQvh3ucFS.html","image":"https://yt3.ggpht.com/LrbgAzhcrSczu_JPGoEHWtIJLzMbtjISzsGlpGlvyZaojQDQssujy1_27J0Pl_hRbJowtr5ebCtAiHk=s1600-rw-nd-v1"},{"title":"It Takes Two arriva su Nintendo Switch 2 con upgrade gratuito e cross-play tramite Pass amici","url":"/news-UgkxmhTWoKHgoMFRBVCVwarDzbQ13biS-HcH.html","image":"https://yt3.ggpht.com/amVWYeD14sFZPuyG3TZHB1xA_9ST6teuh0AfUol8wjzXEJSvXG8hlLdh5Ms3LNsAz9LZiScmSken5Q=s1600-rw-nd-v1"},{"title":"GeForce NOW si aggiorna con NVIDIA DLSS 4.5 e 10 nuovi giochi in arrivo questa settimana","url":"/news-UgkxQY-hCQCCMw3WlbF-zCPiRlsc0UEmSE81.html","image":"https://yt3.ggpht.com/nFRoX0S_44wRJvGoK9RpxYmwb_IGmoJrpoG4chRdjUmchMrRrofxZbmsfmBM3wwQNoRpRkBxgL1kYAA=s1600-rw-nd-v1"},{"title":"WWE 2K26 incontra Street Fighter con un nuovo Elite Pack in arrivo il 28 ottobre","url":"/news-Ugkx9dHcFpP5d1qd5Qby_oVDcCx-FVADEW46.html","image":"https://yt3.ggpht.com/2WRvIMuOnbRtWY6x33k4bAQ6qfZDD8rbUJczrZF8Ta4yiQE0ChchUofLYysHvoKO3EUtwDTsA9Ix1Q=s1600-rw-nd-v1"},{"title":"Bluey’s Happy Snaps è disponibile ora su console e PC con esplorazione, fotografie e gioco creativo","url":"/news-UgkxPCOgryK5A4RSA43juUimmAUZVqL7vhSE.html","image":"https://yt3.ggpht.com/jPHEWNqf9UmyL_gsNDdRlpVxDBD4mIILZ4_3ajbI_xcAo8uuaIrgbeOaNFdLzeLXOotGguVC-tQJag=s1600-rw-nd-v1"},{"title":"VAULTBREAKERS apre l’alpha test pubblico con modalità PvPvE, cinque personaggi e due mappe","url":"/news-Ugkxh7FEm6Cn8P9uU9f6xvh_CJVfQqzEfahc.html","image":"https://yt3.ggpht.com/MF6iX-mRu2bmPVMKHQ1JToYE-zbWNhSs_C9PfoIM4CjIuuVPIa971zfy0FhdI15OFFUqcooous_3RGc=s1600-rw-nd-v1"}];
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
  // One article may appear in ONE visible Home news module only.
  // Priority: featured carousel, ten Tech/Gaming news per column, then
  // Tech Impact / Gaming Inside / Da non perdere / Dalla redazione.
  // Existing backup cards are promoted into the first two slots: do not
  // delete articles, alter SEO, insert filler or change the approved layout.
  let olderTechForPopular=[];
  function reconcileRight(){
    if(!document.documentElement.classList.contains("ztp-home-live-ready"))return;
    function articlePath(node){
      if(!node)return "";
      try{
        const u=new URL(node.getAttribute("href")||"",location.origin);
        return u.origin===location.origin?u.pathname:"";
      }catch(_){return "";}
    }
    const used=new Set();
    for(const link of document.querySelectorAll("#ztFeaturedGrid > a[href]")){
      const path=articlePath(link);if(path)used.add(path);
    }
    for(const link of area.querySelectorAll(".ztp-news-column .ztp-news-items > article .article-copy h3 a[href]")){
      const card=link.closest("article");
      if(card && !card.hidden && getComputedStyle(card).display!=="none"){
        const path=articlePath(link);if(path)used.add(path);
      }
    }
    function fillModule(root,selector,max,linkSelector){
      if(!root)return;
      const cards=[...root.querySelectorAll(selector)];
      if(!cards.length)return;
      // Keep the original newest-first ranking, even after previous repairs.
      cards.forEach((card,i)=>{
        if(card.dataset.ztUniqueOriginalOrder===undefined)
          card.dataset.ztUniqueOriginalOrder=String(i);
      });
      cards.sort((a,b)=>Number(a.dataset.ztUniqueOriginalOrder)-Number(b.dataset.ztUniqueOriginalOrder));
      const chosen=[],rest=[];
      for(const card of cards){
        const path=articlePath(card.matches("a[href]")?card:card.querySelector(linkSelector));
        if(path && !used.has(path) && chosen.length<max){
          used.add(path);chosen.push(card);
        }else rest.push(card);
      }
      const parent=cards[0].parentElement;
      // Existing CSS shows the first two items; move unique backups into
      // those positions so no empty space is created by hidden duplicates.
      for(const card of chosen.concat(rest))parent.appendChild(card);
      for(const card of chosen)card.style.removeProperty("display");
      for(const card of rest)card.style.setProperty("display","none","important");
      root.style.display=chosen.length?"":"none";
    }
    fillModule(impact,".zt-special-item",2,"a.zt-special-thumb[href]");
    fillModule(inside,".zt-special-item",2,"a.zt-special-thumb[href]");
    // Older, verified Tech articles backfill DA NON PERDERE AFTER the
    // browser has finalized the ten newest Tech and Gaming columns.
    // The daily snapshot alone can overlap those asynchronous columns.
    if(pop && olderTechForPopular.length){
      const holder=pop.querySelector(".zt-popular-list");
      if(holder){
        const existing=new Set([...holder.querySelectorAll(".zt-popular-article")].map(articlePath).filter(Boolean));
        for(const item of olderTechForPopular){
          if(!item || !/^\/news-[A-Za-z0-9_-]+\.html$/.test(item.url) ||
             !item.title || !item.image || used.has(item.url) || existing.has(item.url))continue;
          const card=document.createElement("a");
          card.className="zt-popular-article";card.href=item.url;card.title=item.title;
          const image=document.createElement("img");image.src=item.image;image.alt=item.title;image.loading="lazy";
          const copy=document.createElement("span");copy.className="zt-popular-copy";
          const category=document.createElement("span");category.className="zt-popular-category";category.textContent="TECNOLOGIA";
          const title=document.createElement("strong");title.textContent=item.title;
          copy.append(category,title);card.append(image,copy);holder.appendChild(card);
          existing.add(item.url);
          if(existing.size>=16)break;
        }
      }
    }
    fillModule(pop,".zt-popular-article",2,"");
    const chosen=[];
    for(const card of editorialCards){
      const path=articlePath(card);
      if(path && !used.has(path) && chosen.length<3){chosen.push(card);used.add(path);}
    }
    const selected=new Set(chosen);
    editorialCards.forEach(card=>{card.hidden=!selected.has(card);});
    editorialBox.style.display=selected.size?"block":"none";
  }
  window.addEventListener("zt:home-columns-repainted",event=>{
    olderTechForPopular=Array.isArray(event.detail?.techBackups)?event.detail.techBackups:[];
    requestAnimationFrame(reconcileRight);
  });

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
    function explicitArchiveCategory(from) {
      const route=(from.dataset.postCategory||"").toLowerCase();
      const heading=(from.querySelector(".news-copy h2 a")?.textContent||"").trim();
      const url=from.querySelector(".news-copy h2 a")?.getAttribute("href")||"";
      const signature=String(from.getAttribute("data-news-search")||"").slice(0,600);
      if(/\/(?:tech-impact|gaming-inside)-/.test(url)
         || /^news\s+(?:tech\s+impact|gaming\s+inside|extra)\s*:/i.test(heading)
         || /\bnews\s+(?:tech\s+impact|gaming\s+inside|extra)\s*:/i.test(signature)
         || route==="extra")return null;
      if(route==="tech"||route==="gaming")return route;
      const label=signature.match(/\bnews\s+(tech|gaming)\s*:/i);
      if(label)return label[1].toLowerCase();
      // Only explicitly categorized Tech/Gaming posts can appear here.
      // Guides, celebratory posts and other categories stay in their own sections.
      return null;
    }
    function makeArticle(from) {
      var link=from.querySelector(".news-copy h2 a");
      var img=from.querySelector("img");
      if (!link||!img) return null;
      var title=String(link.textContent||"").trim();
      if(!explicitArchiveCategory(from)||/^news\s+extra\s*:/i.test(title)||from.getAttribute("data-post-category")==="extra")return null;
      var url=link.getAttribute("href");
      if (!url||!/^\/(news-|tech-impact-|gaming-inside-)[\w-]+\.html$/.test(url)||seen.has(url)
          )return null;
      seen.add(url);
      var article=document.createElement("article");
      article.className="article-row ztp-news-item zt-mag-archive";
      // Original ISO timestamp comes directly from the editorial archive.
      // Never use the re-entry time or the day-only label for ordering.
      article.dataset.publishedAt=from.getAttribute("data-published-at")||"";
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

    // Revision 17 ottobre: ridimensionare la seconda card Tech in evidenza.
    // Gaming può usare un undicesimo articolo *reale* solo quando chiude
    // sensibilmente prima di Tech. Non riempire con contenuto inventato.
    var queuedAlignment=false;
    function featuredPaths(){
      return new Set([].slice.call(document.querySelectorAll("#ztFeaturedGrid a[href]"))
        .map(function(a){try{return new URL(a.getAttribute("href"),location.origin).pathname;}catch(_){return "";}}));
    }
    function shownRows(column){
      return [].slice.call(column.querySelectorAll(":scope > article.article-row")).filter(function(row){
        return !row.hidden && getComputedStyle(row).display!=="none";
      });
    }
    function renderedHeight(column){
      var shown=shownRows(column);
      return shown.length
        ? shown[shown.length-1].getBoundingClientRect().bottom-column.getBoundingClientRect().top
        : 0;
    }
    function alignBottoms(){
      // The columns show EXACTLY the ten newest non-featured real stories
      // each. Never insert an 11th/12th "filler" article for visual balance.
      // Preserve the existing 16:9 cards and spread only small height
      // differences through the existing card padding on wide desktop.
      const left=shownRows(tech),right=shownRows(gaming);
      for(const row of left.concat(right))row.style.removeProperty("padding-bottom");
      if(!archivesReady||!window.matchMedia("(min-width:821px)").matches)return;
      if(left.length!==10||right.length!==10)return;
      const difference=renderedHeight(tech)-renderedHeight(gaming);
      if(!Number.isFinite(difference)||Math.abs(difference)<2)return;
      // Too-large differences must never distort thumbnails or typography.
      if(Math.abs(difference)>320)return;
      const shorter=difference>0?right:left;
      const extra=Math.abs(difference)/shorter.length;
      for(const row of shorter){
        const current=parseFloat(getComputedStyle(row).paddingBottom)||12;
        row.style.setProperty("padding-bottom",(current+extra).toFixed(2)+"px","important");
      }
    }
    function requestAlignment(){
      if(queuedAlignment)return;
      queuedAlignment=true;
      requestAnimationFrame(function(){queuedAlignment=false;alignBottoms();});
    }
    function sourcePublishedAt(row){
      const raw=row.getAttribute("data-published-at")||"";
      const timestamp=Date.parse(raw);
      if(raw && Number.isFinite(timestamp))return timestamp;
      const label=(row.querySelector(".article-meta")?.textContent||"").toLowerCase();
      const months={gennaio:0,febbraio:1,marzo:2,aprile:3,maggio:4,
        giugno:5,luglio:6,agosto:7,settembre:8,ottobre:9,novembre:10,dicembre:11};
      const date=label.match(/(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(20\d{2})/);
      return date?Date.UTC(+date[3],months[date[2]],+date[1]):-Infinity;
    }
    function rebalance(){
      [[tech,3],[gaming,4]].forEach(function(pair){
        var col=pair[0],maxBig=pair[1];
        var all=[].slice.call(col.querySelectorAll(":scope > article.article-row"));
        // The archive and canonical feed share the ORIGINAL publication time.
        // Re-sort after each archive page, before truncating, so a story that
        // leaves the carousel returns between the correct older/newer stories.
        all=all.map(function(row,index){return {row,index,time:sourcePublishedAt(row)};})
          .sort(function(a,b){return b.time-a.time||a.index-b.index;})
          .map(function(entry){return entry.row;});
        all.forEach(function(row){col.appendChild(row);});
        // Preserve exactly ten column cards; older entries stay in archives.
        all.slice(10).forEach(function(row){row.remove();});
        all=all.slice(0,10);
        var topTen=all;
        all.forEach(function(row){
          row.hidden=true;
          row.classList.remove("zt-mag-big","ztp-gaming-feature");
        });
        topTen.forEach(function(row){
          row.hidden=false;
          row.style.removeProperty("display");
        });
        var indexes=(maxBig===3?[0,4,8]:[0,3,6,9]).filter(function(i){return i<topTen.length;});
        indexes.slice(0,maxBig).forEach(function(i){topTen[i].classList.add("zt-mag-big");});
        if(col===tech){
          // The second large Tech image (e.g. Midea in the screenshot)
          // becomes a compact horizontal article, preserving the full image.
          var large=topTen.filter(function(row){return row.classList.contains("zt-mag-big");});
          var specific=large.find(function(row){
            return /midea.*powerinfi|powerinfi.*midea/i.test(row.querySelector(".article-copy h3")?.textContent||"");
          });
          var compact=specific || large[1];
          if(compact)compact.classList.remove("zt-mag-big");
        }
        var count=col.closest(".ztp-news-column").querySelector(".ztp-news-head small");
        if(count)count.textContent=topTen.length+" news";
      });
      requestAlignment();
    }
    // Respond to actual image loading and window resizing, not artificial spacers.
    area.addEventListener("load",function(e){if(e.target && e.target.tagName==="IMG")requestAlignment();},true);
    window.addEventListener("resize",function(){rebalance();},{passive:true});
    rebalance();
    // Load every existing published source BEFORE selecting the newest ten
    // TECH and GAMING articles. Stopping at ten while browsing individual
    // archive pages used to omit newer items and create unsynchronised columns.
    // The canonical 15-news feed, page structure and original timestamps stay.
    const candidates={tech:[...tech.querySelectorAll(":scope > article.article-row")],
                      gaming:[...gaming.querySelectorAll(":scope > article.article-row")]};
    let archivesReady=false;
    function archiveHref(row){
      const anchor=row.querySelector(".article-copy h3 a[href]");
      try{return new URL(anchor?.getAttribute("href")||"",location.origin).pathname;}
      catch(_){return "";}
    }
    function paintCurrentColumns(){
      if(!archivesReady)return;
      const featured=featuredPaths();
      for(const [name,column] of [["tech",tech],["gaming",gaming]]){
        const ranked=candidates[name].filter(row=>{
          const url=archiveHref(row);
          return url && !featured.has(url) && !row.matches("[data-post-category='extra']");
        }).map((row,index)=>({row,index,time:sourcePublishedAt(row)}));
        ranked.sort((a,b)=>b.time-a.time||a.index-b.index);
        // Keep references to older published articles in candidates, not DOM.
        // They can return to their original publication position when the
        // featured carousel rotates without needing to republish an article.
        column.replaceChildren(...ranked.slice(0,10).map(item=>item.row));
      }
      rebalance();
      // Sidebar cards must be rechecked whenever archived news or featured
      // carousel changes. Only visible, real article links count as duplicates.
      const visibleTech=new Set([...tech.querySelectorAll(".article-copy h3 a[href]")].map(a=>{
        try{return new URL(a.getAttribute("href"),location.origin).pathname;}catch(_){return "";}
      }));
      const techBackups=candidates.tech
        .filter(row=>{
          const url=archiveHref(row);
          return url && !featured.has(url) && !visibleTech.has(url);
        })
        .sort((a,b)=>sourcePublishedAt(b)-sourcePublishedAt(a))
        .slice(0,22).map(row=>({
          url:archiveHref(row),
          title:(row.querySelector(".article-copy h3 a")?.textContent||"").trim(),
          image:row.querySelector("img.article-image")?.getAttribute("src")||""
        }));
      window.dispatchEvent(new CustomEvent("zt:home-columns-repainted",{detail:{techBackups}}));
    }
    function addPublishedNews(src){
      const route=explicitArchiveCategory(src);
      if(route!=="tech"&&route!=="gaming")return;
      const row=makeArticle(src);
      if(row)candidates[route].push(row);
    }
    function addChronologicalHome(src){
      const category=(src.getAttribute("data-post-category")||"").toLowerCase();
      if(category!=="tech"&&category!=="gaming")return;
      const link=src.querySelector(".article-copy h3 a[href]");
      const photo=src.querySelector("img.article-image");
      if(!link||!photo)return;
      let url;
      try{url=new URL(link.getAttribute("href"),location.origin);}catch(_){return;}
      if(url.origin!==location.origin||!/^\/news-[\w-]+\.html$/.test(url.pathname)||
         seen.has(url.pathname))return;
      const row=src.cloneNode(true);
      row.classList.add("ztp-news-item","zt-mag-archive");
      row.classList.remove("zt-mag-big","ztp-gaming-feature");
      row.hidden=false;
      row.style.removeProperty("display");
      candidates[category].push(row);
      seen.add(url.pathname);
    }
    const sources=[
      ["/news.html","news"],["/news-2.html","news"],["/news-3.html","news"],
      ["/news-4.html","news"],["/news-5.html","news"],
      ["/pagina-2.html","home"],["/pagina-3.html","home"],
      ["/pagina-4.html","home"],["/pagina-5.html","home"]
    ];
    Promise.all(sources.map(async ([path,kind])=>{
      try{
        const response=await fetch(path,{cache:"no-store",credentials:"same-origin"});
        if(!response.ok)throw new Error("HTTP "+response.status);
        const documentSource=new DOMParser().parseFromString(await response.text(),"text/html");
        const selector=kind==="news"?".news-list article.news-row":"#articleList > article.article-row";
        documentSource.querySelectorAll(selector).forEach(source=>
          kind==="news"?addPublishedNews(source):addChronologicalHome(source));
      }catch(error){
        console.info("Home archive read skipped:",path,error.message);
      }
    })).then(()=>{
      archivesReady=true;
      paintCurrentColumns();
      const grid=document.getElementById("ztFeaturedGrid");
      if(grid && typeof MutationObserver==="function")
        new MutationObserver(paintCurrentColumns).observe(grid,{
          childList:true,subtree:true,attributes:true,attributeFilter:["href"]
        });
      requestAlignment();
    }).catch(error=>{
      console.warn("Preserved the existing Tech/Gaming columns:",error);
      archivesReady=true;
      paintCurrentColumns();
    });
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
       reviewCard({href:"/thermomate-2500w-recensione-riscaldatore-infrarossi-2-in-1.html",title:"ThermoMate 2500W | Recensione riscaldatore a infrarossi",img:"/assets/recensioni/thermomate-2500w/cover.webp",kind:"17 ottobre 2026"}),
       reviewCard({href:"/recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html",title:"70mai Dash Cam 4K A900 | Recensione",img:"https://yt3.ggpht.com/_Dt3qOg45HgYDTfEAyPaMIcIFyrOaQLiH8WoY2GfoAvX7uaU1uc9OUTBBBqKuTgWNnWAGeV-aoFx4Ug=s1600-rw-nd-v1",kind:"Recensione scritta"}),
       reviewCard({href:"/recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html",title:"IIFACTOR M08E AI Smart Glasses | Recensione",img:"https://yt3.ggpht.com/g9pYihIxSd_5JUYmWF3t8PVGJAEsueYJmPZoCfl_hiYkrBhnn-37gOzbY-09frAt_xG23eBgmQLUMA=s1600-rw-nd-v1",kind:"Recensione scritta"})
     );
   }
   // Auto-refresh the TECH shelf from the official dated review archive.
   // Static cards above remain a safe fallback if the archive is unreachable.
   if(track)fetch("/recensioni-scritte.html",{cache:"no-store"}).then(function(r){
     if(!r.ok)throw new Error("archive HTTP "+r.status);
     return r.text();
   }).then(function(markup){
     const doc=new DOMParser().parseFromString(markup,"text/html");
     const months={gennaio:1,febbraio:2,marzo:3,aprile:4,maggio:5,giugno:6,
       luglio:7,agosto:8,settembre:9,ottobre:10,novembre:11,dicembre:12};
     const entries=[...doc.querySelectorAll("#reviewList .news-row")].map(function(row){
       const link=row.querySelector(".news-copy h2 a"), image=row.querySelector("img");
       if(!link||!image)return null;
       const href=link.getAttribute("href")||"";
       if(!href.startsWith("/")||!href.endsWith(".html"))return null;
       const title=link.textContent.trim();
       const techTag=(row.getAttribute("data-review-category")||"").toLowerCase();
       if(techTag!=="tech" && !/thermomate|70mai.*dash|iifactor.*smart|smartphone|smart glasses|mini pc|router|riscaldatore|aspirapolvere/i.test(title))return null;
       const meta=row.querySelector(".news-meta")?.textContent||"";
       const m=meta.toLowerCase().match(/(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})/);
       if(!m)return null;
       return {href,title,img:image.getAttribute("src"),kind:m[1]+" "+m[2]+" "+m[3],
         order:Number(m[3])*10000+months[m[2]]*100+Number(m[1])};
     }).filter(Boolean).sort(function(a,b){return b.order-a.order;});
     // Never downgrade the shelf when the feed is incomplete.
     if(entries.length<3 || !entries.some(e=>e.href.includes("thermomate-2500w")))return;
     const unique=[...new Map(entries.map(e=>[e.href,e])).values()];
     track.replaceChildren(...unique.slice(0,3).map(reviewCard));
   }).catch(function(e){console.info("Tech reviews fallback retained",e.message);});
   const h=review.querySelector(".module-head h2");if(h)h.textContent="RECENSIONI TECH";
   const label=review.querySelector(".module-head span");if(label)label.textContent="Tre recensioni Tech";
   const techHead=review.querySelector(".module-head");
   if(techHead&&!techHead.querySelector(".ztp-review-all")){
     const seeAll=document.createElement("a");seeAll.className="ztp-review-all ztp-tech-review-all";
     seeAll.href="/recensioni-tech.html";seeAll.textContent="VEDI TUTTE →";techHead.appendChild(seeAll);
   }

   // Attach the approved Extra section next to Guides, using real article URLs.
   const panel=document.createElement("div");panel.id="ztp-guide-extra";guide.parentNode.insertBefore(panel,guide);panel.appendChild(guide);
   const extra=document.createElement("section");extra.id="ztHomeExtra";extra.className="ztp-extra";
   const exHead=document.createElement("div");exHead.className="ztp-extra-head";
   const exTitle=document.createElement("h2");exTitle.textContent="EXTRA";
   const all=document.createElement("a");all.href="/extra.html";all.textContent="VEDI TUTTO →";exHead.append(exTitle,all);
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
   const verifiedExtraCards=async function(items){
     const working=[];
     // Avoid broken links during Firebase propagation: only show a verified 200.
     for(const item of items.slice(0,12)){
       if(working.length===2)break;
       try{
         const target=new URL(item.href,window.location.origin);
         if(target.origin!==window.location.origin)continue;
         const response=await fetch(target.pathname,{method:"HEAD",cache:"no-store"});
         if(response.ok)working.push(item);
       }catch(error){
         console.warn("Skipping unreachable Extra article:",item.href,error);
       }
     }
     if(!working.length)throw Error("No published Extra articles return HTTP 200");
     renderExtraCards(working);
   };
   readExtraArchive().then(verifiedExtraCards).catch(function(error){
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

/* Hardcoded outdated Gaming gap fillers replaced by dated archive candidates.
   Editorial content can move; approved Home layout remains unchanged. */

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
