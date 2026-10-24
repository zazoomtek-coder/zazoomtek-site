#!/usr/bin/env node
/* Actual Chromium smoke: run the built site, inspect computed CSS and click Studio.
   The test fails the release BEFORE Cloudflare deploy if a visible requirement fails.
   No simulated DOM, no simulated video or Community story records. */
"use strict";
const fs = require("fs");
const path = require("path");
const http = require("http");
const { chromium } = require("playwright");

const ROOT = path.resolve(process.argv[2] || "dist");
const MIME = {".html":"text/html; charset=utf-8",".js":"application/javascript; charset=utf-8",
  ".json":"application/json; charset=utf-8",".css":"text/css; charset=utf-8",
  ".svg":"image/svg+xml",".webp":"image/webp",".jpg":"image/jpeg",
  ".png":"image/png",".woff2":"font/woff2"};
function die(message) { throw new Error("VISIBLE SITE QA FAILURE: " + message); }
const server=http.createServer((req,res)=>{
  const u=new URL(req.url||"/","http://127.0.0.1");
  let rel;
  try{rel=decodeURIComponent(u.pathname);}catch{res.writeHead(400).end();return;}
  if(rel.endsWith("/"))rel+="index.html";
  else if(!path.extname(rel))rel+=".html";
  const target=path.resolve(ROOT,"."+rel);
  if(!target.startsWith(ROOT+path.sep)){res.writeHead(403).end();return;}
  fs.readFile(target,(err,buffer)=>{
    if(err){res.writeHead(404).end();return;}
    res.writeHead(200,{"Content-Type":MIME[path.extname(target)]||"application/octet-stream",
      "Cache-Control":"no-store"});
    res.end(buffer);
  });
});
(async()=>{
  if(!fs.existsSync(path.join(ROOT,"index.html")))die("index.html missing");
  const dataPath=path.resolve("services10-data/community.json");
  const posts=JSON.parse(fs.readFileSync(dataPath,"utf8"));
  const yesterday=posts.filter(x=>String(x.published_iso||"").startsWith("2026-10-23"));
  if(yesterday.length<5)die("23 October archived Community posts: "+yesterday.length+" (expected >=5)");
  for(const p of yesterday){
    if(!fs.existsSync(path.join(ROOT,"news-"+p.id+".html")))die("Unpublished yesterday Community "+p.id);
  }
  await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
  const url="http://127.0.0.1:"+server.address().port;
  const browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  const jsErrors=[];
  page.on("pageerror",err=>jsErrors.push(err.message));
  try{
    await page.goto(url+"/",{waitUntil:"domcontentloaded",timeout:20000});
    await page.waitForTimeout(2000);
    const home=await page.evaluate(()=>{
      const box=document.querySelector("#zt-popular-box");
      const cards=[...(box?.querySelectorAll(".zt-popular-list>.zt-popular-article")||[])];
      const visible=cards.filter(el=>{
        const c=getComputedStyle(el);
        return c.display!=="none"&&c.visibility!=="hidden"&&
               c.opacity!=="0"&&el.getBoundingClientRect().width>0&&el.getBoundingClientRect().height>0;
      });
      const headlines=visible.map(el=>el.querySelector("strong")?.textContent?.trim()||"");
      const headingSelectors=[
        "#zt-popular-box .zt-popular-head h2",
        "#articoli .ztp-news-head h2 span",
        "#articoli .ztp-news-rail .zt-special-head h2"
      ];
      const headings=headingSelectors.flatMap(selector=>
        [...document.querySelectorAll(selector)].map(el=>({
          selector,clip:getComputedStyle(el).clipPath,radius:getComputedStyle(el).borderRadius,
          width:Math.round(el.getBoundingClientRect().width)
        })));
      const web=document.querySelector("#zt-webnews-home");
      const video=document.querySelector("#zt-home-shelves");
      const webPlaced=!!web&&!!video&&web.previousElementSibling===video;
      return {count:cards.length,visible:visible.length,headlines,headings,
              webPlaced,webCards:web?.querySelectorAll(".zt-webnews-item").length||0};
    });
    console.log("VISIBLE_HOME_QA",JSON.stringify(home));
    if(home.visible!==5)die("Da non perdere rendered "+home.visible+" visible thumbnails, not five");
    if(home.headlines.some(t=>!t)||new Set(home.headlines.map(t=>t.normalize("NFKC").toLowerCase().replace(/\s+/g," ").trim())).size!==5)
      die("Da non perdere headlines blank or duplicated");
    if(home.headings.length<2)die("Expected square box headers not actually mounted");
    if(home.headings.some(h=>h.clip!=="none"||h.radius!=="0px"))
      die("Still diagonal or rounded editorial header: "+JSON.stringify(home.headings));
    if(!home.webPlaced||home.webCards!==5)die("Web-news block not below Esplora latest videos or lacks 1+4 cards");
    fs.mkdirSync("qa-screenshots",{recursive:true});
    await page.screenshot({path:"qa-screenshots/home-desktop.png",fullPage:true});
    // Use a real archived article and verify button is visible even without
    // localStorage login; actual GitHub editing still requires authentication.
    const post=yesterday[0];
    const articleName="news-"+post.id+".html";
    await page.goto(url+"/"+articleName,{waitUntil:"domcontentloaded",timeout:20000});
    const edit=page.locator("#zt-studio-edit-title");
    if(await edit.count()!==1)die("Static Modifica missing in Community article");
    if(!await edit.isVisible())die("Modifica button hidden on interior page");
    const href=await edit.getAttribute("href");
    if(href!=="/studio/?edit="+encodeURIComponent(articleName))die("Modifica points to wrong Studio path: "+href);
    await page.screenshot({path:"qa-screenshots/article-edit.png",fullPage:false});
    await edit.click();
    if(!page.url().includes("/studio/?edit="))die("Modifica click failed to open Studio");
    console.log("VISIBLE_STUDIO_QA",JSON.stringify({article:articleName,edit:href,editorDestination:page.url()}));
    console.log("REAL_COMMUNITY_YESTERDAY_QA",JSON.stringify({count:yesterday.length,
      sample:yesterday.slice(0,5).map(x=>({id:x.id,title:x.title,date:x.published_iso}))}));
    if(jsErrors.length)console.log("NON_BLOCKING_PAGE_JS_ERRORS",JSON.stringify(jsErrors.slice(0,5)));
    console.log("PASS: Chromium displayed five Tech images, square headings, web 1+4, linked Studio and yesterday's real Community pages");
  }finally{
    await browser.close();
    server.close();
  }
})().catch(err=>{console.error(err.stack||err);server.close();process.exitCode=1});
