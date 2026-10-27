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

 // Match each editorial rail to the real article/Home column height.
 // Only whole cards are rendered, without cropping or reusing articles.
 function sizeEditorialRail(aside){
  const stack=aside.querySelector(".sidebar-stack");
  if(!stack)return;
  const home=aside.classList.contains("home-sidebar");
  const compact=window.matchMedia("(max-width:780px)").matches;
  const column=home?aside.closest(".home-layout")?.querySelector(".home-column"):
                    aside.closest(".inner-layout")?.querySelector(".inner-column");
  if(!column)return;
  stack.style.minHeight="";
  stack.style.justifyContent="";
  const sections=[...stack.querySelectorAll(":scope > .editorial-box")];
  for(const box of sections){
   box.hidden=true;
   for(const row of box.querySelectorAll(".editorial-row"))row.hidden=true;
  }
  const maxHeight=compact?Number.POSITIVE_INFINITY:Math.max(0,Math.floor(column.getBoundingClientRect().height)-2);
  const maxSections=compact?3:30;
  const perSection=compact?2:(home?4:3);
  let visibleSections=0;
  for(const box of sections){
   if(visibleSections>=maxSections)break;
   const entries=[...box.querySelectorAll(".editorial-row")];
   if(!entries.length)continue;
   box.hidden=false;
   let shown=0;
   for(const row of entries){
    if(shown>=perSection)break;
    row.hidden=false;
    if(!compact&&stack.scrollHeight>maxHeight+2){
     row.hidden=true;
     break;
    }
    shown++;
   }
   if(!shown){box.hidden=true;break}
   visibleSections++;
  }
  if(!compact&&visibleSections>1){
   const remaining=maxHeight-stack.scrollHeight;
   if(remaining>30){stack.style.minHeight=maxHeight+"px";stack.style.justifyContent="space-between"}
  }
  aside.classList.add("rail-ready");
 }
 function syncEditorialRails(){
  for(const aside of document.querySelectorAll(".home-sidebar,.inner-sidebar"))sizeEditorialRail(aside);
 }
 syncEditorialRails();
 window.addEventListener("load",syncEditorialRails,{once:true});
 window.addEventListener("resize",syncEditorialRails);

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

 // Seamless breaking ticker: twelve real news headlines, updated when a new build is deployed.
 const tickerTrack=document.querySelector("#ticker-track");
 const tickerViewport=document.querySelector("#ticker-viewport");
 const tickerPause=document.querySelector("#ticker-pause");
 const reducedMotion=window.matchMedia("(prefers-reduced-motion: reduce)");
 let manuallyPaused=false,tickerSignature="";
 // The news bar must end directly below the last menu link ("VIDEO").
 // Measure it rather than estimating a fixed pixel position.
 function fitTickerToMenu(){
  if(!tickerViewport)return;
  const lastMenuLink=document.querySelector("#nav a:last-child");
  const onDesktop=window.matchMedia("(min-width: 781px)").matches;
  tickerViewport.style.removeProperty("width");
  tickerViewport.classList.remove("ticker-desktop-capped");
  if(!onDesktop||!lastMenuLink||!tickerPause)return;
  const lastLinkRect=lastMenuLink.getBoundingClientRect();
  const viewportRect=tickerViewport.getBoundingClientRect();
  const containerRect=tickerViewport.parentElement.getBoundingClientRect();
  if(!lastLinkRect.width||!viewportRect.width)return;
  const target=lastLinkRect.right-viewportRect.left-tickerPause.getBoundingClientRect().width;
  const limit=containerRect.right-viewportRect.left-tickerPause.getBoundingClientRect().width;
  const next=Math.max(180,Math.min(target,limit));
  tickerViewport.style.width=next.toFixed(1)+"px";
  tickerViewport.classList.add("ticker-desktop-capped");
 }
 function setTickerPaused(pause){
  manuallyPaused=pause;
  tickerTrack?.classList.toggle("ticker-user-paused",pause);
  if(tickerPause){
   tickerPause.setAttribute("aria-pressed",String(pause));
   tickerPause.setAttribute("aria-label",pause?"Riprendi lo scorrimento delle notizie":"Metti in pausa lo scorrimento delle notizie");
   tickerPause.querySelector("span").textContent=pause?"▶":"Ⅱ";
  }
 }
 function restartTicker(){
  if(!tickerTrack)return;
  const group=tickerTrack.querySelector(".ticker-group");
  if(!group)return;
  tickerTrack.querySelectorAll(".ticker-group[aria-hidden='true']").forEach(x=>x.remove());
  const links=[...group.querySelectorAll("a.ticker-link")];
  if(links.length<10)return;
  const copy=group.cloneNode(true);
  copy.setAttribute("aria-hidden","true");
  copy.querySelectorAll("a").forEach(a=>a.setAttribute("tabindex","-1"));
  tickerTrack.append(copy);
  const distance=group.getBoundingClientRect().width;
  // 82 CSS pixels per second: native-news-ticker-like constant movement.
  tickerTrack.style.setProperty("--ticker-duration",Math.max(28,distance/82).toFixed(2)+"s");
  tickerTrack.classList.add("ticker-running");
  tickerTrack.classList.toggle("ticker-user-paused",manuallyPaused);
 }
 function updateTickerStories(items){
  if(!tickerTrack||!Array.isArray(items)||items.length<10)return;
  const rows=items.filter(x=>typeof x.title==="string"&&/^\/[a-z0-9-]+$/.test(x.url||"")).slice(0,15);
  if(rows.length<10)return;
  const signature=JSON.stringify(rows.map(x=>[x.title,x.url]));
  if(signature===tickerSignature)return;
  tickerSignature=signature;
  const group=tickerTrack.querySelector(".ticker-group");
  if(!group)return;
  group.replaceChildren();
  for(const x of rows){
   const a=document.createElement("a");
   a.className="ticker-link";
   a.href=x.url;
   const dot=document.createElement("span");
   dot.className="ticker-dot";
   dot.setAttribute("aria-hidden","true");
   a.append(dot,document.createTextNode(x.title));
   group.append(a);
  }
  restartTicker();
 }
 async function refreshTicker(){
  if(!tickerTrack)return;
  try{
   const response=await fetch("/news-ticker.json",{cache:"no-store"});
   if(!response.ok)throw new Error("Ticker HTTP "+response.status);
   const obj=await response.json();
   updateTickerStories(obj.items);
  }catch(_){/* Retain already server-rendered real headlines if temporarily offline. */}
 }
 if(tickerTrack){
  fitTickerToMenu();
  restartTicker();
  // The server already rendered the same headlines; avoid restarting on first fetch.
  const initialGroup=tickerTrack.querySelector(".ticker-group");
  if(initialGroup){
   tickerSignature=JSON.stringify([...initialGroup.querySelectorAll("a.ticker-link")].map(a=>[
    a.textContent.trim(),new URL(a.href).pathname
   ]));
  }
  refreshTicker();
  // Newly published stories are fetched without reloading or interrupting current motion.
  setInterval(()=>{if(!document.hidden)refreshTicker()},300000);
  tickerPause?.addEventListener("click",()=>setTickerPaused(!manuallyPaused));
  let resizeFrame=0;
  window.addEventListener("resize",()=>{
   cancelAnimationFrame(resizeFrame);
   resizeFrame=requestAnimationFrame(fitTickerToMenu);
  },{passive:true});
  // Fonts may settle after first paint. Re-measure alignment without restarting the animation.
  window.addEventListener("load",fitTickerToMenu,{once:true});
 }
})();
