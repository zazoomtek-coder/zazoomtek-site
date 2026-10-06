#!/usr/bin/env python3
# Global scrollbar refresh marker
import json,re,html,urllib.request
from datetime import datetime,timezone
from pathlib import Path

URL="https://www.youtube.com/@ZazoomTek/posts"
STATE=Path(".youtube-posts.json")
INDEX=Path("index.html")

def fetch():
    req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36","Accept-Language":"it-IT,it;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req,timeout=30) as r:return r.read().decode("utf-8","replace")

def initial_data(s):
    pats=[r'var ytInitialData = ({.*?});</script>',r'ytInitialData\s*=\s*({.*?});</script>']
    for p in pats:
        m=re.search(p,s,re.S)
        if m:
            try:return json.loads(m.group(1))
            except:pass
    return {}

def txt(v):
    if not isinstance(v,dict):return ""
    if "simpleText" in v:return v["simpleText"]
    return "".join(x.get("text","") for x in v.get("runs",[]) if isinstance(x,dict))

def walk(x,out):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ("backstagePostRenderer","postRenderer") and isinstance(v,dict): out.append(v)
            walk(v,out)
    elif isinstance(x,list):
        for v in x:walk(v,out)

def image_url(p):
    # Prefer the FIRST photo attached to the Community post.
    # Do not pick the largest image from the whole renderer (which can select
    # a different attachment or unrelated thumbnail).
    def first_thumb_group(x):
        if isinstance(x,dict):
            thumbs=x.get("thumbnails")
            if isinstance(thumbs,list):
                valid=[t for t in thumbs if isinstance(t,dict) and str(t.get("url","")).startswith("http")]
                if valid:
                    best=max(valid,key=lambda t:(t.get("width",0) or 0)*(t.get("height",0) or 0))
                    return best.get("url","").replace("\\u0026","&")
            for v in x.values():
                u=first_thumb_group(v)
                if u:return u
        elif isinstance(x,list):
            for v in x:
                u=first_thumb_group(v)
                if u:return u
        return ""

    # YouTube normally stores Community post media here.
    for key in ("backstageAttachment","attachment","postMultiImageRenderer"):
        if isinstance(p,dict) and p.get(key):
            u=first_thumb_group(p[key])
            if u:return u

    # Fallback for renderer variants: keep previous behavior.
    found=[]
    def w(x):
        if isinstance(x,dict):
            if isinstance(x.get("thumbnails"),list):
                for t in x["thumbnails"]:
                    u=t.get("url","")
                    if u.startswith("http"):found.append((t.get("width",0)*t.get("height",0),u))
            for v in x.values():w(v)
        elif isinstance(x,list):
            for v in x:w(v)
    w(p)
    return max(found,default=(0,""))[1].replace("\\u0026","&")

def continuation_tokens(x):
    out=[]
    def w(v):
        if isinstance(v,dict):
            cc=v.get("continuationCommand")
            if isinstance(cc,dict) and cc.get("token"): out.append(cc["token"])
            for z in v.values(): w(z)
        elif isinstance(v,list):
            for z in v: w(z)
    w(x)
    return out

def innertube_config(page):
    key=""
    ver=""
    m=re.search(r'"INNERTUBE_API_KEY":"([^"]+)"',page)
    if m:key=m.group(1)
    m=re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"',page)
    if m:ver=m.group(1)
    return key,ver

def fetch_continuation(token,key,ver):
    if not key or not ver:return {}
    payload=json.dumps({
        "context":{"client":{"clientName":"WEB","clientVersion":ver,"hl":"it","gl":"IT"}},
        "continuation":token
    }).encode("utf-8")
    req=urllib.request.Request(
        "https://www.youtube.com/youtubei/v1/browse?key="+key,
        data=payload,
        headers={
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Content-Type":"application/json",
            "Accept-Language":"it-IT,it;q=0.9,en;q=0.8"
        }
    )
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def parse_nodes(data,posts,seen):
    nodes=[];walk(data,nodes)
    for p in nodes:
        pid=p.get("postId") or p.get("backstagePostId")
        if not pid or pid in seen:continue
        seen.add(pid)
        body=txt(p.get("contentText",{})) or txt(p.get("backstagePostText",{}))
        when=txt(p.get("publishedTimeText",{}))
        posts.append({"id":pid,"text":body.strip(),"published":when,"image":image_url(p),"url":"https://www.youtube.com/post/"+pid})

def looks_like_review_post(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    first=lines[0].lower() if lines else ""
    body=(p.get("text") or "").lower()
    return (not first.startswith("news:")) and ("recensione" in first or "review" in first or "voto finale" in body)

def parse(s):
    data=initial_data(s)
    posts=[];seen=set()
    parse_nodes(data,posts,seen)
    key,ver=innertube_config(s)
    tokens=continuation_tokens(data)
    used=set()
    pages=0
    # Continue loading older Community posts until at least 20 written reviews
    # are found, so the Recensioni archive is actually populated.
    # A generous safety ceiling prevents runaway pagination.
    while sum(1 for p in posts if looks_like_review_post(p)) < 20 and tokens and pages < 220:
        token=next((t for t in tokens if t not in used),None)
        if not token:break
        used.add(token);pages+=1
        try:
            more=fetch_continuation(token,key,ver)
        except Exception:
            break
        parse_nodes(more,posts,seen)
        tokens.extend(t for t in continuation_tokens(more) if t not in used)
    return posts

def is_review(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    first=lines[0].lower() if lines else ""
    body=(p.get("text") or "").lower()
    return (not first.startswith("news:")) and ("recensione" in first or "review" in first or "voto finale" in body)

def review_title(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    # Ignore generic labels such as "Review:" and use the first real line
    # that identifies the reviewed product/game.
    for line in lines[:8]:
        low=line.lower().strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)
        if plain in ("review","recensione"):
            continue
        if "recensione" in low or "review" in low:
            return line
    for line in lines:
        low=line.lower().strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)
        if plain not in ("review","recensione"):
            return line
    return "Recensione ZazoomTek"

def review_slug(p):
    return "recensione-"+p["id"]+".html"

def review_body_html(p):
    blocks=[x.strip() for x in re.split(r'\n\s*\n|⠀',p.get("text") or "") if x.strip()]
    title=review_title(p)
    cleaned=[]
    for b in blocks:
        low=b.lower().strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)
        if plain in ("review","recensione"):
            continue
        if b==title:
            continue
        cleaned.append(b)
    blocks=cleaned
    out=[]
    headings={"gameplay","la città","my player","my career","my nba, the w e my wnba","my team","aspetto tecnico su ps5","esperienza complessiva","conclusioni","materiali e design","hardware e prestazioni","uso quotidiano"}
    for b in blocks:
        low=b.lower().strip()
        if low in headings or (len(b)<60 and low.isupper()):
            out.append(f"<h2>{html.escape(b)}</h2>")
        elif low.startswith("voto finale"):
            out.append(f'<div class="review-score">{html.escape(b)}</div>')
        else:
            out.append(f"<p>{html.escape(b)}</p>")
    return "\n".join(out)

