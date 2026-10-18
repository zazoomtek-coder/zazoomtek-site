#!/usr/bin/env node
/* Controlli di sicurezza: Studio deve usare sempre i template editoriali approvati. */
const assert=require("node:assert/strict");
const fs=require("node:fs");
const get=p=>fs.readFileSync(p,"utf8");
const studio=get("studio/index.html");
const publisher=get("studio/publisher.js");
const layouts=get("studio/layouts.js");
const news=get("studio/template-news.html");
const review=get("studio/template-review.html");
assert.match(studio,/<script src="\/studio\/layouts\.js" defer><\/script>/);
assert.ok(studio.indexOf("/studio/layouts.js")<studio.indexOf("/studio/publisher.js"),"Libreria deve precedere il pubblicatore");
assert.match(publisher,/await window\.ZTStudioLayouts\.build\(/);
assert.match(publisher,/recensione-studio-/);
assert.doesNotMatch(publisher,/const html=articleHTML\(/);
assert.match(layouts,/function preview\(/);
assert.match(layouts,/cache:"no-store"/);
assert.match(layouts,/template-news\.html/);
assert.match(layouts,/template-review\.html/);
assert.match(layouts,/function appendRating\(/);
assert.match(layouts,/function appendProsCons\(/);
assert.match(layouts,/zt-sidebar-feed\.json/);
assert.match(news,/class="article-body"/);
assert.match(news,/class="article-main"/);
assert.match(review,/class="rating"/);
assert.match(review,/class="proscons"/);
assert.match(review,/class="article-body article-main"/);
assert.match(news,/<meta name="robots" content="noindex,nofollow">/);
assert.match(review,/<meta name="robots" content="noindex,nofollow">/);
const cloudflare=get("scripts/build-cloudflare-pages.py");
const build=get("scripts/cloudflare-build-site.py");
for(const file of ["layouts.js","template-news.html","template-review.html"]){
  assert.ok(cloudflare.includes('"'+file+'"'),"Cloudflare whitelist missing "+file);
  assert.ok(build.includes('studio/'+file),"Cloudflare build missing "+file);
}

console.log("Studio layout checks OK: modelli di News e Recensioni approvati, nessuna modifica alla Home.");
