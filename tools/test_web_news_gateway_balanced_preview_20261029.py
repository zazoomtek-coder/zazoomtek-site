#!/usr/bin/env python3
from pathlib import Path
import re,shutil,subprocess,json,html
from threading import Thread
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler

root=Path(__file__).resolve().parents[1]/"dist"
pages=list(root.glob("notizia-web-*.html"))
assert len(pages)>=4,("too few Web News pages",len(pages))
for p in pages:
 data=p.read_text()
 assert data.count('class="web-gateway-card"')==3,(p.name,"wrong card count")
 assert data.index('class="web-gateway-source-link"')<data.index('class="web-gateway-related"'),p.name
 assert 'class="inner-layout web-gateway-layout"' in data,p.name
 assert 'Ultime news' in data or 'ULTIME NEWS' in data,p.name
 assert 'class="web-gateway-primary"' not in data or data.index('class="web-gateway-primary"')<data.index('class="web-gateway-related"'),p.name
 print("WEB GATEWAY HTML PASS",p.name,flush=True)

chrome=next((p for n in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(n))),None)
assert chrome,"Chromium missing"
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
probe="""<script>
setTimeout(()=>{
const $$=s=>Array.from(document.querySelectorAll(s)),r=e=>e.getBoundingClientRect();
const c=$$$(.web-gateway-layout .web-gateway-card"),
side=$$$(.web-gateway-layout .inner-sidebar .editorial-row"),
visible=side.filter(e=>{const k=r(e);return k.height>0&&getComputedStyle(e).display!=="none"&&k.width>0;});
const rel=$$$(.web-gateway-layout .web-gateway-related"),source=$$$(.web-gateway-source-link");
const d={cards:c.length,cardY:c.map(e=>Math.round(r(e).y)),
 sourceY:source.map(e=>Math.round(r(e).y)),relatedY:rel.map(e=>Math.round(r(e).y)),
 sideVisible:visible.length,sideYs:visible.map(e=>Math.round(r(e).y)),sideBoxHeight:Math.round(r($(".web-gateway-layout .inner-sidebar")[0]).height),
 sidebarCount:$$$(.web-gateway-layout .compact-editorial-box").length,
 scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth};
 const pre=document.createElement("pre");pre.id="gateway-audit-result";pre.textContent=JSON.stringify(d);document.body.append(pre);
},700);
</script>"""
try:
 for width in (1450,390):
  p=pages[0]
  raw=p.read_text();p.write_text(raw.replace("</body>",probe+"</body>"))
  try:
   args=[chrome,"--headless=new","--no-sandbox","--disable-gpu","--disable-extensions","--disable-dev-shm-usage","--virtual-time-budget=6000",f"--window-size={width},1000","--dump-dom",f"http://127.0.0.1:{server.server_address[1]}/{p.name}"]
   z=subprocess.run(args,text=True,capture_output=True,timeout=75)
   assert z.returncode==0,z.stderr[-700:]
   m=re.search(r'<pre id="gateway-audit-result">(.*?)</pre>',z.stdout,re.S)
   assert m,"No browser probe"
   d=json.loads(html.unescape(m.group(1)))
   assert d["cards"]==3,d
   assert d["sidebarCount"]==1,d
   assert d["relatedY"][0]>d["sourceY"][0],d
   assert d["scrollWidth"]<=d["clientWidth"]+3,d
   if width==1450:
    assert d["sideVisible"]>=3,("sidebar still shows only 1 item",d)
    assert len(set(d["cardY"]))==1,("three card rows not aligned",d)
   print("WEB NEWS CHROME PASS",width,json.dumps(d),flush=True)
  finally:p.write_text(raw)
finally:server.shutdown()
