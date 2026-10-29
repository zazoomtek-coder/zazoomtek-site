#!/usr/bin/env python3
"""Assert real pagewide social links, layout alignment and no mobile overflow in Chromium."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from threading import Thread
import subprocess,re,html,json,shutil

root=Path(__file__).resolve().parents[1]/"dist"
chrome=next((p for n in ("google-chrome","chromium","chromium-browser") if (p:=shutil.which(n))),None)
assert chrome,"Chrome/Chromium missing: cannot validate actual layout"
pages=["index.html","news.html","recensioni.html","notizie-web.html"]
pages+=sorted(p.name for p in root.glob("notizia-web-*.html"))[:1]
pages+=sorted(p.name for p in root.glob("community-*.html"))[:1]
assert len(pages)==6,pages
expected={"ticker-social-youtube":"https://www.youtube.com/@ZazoomTek",
          "ticker-social-tiktok":"https://www.tiktok.com/@zazoomtek"}
for name in pages:
 source=(root/name).read_text(encoding="utf-8")
 assert source.count('class="ticker-social-button ticker-social-youtube"')==1,(name,"missing YouTube")
 assert source.count('class="ticker-social-button ticker-social-tiktok"')==1,(name,"missing TikTok")
 for link in expected.values():
  assert link in source,(name,link)
 assert '<nav class="ticker-social"' in source
 assert 'target="_blank" rel="noopener noreferrer"' in source
print("ALL SIX PAGES HAVE BOTH REAL SOCIAL LINKS",pages,flush=True)

probe=r"""<script>
window.addEventListener("load",()=>setTimeout(()=>{
 const q=x=>document.querySelector(x),rect=x=>{
  const r=x.getBoundingClientRect();
  return {left:Math.round(r.left),right:Math.round(r.right),
   top:Math.round(r.top),bottom:Math.round(r.bottom),
   width:Math.round(r.width),height:Math.round(r.height)};
 };
 const nav=q(".ticker-social"), yt=q(".ticker-social-youtube"), tt=q(".ticker-social-tiktok"),
 strip=q(".breaking-ticker-inner"),text=q(".ticker-viewport"),label=q(".breaking-label");
 const data={social:rect(nav),yt:rect(yt),tt:rect(tt),strip:rect(strip),
  ticker:rect(text),label:rect(label),socialDisplay:getComputedStyle(nav).display,
  socialBg:getComputedStyle(yt).backgroundColor,
  ytUrl:yt.getAttribute("href"),ttUrl:tt.getAttribute("href"),
  ariaYT:yt.getAttribute("aria-label"),ariaTT:tt.getAttribute("aria-label"),
  ytNewTab:yt.getAttribute("target"),ttNewTab:tt.getAttribute("target"),
  ytRel:yt.getAttribute("rel"),ttRel:tt.getAttribute("rel"),
  innerWidth:document.documentElement.clientWidth,
  scrollWidth:document.documentElement.scrollWidth,
  tickerCount:document.querySelectorAll(".ticker-link").length};
 const p=document.createElement("pre");p.id="zzt-social-audit";p.textContent=JSON.stringify(data);document.body.append(p);
},650));
</script>"""
server=ThreadingHTTPServer(("127.0.0.1",0),partial(SimpleHTTPRequestHandler,directory=str(root)))
Thread(target=server.serve_forever,daemon=True).start()
try:
 for width in (1460,768,390,320):
  page=root/"index.html"
  original=page.read_text(encoding="utf-8")
  page.write_text(original.replace("</body>",probe+"</body>"),encoding="utf-8")
  try:
   url=f"http://127.0.0.1:{server.server_address[1]}/index.html"
   args=[chrome,"--headless=new","--no-sandbox","--disable-gpu",
    "--disable-extensions","--disable-dev-shm-usage","--hide-scrollbars",
    "--virtual-time-budget=6000",f"--window-size={width},1000","--dump-dom",url]
   out=subprocess.run(args,text=True,capture_output=True,timeout=80)
   assert out.returncode==0,out.stderr[-1600:]
   match=re.search(r'<pre id="zzt-social-audit">(.*?)</pre>',out.stdout,re.S)
   assert match,("Browser probe missing",out.stdout[-1200:])
   d=json.loads(html.unescape(match.group(1)))
   assert d["ytUrl"]==expected["ticker-social-youtube"],d
   assert d["ttUrl"]==expected["ticker-social-tiktok"],d
   assert d["ytNewTab"]==d["ttNewTab"]=="_blank",d
   assert "noopener" in d["ytRel"] and "noopener" in d["ttRel"],d
   assert "YouTube" in d["ariaYT"] and "TikTok" in d["ariaTT"],d
   assert d["tickerCount"]>=10,d
   assert d["socialDisplay"]=="flex",d
   assert d["yt"]["width"]>=26 and d["tt"]["width"]>=26,d
   assert d["yt"]["top"]>=d["strip"]["top"]-3,d
   assert d["tt"]["right"]<=d["strip"]["right"]+3,d
   assert d["ticker"]["right"]<=d["yt"]["left"]+3,("ticker overlaps icons",d)
   assert d["scrollWidth"]<=d["innerWidth"]+2,("horizontal overflow",d)
   print("SOCIAL LINKS CHROME PASS",width,json.dumps(d,ensure_ascii=False),flush=True)
  finally:
   page.write_text(original,encoding="utf-8")
finally:
 server.shutdown()
