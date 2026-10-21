#!/usr/bin/env node
"use strict";
/* Read-only browser investigation on the ACTUAL public ZazoomTek.it.
   It does not change the site, create a release, or trigger the Master.
   Collects LCP element and LayoutShiftAttribution to avoid guesswork. */
const {chromium}=require("playwright-core");
const BASE="https://zazoomtek.it/";
const hosts=["mobile","desktop"];
function n(x){return typeof x==="number"?Math.round(x*100)/100:x;}
async function audit(browser,kind){
 const mobile=kind==="mobile";
 const context=await browser.newContext({
   viewport:mobile?{width:390,height:844}:{width:1365,height:900},
   deviceScaleFactor:mobile?2:1,isMobile:mobile,hasTouch:mobile,
   ...(mobile?{userAgent:"Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36"}:{})
 });
 const page=await context.newPage();
 await page.addInitScript(()=>{
   window.__ztVitals={lcp:[],shifts:[],mutations:[],marks:[]};
   let mark=()=>performance.now().toFixed(0);
   const desc=el=>{
     if(!el)return null;
     let s=el.tagName?.toLowerCase()||"node";
     if(el.id)s+="#"+el.id;
     if(el.classList?.length)s+="."+[...el.classList].slice(0,3).join(".");
     return s;
   };
   try{new PerformanceObserver(l=>{
     for(const e of l.getEntries()){
       const el=e.element;
       window.__ztVitals.lcp.push({start:Math.round(e.startTime),size:Math.round(e.size),element:desc(el),
         src:el?.currentSrc||el?.src||null,url:e.url||null,text:el?.textContent?.trim().slice(0,85)||null});
     }
   }).observe({type:"largest-contentful-paint",buffered:true});}catch(_){}
   try{new PerformanceObserver(l=>{
     for(const e of l.getEntries()){
       if(e.hadRecentInput)continue;
       window.__ztVitals.shifts.push({at:Math.round(e.startTime),value:e.value,
         sources:(e.sources||[]).map(s=>({node:desc(s.node),
           from:s.previousRect?{x:Math.round(s.previousRect.x),y:Math.round(s.previousRect.y),w:Math.round(s.previousRect.width),h:Math.round(s.previousRect.height)}:null,
           to:s.currentRect?{x:Math.round(s.currentRect.x),y:Math.round(s.currentRect.y),w:Math.round(s.currentRect.width),h:Math.round(s.currentRect.height)}:null})).slice(0,8)});
     }
   }).observe({type:"layout-shift",buffered:true});}catch(_){}
   const watch=()=>{
     const body=document.body;if(!body)return;
     try{new MutationObserver(records=>{
       if(window.__ztVitals.mutations.length>120)return;
       for(const item of records){
         if(item.type!=="childList"||(!item.addedNodes.length&&!item.removedNodes.length))continue;
         const el=item.target, first=[...item.addedNodes].find(n=>n.nodeType===1);
         if(!first&&item.addedNodes.length===0)continue;
         window.__ztVitals.mutations.push({at:Math.round(performance.now()),target:desc(el),
           added:desc(first),deleted:item.removedNodes.length});
       }
     }).observe(body,{subtree:true,childList:true});}catch(_){}
   };
   if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",watch,{once:true});else watch();
 });
 let errors=[];page.on("pageerror",e=>errors.push(e.message));let failed=[];
 page.on("requestfailed",q=>{if(failed.length<30)failed.push({url:q.url(),error:q.failure()?.errorText})});
 const t0=Date.now();
 const response=await page.goto(BASE+"?webvitals-audit="+kind+"-"+Date.now(),{waitUntil:"domcontentloaded",timeout:60000});
 await page.waitForTimeout(mobile?25000:12000);
 const d=await page.evaluate(()=>{
   const v=window.__ztVitals||{lcp:[],shifts:[]};
   let nav=performance.getEntriesByType("navigation")[0];
   const lead=document.querySelector("#ztFeaturedGrid img");
   const head=document.head.innerHTML;
   const css=document.querySelector("#zt-home-graphic-approved-20261016");
   const main=document.querySelector("#ztFeaturedGrid");
   return {vitals:v,ttfb:nav?.responseStart||0,fcp:performance.getEntriesByName("first-contentful-paint")[0]?.startTime||0,
     dom:document.documentElement.outerHTML.length,
     cssInHead:!!css,preloadImage:head.match(/<link[^>]+rel="preload"[^>]+as="image"[^>]*>/g)?.slice(0,3)||[],
     lead:{src:lead?.currentSrc,loading:lead?.loading,fetchPriority:lead?.fetchPriority,
           complete:lead?.complete,naturalWidth:lead?.naturalWidth},
     featuredCards:main?.children.length,shiftsTotal:v.shifts.reduce((sum,x)=>sum+x.value,0),
     cookie:document.querySelector("[id*='cookie'],[class*='cookie']")?.getBoundingClientRect().toJSON()||null,
     bodyWidth:document.body.scrollWidth,viewportWidth:innerWidth};
 });
 const lcp=d.vitals.lcp.slice(-1)[0]||null;
 const sorted=[...d.vitals.shifts].sort((a,b)=>b.value-a.value);
 const out={kind,status:response?.status(),pageTimeMs:Date.now()-t0,
  ttfb:n(d.ttfb),fcp:n(d.fcp),lcp,cls:n(d.shiftsTotal),
  lead:d.lead,cssInHead:d.cssInHead,preload:d.preloadImage,
  cards:d.featuredCards,documentLength:d.dom,overflow:d.bodyWidth-d.viewportWidth,
  topShifts:sorted.slice(0,12),firstShifts:d.vitals.shifts.slice(0,10),
  mutations:d.vitals.mutations.slice(0,35),errors:errors.slice(0,12),failedRequests:failed.slice(0,12)};
 console.log("ZT_ACTUAL_SITE_VITALS "+JSON.stringify(out));
 await page.screenshot({path:"/tmp/zt-live-"+kind+".png",fullPage:false}).catch(()=>{});
 await context.close();
}
async function main(){
 const browser=await chromium.launch({headless:true,executablePath:"/usr/bin/google-chrome",
   args:["--no-sandbox","--disable-dev-shm-usage"]});
 try{for(const kind of hosts)await audit(browser,kind)}
 finally{await browser.close()}
}
main().catch(e=>{console.error("LIVE_AUDIT_ERROR "+e.stack);process.exit(1)});
