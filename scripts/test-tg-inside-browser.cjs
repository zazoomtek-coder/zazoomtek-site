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
   const groups=page.locator('header .topbar nav.nav > .nav-drop');
   const insights=groups.filter({has:page.locator('button.nav-drop-trigger', {hasText:'INSIGHTS'})});
   if(await insights.count()!==1)throw Error(name+': expected one INSIGHTS menu');
   const trigger=insights.locator('button.nav-drop-trigger');
   if(await trigger.innerText()!=='INSIGHTS')throw Error(name+': wrong visible menu label');
   if(name==='desktop')await trigger.hover(); else await trigger.click();
   const menu=insights.locator('.nav-submenu');
   await menu.waitFor({state:'visible',timeout:12000});
   const links=await menu.locator('a').evaluateAll(nodes=>nodes.map(x=>({
     text:x.textContent.trim().toUpperCase(),path:new URL(x.href).pathname
   })));
   const expected=[
    {text:'TECH IMPACT',path:'/tech-today.html'},
    {text:'GAMING INSIDE',path:'/gaming-today.html'},
    {text:'SPECIALI',path:'/speciali.html'}
   ];
   if(JSON.stringify(links)!==JSON.stringify(expected))
     throw Error(name+': wrong INSIGHTS links '+JSON.stringify(links));
   if(await page.locator('header .topbar nav.nav').innerText().then(x=>x.includes('TG INSIDE')))
     throw Error(name+': old navigation label still visible');
   await menu.locator('a[href="/speciali.html"]').click();
   await page.waitForURL('**/speciali.html');
   const state=await page.evaluate(()=>({
    canonical:document.querySelector('link[rel=canonical]')?.href,
    seo:!!document.getElementById('zt-specials-ld'),
    rail:!!document.querySelector('aside.news-sidebar.zt-side-mix'),
    editorial:!!document.querySelector('aside.news-sidebar .zt-special-box, aside.news-sidebar .zt-mix-feature, aside.news-sidebar .zt-mix-recent'),
    related:document.querySelectorAll('.zt-specials-related-card').length,
    footer:!!document.querySelector('footer.zt-unified-footer'),
    overflow:document.documentElement.scrollWidth-innerWidth,
    title:document.querySelector('h1')?.textContent?.trim(),
    nav:!![...document.querySelectorAll('header .topbar nav.nav button.nav-drop-trigger')].find(x=>x.textContent.trim()==='INSIGHTS')
   }));
   if(!state.canonical?.endsWith('/speciali.html')||!state.seo||!state.rail||!state.editorial
     ||!state.footer||state.related<4||state.overflow>8||state.title!=='Speciali'||!state.nav||pageErrors.length)
     throw Error(name+': incomplete SPECIALI '+JSON.stringify({state,pageErrors}));
   console.log('PASS',name,JSON.stringify({links,state}));
   await page.close();
  }
 }finally{await browser.close();}
}
main().catch(e=>{console.error('INSIGHTS browser gate FAILED:',e);process.exit(1)});
