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

 // Fill each right-hand editorial rail, respecting the height of the actual article column.
 // Fixed Home order: I più letti, Amazon, Da non perdere, Dalla redazione, Altre news.
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
  const boxes=[...stack.querySelectorAll(":scope > .editorial-box")];
  const contents=boxes.map(box=>[...box.querySelectorAll(".editorial-row")]);
  for(const box of boxes)box.hidden=true;
  for(const rows of contents)for(const row of rows)row.hidden=true;
  if(compact){
   // On phones and tablets the rail stacks below content; never hide the Amazon panel.
   boxes.forEach((box,i)=>{
    box.hidden=false;
    contents[i].slice(0,4).forEach(row=>row.hidden=false);
   });
   aside.classList.add("rail-ready");
   return;
  }
  const target=Math.max(0,Math.floor(column.getBoundingClientRect().height)-3);
  if(target<100)return;
  const fits=()=>stack.scrollHeight<=target+1;
  const mandatory=home?boxes.length:Math.min(2,boxes.length);
  // Show all fixed Home panels, at least first two inner panels.
  boxes.forEach((box,i)=>{
   box.hidden=false;
   if(!fits()&&i>=mandatory){box.hidden=true;return}
   const first=contents[i][0];
   if(first){
    first.hidden=false;
    if(!fits())first.hidden=true;
   }
  });
  let changed=true;
  while(changed){
   changed=false;
   for(let i=0;i<boxes.length;i++){
    if(boxes[i].hidden)continue;
    const next=contents[i].find(row=>row.hidden);
    if(!next)continue;
    next.hidden=false;
    if(!fits()){next.hidden=true;continue}
    changed=true;
   }
  }
  // Remaining small gaps are distributed between intact sections, not inside cropped cards.
  const remaining=Math.max(0,target-stack.scrollHeight);
  const shown=boxes.filter(box=>!box.hidden).length;
  if(remaining>14&&shown>1&&remaining/shown<115){
   stack.style.minHeight=target+"px";
   stack.style.justifyContent="space-between";
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
   if(document.hidden||tickerReduceMotion.matches)return;
   const count=tickerGroup.querySelectorAll("a.ticker-link").length;
   if(count>1){activeTicker=(activeTicker+1)%count;paintActiveTicker()}
  },5200);
  // Keep a long-lived tab in sync with the current published news.
  setInterval(()=>{if(!document.hidden)fetchTickerUpdates()},300000);
  let frame=0;
  window.addEventListener("resize",()=>{
   cancelAnimationFrame(frame);
   frame=requestAnimationFrame(fitTickerToMenu);
  },{passive:true});
  window.addEventListener("load",fitTickerToMenu,{once:true});
 }

})();