DETAIL_STYLE = """<style>
:root{--orange:#006CFF;--accent-blue:#006CFF;--accent-mid:#263778;--accent-red:#D51232;--accent-gradient:linear-gradient(90deg,var(--accent-blue) 0%,var(--accent-mid) 48%,var(--accent-red) 100%);--line:#ddd;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.68}
.wrap{width:min(1100px,calc(100% - 32px));margin:auto}header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--accent-gradient) 1}
.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}
.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}
.nav a:hover{background:var(--orange)}a{color:inherit;text-decoration:none}
.hero{margin:26px 0 0;overflow:hidden;border:1px solid var(--line);background:#fff}.hero img{width:100%;max-height:560px;object-fit:cover;display:block}
.hero-copy{padding:22px;border-top:5px solid transparent;border-image:var(--accent-gradient) 1}.hero h1{margin:0 0 8px;font-size:clamp(1.8rem,4vw,3rem);line-height:1.08}
.meta{color:var(--muted);font-size:.9rem}.article{background:#fff;border:1px solid var(--line);border-top:0;padding:28px;margin-bottom:36px}
.article h2{margin:30px 0 10px;border-left:6px solid var(--accent-blue);box-shadow:inset 2px 0 0 var(--accent-red);padding-left:10px}.article p{margin:0 0 18px;white-space:pre-line}
.review-score{margin-top:28px;padding:16px 18px;background:#202020;border-left:8px solid var(--accent-blue);box-shadow:inset 2px 0 0 var(--accent-red);color:#fff;font-size:1.35rem;font-weight:900}
@media(max-width:760px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.article{padding:20px}}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}</style>"""

ARCHIVE_STYLE = """<style>
:root{--orange:#006CFF;--line:#ddd;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif}
.wrap{width:min(1320px,calc(100% - 36px));margin:auto}header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--accent-gradient) 1}
.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}
.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}
.nav a:hover,.nav a.active{background:var(--accent-gradient)}a{color:inherit;text-decoration:none}
main{background:#fff;padding:24px 24px 40px}h1{margin:4px 0 6px}.sub{color:var(--muted);margin-bottom:18px}
.community-posts-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.community-post-card{background:#fff;border:1px solid var(--line);border-top:5px solid transparent;border-image:var(--accent-gradient) 1;min-width:0}
.community-post-card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.community-post-copy{padding:14px}.community-post-copy p{margin:0;font-size:1rem;line-height:1.35;font-weight:800}
.community-post-copy small{display:block;margin-top:9px;color:var(--muted);font-size:.72rem}.community-post-copy a{display:inline-block;margin-top:10px;background:var(--accent-gradient);color:#fff;padding:7px 10px;font-size:.72rem;font-weight:900}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}@media(max-width:900px){.community-posts-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.community-posts-grid{grid-template-columns:1fr}}
</style>"""


NEWS_COMMON = """
:root{--zt-blue:#006CFF;--zt-mid:#263778;--zt-red:#D51232;--zt-grad:linear-gradient(90deg,var(--zt-blue) 0%,var(--zt-mid) 48%,var(--zt-red) 100%);--zt-dark:#171717;--zt-line:#e3e3e3;--zt-text:#303030;--zt-muted:#777}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#ececec;color:var(--zt-text);font-family:Arial,Helvetica,sans-serif}a{color:inherit;text-decoration:none}
.zt-wrap{width:min(1460px,calc(100% - 28px));margin:auto}
.zt-header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--zt-grad) 1}
.zt-headrow{min-height:78px;display:grid;grid-template-columns:auto 1fr minmax(260px,370px);align-items:stretch}
.zt-brand{display:flex;align-items:center;gap:10px;padding:10px 24px 10px 0;border-right:1px solid #333}
.zt-brand img{width:52px;height:52px;object-fit:cover;border-radius:8px}.zt-brand strong{font-size:1.7rem}
.zt-nav{display:flex;align-items:stretch;flex-wrap:wrap}.zt-nav a{display:flex;align-items:center;padding:0 20px;font-weight:800;font-size:.82rem;border-right:1px solid #2d2d2d;text-transform:uppercase}
.zt-nav a:hover,.zt-nav a.active{background:var(--zt-grad);color:#fff}
.zt-tools{display:flex;flex-direction:column;justify-content:center;padding-left:16px}.zt-search{display:flex;width:100%;background:#303030;border:1px solid #444}.zt-search input{width:100%;border:0;background:transparent;color:#fff;padding:12px 14px;outline:none}.zt-search button{width:48px;border:0;background:var(--zt-grad);color:#fff;font-weight:900;cursor:pointer}
.zt-socials{display:flex;justify-content:flex-end;gap:9px;margin-top:7px}.zt-socials a{display:grid;place-items:center;width:35px;height:35px;border-radius:50%;background:#202020;border:1px solid #373737}.zt-socials img{width:24px;height:24px;object-fit:contain}
.zt-strip{background:#222;border-top:1px solid #2c2c2c;color:#ddd}.zt-strip .zt-wrap{display:flex;align-items:center;min-height:46px}.zt-strip strong{align-self:stretch;display:flex;align-items:center;padding:0 20px;background:var(--zt-grad);color:#fff;text-transform:uppercase}.zt-strip span{padding:0 16px;font-size:.86rem}
.module-title{height:48px;background:#202020;color:#fff;display:flex;align-items:center;border-left:7px solid var(--zt-blue);box-shadow:inset 2px 0 0 var(--zt-red);padding:0 16px;font-weight:900;text-transform:uppercase;letter-spacing:.01em}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}
@media(max-width:1080px){.zt-headrow{grid-template-columns:auto 1fr}.zt-tools{grid-column:1/-1;padding:10px 0 12px}.zt-socials{justify-content:flex-end}}
@media(max-width:720px){.zt-wrap{width:min(100% - 18px,1460px)}.zt-headrow{display:block}.zt-brand{justify-content:center;padding:10px 0;border-right:0}.zt-nav{justify-content:center}.zt-nav a{padding:12px 10px}.zt-tools{padding:10px 0 12px}.zt-socials{justify-content:center}}
"""

