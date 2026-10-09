#!/usr/bin/env python3
"""One shared ZazoomTek editorial article layout for all featured NEWS."""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parent.parent
CSS = """
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:#bfc0c0;color:#252525;font:16px/1.7 Arial,Helvetica,sans-serif}
.zt-head{background:#171717;color:#fff;border-top:3px solid #d51232}
.zt-head-row{max-width:1460px;margin:auto;min-height:78px;display:grid;grid-template-columns:238px minmax(0,1fr) 215px;align-items:stretch;gap:0}
.zt-brand{display:flex;align-items:center;gap:9px;padding:10px 12px;color:#fff;text-decoration:none;white-space:nowrap;border-right:1px solid #333;font-size:22px;font-weight:800;min-width:0}
.zt-brand img{width:47px;height:47px;object-fit:cover;border-radius:9px}.zt-brand em{color:#ef2948;font-style:normal}
.zt-menu{display:flex;align-items:stretch;flex-wrap:nowrap;min-width:0;white-space:nowrap;justify-content:space-between}
.zt-menu a{display:flex;align-items:center;justify-content:center;padding:10px 9px;min-width:0;color:#fff;text-decoration:none;text-transform:uppercase;font-size:12px;font-weight:bold;border-right:1px solid #303030;white-space:nowrap}
.zt-menu a:hover,.zt-menu a.active{background:#d51232;color:#fff}
.zt-search{margin:0;display:flex;align-items:center;align-self:center;background:#303030;min-width:0;width:100%;max-width:none}
.zt-search input{min-width:0;width:100%;background:none;border:0;padding:13px;color:#fff}
.zt-search button{border:0;background:#d51232;color:#fff;padding:13px;cursor:pointer}
.zt-strip{background:#222;color:#ddd}.zt-strip-inner{max-width:1460px;margin:auto;display:flex;min-height:39px;align-items:center;font-size:13px}
.zt-strip strong{align-self:stretch;display:flex;align-items:center;background:#d51232;padding:0 18px;color:white;text-transform:uppercase}.zt-strip span{padding:0 14px}
.zt-feature-layout{max-width:1460px;margin:0 auto;background:white;padding:22px 24px 44px;display:grid;grid-template-columns:minmax(0,1fr) 298px;gap:36px;align-items:start}
.zt-feature-layout>main{display:block;min-width:0;width:auto;max-width:none;margin:0;padding:26px 15px 25px;background:white;color:#252525;box-sizing:border-box}
.zt-feature-layout>main h1{font-size:clamp(30px,3.2vw,45px);line-height:1.18;font-weight:800;color:#242424;margin:12px 0 16px}
.zt-feature-layout>main .eyebrow{font-size:13px;font-weight:800;color:#c11734;text-transform:uppercase}
.zt-feature-layout>main .meta{color:#777;font-size:13px}
.zt-feature-layout>main figure.hero{margin:20px 0 22px}
.zt-feature-layout>main figure.hero>img{width:100%;height:auto;max-width:100%;aspect-ratio:auto;object-fit:contain;display:block}
.zt-feature-layout>main p{line-height:1.78}
.zt-feature-layout>main p.lead{font-size:19px;line-height:1.55;color:#444}
.zt-feature-layout>main .image-credit,.zt-feature-layout>main figcaption{font-size:12px;color:#777;line-height:1.5}
.zt-feature-layout>main a{color:#b7132a}
.zt-side{padding-top:0;min-width:0}
.zt-side-box{border:1px solid #e1e1e1;background:white;margin:0 0 18px}
.zt-side-title{background:#222;color:white;font-size:15px;letter-spacing:.03em;font-weight:800;text-transform:uppercase;border-left:7px solid #d51232;padding:11px 12px}
.zt-side-feature{padding:9px}.zt-side-feature img{width:100%;height:auto;display:block}.zt-side-feature h3{margin:6px 0 9px;font-size:14px;line-height:1.25}
.zt-side-feature a,.zt-side-list a{color:#222;text-decoration:none}
.zt-side-action{display:block;background:#d51232;color:white!important;text-align:center;text-decoration:none;padding:9px 8px;font-size:12px;font-weight:800;text-transform:uppercase}
.zt-side-list{list-style:none;padding:0;margin:0}.zt-side-list li{display:flex;gap:8px;padding:9px;border-bottom:1px solid #e4e4e4;min-height:61px}
.zt-side-list img{width:83px;height:52px;object-fit:cover;flex-shrink:0}
.zt-side-list a{font-size:12px;font-weight:700;line-height:1.3}.zt-follow{text-align:center;padding:16px}
.zt-follow img{height:52px;width:52px;object-fit:cover;border-radius:10px}.zt-follow strong{display:block;margin:7px 0}
.zt-feature-layout~footer{margin-top:0}
@media(max-width:1250px){.zt-head-row{grid-template-columns:205px minmax(0,1fr) 170px}.zt-brand{font-size:19px;padding:7px}.zt-brand img{width:42px;height:42px}.zt-menu a{font-size:11px;padding:8px 5px}.zt-feature-layout{grid-template-columns:minmax(0,1fr) 245px;gap:18px}}
@media(max-width:1040px){.zt-head-row{grid-template-columns:1fr;justify-items:center}.zt-brand{border-right:0}.zt-menu{width:100%;justify-content:center;flex-wrap:wrap;min-height:0}.zt-menu a{font-size:12px;padding:12px}.zt-search{max-width:430px;margin:8px auto 12px}.zt-feature-layout{grid-template-columns:1fr;padding:12px;gap:6px}.zt-feature-layout>main{padding:15px 10px}.zt-side{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.zt-side-box{margin:0}}
@media(max-width:530px){.zt-brand{font-size:20px}.zt-menu a{font-size:11px;padding:8px 7px}.zt-feature-layout>main h1{font-size:28px}.zt-side{grid-template-columns:1fr}.zt-strip span{font-size:11px}}
"""

