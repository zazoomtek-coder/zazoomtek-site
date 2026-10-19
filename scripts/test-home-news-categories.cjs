"use strict";
const fs=require("fs");
const vm=require("vm");
const assert=require("assert").strict;
const source=fs.readFileSync("zt-home-live.js","utf8");
const part=source.split("// HOME_TOPIC_CLASSIFIER_START")[1]?.split("// HOME_TOPIC_CLASSIFIER_END")[0];
assert(part&&part.includes("function categorizeHomeArticle"),"topic classifier must exist");
// The extracted browser classifier sets a window property; supply its browser global\n// without executing the complete Home script or relaxing classifier assertions.\nconst classify=vm.runInNewContext(part+"\ncategorizeHomeArticle",{window:{}},{timeout:1500});
const samples=[
 ["Battlefield 6 Stagione 5 parte oggi con Las Vegas, Area 51, Rapid Royale e crossover Dead Space","gaming"],
 ["PUBG Mobile Global Open 2026 Season 2, nuovo formato e montepremi da 500.000 dollari","gaming"],
 ["Hasbro Games Junior Collection riunisce Monopoly, Cluedo e Il Gioco della Vita in una raccolta per tutta la famiglia","gaming"],
 ["Trust punta sul benessere digitale, dalla postura alle periferiche ergonomiche per lavoro e gaming","tech"],
 ["SpongeBob SquarePants: Titans of the Tide arriva su Nintendo Switch","gaming"],
 ["Total War: SHOGUN 2 - Complete Edition è disponibile oggi","gaming"],
 ["Lucca Comics & Games lancia LC&G Card Collection, il nuovo gioco di carte digitali","gaming"],
 ["Sharp presenta BP-80C70 e BP-80C80, nuove multifunzione","tech"],
 ["PLAYERS al M9 di Venezia Mestre racconta 80 anni di videogiochi","gaming"],
 ["Totem arriva nei negozi Città del Sole, 160 giochi senza schermo né connessione","tech"],
 ["realme passa a ColorOS 17 basato su Android 17","tech"],
 ["Hisense presenta Speed Oven, il forno 7-in-1","tech"],
 ["AI e governance, per Veeam senza visibilità non può esistere un vero controllo","tech"],
 ["Huawei lancia WATCH 6 Series e MatePad Pro 12","tech"],
 ["Be Comics! Be Games! Be XMAS! arriva a Torino con gaming e cosplay","gaming"],
 ["Oltre il Black Friday, SMS e WhatsApp per le aziende","tech"],
 ["Crazy Taxi: World Tour, la quarta mappa in Brasile","gaming"],
 ["ROCKBEASTS arriverà a gennaio, demo gratuita su Steam","gaming"],
 ["Tower Tactics II arriva su Steam con 190 carte","gaming"],
 ["CORSAIR HS80 cuffie per il gaming competitivo","tech"],
 ["Nuovo gioco fantasy di uno studio indipendente","gaming","Il videogioco è un RPG narrativo sviluppato per PC."],
 ["Sharp introduce nuove stampanti per il settore gaming","tech"]
];
for(const [title,expected,lead] of samples){
 const value=classify(title,lead||"");
 assert.equal(value,expected,title+": expected "+expected+" but got "+value);
}
const chronological=source.split("// HOME_PUBLICATION_ORDER_START")[1]?.split("// HOME_PUBLICATION_ORDER_END")[0];
assert(chronological&&chronological.includes("homePublicationTime"),"Home publication date parser missing");
const order=vm.runInNewContext(chronological+"\nhomePublicationTime",{},{timeout:1600});
for(const [newer,older] of [
 ["13 ottobre 2026","12 ottobre 2026"],
 ["12 ottobre 2026","11 ottobre 2026"],
 ["2026-10-13T12:30:00Z","2026-10-13T08:00:00Z"],
 ["13/10/2026","11/10/2026"],
 ["2026-10-14","2026-10-13"]
]) assert(order(newer)>order(older),newer+" must appear above "+older);
assert(source.includes("orderHomeColumn(tech)")&&source.includes("orderHomeColumn(gaming)"),
 "Both Tech and Gaming must be ordered by publication");
const templateLiteral=source.match(/const fragmentHTML=("(?:\\.|[^"\\])*");/);
assert(templateLiteral,"Home layout template must exist");
const homeTemplate=JSON.parse(templateLiteral[1]);
assert(!homeTemplate.includes("ztpMoreGaming")&&!homeTemplate.includes("ztp-gaming-extra"),
 "Obsolete fixed Gaming articles must never outrank current YouTube Community news");
assert(!source.includes('oldArchive.querySelectorAll'),"Static Gaming article reinsertion must be removed");
assert(source.includes("function balance()") &&
 !source.includes('col.style.justifyContent="space-between"') &&
 source.includes('col.style.removeProperty(p)'),
 "Gaming articles must flow contiguously without forced height or space-between");
assert(source.includes('ztpGamingReviews') && source.includes('ztHomeExtra') && source.includes('RECENSIONI TECH'),
 "Homepage must restore Gaming reviews below news, Extra next to Guide and three Tech reviews");
const css=fs.readFileSync("zt-home-gap-fix-20261014.css","utf8");
assert(css.includes(".ztp-news-tech") && css.includes("-webkit-line-clamp:3") &&
 css.includes("#ztp-guide-extra") && css.includes(".ztp-gaming-reviews"),
 "Updated Home must preserve Tech descriptions, Guide/Extra and Gaming review styles");
const index=fs.readFileSync("index.html","utf8");
const feed=index.split("<!-- ARTICLE_FEED_START -->")[1]?.split("<!-- ARTICLE_FEED_END -->")[0];
assert(feed,"canonical Home feed missing");
const rows=[...feed.matchAll(/<article\b[^>]*class="article-row"[\s\S]*?<h3><a[^>]*>(.*?)<\/a><\/h3>/g)];
const published=[...feed.matchAll(/<article\b[^>]*class="article-row"[^>]*data-published-at="([^"]+)"/g)]
 .map(m=>order(m[1]));
assert.equal(published.length,rows.length,"Every Home news card must include its real publication timestamp");
for(let n=1;n<published.length;n++)assert(published[n-1]>=published[n],
 "Canonical Home news must be newest-first at indexes "+(n-1)+" and "+n);

assert(rows.length>=10,"Home must contain at least 10 current articles");
const categories=rows.map(x=>classify(x[1].replace(/&amp;/g,"&").replace(/&quot;/g,'"')));
const gaming=categories.filter(x=>x==="gaming").length;
const tech=categories.filter(x=>x==="tech").length;
assert(gaming>=3&&tech>=3,"Both categories must receive actual news");
console.log("PASS topic split on "+samples.length+" fixtures and "+rows.length+" current Home stories: "+tech+" Tech, "+gaming+" Gaming");