NEWS_ARCHIVE_STYLE = """<style>"""+NEWS_COMMON+"""
.news-page{background:#fff;padding:24px 0 40px}.news-layout{display:grid;grid-template-columns:minmax(0,1fr) 355px;gap:22px;align-items:start}
.news-main{min-width:0}.news-main-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border-bottom:3px solid transparent;border-image:var(--zt-grad) 1}.news-main-head h1{font-size:1.65rem;margin:0;padding:0 0 10px;text-transform:uppercase}.news-filter{display:flex;gap:8px;flex-wrap:wrap;padding-bottom:10px}.news-filter span{font-size:.72rem;font-weight:900;text-transform:uppercase;color:#666}
.news-list{border:1px solid var(--zt-line);border-bottom:0}.news-row{display:grid;grid-template-columns:360px minmax(0,1fr);gap:20px;padding:18px;border-bottom:1px solid var(--zt-line);background:#fff;align-items:start}.news-row img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.news-copy h2{margin:0 0 8px;font-size:1.3rem;line-height:1.12}.news-meta{font-size:.76rem;color:#888;margin-bottom:9px}.news-copy p{margin:0 0 13px;color:#555;line-height:1.48;font-size:.93rem}.news-read{display:inline-block;background:var(--zt-grad);color:#fff;padding:10px 14px;font-size:.75rem;font-weight:900;text-transform:uppercase}
.news-sidebar{min-width:0;align-self:start;height:max-content;position:sticky;top:var(--zt-smart-sticky-top,16px)}.side-box{margin-bottom:18px;border:1px solid #ddd;background:#fff}.side-video{padding:10px}.side-video a.thumb{display:block;position:relative}.side-video img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}.side-video a.thumb:after{content:"▶";position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:50px;height:36px;border-radius:8px;background:rgba(220,0,0,.92);display:grid;place-items:center;color:#fff}.side-video h3{margin:8px 2px 6px;font-size:.92rem;line-height:1.25}.side-video small{display:block;color:#888;margin:0 2px 6px}.amazon-mini{padding:16px}.amazon-mini h3{margin:0 0 8px}.amazon-mini p{font-size:.78rem;color:#666;line-height:1.4}.amazon-mini a{display:block;text-align:center;background:var(--zt-grad);color:#fff;padding:11px 8px;font-weight:900;font-size:.75rem}.archive-pagination{margin:28px 0 0;background:#202020;padding:20px;display:flex;gap:8px;justify-content:center;align-items:center;flex-wrap:wrap}.archive-pagination a,.archive-pagination span{min-width:52px;height:50px;padding:0 15px;border:1px solid #555;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.05rem}.archive-pagination .active{background:var(--zt-grad);border-color:transparent}.archive-pagination .next{min-width:92px}
@media(max-width:980px){.news-layout{grid-template-columns:1fr}.news-sidebar{position:static;top:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.side-box{margin:0}}
@media(max-width:720px){.news-row{grid-template-columns:1fr;padding:14px}.news-sidebar{grid-template-columns:1fr}}
</style>"""

NEWS_DETAIL_STYLE = """<style>"""+NEWS_COMMON+"""
.news-detail-page{background:#fff;padding:24px 0 42px}.detail-grid{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:24px;align-items:start}.article-main{min-width:0}.breadcrumbs{font-size:.8rem;color:#777;border-bottom:1px solid #ddd;padding:0 0 13px;margin-bottom:16px}.article-main h1{font-size:clamp(2rem,3.3vw,3.25rem);line-height:1.05;margin:0 0 14px;letter-spacing:-.02em}.article-meta{display:flex;gap:16px;flex-wrap:wrap;color:#777;font-size:.86rem;margin-bottom:18px}.article-hero{width:100%;max-height:610px;object-fit:cover;display:block;margin-bottom:20px}.article-body{font-size:1.05rem;line-height:1.65}.article-body p{margin:0 0 18px;white-space:pre-line}.article-side{min-width:0;align-self:start;height:max-content;position:sticky;top:var(--zt-smart-sticky-top,16px)}.compact-box{margin-bottom:18px}.compact-list{border:1px solid #ddd;border-top:0;background:#fff}.compact-item{display:grid;grid-template-columns:92px 1fr;gap:10px;padding:11px;border-bottom:1px solid #eee}.compact-item:last-child{border-bottom:0}.compact-item img{width:92px;height:64px;object-fit:cover}.compact-item h3{margin:0;font-size:.86rem;line-height:1.18}.compact-item small{display:block;margin-top:5px;color:#888;font-size:.7rem}.feature-card{border:1px solid #ddd;border-top:0;background:#fff;padding:10px}.feature-card img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block}.feature-card h3{margin:10px 2px 4px;font-size:1rem}.feature-card .cta{display:block;margin-top:10px;background:var(--zt-grad);color:#fff;text-align:center;padding:11px 8px;font-weight:900;font-size:.75rem}.follow-box{padding:14px;text-align:center;border:1px solid #ddd;border-top:0;background:#fff}.follow-box img{width:58px;height:58px;border-radius:12px}.follow-box strong{display:block;margin-top:6px}.follow-box a{display:inline-block;margin-top:9px;background:var(--zt-grad);color:#fff;padding:9px 12px;font-size:.74rem;font-weight:900}
@media(max-width:1180px){.detail-grid{grid-template-columns:minmax(0,1fr) 330px}.article-side.middle{display:none}}
@media(max-width:820px){.detail-grid{grid-template-columns:1fr}.article-side{position:static;top:auto}.article-side.middle{display:block}.article-main h1{font-size:2rem}}
</style>"""

