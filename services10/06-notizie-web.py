#!/usr/bin/env python3
"""Render Notizie dal web: one lead on left, four small right, no 'Vedi tutte'.

Only this section's HTML/CSS/placement is edited. It keeps the approved
source list and does not touch YouTube, highlights, articles or review cards.
"""
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STYLE_ID="zt-services10-webnews-layout"
SCRIPT_ID="zt-services10-webnews-place"

STYLE='''<style id="zt-services10-webnews-layout">
#zt-webnews-home{clear:both;margin:18px 0;border:1px solid #ddd;border-radius:0;background:white}
#zt-webnews-home .zt-webnews-head{background:#1e1e1e;color:white;min-height:46px}
#zt-webnews-home .zt-webnews-head h2{color:white;background:#d51232;display:inline-block;margin:0;padding:13px 18px;font:900 15px/1.3 Arial,sans-serif}
#zt-webnews-home .zt-webnews-grid{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,1fr);grid-template-rows:repeat(4,minmax(95px,auto));gap:0;padding:9px}
#zt-webnews-home .zt-webnews-item{display:grid;grid-template-columns:94px minmax(0,1fr);align-items:center;gap:10px;padding:8px;border-bottom:1px solid #eee;text-decoration:none;min-width:0}
#zt-webnews-home .zt-webnews-item img{width:94px;height:78px;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child{grid-column:1;grid-row:1/5;display:block;padding:5px 13px 8px 5px;border-right:1px solid #eee;border-bottom:0}
#zt-webnews-home .zt-webnews-item:first-child img{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-info{display:block;margin:9px 3px}
#zt-webnews-home .zt-webnews-item:first-child strong{font-size:18px;line-height:1.35}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-excerpt{display:block;color:#666;font-size:13px;line-height:1.45;margin:7px 0}
#zt-webnews-home .zt-webnews-item:not(:first-child) .zt-webnews-excerpt{display:none}
@media(max-width:650px){#zt-webnews-home .zt-webnews-grid{display:flex;flex-direction:column}
#zt-webnews-home .zt-webnews-item:first-child{border-right:0;border-bottom:1px solid #eee}
#zt-webnews-home .zt-webnews-item:first-child img{height:auto}}
</style>'''
SCRIPT='''<script id="zt-services10-webnews-place">
(function(){
  function place(){
    const block=document.getElementById("zt-webnews-home");
    const videoExplorer=document.querySelector(".ztp-top-videos");
    if(!block||!videoExplorer||!videoExplorer.parentNode)return false;
    if(block.previousElementSibling!==videoExplorer)
      videoExplorer.insertAdjacentElement("afterend",block);
    return true;
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",place);
  else place();
  const observer=new MutationObserver(function(){if(place())observer.disconnect()});
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(function(){observer.disconnect()},15000);
})();
</script>'''

def panel(items):
    tiles=[]
    for item in items[:5]:
        if not isinstance(item,dict):continue
        url=str(item.get("url") or "")
        cover=str(item.get("image") or "")
        title=str(item.get("original_title") or item.get("title") or "")
        excerpt=str(item.get("excerpt") or "")
        origin=str(item.get("source") or "")
        if not url.startswith("https://") or not cover or not title:continue
        tiles.append('<a class="zt-webnews-item" href="'+html.escape(url,quote=True)+
            '" target="_blank" rel="noopener noreferrer"><img src="'+
            html.escape(cover,quote=True)+'" alt="'+html.escape(title,quote=True)+
            '" loading="lazy"><span class="zt-webnews-info"><small>'+
            html.escape(origin)+'</small><strong>'+html.escape(title)+
            '</strong><span class="zt-webnews-excerpt">'+html.escape(excerpt)+
            '</span></span></a>')
    return ('<section id="zt-webnews-home" class="zt-webnews-home" aria-label="NOTIZIE DAL WEB">'
        '<header class="zt-webnews-head"><h2>NOTIZIE DAL WEB</h2></header>'
        '<div class="zt-webnews-grid">'+''.join(tiles)+'</div></section>'),len(tiles)

def update(root:Path=ROOT):
    news=root/"notizie-dal-web.json"
    home=root/"index.html"
    if not news.is_file() or not home.is_file():return 0
    try:items=json.loads(news.read_text(encoding="utf-8")).get("items",[])
    except (ValueError,AttributeError):return 0
    section,count=panel(items)
    if not count:return 0
    source=home.read_text(encoding="utf-8")
    pattern=r'<section\b[^>]*id="zt-webnews-home"[^>]*>[\s\S]*?</section>'
    source,n=re.subn(pattern,lambda _: section,source,count=1)
    if not n:return 0
    # Previous iterations had conflicting CSS and relocation scripts.
    for ident in ("zt-draft-webnews-center",STYLE_ID):
        source=re.sub(r'<style id="'+ident+r'">[\s\S]*?</style>',"",source)
    for ident in ("zt-draft-webnews-relocate",SCRIPT_ID):
        source=re.sub(r'<script id="'+ident+r'">[\s\S]*?</script>',"",source)
    source=source.replace("</head>",STYLE+"\n</head>",1)
    source=source.replace("</body>",SCRIPT+"\n</body>",1)
    home.write_text(source,encoding="utf-8")
    print("Notizie dal web:",count,"stories, one lead + four compact")
    return count

if __name__=="__main__":
    update()
