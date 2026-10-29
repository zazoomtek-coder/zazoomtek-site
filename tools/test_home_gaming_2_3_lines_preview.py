#!/usr/bin/env python3
"""Run real Chromium headless on compiled full Home: check title clamps and geometry."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from threading import Thread
import subprocess, shutil, re, json, html

root=Path(__file__).resolve().parents[1]/"dist"
page=root/"index.html"
chrome=next((p for name in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(name))),None)
assert chrome,"Headless Chromium unavailable"
original=page.read_text(encoding="utf-8")
# Use exact Home containers: no SEO/page-content mutation in output or ZIP.
assert original.count("gaming-magazine-lead-image")==2, "Not exactly two large Gaming covers"
test_js=r'''<script id="gaming-layout-verification">
setTimeout(() => {
 const $$=(s)=>Array.from(document.querySelectorAll(s));
 const big=$$(".home-layout .home-column .gaming-magazine-leads .gaming-magazine-lead h3 > a");
 const small=$$(".home-layout .home-column .gaming-magazine-list .gaming-magazine-item h3 > a");
 function info(a) {
  const s=getComputedStyle(a);
  const h=a.getBoundingClientRect().height;
  return {display:s.display,clamp:s.webkitLineClamp,height:Math.round(h*10)/10,
    lineHeight:Math.round(parseFloat(s.lineHeight)*10)/10,
    textLength:a.textContent.trim().length,
    text:a.textContent.trim(), href:a.getAttribute("href"), overflow:s.overflow};
 }
 const x={big:big.map(info),small:small.map(info),
  viewport:document.documentElement.clientWidth,
  contentWidth:document.documentElement.scrollWidth,
  bigDates:$$(".home-layout .home-column .gaming-magazine-leads .gaming-magazine-date").length,
  fullTech:[$$(".news-tech-top-grid .news-tech-card").length,
            $$(".news-tech-lead-grid .news-tech-card").length,
            $$(".news-tech-bottom-grid .news-tech-card").length]
 };
 const probe=document.createElement("pre");
 probe.id="gaming-css-verify";probe.textContent=JSON.stringify(x);document.body.appendChild(probe);
},500);
</script>'''
page.write_text(original.replace("</body>",test_js+"</body>"),encoding="utf-8")
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 for width in (1480,390):
  args=[chrome,"--headless=new","--no-sandbox","--disable-gpu",
        "--disable-extensions","--disable-dev-shm-usage","--hide-scrollbars",
        "--virtual-time-budget=5500",f"--window-size={width},1020",
        "--dump-dom",f"http://127.0.0.1:{server.server_address[1]}/index.html"]
  v=subprocess.run(args,text=True,capture_output=True,timeout=65)
  assert v.returncode==0,v.stderr[-1000:]
  m=re.search(r'<pre id="gaming-css-verify">(.*?)</pre>',v.stdout,re.S)
  assert m,("No browser probe",v.stdout[-500:])
  d=json.loads(html.unescape(m.group(1)))
  assert len(d["big"])==2,d
  assert len(d["small"])==4,d
  assert d["bigDates"]==2,d
  assert d["fullTech"]==[3,2,3],d
  assert d["contentWidth"]<=d["viewport"]+3,("Home overflow",d)
  for category,rows,lines in (("big",d["big"],2),("small",d["small"],3)):
   for item in rows:
    assert item["display"] in ("-webkit-box","flow-root"),(category,item) # Chromium maps prefixed box to flow-root with line-clamp
    assert item["clamp"]==str(lines),(category,item)
    assert item["overflow"]=="hidden",(category,item)
    assert item["height"]<=item["lineHeight"]*lines+2,(category,item)
    assert len(item["text"])>=20 and item["href"].startswith("/"),(category,item)
  print("CHROME PASS",width,"px",json.dumps({key:d[key] for key in ("big","small","fullTech","viewport","contentWidth")},ensure_ascii=False),flush=True)
finally:
 server.shutdown()
 page.write_text(original,encoding="utf-8")