SMART_STICKY_SCRIPT = """<script>
function ztInitSmartSticky(selector,mobileWidth){
  const el=document.querySelector(selector);
  if(!el)return;
  function update(){
    if(window.innerWidth<=mobileWidth){
      el.style.removeProperty('--zt-smart-sticky-top');
      return;
    }
    const gap=16;
    const top=Math.min(gap,window.innerHeight-el.offsetHeight-gap);
    el.style.setProperty('--zt-smart-sticky-top',top+'px');
  }
  update();
  window.addEventListener('resize',update,{passive:true});
  if('ResizeObserver' in window){new ResizeObserver(update).observe(el);}
}
document.addEventListener('DOMContentLoaded',function(){
  ztInitSmartSticky('.news-sidebar',980);
  ztInitSmartSticky('.article-side',820);
});
</script>"""

def rich_editorial_header(active="news"):
    def nav(label, href, key):
        cls=' active' if active==key else ''
        ext=' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return f'<a class="{cls.strip()}" href="{href}"{ext}>{label}</a>' if cls else f'<a href="{href}"{ext}>{label}</a>'
    return (
        '<header class="zt-header"><div class="zt-wrap zt-headrow">'
        '<a class="zt-brand" href="/"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong></a>'
        '<nav class="zt-nav">'
        +nav("Home","/","home")+nav("News","/news.html","news")+nav("Recensioni","/recensioni-scritte.html","recensioni")
        +nav("Community","https://www.youtube.com/@ZazoomTek/posts","community")+nav("Video","https://www.youtube.com/@ZazoomTek/videos","video")
        +'</nav>'
        '<div class="zt-tools"><form class="zt-search" action="/news.html" method="get"><input name="q" type="search" placeholder="Cerca articoli..." aria-label="Cerca articoli"><button type="submit">⌕</button></form>'
        '<div class="zt-socials">'
        '<a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/youtube-play.png" alt="YouTube"></a>'
        '<a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/tiktok--v1.png" alt="TikTok"></a>'
        '<a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/whatsapp--v1.png" alt="WhatsApp"></a>'
        '</div></div></div></header>'
        '<div class="zt-strip"><div class="zt-wrap"><strong>News</strong><span>Notizie tech, gaming e novità dalla Community ZazoomTek</span></div></div>'
    )

def load_video_cache():
    p=Path(".youtube-latest.json")
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def latest_video_for(category):
    for v in load_video_cache():
        if v.get("category")==category and not v.get("short") and not v.get("live"):
            return v
    return None

def sidebar_video_box(title, category, link):
    v=latest_video_for(category)
    if not v:
        return ""
    vid=html.escape(v.get("id") or "")
    vt=html.escape(v.get("title") or "")
    return (
        f'<section class="side-box"><a class="module-title" href="{link}">{html.escape(title)}</a>'
        f'<div class="side-video"><a class="thumb" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" alt="{vt}" loading="lazy"></a>'
        f'<h3>{vt}</h3><small>{html.escape(category.title())}</small></div></section>'
    )

def amazon_sidebar_box():
    return '''<section class="side-box"><div class="module-title">Su Amazon</div><div class="amazon-mini"><h3>I prodotti recensiti da ZazoomTek</h3><p>Link affiliato Amazon. In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei senza alcun costo per l’utente.</p><a href="https://www.amazon.it/gp/profile/amzn1.account.AE76ZMY5J56NNH3HUPWFJGVZEC5A?&amp;linkCode=ll2&amp;tag=zazoomtek-21&amp;linkId=d2dd9b9524bc6fb76da94e041a661201&amp;ref_=as_li_ss_tl" target="_blank" rel="nofollow sponsored noopener">VEDI I PRODOTTI SU AMAZON ›</a></div></section>'''

def news_video_sidebar():
    return (
        sidebar_video_box("Video · Recensioni","recensioni","/recensioni.html")
        +sidebar_video_box("Video · Test","test","/test.html")
        +sidebar_video_box("Video · Unboxing","unboxing","/unboxing.html")
        +sidebar_video_box("Video · Gaming","gaming","/gaming.html")
        +sidebar_video_box("Video · AnalogikTek","analogiktek","https://www.youtube.com/playlist?list=PL7dvpppAJr02AQM7WP0D151c_JvKu_OaI")
        +amazon_sidebar_box()
    )

def compact_news_list(news, current_id="", limit=5):
    rows=[]
    for p in news:
        if p.get("id")==current_id:
            continue
        title=news_title(p); slug=news_slug(p); img=html.escape(p.get("image") or "/ChatGPT.png")
        rows.append(
            f'<a class="compact-item" href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy">'
            f'<div><h3>{html.escape(title)}</h3><small>{html.escape(p.get("published") or "")}</small></div></a>'
        )
        if len(rows)>=limit:
            break
    return "".join(rows)