def sidebar():
    """Show the site's existing live editorial review selections, not fake posts."""
    source = (ROOT / "recensioni-scritte.html").read_text(encoding="utf-8")
    mark = source.find('<div class="news-list" id="reviewList">')
    if mark < 0:
        raise RuntimeError("Review list missing; cannot render article sidebar")
    cards = re.findall(r'<article class="news-row".*?</article>', source[mark:], re.S)[:5]
    entries = []
    for card in cards:
        m = re.search(r'<a href="(/recensione-[^"]+\.html)"><img src="([^"]+)"', card)
        t = re.search(r'<div class="news-copy"><h2><a href="[^"]+">([^<]+)</a>', card)
        if m and t:
            entries.append((m.group(1), m.group(2), html.unescape(t.group(1))))
    if len(entries) < 3:
        raise RuntimeError("Not enough real reviews for editorial sidebar")
    def link(e):
        href,img,title=e
        return '<li><a href="'+html.escape(href,quote=True)+'"><img loading="lazy" src="'+html.escape(img,quote=True)+'" alt=""></a><a href="'+html.escape(href,quote=True)+'">'+html.escape(title)+'</a></li>'
    href,img,title=entries[0]
    feature = ('<section class="zt-side-box"><div class="zt-side-title">In evidenza</div><div class="zt-side-feature">'
               '<a href="'+html.escape(href,quote=True)+'"><img src="'+html.escape(img,quote=True)+'" loading="lazy" alt="'+html.escape(title,quote=True)+'"></a>'
               '<h3><a href="'+html.escape(href,quote=True)+'">'+html.escape(title)+'</a></h3>'
               '<a class="zt-side-action" href="'+html.escape(href,quote=True)+'">Leggi la recensione ›</a></div></section>')
    latest = '<section class="zt-side-box"><div class="zt-side-title">Ultime recensioni</div><ul class="zt-side-list">'+''.join(map(link,entries))+'</ul></section>'
    follow = ('<section class="zt-side-box"><div class="zt-side-title">Segui ZazoomTek</div>'
              '<div class="zt-follow"><img src="/ChatGPT.png" alt="ZT"><strong>ZazoomTek</strong>'
              '<a class="zt-side-action" href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener">Iscriviti su YouTube</a></div></section>')
    return '<aside class="zt-side" aria-label="Recensioni e community">'+feature+latest+follow+'</aside>'

def decorate(page, section_label="News"):
    """Enhance a generated HTML page without changing its journalism or URLs."""
    if 'class="zt-feature-layout"' in page:
        return page
    header = ('<header class="zt-head"><div class="zt-head-row">'
              '<a class="zt-brand" href="/"><img src="/ChatGPT.png" alt="Logo ZT"><span>Zazoom<em>Tek</em></span></a>'
              '<nav class="zt-menu" aria-label="Navigazione principale">'
              '<a href="/">Home</a><a class="active" href="/news.html">News</a><a href="/recensioni-scritte.html">Recensioni</a>'
              '<a href="/tech-today.html">Tech Impact</a><a href="/gaming-today.html">Gaming Inside</a>'
              '<a href="https://www.youtube.com/@ZazoomTek/posts">Community</a>'
              '<a href="https://www.youtube.com/@ZazoomTek/videos">Video</a></nav>'
              '<form class="zt-search" action="/cerca.html" method="get"><input name="q" aria-label="Cerca nel sito" placeholder="Cerca nel sito..."><button type="submit">⌕</button></form>'
              '</div></header>'
              '<div class="zt-strip"><div class="zt-strip-inner"><strong>News</strong>'
              '<span>Notizie tech, gaming e novità dalla Community ZazoomTek</span></div></div>')
    page,count=re.subn(r'<body>\s*<header\b[^>]*>.*?</header>', '<body>'+header, page,count=1,flags=re.S)
    if count != 1:
        raise RuntimeError("Cannot replace old article header")
    page,count=re.subn(r'<main\b[^>]*>', '<div class="zt-feature-layout"><main>',page,count=1)
    if count != 1: raise RuntimeError("Article main element absent")
    page,count=re.subn(r'</main>', '</main>'+sidebar()+'</div>',page,count=1)
    if count != 1: raise RuntimeError("Article main closing element absent")
    page=page.replace('</style>',CSS+'</style>',1)
    if 'class="zt-side"' not in page or 'class="zt-head"' not in page:
        raise RuntimeError("Unified layout incomplete")
    return page
