#!/usr/bin/env node
"use strict";
// Non-destructive 3-viewport test of generated Cloudflare Home.
const {chromium}=require("playwright-core");
const base="http://127.0.0.1:8899/";
const views=[["desktop",1600,900],["tablet",1100,900],["mobile",390,844]];
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:"/usr/bin/google-chrome",
   args:["--no-sandbox","--disable-dev-shm-usage"]});
 try{
  for(const [name,width,height] of views){
   const page=await browser.newPage({viewport:{width,height}});
   const pageErrors=[];page.on("pageerror",e=>pageErrors.push(e.message));
   await page.goto(base+"?speciali-test="+name,{waitUntil:"domcontentloaded",timeout:45000});
   await page.waitForSelector("#ztpNewsRail #ztHomeSpeciali",{state:"attached",timeout:30000});
   await page.waitForTimeout(5000);
   const info=await page.evaluate(()=>{
    const q=s=>document.querySelector(s),rect=s=>q(s)?.getBoundingClientRect();
    const rail=q("#ztpNewsRail");
    const specials=[...q("#ztHomeSpeciali")?.querySelectorAll(".zt-special-item")||[]];
    const links=specials.map(x=>x.querySelector("h3 a")?.getAttribute("href"));
    const railChildren=[...rail.children].filter(x=>getComputedStyle(x).display!=="none");
    const order=railChildren.map(x=>x.id||x.getAttribute("data-special-section")||x.className);
    const railB=rect("#ztpNewsRail")?.bottom;
    const videosB=rect("#ztpVideosAnchor")?.bottom;
    const shortsNodes=[...document.querySelectorAll(
      ".zt-shorts-box,.ztp-shorts-companion,#zt-home-shelves .zt-shelf-shorts")];
    const visibleShorts=shortsNodes.filter(x=>{let s=getComputedStyle(x);let r=x.getBoundingClientRect();return s.display!=="none"&&s.visibility!=="hidden"&&r.width>0&&r.height>0;}).length;
    return {order,links,specials:specials.length,railBottom:railB,videoBottom:videosB,
      diff:Math.round((railB||0)-(videosB||0)),visibleShorts,
      videoPresent:!!q("#ztpVideosAnchor .zt-shelf"),
      overflow:document.documentElement.scrollWidth-innerWidth,
      cardImagesGood:specials.every(x=>!!x.querySelector("img[src]")),
      cachedCss:!!document.querySelector('link[id="zt-home-graphic-approved-20261016"]')};
   });
   console.log("ZT_HOME_SPECIALI_VIEW",name,JSON.stringify(info));
   if(info.specials!==2||!info.cardImagesGood)throw Error(name+": exactly two genuine approved specials are expected");
   if(info.order.indexOf("ztHomeSpeciali")<0||info.order.indexOf("ztHomeSpeciali")<
      info.order.indexOf("zt-popular-box")||info.order.indexOf("ztHomeSpeciali")>
      info.order.indexOf("tech"))throw Error(name+": SPECIALI box not between DA NON PERDERE and Tech Impact");
   if(info.visibleShorts!==0)throw Error(name+": old Home Shorts box remains visible");
   if(!info.videoPresent)throw Error(name+": Explore Video disappeared");
   if(info.overflow>10)throw Error(name+": horizontal overflow "+info.overflow);
   if(name==="desktop"&&Math.abs(info.diff)>105)throw Error(
     "Desktop rail must finish aligned to Explore Video, delta "+info.diff+"px");
   if(pageErrors.length)throw Error(name+": browser script errors "+pageErrors.slice(0,3).join("; "));
   await page.screenshot({path:"/tmp/zt-home-speciali-"+name+".png",fullPage:true});
   await page.close();
  }
  console.log("PASS: SPECIALI after popular, no Home Shorts, video shelf preserved, aligned rail, responsive viewports");
 }finally{await browser.close();}
})().catch(error=>{console.error(error.stack);process.exit(1)});
