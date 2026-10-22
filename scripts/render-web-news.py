#!/usr/bin/env python3
"""Render the real Home-only Notizie dal Web module below article pagination.
Relocate the existing GUIDE box after the news module as expressly requested.
No change to Home unless a complete validated five-story feed is available.
"""
from __future__ import annotations
from html import escape
import json
from pathlib import Path
import re
import sys
from web_news_editorial import render_extra, render_rail, CSS as FOLLOWUP_CSS
ROOT=Path(__file__).resolve().parents[1]
START="<!-- ZT_WEB_NEWS_START -->"
END="<!-- ZT_WEB_NEWS_END -->"
GUIDE_START="<!-- HOME_GUIDES_INSET_START -->"
GUIDE_END="<!-- HOME_GUIDES_INSET_END -->"
CSS_ID="zt-web-news-css"
CSS=r"""
/* Scoped external press-review module; does not alter existing editorial cards. */
.zt-webnews{margin:18px 0 25px;background:#fff;border:1px solid #e1e2e5;padding:0 0 14px;min-width:0}
.zt-webnews *{box-sizing:border-box}
.zt-webnews-head{display:flex;align-items:stretch;justify-content:space-between;background:#1c1c1e;color:#fff;min-height:47px}
.zt-webnews-head h2{margin:0;padding:12px 15px;font:900 16px/1.35 Arial,Helvetica,sans-serif;text-transform:uppercase;letter-spacing:.02em}
.zt-webnews-head a{display:flex;align-items:center;padding:0 17px;background:#d51232;color:white;text-decoration:none;font:800 11px/1.2 Arial,Helvetica,sans-serif}
.zt-webnews-grid{display:grid;grid-template-columns:minmax(0,1.04fr) minmax(0,1fr);gap:18px;padding:17px}
.zt-webnews-feature{display:flex;flex-direction:column;min-width:0}
.zt-webnews-image{display:block;aspect-ratio:16/9;overflow:hidden;background:#292e39}
.zt-webnews-image img{display:block;width:100%;height:100%;object-fit:cover;transition:transform .2s}
.zt-webnews-image:hover img{transform:scale(1.025)}
.zt-webnews-label{display:inline-block;background:#d51232;color:#fff;font:800 10px/1.4 Arial,sans-serif;text-transform:uppercase;padding:3px 8px;max-width:max-content;margin-top:10px}
.zt-webnews-feature h3{font:900 19px/1.24 Arial,sans-serif;margin:9px 0 8px;color:#151619;overflow-wrap:anywhere}
.zt-webnews-feature h3 a,.zt-webnews-side h3 a{color:inherit;text-decoration:none}
.zt-webnews-feature h3 a:hover,.zt-webnews-side h3 a:hover{color:#c51234}
.zt-webnews-feature p{margin:0;color:#50545c;font:13px/1.48 Arial,sans-serif}
.zt-webnews-source{display:block;color:#83858a;font:11px/1.5 Arial,sans-serif;margin:9px 0 0}
.zt-webnews-side{display:grid;grid-template-rows:repeat(4,minmax(0,1fr));gap:12px;min-width:0}
.zt-webnews-item{display:grid;grid-template-columns:minmax(100px,37%) minmax(0,1fr);gap:10px;align-items:start;min-width:0;padding-bottom:9px;border-bottom:1px solid #e9e9e9}
.zt-webnews-item:last-child{border-bottom:0;padding-bottom:0}
.zt-webnews-item .zt-webnews-image{aspect-ratio:16/9}
.zt-webnews-side h3{font:800 13px/1.3 Arial,sans-serif;color:#17191d;margin:0 0 4px;overflow-wrap:anywhere}
.zt-webnews-side p{margin:0;font:11px/1.4 Arial,sans-serif;color:#666;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.zt-webnews-side .zt-webnews-source{margin-top:4px;font-size:10px}
.zt-webnews-footer{font:11px/1.5 Arial,sans-serif;color:#777;margin:0 17px;padding-top:10px;border-top:1px solid #eee}
@media(max-width:1080px){.zt-webnews-grid{grid-template-columns:1fr}.zt-webnews-side{grid-template-columns:1fr 1fr;grid-template-rows:auto}.zt-webnews-item{grid-template-columns:minmax(95px,37%) minmax(0,1fr)}}
@media(max-width:640px){.zt-webnews-grid{padding:12px;gap:15px}.zt-webnews-side{grid-template-columns:1fr}.zt-webnews-feature h3{font-size:17px}.zt-webnews-head h2{font-size:14px}.zt-webnews-head a{font-size:10px}.zt-webnews-item{grid-template-columns:36% minmax(0,1fr)}}
"""