def editorial_nav(active=""):
    def a(label, href, key):
        cls=' class="active"' if active==key else ""
        ext=' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return f'<a{cls} href="{href}"{ext}>{label}</a>'
    return (
        '<nav class="nav">'
        +a("Home","/","home")
        +a("News","/news.html","news")
        +a("Recensioni","/recensioni-scritte.html","recensioni")
        +a("Community","https://www.youtube.com/@ZazoomTek/posts","community")
        +a("Video","https://www.youtube.com/@ZazoomTek/videos","video")
        +'</nav>'
    )


def legal_footer():
    return '''<footer class="legal-footer"><div class="wrap">
      <div class="footer-links"><a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener">▶ YouTube</a><a href="https://www.patreon.com/ZazoomTek" target="_blank" rel="noopener">❤️ Patreon</a><a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener">🎵 TikTok</a><a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener">💬 WhatsApp</a><a href="/contatti.html">Contatti</a><a href="/chi-sono.html">Chi sono</a></div>
      <div class="legal-links"><a href="/privacy.html">Privacy Policy</a><a href="/cookie.html">Cookie Policy</a><a href="/disclaimer.html">Disclaimer</a><a href="/note-legali.html">Note legali</a></div>
      <div class="footer-copy">© 2026 ZazoomTek · Tecnologia e gaming.</div>
    </div></footer>'''

def editorial_header(active=""):
    return '<header><div class="wrap headrow"><a class="brand" href="/">ZazoomTek</a>'+editorial_nav(active)+'</div></header>'

def rich_review_header():
    return (
        '<header class="zt-header"><div class="zt-wrap zt-headrow">'
        '<a class="zt-brand" href="/"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong></a>'
        '<nav class="zt-nav">'
        '<a href="/">Home</a><a href="/news.html">News</a><a class="active" href="/recensioni-scritte.html">Recensioni</a>'
        '<a href="https://www.youtube.com/@ZazoomTek/posts" target="_blank" rel="noopener">Community</a>'
        '<a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener">Video</a>'
        '</nav>'
        '<div class="zt-tools"><form class="zt-search" action="/recensioni-scritte.html" method="get">'
        '<input name="q" type="search" placeholder="Cerca recensioni..." aria-label="Cerca recensioni"><button type="submit">⌕</button></form>'
        '<div class="zt-socials">'
        '<a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/youtube-play.png" alt="YouTube"></a>'
        '<a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/tiktok--v1.png" alt="TikTok"></a>'
        '<a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/whatsapp--v1.png" alt="WhatsApp"></a>'
        '</div></div></div></header>'
        '<div class="zt-strip"><div class="zt-wrap"><strong>Recensioni</strong><span>Recensioni scritte di tecnologia e gaming pubblicate da ZazoomTek</span></div></div>'
    )

def compact_review_list(reviews, current_id="", limit=5):
    rows=[]
    for p in reviews:
        if p.get("id")==current_id:
            continue
        title=review_title(p); slug=review_slug(p); img=html.escape(p.get("image") or "/ChatGPT.png")
        rows.append(
            f'<a class="compact-item" href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy">'
            f'<div><h3>{html.escape(title)}</h3><small>{html.escape(p.get("published") or "")}</small></div></a>'
        )
        if len(rows)>=limit:
            break
    return "".join(rows)

def write_review_page(p, all_reviews=None):
    all_reviews=all_reviews or []
    title=review_title(p)
    slug=review_slug(p)
    img=(f'<img class="article-hero" src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    recent=compact_review_list(all_reviews,p.get("id") or "",5)
    featured=next((x for x in all_reviews if x.get("id")!=p.get("id")),None)
    feature_html=""
    if featured:
        ft=review_title(featured); fs=review_slug(featured); fi=html.escape(featured.get("image") or "/ChatGPT.png")
        feature_html=(
            f'<section class="compact-box"><div class="module-title">In evidenza</div><div class="feature-card">'
            f'<a href="/{fs}"><img src="{fi}" alt="{html.escape(ft)}"></a><h3><a href="/{fs}">{html.escape(ft)}</a></h3>'
            f'<a class="cta" href="/{fs}">LEGGI LA RECENSIONE ›</a></div></section>'
        )
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+NEWS_DETAIL_STYLE+'</head><body>'
        +rich_review_header()
        +'<main class="news-detail-page"><div class="zt-wrap detail-grid">'
        +'<article class="article-main"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/recensioni-scritte.html">Recensioni</a> / '+html.escape(title)+'</div>'
        +f'<h1>{html.escape(title)}</h1><div class="article-meta"><span>👤 ZazoomTek</span><span>📅 {html.escape(p.get("published") or "")}</span><span>🏷 Recensione</span></div>'
        +img+f'<div class="article-body">{review_body_html(p)}</div></article>'
        +'<aside class="article-side">'+feature_html
        +'<section class="compact-box"><div class="module-title">Segui ZazoomTek</div><div class="follow-box"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong><a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener">SEGUI SU YOUTUBE</a></div></section>'
        +'<section class="compact-box"><div class="module-title">Ultime recensioni</div><div class="compact-list">'+recent+'</div></section>'
        +'</aside></div></main>'+legal_footer()+SMART_STICKY_SCRIPT+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_review_rows(posts):
    rows=[]
    for p in posts:
        title=review_title(p); slug=review_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,250))
        rows.append(
            f'<article class="news-row" data-news-search="{html.escape((title+" "+(p.get("text") or "")).lower(),quote=True)}">'
            f'<a href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="news-copy"><h2><a href="/{slug}">{html.escape(title)}</a></h2>'
            f'<div class="news-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="news-read" href="/{slug}">Leggi la recensione ›</a></div></article>'
        )
    return "".join(rows)

