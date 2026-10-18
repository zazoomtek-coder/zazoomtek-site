#!/usr/bin/env node
"use strict";
// Cloudflare release gate: render the actual Home and reject regressions.
// This check runs ONLY on a new validated release, not every hourly no-change.
const {chromium}=require("playwright-core");
const BASE=process.env.ZT_BROWSER_BASE||"http://127.0.0.1:8877/";
const VIEWS=[["desktop",1600,900],["tablet",1100,900],["mobile",390,844]];
async function main(){
 const browser=await chromium.launch({headless:true,executablePath:"/usr/bin/google-chrome",
   args:["--no-sandbox","--disable-dev-shm-usage"]});
 try{
  for(const [name,width,height] of VIEWS){
   const page=await browser.newPage({viewport:{width,height}});
   const pageErrors=[];page.on("pageerror",e=>pageErrors.push(e.message));
   await page.goto(BASE+"?release-browser-check="+name,{waitUntil:"domcontentloaded",timeout:45000});
   await page.waitForFunction(()=>{
      return document.querySelector(".ztp-news-tech .ztp-news-items") &&
        document.querySelector(".ztp-news-gaming .ztp-news-items") &&
        document.querySelector("#ztFeaturedGrid");
   },{timeout:25000});
   // Allow the 9 real published archive fetches to settle. Browser runtime
   // selects by original timestamp, not the order in which fetches finish.
   await page.waitForTimeout(4200);
   const info=await page.evaluate(()=>{
      function read(name){
        return [...document.querySelectorAll(".ztp-news-"+name+
          " .ztp-news-items > article.article-row")].map(row=>{
          const a=row.querySelector(".article-copy h3 a[href]");
          const url=a?new URL(a.getAttribute("href"),location.origin).pathname:"";
          const timestamp=Date.parse(row.getAttribute("data-published-at")||"");
          return {url,date:Number.isFinite(timestamp)?timestamp:0,
                  shown:getComputedStyle(row).display!=="none"&&!row.hidden,
                  title:a?.textContent||""};
        });
      }
      const featured=new Set([...document.querySelectorAll("#ztFeaturedGrid a[href]")]
        .map(a=>new URL(a.getAttribute("href"),location.origin).pathname));
      const rect=name=>document.querySelector(".ztp-news-"+name)?.getBoundingClientRect();
      const tech=rect("tech"),gaming=rect("gaming");
      return {tech:read("tech"),gaming:read("gaming"),featured:[...featured],
        techBottom:tech?.bottom||0,gamingBottom:gaming?.bottom||0,
        overflow:document.documentElement.scrollWidth-innerWidth,
        guides:document.querySelectorAll("#ztHomeGuide .zt-magazine-primary,#ztHomeGuide .zt-magazine-small").length,
        extras:document.querySelectorAll("#ztHomeExtra .zt-magazine-primary,#ztHomeExtra .zt-magazine-small").length,
        home:!!document.querySelector("header .topbar,header .shell.topbar,header nav"),
        columns:!!document.querySelector(".ztp-two-news-columns")};
   });
   const all=[...info.tech,...info.gaming],urls=all.map(x=>x.url);
   const failures=[];
   if(!info.columns||!info.home)failures.push("Approved Home/header/columns missing");
   if(info.tech.length!==10||info.gaming.length!==10)
     failures.push("Column counts "+info.tech.length+"/"+info.gaming.length+" instead of 10/10");
   if(all.some(x=>!x.url||!x.shown))failures.push("Missing or invisible article");
   if(new Set(urls).size!==20)failures.push("Duplicate or missing canonical article URL");
   if(all.some(x=>info.featured.includes(x.url)))failures.push("Featured article duplicated in columns");
   for(const name of ["tech","gaming"]){
     const rows=info[name];
     if(rows.some(x=>x.date<=0))failures.push(name+" has an article without a valid original ISO date");
     if(rows.some((x,i)=>i>0&&x.date>rows[i-1].date))
       failures.push(name+" is not newest-to-oldest by original date");
   }
   if(info.overflow>8)failures.push("Horizontal overflow "+info.overflow+"px");
   if(info.guides!==3||info.extras!==3)failures.push("GUIDE/EXTRA not exactly three");
   if(pageErrors.length)failures.push("Browser errors: "+pageErrors.slice(0,3).join("; "));
   console.log("RELEASE BROWSER",name,JSON.stringify({
     tech:info.tech.length,gaming:info.gaming.length,unique:new Set(urls).size,
     dateTech:info.tech[0]?.date,dateGaming:info.gaming[0]?.date,
     bottomDelta:Math.round(Math.abs(info.techBottom-info.gamingBottom)),
     guides:info.guides,extra:info.extras,overflow:info.overflow,failures}));
   if(failures.length)throw Error(name+": "+failures.join(" | "));
   await page.close();
  }
  console.log("PASS: Home 10/10, original chronology, featured exclusivity, GUIDE/EXTRA 3/3, responsive browser");
 }finally{await browser.close()}
}
main().catch(e=>{console.error("CLOUDFLARE RELEASE BLOCKED:",e);process.exit(1)});