def render_cards(data):
    items=data["items"]
    assert len(items)==5,"Exactly 5 distinct news are required"
    assert len({i["id"] for i in items})==5
    for item in items:
        assert item["image"].startswith("/assets/notizie-dal-web/") and item["image"].endswith(".webp")
        assert item["url"].startswith("https://")
        assert len(item["excerpt"].split())<=50
    def link(item):return escape(item["url"],quote=True)
    def title(item):return escape(item["title"])
    def image(item):
        return '<a class="zt-webnews-image" href="'+link(item)+'" target="_blank" rel="nofollow noopener" aria-label="'+title(item)+'"><img src="'+escape(item["image"],quote=True)+'" alt="Illustrazione originale, notizia da '+escape(item["source"])+'" loading="lazy" decoding="async"></a>'
    lead=items[0]
    first='<article class="zt-webnews-feature">'+image(lead)+'<span class="zt-webnews-label">'+escape(lead["source"])+'</span><h3><a href="'+link(lead)+'" target="_blank" rel="nofollow noopener">'+title(lead)+'</a></h3><p>'+escape(lead["excerpt"])+'</p><span class="zt-webnews-source">Fonte: '+escape(lead["source"])+' · Apri la notizia originale ↗</span></article>'
    right=[]
    for v in items[1:]:
        right.append('<article class="zt-webnews-item">'+image(v)+'<div><h3><a href="'+link(v)+'" target="_blank" rel="nofollow noopener">'+title(v)+'</a></h3><p>'+escape(v["excerpt"])+'</p><span class="zt-webnews-source">Fonte: '+escape(v["source"])+'</span></div></article>')
    return START+'<section class="zt-webnews" id="ztWebNews" aria-labelledby="ztWebNewsTitle" data-web-news="independent-external-rss"><header class="zt-webnews-head"><h2 id="ztWebNewsTitle">NOTIZIE DAL WEB</h2><a href="#ztWebNewsCredits">LE FONTI ↗</a></header><div class="zt-webnews-grid">'+first+'<div class="zt-webnews-side">'+"".join(right)+'</div></div><p class="zt-webnews-footer" id="ztWebNewsCredits">Rassegna esterna · 5 notizie · titoli e sintesi rielaborati. Le immagini sono illustrazioni originali WebP, non fotografie delle testate. I collegamenti aprono gli articoli sui siti degli editori.</p></section>'+END