def write_review_archive(reviews):
    rows=render_review_rows(reviews)
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>Recensioni | ZazoomTek</title>'
        '<meta name="description" content="Archivio delle recensioni scritte di ZazoomTek.">'
        '<link rel="canonical" href="https://zazoomtek.it/recensioni-scritte.html">'+NEWS_ARCHIVE_STYLE+'</head><body>'
        +rich_review_header()
        +'<main class="news-page"><div class="zt-wrap news-layout"><section class="news-main">'
        +'<div class="news-main-head"><h1>Recensioni</h1><div class="news-filter"><span>Tutte</span><span>Gaming</span><span>Tech</span><span>Hardware</span><span>Accessori</span></div></div>'
        +'<div class="news-list" id="reviewList">'+rows+'</div></section>'
        +'<aside class="news-sidebar">'+news_video_sidebar()+'</aside></div></main>'
        +legal_footer()+SMART_STICKY_SCRIPT
        +'''<script>(function(){const p=new URLSearchParams(location.search);const q=(p.get("q")||"").trim().toLowerCase();if(!q)return;document.querySelectorAll("[data-news-search]").forEach(function(x){x.style.display=(x.dataset.newsSearch||"").includes(q)?"grid":"none"})})();</script>'''
        +'</body></html>'
    )
    Path("recensioni-scritte.html").write_text(page,encoding="utf-8")


def news_title(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    return lines[0] if lines else "News ZazoomTek"

def news_slug(p):
    return "news-"+p["id"]+".html"

def news_body_html(p):
    blocks=[x.strip() for x in re.split(r'\n\s*\n|⠀',p.get("text") or "") if x.strip()]
    title=news_title(p)
    cleaned=[]
    for b in blocks:
        if b==title:
            continue
        cleaned.append(b)
    return "\n".join(f"<p>{html.escape(b)}</p>" for b in cleaned)

def write_news_page(p, all_news=None):
    all_news=all_news or []
    title=news_title(p)
    slug=news_slug(p)
    img=(f'<img class="article-hero" src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    recent=compact_news_list(all_news,p.get("id") or "",5)
    featured=next((x for x in all_news if x.get("id")!=p.get("id")),None)
    feature_html=""
    if featured:
        ft=news_title(featured); fs=news_slug(featured); fi=html.escape(featured.get("image") or "/ChatGPT.png")
        feature_html=(
            f'<section class="compact-box"><div class="module-title">In evidenza</div><div class="feature-card">'
            f'<a href="/{fs}"><img src="{fi}" alt="{html.escape(ft)}"></a><h3><a href="/{fs}">{html.escape(ft)}</a></h3>'
            f'<a class="cta" href="/{fs}">SCOPRI DI PIÙ ›</a></div></section>'
        )
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+NEWS_DETAIL_STYLE+'</head><body>'
        +rich_editorial_header("news")
        +'<main class="news-detail-page"><div class="zt-wrap detail-grid">'
        +'<article class="article-main"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/news.html">News</a> / '+html.escape(title)+'</div>'
        +f'<h1>{html.escape(title)}</h1><div class="article-meta"><span>👤 ZazoomTek</span><span>📅 {html.escape(p.get("published") or "")}</span><span>🏷 News</span></div>'
        +img+f'<div class="article-body">{news_body_html(p)}</div></article>'
        +'<aside class="article-side">'+feature_html
        +'<section class="compact-box"><div class="module-title">Segui ZazoomTek</div><div class="follow-box"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong><a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener">SEGUI SU YOUTUBE</a></div></section>'
        +'<section class="compact-box"><div class="module-title">Ultimi articoli</div><div class="compact-list">'+recent+'</div></section>'
        +'</aside></div></main>'+legal_footer()+SMART_STICKY_SCRIPT+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_news_rows(posts):
    rows=[]
    for p in posts:
        title=news_title(p); slug=news_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,250))
        rows.append(
            f'<article class="news-row" data-news-search="{html.escape((title+" "+(p.get("text") or "")).lower(),quote=True)}">'
            f'<a href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="news-copy"><h2><a href="/{slug}">{html.escape(title)}</a></h2>'
            f'<div class="news-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="news-read" href="/{slug}">Leggi tutto ›</a></div></article>'
        )
    return "".join(rows)

NEWS_PAGE_SIZE=20
NEWS_MAX_PAGES=5

def news_page_href(n):
    return "/news.html" if n==1 else f"/news-{n}.html"

def render_news_pagination(current,total):
    if total<=1:
        return ""
    items=[]
    for n in range(1,total+1):
        if n==current:
            items.append(f'<span class="active">{n}</span>')
        else:
            items.append(f'<a href="{news_page_href(n)}">{n}</a>')
    if current < total:
        items.append(f'<a class="next" href="{news_page_href(current+1)}">NEXT</a>')
    return '<nav class="archive-pagination" aria-label="Pagine News">'+"".join(items)+'</nav>'

def build_news_archive_page(news_chunk,page_num,total_pages):
    rows=render_news_rows(news_chunk)
    title="News | ZazoomTek" if page_num==1 else f"News - Pagina {page_num} | ZazoomTek"
    canonical="https://zazoomtek.it/news.html" if page_num==1 else f"https://zazoomtek.it/news-{page_num}.html"
    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>'+html.escape(title)+'</title>'
        '<meta name="description" content="Le ultime News pubblicate da ZazoomTek, in ordine cronologico.">'
        '<link rel="canonical" href="'+canonical+'">'+NEWS_ARCHIVE_STYLE+'</head><body>'
        +rich_editorial_header("news")
        +'<main class="news-page"><div class="zt-wrap news-layout"><section class="news-main">'
        +'<div class="news-main-head"><h1>Notizie</h1><div class="news-filter"><span>Tutte</span><span>Gaming</span><span>Tech</span><span>Hardware</span><span>Software</span></div></div>'
        +'<div class="news-list" id="newsList">'+rows+'</div>'
        +render_news_pagination(page_num,total_pages)
        +'</section><aside class="news-sidebar">'+news_video_sidebar()+'</aside></div></main>'
        +legal_footer()+SMART_STICKY_SCRIPT
        +'''<script>(function(){const p=new URLSearchParams(location.search);const q=(p.get("q")||"").trim().toLowerCase();if(!q)return;document.querySelectorAll("[data-news-search]").forEach(function(x){x.style.display=(x.dataset.newsSearch||"").includes(q)?"grid":"none"})})();</script>'''
        +'</body></html>'
    )

