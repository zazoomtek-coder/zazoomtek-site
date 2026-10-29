#!/usr/bin/env python3
"""Verify the real compiled Home structure and CSS in Chromium without deployment."""
import html, json, re, shutil, subprocess
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread

root=Path(__file__).resolve().parents[1]/"dist"
page=root/"index.html"
chrome=next((p for n in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(n))),None)
assert chrome, "Chrome/Chromium not installed; do not claim a geometry pass"
original=page.read_text(encoding="utf-8")
# The two large Gaming cards must contain ONLY photo, heading, and date.
lead_html=re.search(r'<div class="gaming-magazine-leads">(.*?)</div><div class="gaming-magazine-list">', original, re.S)
assert lead_html, "Missing two Gaming leaders"
lead_html=lead_html.group(1)
assert lead_html.count('class="gaming-magazine-lead-image"')==2, "Expected two lead covers"
assert lead_html.count('class="gaming-magazine-date"')==2, "Expected two lead dates"
for extra in ('gaming-magazine-badge','gaming-magazine-byline','gaming-magazine-excerpt','Redazione ZazoomTek'):
 assert extra not in lead_html, "Unexpected label/excerpt/author in lead: "+extra
print("GAMING CLEAN PASS: 2 foto, 2 titoli, 2 date; zero badge/autore/descrizione",flush=True)

script="""<script>
addEventListener("load",()=>setTimeout(()=>{
 const $=s=>document.querySelector(s), $$=s=>Array.from(document.querySelectorAll(s));
 const rect=x=>{const r=x.getBoundingClientRect();return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}};
 const top=$$(".home-column .news-tech-top-grid .news-tech-card-small");
 const middle=$$(".home-column .news-tech-lead-grid .news-tech-card-large");
 const bottom=$$(".home-column .news-tech-bottom-grid .news-tech-card-small");
 const gaming=$$(".home-column .gaming-magazine .gaming-magazine-leads .gaming-magazine-lead");
 const gamingSmall=$$(".home-column .gaming-magazine .gaming-magazine-list .gaming-magazine-item");
 const boxes=$$(".home-sidebar .compact-editorial-box");
 const firstRows=boxes.map(box=>box.querySelector(".editorial-row:first-child .editorial-thumb"));
 const otherRows=boxes.map(box=>box.querySelector(".editorial-row:nth-child(2) .editorial-thumb")).filter(Boolean);
 const data={
 tech:[top.length,middle.length,bottom.length],
 techOrder:top.concat(middle,bottom).map(x=>x.querySelector("a.news-tech-cover")?.getAttribute("href")),
 techTop:top.map(rect),techMiddle:middle.map(rect),techBottom:bottom.map(rect),
 gaming:[gaming.length,gamingSmall.length],
 gamingBigLinks:gaming.map(x=>x.querySelector("a.gaming-magazine-lead-image")?.getAttribute("href")),
 gamingSmallLinks:gamingSmall.map(x=>x.querySelector("a.gaming-magazine-thumb")?.getAttribute("href")),
 gamingBigRects:gaming.map(rect),
 sidebarBoxes:boxes.length,
 sidebarFirstWidth:firstRows.filter(Boolean).map(x=>rect(x).w),
 sidebarFirstHeight:firstRows.filter(Boolean).map(x=>rect(x).h),
 sidebarNextWidth:otherRows.map(x=>rect(x).w),
 viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,
 techColumns:getComputedStyle($(".home-column .news-tech-top-grid")).gridTemplateColumns,
 centerColumns:getComputedStyle($(".home-column .news-tech-lead-grid")).gridTemplateColumns
 };
 const pre=document.createElement("pre");pre.id="zzt-layout-probe";pre.textContent=JSON.stringify(data);document.body.append(pre);
},600));
</script>"""
page.write_text(original.replace("</body>",script+"</body>"),encoding="utf-8")
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 for width in (1500,390):
  link=f"http://127.0.0.1:{server.server_address[1]}/index.html"
  args=[chrome,"--headless=new","--no-sandbox","--disable-gpu","--disable-dev-shm-usage","--disable-extensions","--hide-scrollbars","--virtual-time-budget=5500",f"--window-size={width},1020","--dump-dom",link]
  r=subprocess.run(args,text=True,capture_output=True,timeout=65)
  assert r.returncode==0,r.stderr[-2000:]
  m=re.search(r'<pre id="zzt-layout-probe">(.*?)</pre>',r.stdout,re.S)
  assert m,("Browser probe missing",r.stdout[-1500:])
  d=json.loads(html.unescape(m.group(1)))
  assert d["tech"]==[3,2,3],d
  assert d["gaming"]==[2,4],d
  assert len(set(d["techOrder"]))==8,d
  assert len(set(d["gamingBigLinks"]+d["gamingSmallLinks"]))==6,d
  assert set(d["techOrder"]).isdisjoint(d["gamingBigLinks"]+d["gamingSmallLinks"]),d
  assert d["sidebarBoxes"]>=3,d
  assert len(d["sidebarFirstWidth"])==d["sidebarBoxes"],d
  assert len(d["sidebarNextWidth"])>=3,d
  assert d["scrollWidth"]<=d["viewport"]+2,("Horizontal overflow",d)
  if width==1500:
   assert len(set(x["y"] for x in d["techTop"]))==1,d
   assert len(set(x["y"] for x in d["techMiddle"]))==1,d
   assert len(set(x["y"] for x in d["techBottom"]))==1,d
   assert d["techTop"][0]["y"]<d["techMiddle"][0]["y"]<d["techBottom"][0]["y"],d
   assert all(w>nextw for w,nextw in zip(d["sidebarFirstWidth"],d["sidebarNextWidth"])),d
   assert d["gamingBigRects"][0]["y"]<d["gamingBigRects"][1]["y"],d
  print(f"REAL CHROME PASS {width}px:",json.dumps({k:d[k] for k in ("tech","gaming","sidebarBoxes","scrollWidth","viewport","gamingBigRects","techTop","techMiddle","techBottom")},ensure_ascii=False),flush=True)
finally:
 server.shutdown()
 page.write_text(original,encoding="utf-8")
