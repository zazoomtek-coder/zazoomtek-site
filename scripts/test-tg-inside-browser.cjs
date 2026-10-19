#!/usr/bin/env node
"use strict";
// Browser check for actual built files, never changing production.
const {chromium}=require("playwright-core");
const BASE=process.env.ZT_BROWSER_BASE||"http://127.0.0.1:8877/";
async function main(){
 const browser=await chromium.launch({headless:true,executablePath:"/usr/bin/google-chrome",
  args:["--no-sandbox","--disable-dev-shm-usage"]});
 try{
  for(const [name,opts] of [
   ["desktop",{viewport:{width:1600,height:900}}],
   ["mobile",{viewport:{width:390,height:844},hasTouch:true,isMobile:true}]
  ]){
   const page=await browser.newPage(opts);
   const pageErrors=[];
   page.on('pageerror',e=>pageErrors.push(e.message));
   await page.goto(BASE+"?tg-inside-test="+name,{waitUntil:"domcontentloaded",timeout:45000});
   await page.waitForSelector('#zt-tg-menu',{timeout:15000});
   const link=page.locator('header .topbar nav.nav > a').filter({hasText:'TG INSIDE'});
   if(await link.count()!==1)throw Error(name+': missing exactly one TG Inside button');
   if(await page.locator('header .topbar nav.nav > a.zt-tg-hidden-link').count()!==1)
    throw Error(name+': original category link was not grouped');
   if(name==='desktop')await link.hover();
   else await link.click();
   await page.waitForFunction(()=>document.getElementById('zt-tg-menu')?.classList.contains('is-open'));
   const links=await page.locator('#zt-tg-menu > a').evaluateAll(nodes=>nodes.map(x=>({text:x.textContent.trim(),path:new URL(x.href).pathname})));
   const expected=[
    {text:'TECH IMPACT',path:'/tech-today.html'},
    {text:'GAMING INSIDE',path:'/gaming-today.html'},
    {text:'SPECIALI',path:'/speciali.html'}
   ];
   if(JSON.stringify(links)!==JSON.stringify(expected))throw Error(name+': wrong submenu '+JSON.stringify(links));
   await page.locator('#zt-tg-menu > a[href="/speciali.html"]').click();
   await page.waitForURL('**/speciali.html');
   const state=await page.evaluate(()=>({
    canonical:document.querySelector('link[rel=canonical]')?.href,
    seo:!!document.getElementById('zt-specials-ld'),
    rail:!!document.querySelector('aside.news-sidebar.zt-side-mix'),
    editorial:!!document.querySelector('.zt-mix-feature')&&!!document.querySelector('.zt-mix-recent'),
    footer:!!document.querySelector('footer.zt-unified-footer'),
    overflow:document.documentElement.scrollWidth-innerWidth,
    title:document.querySelector('h1')?.textContent?.trim(),
    nav:!![...document.querySelectorAll('header .topbar nav.nav > a')].find(x=>x.textContent.trim()==='TG INSIDE')
   }));
   if(!state.canonical?.endsWith('/speciali.html')||!state.seo||!state.rail||!state.editorial
     ||!state.footer||state.overflow>8||state.title!=='Speciali'||!state.nav||pageErrors.length)
     throw Error(name+': incomplete SPECIALI '+JSON.stringify({state,pageErrors}));
   console.log('PASS',name,JSON.stringify({links,state}));
   await page.close();
  }
 }finally{await browser.close();}
}
main().catch(e=>{console.error('TG Inside browser gate FAILED:',e);process.exit(1)});