def write_news_archive(news):
    news=news[:NEWS_PAGE_SIZE*NEWS_MAX_PAGES]
    total_pages=max(1,min(NEWS_MAX_PAGES,(len(news)+NEWS_PAGE_SIZE-1)//NEWS_PAGE_SIZE))
    for page_num in range(1,total_pages+1):
        chunk=news[(page_num-1)*NEWS_PAGE_SIZE:page_num*NEWS_PAGE_SIZE]
        page=build_news_archive_page(chunk,page_num,total_pages)
        filename="news.html" if page_num==1 else f"news-{page_num}.html"
        Path(filename).write_text(page,encoding="utf-8")



def post_kind(p):
    return "Recensione" if is_review(p) else "News"

def post_title(p):
    return review_title(p) if is_review(p) else news_title(p)

def post_slug(p):
    return review_slug(p) if is_review(p) else news_slug(p)

def post_excerpt(p, limit=220):
    text=(p.get("text") or "").replace("⠀"," ").replace("\n"," ")
    title=post_title(p)
    if text.startswith(title):
        text=text[len(title):].strip(" :-–—")
    text=re.sub(r"\s+"," ",text).strip()
    return text if len(text)<=limit else text[:limit].rsplit(" ",1)[0]+"…"

def render_ticker(news):
    rows=[]
    for i,p in enumerate(news[:5]):
        cls=' class="active"' if i==0 else ""
        rows.append(f'    <a{cls} href="{news_slug(p)}">{html.escape(news_title(p))}</a>')
    return "\n".join(rows)

def render_featured_news(news):
    news=news[:5]
    slides=[]
    tabs=[]
    for i,p in enumerate(news):
        title=html.escape(news_title(p))
        slug=news_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        active=" active" if i==0 else ""
        slides.append(
            f'            <article class="news-slide{active}" data-slide="{i}">'
            f'<a href="{slug}"><img src="{img}" alt="{title}"></a>'
            f'<div class="news-slide-copy"><span class="tag">News</span>'
            f'<h1><a href="{slug}">{title}</a></h1>'
            f'<p>{html.escape(post_excerpt(p,180))}</p></div></article>'
        )
        tabs.append(f'            <button class="news-tab{active}" data-go="{i}">{title}</button>')
    return (
        '<div class="news-slider" id="newsSlider">\n'
        '          <div class="news-slides">\n'+"\n".join(slides)+'\n          </div>\n'
        '          <div class="news-tabs">\n'+"\n".join(tabs)+'\n          </div>\n'
        '        </div>'
    )

def render_article_feed(posts):
    rows=[]
    for p in posts:
        kind=post_kind(p)
        title=post_title(p)
        slug=post_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,230))
        search=html.escape((title+" "+kind+" "+(p.get("text") or ""))[:1200],quote=True)
        rows.append(
            f'          <article class="article-row" data-search="{search.lower()}">'
            f'<a href="{slug}"><img class="article-image" src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="article-copy">'
            f'<h3><a href="{slug}">{html.escape(title)}</a></h3>'
            f'<div class="article-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="read-more" href="{slug}">Leggi tutto ›</a></div></article>'
        )
    return "\n".join(rows)

def render(posts):
    return render_news_cards(posts)


def update_sitemap():
    base=["","recensioni.html","test.html","unboxing.html","gaming.html","news.html","recensioni-scritte.html","chi-sono.html","contatti.html"]
    dynamic=sorted([p.name for p in Path(".").glob("news-*.html")]+[p.name for p in Path(".").glob("recensione-*.html")])
    names=[]; seen=set()
    for n in base+dynamic:
        if n in seen: continue
        seen.add(n); names.append(n)
    lastmod=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    rows=[]
    for n in names:
        priority="1.0000" if n=="" else "0.8000"
        rows.append(
            "  <url>\n"
            f"       <loc>https://zazoomtek.it/{html.escape(n)}</loc>\n"
            f"       <lastmod>{lastmod}</lastmod>\n"
            f"       <priority>{priority}</priority>\n"
            "  </url>"
        )
    xml=(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<?xml-stylesheet type="text/css" href="https://www.xml-sitemaps.com/css/sitemap.css"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n\n'
        +"\n".join(rows)
        +'\n</urlset>\n'
    )
    Path("sitemap.xml").write_text(xml,encoding="utf-8")


PAGE_SIZE=20

PAGINATED_ARTICLE_STYLE = """<style>
:root{--blue:#006CFF;--mid:#263778;--red:#D51232;--grad:linear-gradient(90deg,var(--blue) 0%,var(--mid) 48%,var(--red) 100%);--line:#e5e5e5;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif}.wrap{width:min(1180px,calc(100% - 32px));margin:auto}
header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--grad) 1}.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}.nav a:hover,.nav a.active{background:var(--grad)}a{color:inherit;text-decoration:none}
main{background:#fff;padding:26px 0 40px}.archive-head{padding:0 22px 18px}.archive-head h1{margin:0 0 6px}.archive-head p{margin:0;color:var(--muted)}
.article-list{border-top:1px solid var(--line)}.article-row{display:grid;grid-template-columns:330px 1fr;gap:20px;padding:18px 22px;border-bottom:1px solid var(--line);align-items:start}.article-image{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.article-copy h3{font-size:1.18rem;line-height:1.18;margin:0 0 6px}.article-meta{font-size:.78rem;color:var(--muted);margin-bottom:8px}.article-copy p{margin:0 0 12px;line-height:1.45}.read-more{display:inline-block;background:var(--grad);color:#fff;padding:9px 13px;font-size:.76rem;font-weight:900;text-transform:uppercase}
.pagination{margin:28px 22px 0;background:#202020;padding:20px;display:flex;gap:7px;justify-content:center;align-items:center;flex-wrap:wrap}.pagination a,.pagination span{min-width:52px;height:50px;padding:0 15px;border:1px solid #555;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.05rem}.pagination .active{background:var(--grad);border-color:transparent}.pagination .next{min-width:92px}
@media(max-width:760px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.article-row{grid-template-columns:1fr;padding:16px}.pagination{margin:22px 16px 0;padding:14px}.pagination a,.pagination span{min-width:42px;height:44px;padding:0 10px}}
</style>.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}"""