def apply(home,data,root=ROOT):
    # Use the real approved GUIDE markup unchanged, and render only true
    # existing EXTRA and right-rail editorial articles. No fabricated links.
    p=home.find(GUIDE_START);q=home.find(GUIDE_END,p)
    if p<0 or q<0:raise ValueError("Official GUIDE markers missing; refuse Home rewrite")
    q+=len(GUIDE_END)
    guide=home[p:q]
    card=render_cards(data).replace(START,"").replace(END,"")
    extra=render_extra(root)
    rail=render_rail(root)
    block=(
        START+'<section class="zt-webnews-followup" id="ztWebNewsFollowup" aria-label="Notizie dal Web e approfondimenti">'
        '<div class="zt-webnews-followup-main">'+card+'\n'+guide+'\n'+extra+
        '</div>'+rail+'</section>'+END
    )
    # Leave a literally identical article snapshot untouched, avoiding churn
    # and costly Pages builds when the RSS content has not changed.
    if START in home and END in home:
        present=home[home.index(START):home.index(END)+len(END)]
        if present==block and f'id="{CSS_ID}"' in home:
            return home
        home=home.replace(present,"",1)
    # Relocate GUIDE by its original preserved HTML; do not edit the card.
    p=home.find(GUIDE_START);q=home.find(GUIDE_END,p)
    if p>=0 and q>=p:
        home=home[:p]+home[q+len(GUIDE_END):]
    if f'id="{CSS_ID}"' in home:
        home=re.sub(r'<style id="'+CSS_ID+r'">[\s\S]*?</style>\s*',"",home,count=1)
    paginations=list(re.finditer(r'<!-- ARTICLE_PAGINATION_END -->\s*</section>',home,re.I))
    if len(paginations)!=1:raise ValueError("Expected exactly one genuine Home pagination")
    # Existing .layout contains the left paginated feed plus the approved
    # editorial right sidebar. Add a distinct 2-column follow-up immediately
    # after the closing .layout, not in either of its columns. No overlap.
    anchor=re.search(r'</aside>\s*</div>',home[paginations[0].end():],re.I)
    if not anchor:raise ValueError("Cannot identify safe closing anchor of Home 2-column layout")
    idx=paginations[0].end()+anchor.end()
    result=home[:idx]+'\n'+block+'\n'+home[idx:]
    if "</head>" not in result:raise ValueError("Home head missing")
    result=result.replace("</head>",'<style id="'+CSS_ID+'">'+CSS+FOLLOWUP_CSS+'</style>\n</head>',1)
    if result.count(START)!=1 or result.count(GUIDE_START)!=1 or result.count('id="ztWebNewsFollowup"')!=1:
        raise ValueError("Duplicate Home sections prevented")
    assert result.index("<!-- ARTICLE_PAGINATION_END -->")<result.index(START)<result.index(GUIDE_START)
    assert result.index(GUIDE_END)<result.index("ZT_WEB_EXTRA_START")<result.index("ZT_WEB_EDITORIAL_RAIL_START")
    return result

def run(root=ROOT):
    path=root/"notizie-dal-web.json"
    if not path.is_file():
        print("WEB-NEWS: no validated feed snapshot; no change to Home")
        return False
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("version")!=1 or len(data.get("items",[]))!=5:
        print("WEB-NEWS: incomplete snapshot, preserving Home unchanged")
        return False
    page=root/"index.html"
    old=page.read_text(encoding="utf-8")
    new=apply(old,data,root)
    if old!=new:page.write_text(new,encoding="utf-8")
    print("WEB-NEWS: 5 items rendered after pagination, before official GUIDE")
    return True

def self_test():
    sample='<html><head></head><body><!-- HOME_GUIDES_INSET_START --><section id="ztHomeGuide">GUIDE</section><!-- HOME_GUIDES_INSET_END --><div class="layout"><div class="maincol"><section><nav>1,2,3</nav><!-- ARTICLE_PAGINATION_END --></section></div><aside class="sidebar"><div>Original sidebar</div></aside></div></body></html>'
    data={"items":[{"id":str(i),"source":"HDblog","url":"https://hdblog.it/test/"+str(i),"image":"/assets/notizie-dal-web/"+str(i)+".webp","title":"Focus tecnologia numero "+str(i),"excerpt":"Sintesi rielaborata."} for i in range(5)]}
    first=apply(sample,data)
    assert first.count("NOTIZIE DAL WEB")>=1
    assert first.count('id="ztWebNewsFollowup"')==1
    assert 'zt-webnews-followup-rail' in first and 'ZT_WEB_EXTRA_START' in first
    assert first.index("ARTICLE_PAGINATION_END")<first.index("ZT_WEB_NEWS_START")<first.index("HOME_GUIDES_INSET_START")
    assert apply(first,data)==first
    print("PASS: one module; 5 cards; exact after-pagination/before-GUIDE order; idempotent")
if __name__=="__main__":
    if "--self-test" in sys.argv:self_test()
    else:run()
