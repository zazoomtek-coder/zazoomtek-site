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
})();