def page_href(n):
    return "/" if n==1 else f"/pagina-{n}.html"

def render_pagination(current,total):
    if total<=1:
        return ""
    # Show up to five numbered pages, as in the requested template.
    visible=list(range(1,min(total,5)+1))
    items=[]
    for n in visible:
        if n==current:
            items.append(f'<span class="active">{n}</span>')
        else:
            items.append(f'<a href="{page_href(n)}">{n}</a>')
    if current < total:
        items.append(f'<a class="next" href="{page_href(current+1)}">NEXT</a>')
    return '<nav class="pagination" aria-label="Pagine articoli">'+"".join(items)+'</nav>'

def write_article_pages(posts):
    total=max(1,(len(posts)+PAGE_SIZE-1)//PAGE_SIZE)
    total=min(total,5)

    # Reuse the real Home HTML as the template so pagina 2-5 keep exactly
    # the same header, colors, spacing, sidebar, footer and responsive layout.
    home_template=INDEX.read_text(encoding="utf-8")

    for page_num in range(2,total+1):
        chunk=posts[(page_num-1)*PAGE_SIZE:page_num*PAGE_SIZE]
        page=home_template

        # Page-specific SEO.
        page=re.sub(r'<title>.*?</title>',
                    f'<title>Articoli - Pagina {page_num} | ZazoomTek</title>',
                    page,count=1,flags=re.S)
        page=re.sub(r'<meta name="description" content="[^"]*">',
                    f'<meta name="description" content="Archivio ZazoomTek, pagina {page_num}: news e recensioni meno recenti.">',
                    page,count=1)
        page=re.sub(r'<link rel="canonical" href="[^"]+">',
                    f'<link rel="canonical" href="https://zazoomtek.it/pagina-{page_num}.html">',
                    page,count=1)

        # Replace only the article stream and pagination.
        feed="<!-- ARTICLE_FEED_START -->\n"+render_article_feed(chunk)+"\n          <!-- ARTICLE_FEED_END -->"
        page=re.sub(r'<!-- ARTICLE_FEED_START -->.*?<!-- ARTICLE_FEED_END -->',
                    feed,page,flags=re.S)

        pagination="<!-- ARTICLE_PAGINATION_START -->\n"+render_pagination(page_num,total)+"\n        <!-- ARTICLE_PAGINATION_END -->"
        if "<!-- ARTICLE_PAGINATION_START -->" in page:
            page=re.sub(r'<!-- ARTICLE_PAGINATION_START -->.*?<!-- ARTICLE_PAGINATION_END -->',
                        pagination,page,flags=re.S)
        else:
            page=page.replace('</div>\n      </section>\n    </div>\n\n    <aside class="sidebar">',
                              '</div>\n        '+pagination+'\n      </section>\n    </div>\n\n    <aside class="sidebar">',1)

        # Clear duplicated search query state and keep the Home visual shell unchanged.
        Path(f"pagina-{page_num}.html").write_text(page,encoding="utf-8")

    return total

def main():
    posts=parse(fetch())
    if not posts:
        print("No public posts parsed; keeping current site unchanged.")
        return
    STATE.write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    reviews=[p for p in posts if is_review(p)]
    news=[p for p in posts if not is_review(p)]
    for p in reviews: write_review_page(p,reviews)
    write_review_archive(reviews)
    for p in news: write_news_page(p,news)
    write_news_archive(news)
    total_article_pages=write_article_pages(posts)
    # sitemap.xml is manually approved; automatic YouTube sync must not rewrite it.
    s=INDEX.read_text(encoding="utf-8")
    s2=s
    ticker="<!-- NEWS_TICKER_START -->\n"+render_ticker(news)+"\n    <!-- NEWS_TICKER_END -->"
    s2=re.sub(r'<!-- NEWS_TICKER_START -->.*?<!-- NEWS_TICKER_END -->',ticker,s2,flags=re.S)

    featured="<!-- FEATURED_NEWS_START -->\n        "+render_featured_news(news)+"\n        <!-- FEATURED_NEWS_END -->"
    s2=re.sub(r'<!-- FEATURED_NEWS_START -->.*?<!-- FEATURED_NEWS_END -->',featured,s2,flags=re.S)

    feed="<!-- ARTICLE_FEED_START -->\n"+render_article_feed(posts[:PAGE_SIZE])+"\n          <!-- ARTICLE_FEED_END -->"
    s2=re.sub(r'<!-- ARTICLE_FEED_START -->.*?<!-- ARTICLE_FEED_END -->',feed,s2,flags=re.S)

    pagination="<!-- ARTICLE_PAGINATION_START -->\n"+render_pagination(1,total_article_pages)+"\n        <!-- ARTICLE_PAGINATION_END -->"
    if "<!-- ARTICLE_PAGINATION_START -->" in s2:
        s2=re.sub(r'<!-- ARTICLE_PAGINATION_START -->.*?<!-- ARTICLE_PAGINATION_END -->',pagination,s2,flags=re.S)
    else:
        s2=s2.replace('</div>\n      </section>\n    </div>\n\n    <aside class="sidebar">',
                      '</div>\n        '+pagination+'\n      </section>\n    </div>\n\n    <aside class="sidebar">',1)

    if s2!=s:INDEX.write_text(s2,encoding="utf-8")
    print("Synced",len(news),"YouTube Community news posts and",len(reviews),"review posts")

if __name__=="__main__":main()
