#!/usr/bin/env python3
"""Check literal three-dot truncation ONLY when necessary, using real Chrome."""
import html,json,re,shutil,subprocess
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
root=Path(__file__).resolve().parents[1]/"dist"
page=root/"index.html"
chrome=next((p for name in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(name))),None)
assert chrome,"Chrome missing"
raw=page.read_text(encoding="utf-8")
assert "news-tech-top-grid" in raw and "gaming-magazine-lead-secondary" in raw
script=r"""<script>
window.__homeOriginal=Array.from(document.querySelectorAll(
 "main.wrap .featured-wide .spotlight-grid .tile-title,"+
 "main.wrap .home-layout > .home-column article h3 > a"
)).map(a=>({text:a.textContent.trim(),font:getComputedStyle(a).fontFamily,
 size:getComputedStyle(a).fontSize,weight:getComputedStyle(a).fontWeight}));
window.addEventListener("load",()=>setTimeout(()=>{
 const links=Array.from(document.querySelectorAll(
  "main.wrap .featured-wide .spotlight-grid .tile-title,"+
  "main.wrap .home-layout > .home-column article h3 > a"
 ));
 const arr=links.map((a,i)=>{
  const original=window.__homeOriginal[i];
  const style=getComputedStyle(a);
  const range=document.createRange();range.selectNodeContents(a);
  const tops=[];
  for(const r of range.getClientRects())
   if(r.height>0.5&&r.width>0.5&&!tops.some(y=>Math.abs(y-r.top)<1))tops.push(r.top);
  return {full:original.text,now:a.textContent.trim(),
   truncated:a.dataset.homeTitleClipped,lines:tops.length,
   originalFont:original.font,font:style.fontFamily,originalSize:original.size,size:style.fontSize,
   originalWeight:original.weight,weight:style.fontWeight,
   title:a.getAttribute("title"),label:a.getAttribute("aria-label"),
   height:a.getBoundingClientRect().height,lineHeight:parseFloat(style.lineHeight)};
 });
 const side=Array.from(document.querySelectorAll(".home-sidebar .editorial-row-copy a strong"));
 const result={headlines:arr,sidebar:side.length,viewport:document.documentElement.clientWidth,
  scrollWidth:document.documentElement.scrollWidth};
 let p=document.createElement("pre");p.id="real-three-dot-check";p.textContent=JSON.stringify(result);document.body.appendChild(p);
},700));
</script>"""
page.write_text(raw.replace("</body>",script+"</body>"),encoding="utf-8")
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 for width in (1500,390):
  args=[chrome,"--headless=new","--no-sandbox","--disable-gpu",
        "--disable-extensions","--disable-dev-shm-usage","--hide-scrollbars",
        "--virtual-time-budget=7000",f"--window-size={width},1000","--dump-dom",
        f"http://127.0.0.1:{server.server_address[1]}/index.html"]
  v=subprocess.run(args,text=True,capture_output=True,timeout=70)
  assert v.returncode==0,v.stderr[-2000:]
  m=re.search(r'<pre id="real-three-dot-check">(.*?)</pre>',v.stdout,re.S)
  assert m,("No Chrome probe",v.stdout[-1600:])
  data=json.loads(html.unescape(m.group(1)))
  assert len(data["headlines"])>=35,len(data["headlines"])
  assert data["sidebar"]>=3,"Editorial sidebars unavailable"
  assert data["scrollWidth"]<=data["viewport"]+2,"Horizontal overflow"
  short=0
  clipped=0
  for article in data["headlines"]:
   assert article["lines"]<=2,article
   assert article["font"]==article["originalFont"],article
   assert article["size"]==article["originalSize"],article
   assert article["weight"]==article["originalWeight"],article
   if article["truncated"]=="true":
    clipped+=1
    assert article["now"].endswith("..."),article
    assert not article["full"].endswith("..."),article
    assert article["now"]!=article["full"],article
    assert article["label"]==article["full"],article
    assert article["title"]==article["full"],article
   else:
    short+=1
    assert article["truncated"]=="false",article
    assert article["now"]==article["full"],article
  assert short>=2,("No complete short titles found",short)
  assert clipped>=4,("No long titles truncated",clipped)
  print("CHROME THREE DOTS PASS",width,"px;",len(data["headlines"]),"home headlines;",
        short,"whole titles NO dots;",clipped,"true truncations with ...;",
        data["sidebar"],"editorial sidebar headlines untouched; NO OVERFLOW",flush=True)
finally:
 server.shutdown()
 page.write_text(raw,encoding="utf-8")
