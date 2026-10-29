#!/usr/bin/env python3
"""Test current ZazoomTek article sidebar policy in real Chromium, no deploy."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
import subprocess,shutil,html,json,re

root=Path(__file__).resolve().parents[1]/"dist"
htmls=list(root.glob("*.html"))
long=[p for p in htmls if 'data-rail-mode="split"' in p.read_text()]
shortnews=[p for p in htmls if p.name.startswith("news-") and
           p.name not in ("news-tech.html","news-gaming.html") and
           'data-rail-mode="split"' not in p.read_text() and
           'class="story-article"' in p.read_text()]
shortother=root/"contatti.html"
reviewlong=[p for p in long if "recensione" in p.name or "review" in p.name]
assert len(long)>=12,("Not enough long article/review pages",len(long))
assert len(reviewlong)>=3,("No long reviews",len(reviewlong))
assert len(shortnews)>=1,("No short News articles",len(shortnews))
assert shortother.is_file()
print("ARTICLE SIDE BAR SETS",len(long),"long",len(reviewlong),"reviews",len(shortnews),"short news",flush=True)

def items(page):
 h=page.read_text(encoding="utf-8")
 m=re.search(r'<aside class="sidebar inner-sidebar"([^>]+)>(.*?)</aside>',h,re.S)
 assert m,(page.name,"Missing sidebar")
 captions=re.findall(r'<div class="bar">.*?<h2[^>]*>([^<]+)</h2>',m.group(2),re.S)
 # Bar implementation may use other tags. Search visible bar link heading directly.
 if not captions:
  captions=re.findall(r'<h2[^>]*>(Ultime news|Ultime recensioni|Dalla redazione)</h2>',m.group(2),re.I)
 return m.group(1),captions,h

for file in long:
 flags,titles,h=items(file)
 assert 'data-rail-mode="split"' in flags,(file.name,flags)
 assert len(re.findall(r'class="box editorial-box compact-editorial-box"',h))==2,(file.name,"not exactly 2")
 assert "Ultime news" in h and "Dalla redazione" in h,(file.name,"missing long sections")
 assert '<aside class="inner-amazon-fill"' in h,(file.name,"Missing Amazon")
 assert '<section class="related"' in h,(file.name,"Missing related")
 assert 'https://link.amazon/A0dJXv9PO' in h
for file in shortnews:
 flags,titles,h=items(file)
 assert 'data-rail-mode="split"' not in flags,file.name
 assert 'Ultime recensioni' in h,(file.name,"no reviews")
 assert 'Ultime news' not in h,(file.name,"wrong rail")
 assert len(re.findall(r'class="box editorial-box compact-editorial-box"',h))==1,(file.name,"not one box")
flags,titles,h=items(shortother)
assert 'Ultime news' in h and 'Ultime recensioni' not in h and 'Dalla redazione' not in h
assert len(re.findall(r'class="box editorial-box compact-editorial-box"',h))==1
home=(root/"index.html").read_text()
assert 'data-rail-mode="split"' not in home
assert home.count('class="amazon-feature-box"')>=1
assert 'news-tech-top-grid' in home and 'gaming-magazine-lead-secondary' in home
assert 'function fitHomeTitles()' in (root/"assets/js/site.js").read_text()
print("STATIC RAIL POLICY PASS",len(long),"long",len(shortnews),"short news; Amazon+Home unchanged",flush=True)

chrome=next((v for n in ("google-chrome","chromium","chromium-browser") if (v:=shutil.which(n))),None)
assert chrome,"Chromium browser not installed"
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
probe=r"""<script>
addEventListener("load",()=>setTimeout(()=>{
 let el=s=>document.querySelector(s),all=s=>Array.from(document.querySelectorAll(s));
 let box=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height,left:r.left,right:r.right}};
 let central=el(".inner-layout .inner-column"), aside=el(".inner-layout .inner-sidebar");
 let panels=all(".inner-layout .inner-sidebar .compact-editorial-box");
 let data={mode:aside?.dataset.railMode||"single",central:box(central),aside:box(aside),
  panels:panels.map(p=>({heading:p.querySelector(".bar")?.textContent?.trim().slice(0,90),
    rect:box(p),hidden:p.hidden,rows:Array.from(p.querySelectorAll(".editorial-row"))
     .filter(x=>!x.hidden && getComputedStyle(x).display!=="none")
     .map(x=>box(x))})),
  related:el(".inner-layout>.related")?box(el(".inner-layout>.related")):null,
  amazon:el(".inner-layout>.inner-amazon-fill")?box(el(".inner-layout>.inner-amazon-fill")):null,
  width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth
 };
 let pre=document.createElement("pre");pre.id="sidebar-preview-probe";pre.textContent=JSON.stringify(data);
 document.body.append(pre);
},950));
</script>"""
try:
 for page,width in ((reviewlong[0],1450),(long[0],1450),(shortnews[0],1450),(shortother,1450),(reviewlong[0],390)):
  original=page.read_text()
  page.write_text(original.replace("</body>",probe+"</body>"))
  try:
   args=[chrome,"--headless=new","--no-sandbox","--disable-gpu","--disable-extensions",
      "--disable-dev-shm-usage","--virtual-time-budget=6500",
      f"--window-size={width},1000","--dump-dom",
      f"http://127.0.0.1:{server.server_address[1]}/{page.name}"]
   result=subprocess.run(args,text=True,capture_output=True,timeout=75)
   assert result.returncode==0,(page.name,result.stderr[-1800:])
   m=re.search(r'<pre id="sidebar-preview-probe">(.*?)</pre>',result.stdout,re.S)
   assert m,("No probe",page.name,result.stdout[-1400:])
   d=json.loads(html.unescape(m.group(1)))
   assert d["scrollWidth"]<=d["width"]+2,("Horizontal overflow",page.name,d)
   if d["mode"]=="split":
    assert len(d["panels"])==2,(page.name,d)
    assert all(len(p["rows"])>=1 for p in d["panels"]),(page.name,d)
    if width>780:
     p1,p2=d["panels"]
     half=d["central"]["height"]/2
     assert abs(p2["rect"]["top"]-(d["central"]["top"]+half))<=20,(page.name,"not 50/50",d)
     assert d["aside"]["bottom"]<=d["central"]["bottom"]+6,(page.name,"rail overflows content",d)
     for p in d["panels"]:
      assert p["rows"][-1]["bottom"]<=p["rect"]["bottom"]+1,(page.name,"cropped thumbnail",d)
    assert d["amazon"] and d["related"],(page.name,"Amazon and related not present",d)
    if width>780:assert abs(d["amazon"]["top"]-d["related"]["top"])<=6,(page.name,"Amazon misaligned",d)
   else:
    assert len(d["panels"])==1,(page.name,d)
    if width>780:
     assert d["panels"][0]["rows"],(page.name,"No visible short page thumbnails",d)
     assert d["aside"]["bottom"]<=d["central"]["bottom"]+6,(page.name,"Short rail overflow",d)
   print("CHROME RAIL PASS",width,page.name,"mode",d["mode"],
         "rows",[len(x["rows"]) for x in d["panels"]],
         "page_height",round(d["central"]["height"]),
         "panel_start",[round(x["rect"]["top"]) for x in d["panels"]],
         flush=True)
  finally:
   page.write_text(original,encoding="utf-8")
finally:
 server.shutdown()
