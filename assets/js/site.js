"use strict";
(()=>{
 const menu=document.querySelector("#mobile-menu"),nav=document.querySelector("#nav");
 if(menu&&nav)menu.addEventListener("click",()=>{
  const expanded=!nav.classList.contains("open");
  nav.classList.toggle("open",expanded);
  menu.setAttribute("aria-expanded",String(expanded));
 });
 for(const a of document.querySelectorAll("#nav a"))if(new URL(a.href).pathname===location.pathname)a.setAttribute("aria-current","page");

 const choiceKey="zazoomtek_analytics_consent_v1";
 const measurementId="G-01F6Q4BGTC";
 let currentChoice=null,analyticsLoaded=false;
 try{currentChoice=localStorage.getItem(choiceKey);}catch(_){}
 const panel=document.querySelector("#cookie-panel"),toggle=document.querySelector("#cookie-preferences");
 function showPanel(open){
  if(!panel||!toggle)return;
  panel.hidden=!open;
  toggle.setAttribute("aria-expanded",String(open));
 }
 toggle?.addEventListener("click",()=>showPanel(panel.hidden));
 const loadAnalytics=()=>{
  if(analyticsLoaded)return;
  analyticsLoaded=true;
  window.dataLayer=window.dataLayer||[];
  window.gtag=function(){window.dataLayer.push(arguments);};
  window.gtag("consent","default",{
   analytics_storage:"granted",ad_storage:"denied",ad_user_data:"denied",ad_personalization:"denied"
  });
  window.gtag("js",new Date());
  window.gtag("config",measurementId,{
   allow_google_signals:false,allow_ad_personalization_signals:false,send_page_view:true
  });
  const script=document.createElement("script");
  script.async=true;
  script.src="https://www.googletagmanager.com/gtag/js?id="+encodeURIComponent(measurementId);
  document.head.appendChild(script);
 };
 function choose(accepted){
  const earlier=currentChoice;
  currentChoice=accepted?"accepted":"rejected";
  try{localStorage.setItem(choiceKey,currentChoice);}catch(_){}
  showPanel(false);
  if(accepted)loadAnalytics();
  else if(earlier==="accepted"){
   window.gtag?.("consent","update",{analytics_storage:"denied",ad_storage:"denied",
     ad_user_data:"denied",ad_personalization:"denied"});
   location.reload(); // Remove previously loaded Analytics from this document after withdrawal.
  }
 }
 document.querySelector("#cookie-accept")?.addEventListener("click",()=>choose(true));
 document.querySelector("#cookie-reject")?.addEventListener("click",()=>choose(false));
 if(currentChoice==="accepted")loadAnalytics();
 else if(currentChoice!=="rejected")showPanel(true);

 // Enhanced-privacy YouTube iframe is created only after explicit user interaction.
 document.addEventListener("click",event=>{
  const btn=event.target.closest?.("button.video-start");
  if(!btn)return;
  const id=btn.dataset.youtubeId||"";
  if(!/^[A-Za-z0-9_-]{11}$/.test(id))return;
  const iframe=document.createElement("iframe");
  iframe.title="Video YouTube";
  iframe.loading="eager";
  iframe.allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share";
  iframe.referrerPolicy="strict-origin-when-cross-origin";
  iframe.allowFullscreen=true;
  iframe.src="https://www.youtube-nocookie.com/embed/"+id+"?autoplay=1";
  btn.replaceWith(iframe);
 });

 // v44: measured editorial rail. Use the TRUE bottom of the central column:
 // no cropped thumbnail, no overflowing box and no empty sidebar on long pages.
 function sizeEditorialRail(aside){
  const stack=aside.querySelector(".sidebar-stack");
  if(!stack)return;
  const home=aside.classList.contains("home-sidebar");
  const compact=window.matchMedia("(max-width:780px)").matches;
  const column=home?aside.closest(".home-layout")?.querySelector(".home-column"):
                    aside.closest(".inner-layout")?.querySelector(".inner-column");
  if(!column)return;
  aside.classList.remove("rail-ready");
  aside.style.removeProperty("--inner-rail-height");
  stack.style.removeProperty("min-height");
  stack.style.removeProperty("height");
  stack.style.removeProperty("justify-content");
  const panels=[...stack.querySelectorAll(":scope > .editorial-box")];
  const rows=panels.map(box=>[...box.querySelectorAll(".editorial-row")]);
  // The Amazon Associates panel has no .editorial-row children. The normal
  // fitting algorithm previously hid it permanently as an empty editorial box.
  // On the Home it is a mandatory, intact second panel: reserve its FULL
  // height before selecting the number of ordinary editorial thumbnails.
  const amazon=home?panels.find(box=>box.classList.contains("amazon-feature-box")):null;
  panels.forEach(panel=>{panel.hidden=true;});
  rows.forEach(group=>group.forEach(row=>{row.hidden=true;}));
  if(amazon)amazon.hidden=false;
  if(compact){
   panels.forEach((panel,i)=>{
    panel.hidden=false;
    rows[i].slice(0,4).forEach(row=>{row.hidden=false;});
   });
   aside.classList.add("rail-ready");
   return;
  }
  // Two equal-height editorial halves ONLY for long article/review pages.
  // Show complete rows within each half; never crop a thumbnail or exceed
  // the article column. The Amazon affiliate box is in the NEXT grid row
  // beside related articles and is intentionally independent of this rail.
  if(aside.dataset.railMode==="split"){
   const mainRect=column.getBoundingClientRect();
   const top=stack.getBoundingClientRect().top;
   const usable=Math.max(0,Math.floor(mainRect.bottom-top-6));
   aside.style.setProperty("--inner-rail-height",Math.floor(mainRect.height)+"px");
   aside.style.setProperty("--split-stack-height",usable+"px");
   aside.classList.add("rail-ready");
   for(const panel of panels)panel.hidden=false;
   for(let i=0;i<panels.length;i++){
    const boundary=Math.min(panels[i].getBoundingClientRect().bottom-9,mainRect.bottom-6);
    let count=0;
    for(const row of rows[i]){
     row.hidden=false;
     if(row.getBoundingClientRect().bottom<=boundary+1)count++;
     else {row.hidden=true;break;}
    }
    if(!count)panels[i].hidden=true;
   }
   return;
  }
  // The page boundary is measured in actual rendered pixels, not a parent's
  // scrollHeight (which can include min-height/flex gaps and hide overflow).
  const mainRect=column.getBoundingClientRect();
  const boundary=mainRect.bottom-6;
  const stackTop=stack.getBoundingClientRect().top;
  const usable=Math.max(0,Math.floor(boundary-stackTop));
  aside.style.setProperty("--inner-rail-height",Math.max(0,Math.floor(mainRect.height))+"px");
  const lastVisible=()=>[...stack.children].filter(el=>!el.hidden).at(-1);
  const bottom=()=>{
   const last=lastVisible();
   return last?last.getBoundingClientRect().bottom:stackTop;
  };
  const fits=()=>bottom()<=boundary;
  const tryFirst=i=>{
   if(!rows[i].length)return false;
   panels[i].hidden=false;
   rows[i][0].hidden=false;
   if(fits())return true;
   rows[i][0].hidden=true;
   panels[i].hidden=true;
   return false;
  };
  const tryNext=i=>{
   if(panels[i].hidden)return false;
   const next=rows[i].find(row=>row.hidden);
   if(!next)return false;
   next.hidden=false;
   if(fits())return true;
   next.hidden=true;
   return false;
  };
  // Each box must contain a FULL first article; empty headers are forbidden.
  panels.forEach((_,i)=>{tryFirst(i);});
  // Fill to the available height with authentic, distinct articles.
  // Never insert a row that would extend beyond the center column.
  let changed=true,pass=0;
  const guard=rows.reduce((n,group)=>n+group.length,0)+1;
  while(changed&&pass++<guard){
   changed=false;
   for(let i=0;i<panels.length;i++)if(tryNext(i))changed=true;
  }
  const visiblePanels=panels.filter(panel=>!panel.hidden);
  const remaining=Math.max(0,boundary-bottom());
  if(remaining>1&&visiblePanels.length>1){
   // Distribute only leftover space; the LAST intact box ends at the
   // same bottom line as the page's central text or archive grid.
   stack.style.minHeight=usable+"px";
   stack.style.justifyContent="space-between";
  }
  // Final safety pass: never hide the required Amazon affiliate showcase.
  // Final safety pass after distribution or subpixel image scaling.
  let remainingTrims=guard;
  while(!fits()&&remainingTrims-->0){
   const last=panels.map((panel,i)=>({panel,i})).filter(x=>!x.panel.hidden&&x.panel!==amazon).at(-1);
   if(!last)break;
   const row=rows[last.i].filter(x=>!x.hidden).at(-1);
   if(row)row.hidden=true;
   if(!rows[last.i].some(x=>!x.hidden))last.panel.hidden=true;
  }
  aside.classList.add("rail-ready");
 }
 function syncEditorialRails(){
  document.querySelectorAll(".home-sidebar,.inner-sidebar").forEach(sizeEditorialRail);
 }
 let editorialResizeFrame=0;
 function scheduleEditorialSizing(){
  cancelAnimationFrame(editorialResizeFrame);
  editorialResizeFrame=requestAnimationFrame(syncEditorialRails);
 }
 scheduleEditorialSizing();
 window.addEventListener("load",scheduleEditorialSizing,{once:true});
 window.addEventListener("resize",scheduleEditorialSizing,{passive:true});
 window.addEventListener("pageshow",scheduleEditorialSizing,{passive:true});
 // Image loads and font swaps can change measured card heights without
 // resizing the center column. Re-run fitting after these genuine changes.
 document.addEventListener("load",event=>{
  if(event.target?.matches?.(".sidebar img"))scheduleEditorialSizing();
 },true);
 document.fonts?.ready?.then(scheduleEditorialSizing);

 if(typeof ResizeObserver!=="undefined"){
  const railObserver=new ResizeObserver(scheduleEditorialSizing);
  document.querySelectorAll(".home-column,.inner-column").forEach(col=>railObserver.observe(col));
 }

 // Broken or unavailable media always falls back to a filled 16:9 editorial title card.
 for(const image of document.querySelectorAll(".editorial-media-frame .editorial-media-fg")){
  const frame=image.closest(".editorial-media-frame");
  if(!frame)continue;
  const fail=()=>frame.classList.add("is-fallback");
  image.addEventListener("error",fail,{once:true});
  if(image.complete&&image.naturalWidth===0)fail();
 }

 const returnTop=document.querySelector("#back-to-top");
 if(returnTop){
  const updateScrollTop=()=>{
   returnTop.hidden=window.scrollY<300;
  };
  returnTop.addEventListener("click",()=>{
   window.scrollTo({top:0,behavior:window.matchMedia("(prefers-reduced-motion: reduce)").matches?"instant":"smooth"});
  });
  window.addEventListener("scroll",updateScrollTop,{passive:true});
  updateScrollTop();
 }

 // Dynamic, same-origin, full-archive site search: available on every generated page.
 const searchOpen=document.querySelector("#site-search-open");
 const searchPanel=document.querySelector("#site-search-panel");
 const searchInput=document.querySelector("#site-search-input");
 const searchForm=document.querySelector("#site-search-form");
 const searchClose=document.querySelector("#site-search-close");
 const searchResults=document.querySelector("#site-search-results");
 const searchStatus=document.querySelector("#site-search-status");
 const searchMore=document.querySelector("#site-search-more");
 let searchable=null,results=[],shown=0,searchSequence=0,searchTimer=0;
 const normalized=s=>String(s||"").normalize("NFKD").replace(/[\u0300-\u036f]/g,"")
  .toLocaleLowerCase("it").replace(/\s+/g," ").trim();
 function setSearchStatus(message){
  if(searchStatus)searchStatus.textContent=message;
 }
 function openSearch(){
  if(!searchPanel||!searchOpen)return;
  searchPanel.hidden=false;
  searchOpen.setAttribute("aria-expanded","true");
  searchInput?.focus();
  if(!searchable)loadSearch();
 }
 function closeSearch(){
  if(!searchPanel||!searchOpen)return;
  searchPanel.hidden=true;
  searchOpen.setAttribute("aria-expanded","false");
  searchOpen.focus();
 }
 async function loadSearch(){
  setSearchStatus("Caricamento dell'archivio...");
  try{
   const response=await fetch("/search-index.json",{cache:"no-store"});
   if(!response.ok)throw new Error("HTTP "+response.status);
   const json=await response.json();
   if(!Array.isArray(json.articles))throw new Error("Archivio non valido");
   searchable=json.articles.map(r=>({
    ...r,
    _title:normalized(r.title),
    _body:normalized(r.text),
    _category:normalized(r.category)
   }));
   if(searchInput?.value.trim())runSearch();
   else setSearchStatus("Cerca tra "+searchable.length+" articoli, news, recensioni e guide.");
  }catch(error){
   setSearchStatus("Ricerca momentaneamente non disponibile. Riprova.");
  }
 }
 function renderSearchBatch(){
  if(!searchResults||!searchMore)return;
  const batch=results.slice(shown,shown+12);
  const fragment=document.createDocumentFragment();
  for(const r of batch){
   if(typeof r.url!=="string"||!/^\/[a-z0-9-]+$/.test(r.url))continue;
   const a=document.createElement("a");
   a.href=r.url;
   a.className="site-search-result";
   const meta=document.createElement("span");
   meta.className="site-search-result-meta";
   meta.textContent=(r.category||"Articolo")+(r.date?" · "+r.date:"");
   const title=document.createElement("strong");
   title.textContent=r.title;
   const description=document.createElement("span");
   description.className="site-search-result-excerpt";
   description.textContent=r.excerpt||"";
   a.append(meta,title,description);
   fragment.append(a);
  }
  searchResults.append(fragment);
  shown+=batch.length;
  searchMore.hidden=shown>=results.length;
 }
 function runSearch(){
  if(!searchable)return;
  const raw=searchInput?.value.trim()||"";
  const query=normalized(raw);
  const seq=++searchSequence;
  if(!query){results=[];shown=0;searchResults.replaceChildren();
   searchMore.hidden=true;setSearchStatus("Scrivi un argomento da cercare.");return;}
  const tokens=query.split(" ").filter(Boolean);
  results=[];
  for(const r of searchable){
   if(!tokens.every(token=>r._title.includes(token)||r._body.includes(token)||r._category.includes(token)))continue;
   let score=0;
   if(r._title===query)score+=150;
   else if(r._title.includes(query))score+=65;
   for(const t of tokens){
    if(r._title.includes(t))score+=35;
    if(r._category.includes(t))score+=10;
    if(r._body.includes(t))score+=3;
   }
   results.push({...r,_score:score});
  }
  results.sort((a,b)=>b._score-a._score||String(b.date||"").localeCompare(String(a.date||"")));
  shown=0;
  searchResults.replaceChildren();
  setSearchStatus(results.length?results.length+" risultati trovati per «"+raw+"»":"Nessun risultato. Prova con termini diversi.");
  renderSearchBatch();
 }
 searchOpen?.addEventListener("click",()=>searchPanel?.hidden?openSearch():closeSearch());
 searchClose?.addEventListener("click",closeSearch);
 searchForm?.addEventListener("submit",event=>{event.preventDefault();runSearch()});
 searchInput?.addEventListener("input",()=>{
  clearTimeout(searchTimer);
  searchTimer=setTimeout(runSearch,160);
 });
 searchMore?.addEventListener("click",renderSearchBatch);
 document.addEventListener("keydown",event=>{
  if(event.key==="Escape"&&searchPanel&&!searchPanel.hidden){event.preventDefault();closeSearch()}
  else if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
   event.preventDefault();openSearch();
  }
 });


 // Native-style compact headline rotator: exactly one of ten genuine news items visible.
 const tickerTrack=document.querySelector("#ticker-track");
 const tickerViewport=document.querySelector("#ticker-viewport");
 const tickerGroup=tickerTrack?.querySelector(".ticker-group");
 const tickerReduceMotion=window.matchMedia("(prefers-reduced-motion: reduce)");
 let tickerSignature="",activeTicker=0;

 function fitTickerToMenu(){
  if(!tickerViewport)return;
  const lastMenuLink=document.querySelector("#nav a:last-child");
  const onDesktop=window.matchMedia("(min-width: 781px)").matches;
  tickerViewport.style.removeProperty("width");
  tickerViewport.classList.remove("ticker-desktop-capped");
  if(!onDesktop||!lastMenuLink)return;
  const lastRect=lastMenuLink.getBoundingClientRect();
  const tickerRect=tickerViewport.getBoundingClientRect();
  const containerRect=tickerViewport.parentElement.getBoundingClientRect();
  if(!lastRect.width||!tickerRect.width)return;
  const target=Math.max(140,Math.min(lastRect.right-tickerRect.left,containerRect.right-tickerRect.left));
  tickerViewport.style.width=target.toFixed(1)+"px";
  tickerViewport.classList.add("ticker-desktop-capped");
 }

 function paintActiveTicker(){
  if(!tickerGroup)return;
  const links=[...tickerGroup.querySelectorAll("a.ticker-link")];
  if(!links.length)return;
  activeTicker=((activeTicker%links.length)+links.length)%links.length;
  links.forEach((a,i)=>{
   const visible=i===activeTicker;
   a.classList.toggle("ticker-active",visible);
   a.tabIndex=visible?0:-1;
   if(visible)a.removeAttribute("aria-hidden");
   else a.setAttribute("aria-hidden","true");
  });
  tickerGroup.classList.add("ticker-carousel-ready");
 }

 function refreshTickerEntries(items){
  if(!tickerGroup||!Array.isArray(items))return;
  const news=items.filter(x=>typeof x?.title==="string"&&/^\/[a-z0-9-]+$/.test(x.url||"")).slice(0,10);
  if(news.length!==10)return;
  const sig=JSON.stringify(news.map(x=>[x.title,x.url]));
  if(sig===tickerSignature)return;
  const previous=tickerGroup.querySelectorAll("a.ticker-link")[activeTicker]?.getAttribute("href");
  tickerSignature=sig;
  const fragment=document.createDocumentFragment();
  for(const item of news){
   const link=document.createElement("a");
   link.href=item.url;
   link.className="ticker-link";
   link.textContent=item.title;
   fragment.append(link);
  }
  tickerGroup.replaceChildren(fragment);
  const previousIndex=news.findIndex(x=>x.url===previous);
  activeTicker=previousIndex>=0?previousIndex:0;
  paintActiveTicker();
 }

 async function fetchTickerUpdates(){
  if(!tickerGroup)return;
  try{
   const response=await fetch("/news-ticker.json",{cache:"no-store"});
   if(!response.ok)throw new Error("News feed HTTP "+response.status);
   const data=await response.json();
   refreshTickerEntries(data.items);
  }catch(_){
   // Keep the server-rendered headlines even if refresh fails.
  }
 }

 if(tickerGroup){
  // Ensure only the first server-rendered headline is visible before the first refresh.
  const original=[...tickerGroup.querySelectorAll("a.ticker-link")].slice(0,10);
  for(const excess of [...tickerGroup.querySelectorAll("a.ticker-link")].slice(10))excess.remove();
  if(original.length===10){
   tickerSignature=JSON.stringify(original.map(a=>[a.textContent.trim(),a.getAttribute("href")]));
  }
  paintActiveTicker();
  fitTickerToMenu();
  fetchTickerUpdates();
  // Every cycle replaces the visible headline. Never show multiple headlines at once.
  setInterval(()=>{
   if(document.hidden)return;
   const count=tickerGroup.querySelectorAll("a.ticker-link").length;
   if(count>1){activeTicker=(activeTicker+1)%count;paintActiveTicker()}
  },3500);
  // Keep a long-lived tab in sync with the current published news.
  setInterval(()=>{if(!document.hidden)fetchTickerUpdates()},300000);
  let frame=0;
  window.addEventListener("resize",()=>{
   cancelAnimationFrame(frame);
   frame=requestAnimationFrame(fitTickerToMenu);
  },{passive:true});
  window.addEventListener("load",fitTickerToMenu,{once:true});
 }

 // Admin-only edit button: NEVER trust browser storage or a CSS "admin" flag.
 // The button is created only after the Studio API verifies a server-sealed,
 // HttpOnly GitHub-owner session. Each page visit also renews that cookie.
 const editableArticle=document.querySelector(".story-article[data-studio-slug]");
 if(editableArticle){
  const slug=editableArticle.getAttribute("data-studio-slug");
  if(/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(slug||"")){
   fetch("/api/studio/session",{credentials:"same-origin",cache:"no-store",redirect:"manual"})
    .then(async response=>{
     if(!response.ok||!(response.headers.get("content-type")||"").includes("application/json"))
      return null;
     return response.json();
    })
    .then(session=>{
     if(session?.admin!==true||session.authenticated!==true)return;
     const edit=document.createElement("a");
     edit.className="studio-admin-edit";
     edit.href="/studio-v2/?edit="+encodeURIComponent(slug);
     edit.textContent="Modifica";
     edit.setAttribute("aria-label","Modifica questo contenuto nello Studio amministratore");
     editableArticle.insertAdjacentElement("afterbegin",edit);
    })
    .catch(()=>{});
  }
 }


 // Home titles: full text when it fits in <=2 lines; otherwise truncate
 // exactly at 2 rendered lines with three literal ASCII dots ("...").
 // The ORIGINAL anchor text remains in the generated HTML for search engines.
 // The full title stays accessible through aria-label/title on truncated cards.
 const homeTitleSelector=
  "main.wrap .featured-wide .spotlight-grid .tile-title,"+
  "main.wrap .home-layout > .home-column article h3 > a";
 const homeTitleLinks=[...document.querySelectorAll(homeTitleSelector)];
 const homeTitleOriginals=new WeakMap();
 for(const link of homeTitleLinks)homeTitleOriginals.set(link,link.textContent.trim());
 const homeTitleTemporaryProperties=[
  "display","-webkit-line-clamp","line-clamp",
  "overflow","text-overflow","white-space"
 ];
 let homeTitleFrame=0;
 function fitHomeTitles(){
  if(!homeTitleLinks.length)return;
  for(const link of homeTitleLinks){
   const full=homeTitleOriginals.get(link);
   if(!full)continue;
   // Layout measurement uses this exact card, font and available width.
   link.textContent=full;
   link.style.setProperty("display","block","important");
   link.style.setProperty("-webkit-line-clamp","unset","important");
   link.style.setProperty("line-clamp","unset","important");
   link.style.setProperty("overflow","visible","important");
   link.style.setProperty("text-overflow","clip","important");
   link.style.setProperty("white-space","normal","important");
   const textRange=document.createRange();
   const lineCount=()=>{
    textRange.selectNodeContents(link);
    const tops=[];
    for(const rect of textRange.getClientRects()){
     if(rect.height<=0.5||rect.width<=0.5)continue;
     if(!tops.some(top=>Math.abs(top-rect.top)<1))tops.push(rect.top);
    }
    return tops.length;
   };
   if(lineCount()<=2){
    link.dataset.homeTitleClipped="false";
    continue;
   }
   // Binary search finds the longest character prefix that still fits
   // the three literal dots at the end of the SECOND line.
   let low=0,high=full.length;
   const fits=count=>{
    const prefix=full.slice(0,count).trimEnd();
    link.textContent=prefix+"...";
    return lineCount()<=2;
   };
   while(low<high){
    const mid=Math.floor((low+high+1)/2);
    if(fits(mid))low=mid;
    else high=mid-1;
   }
   // Avoid dangling space, and do not claim full title is visible.
   const shortened=full.slice(0,low).trimEnd();
   link.textContent=shortened+"...";
   link.dataset.homeTitleClipped="true";
   link.setAttribute("aria-label",full);
   link.setAttribute("title",full);
  }
  // Clear all measurement overrides after text has been fitted. For a
  // truncated title the CSS clamp remains a second safety net.
  for(const link of homeTitleLinks)
   for(const name of homeTitleTemporaryProperties)
    link.style.removeProperty(name);
 }
 function scheduleHomeTitleFitting(){
  if(!homeTitleLinks.length)return;
  cancelAnimationFrame(homeTitleFrame);
  homeTitleFrame=requestAnimationFrame(fitHomeTitles);
 }
 if(homeTitleLinks.length){
  fitHomeTitles();
  window.addEventListener("resize",scheduleHomeTitleFitting,{passive:true});
  window.addEventListener("load",scheduleHomeTitleFitting,{once:true});
  document.fonts?.ready?.then(scheduleHomeTitleFitting);
 }

})();
