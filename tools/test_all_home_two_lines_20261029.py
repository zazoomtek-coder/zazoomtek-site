#!/usr/bin/env python3
"""Real browser check of 2-line card titles across Home; editorial rail untouched."""
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import json,html,re,shutil,subprocess
root=Path(__file__).resolve().parents[1]/"dist"
page=root/"index.html"
chrome=next((p for name in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(name))),None)
assert chrome,"Chromium unavailable"
original=page.read_text(encoding="utf-8")
probe=r"""<script>
window.addEventListener("load",()=>setTimeout(()=>{
 const $$=(s)=>Array.from(document.querySelectorAll(s)),style=e=>getComputedStyle(e);
 const headings=$$("main.wrap .featured-wide .spotlight-grid .tile-title,main.wrap .home-layout > .home-column article h3 > a");
 const sidebar=$$("main.wrap .home-layout .home-sidebar .editorial-row-copy a strong");
 const subsets={
  spotlight:$$(".featured-wide .spotlight-grid .tile-title").length,
  tech:$$(".home-column .news-tech-showcase article h3 > a").length,
  gaming:$$(".home-column .gaming-magazine article h3 > a").length,
  reviews:$$(".home-column .home-review-web-grid article h3 > a").length,
  specials:$$(".home-column .specials-showcase article h3 > a").length,
  guidesExtras:$$(".home-column .feature-pair article h3 > a").length,
  videos:$$(".home-column .video-magazine article h3 > a").length,
  webNews:$$(".home-column .web-news-grid:not(.home-review-web-grid) article h3 > a").length
 };
 const entries=headings.map(e=>{
  const x=style(e),rect=e.getBoundingClientRect(),lh=parseFloat(x.lineHeight);
  return {className:e.className,clamp:x.webkitLineClamp,display:x.display,
          height:Math.round(rect.height*10)/10,
          lineHeight:Number.isFinite(lh)?Math.round(lh*10)/10:null,
          fullTextLength:e.textContent.trim().length,
          overflow:x.overflow,whiteSpace:x.whiteSpace};
 });
 const rail=sidebar.map(e=>({size:style(e).fontSize,weight:style(e).fontWeight,
                            family:style(e).fontFamily,
                            matchesNewSelector:e.matches("main.wrap .home-layout > .home-column article h3 > a")}));
 const data={subsets,titles:entries,sidebar:rail,clientWidth:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth};
 const pre=document.createElement("pre");pre.id="zzt-full-home-clamp-probe";pre.textContent=JSON.stringify(data);document.body.append(pre);
},650));
</script>"""
page.write_text(original.replace("</body>",probe+"</body>"),encoding="utf-8")
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 for width in (1440,390):
  url=f"http://127.0.0.1:{server.server_address[1]}/index.html"
  args=[chrome,"--headless=new","--no-sandbox","--disable-gpu","--disable-extensions",
        "--disable-dev-shm-usage","--hide-scrollbars","--virtual-time-budget=5500",
        f"--window-size={width},1020","--dump-dom",url]
  result=subprocess.run(args,text=True,capture_output=True,timeout=70)
  assert result.returncode==0,result.stderr[-1700:]
  m=re.search(r'<pre id="zzt-full-home-clamp-probe">(.*?)</pre>',result.stdout,re.S)
  assert m,"No Chrome verification output"
  data=json.loads(html.unescape(m.group(1)))
  req={"spotlight":5,"tech":8,"gaming":6,"reviews":3,"specials":1,
       "guidesExtras":2,"videos":4,"webNews":4}
  for category,minimum in req.items():
   assert data["subsets"][category]>=minimum,(category,data["subsets"])
  assert len(data["titles"])>=30,len(data["titles"])
  assert len(data["sidebar"])>=1,("Editorial sidebar unexpectedly absent",data)
  assert not any(x["matchesNewSelector"] for x in data["sidebar"]),data["sidebar"]
  assert data["scrollWidth"]<=data["clientWidth"]+2,("Overflow",data["scrollWidth"],data["clientWidth"])
  for n,e in enumerate(data["titles"]):
   assert e["clamp"]=="2",(width,n,e)
   assert e["overflow"]=="hidden",(width,n,e)
   assert e["whiteSpace"]=="normal",(width,n,e)
   if e["lineHeight"] is not None and e["height"]>0:
    assert e["height"]<=e["lineHeight"]*2+3,(width,n,e)
  print("HOME TWO LINE PASS",width,
        "titles",len(data["titles"]),
        "sections",json.dumps(data["subsets"]),
        "editorial_side_titles_untouched",len(data["sidebar"]),
        "overflow",data["scrollWidth"]-data["clientWidth"],flush=True)
finally:
 server.shutdown()
 page.write_text(original,encoding="utf-8")
