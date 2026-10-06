#!/usr/bin/env python3
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

def parse(s):
    data=initial_data(s)
    posts=[];seen=set()
    parse_nodes(data,posts,seen)
    key,ver=innertube_config(s)
    tokens=continuation_tokens(data)
    used=set()
    pages=0
    # Continue loading older Community posts until at least 5 reviews are found
    # or a safe pagination limit is reached.
    while len(posts)<40 and tokens and pages<40:
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
:root{--orange:#00035f;--accent-blue:#00035f;--accent-mid:#230015;--accent-red:#800001;--accent-gradient:linear-gradient(90deg,var(--accent-blue) 0%,var(--accent-mid) 48%,var(--accent-red) 100%);--line:#ddd;--text:#303030;--muted:#777}
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
.legal-footer{margin-top:32px;background:#161616;color:#aaa;padding:24px 16px;font-size:.78rem;text-align:center}.legal-footer .wrap{max-width:1100px}.legal-footer a{color:#ddd;text-decoration:none}.legal-footer span{display:inline-block;margin-top:8px}</style>"""

ARCHIVE_STYLE = """<style>
:root{--orange:#ff7a00;--line:#ddd;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif}
.wrap{width:min(1320px,calc(100% - 36px));margin:auto}header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--accent-gradient) 1}
.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}
.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}
.nav a:hover,.nav a.active{background:var(--accent-gradient)}a{color:inherit;text-decoration:none}
main{background:#fff;padding:24px 24px 40px}h1{margin:4px 0 6px}.sub{color:var(--muted);margin-bottom:18px}
.community-posts-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.community-post-card{background:#fff;border:1px solid var(--line);border-top:5px solid transparent;border-image:var(--accent-gradient) 1;min-width:0}
.community-post-card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block}.community-post-copy{padding:14px}.community-post-copy p{margin:0;font-size:1rem;line-height:1.35;font-weight:800}
.community-post-copy small{display:block;margin-top:9px;color:var(--muted);font-size:.72rem}.community-post-copy a{display:inline-block;margin-top:10px;background:var(--accent-gradient);color:#fff;padding:7px 10px;font-size:.72rem;font-weight:900}
@media(max-width:900px){.community-posts-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.community-posts-grid{grid-template-columns:1fr}}
</style>"""

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
    return '''<footer class="legal-footer"><div class="wrap"><a href="/privacy.html">Privacy Policy</a> · <a href="/cookie.html">Cookie Policy</a> · <a href="/disclaimer.html">Disclaimer</a> · <a href="/note-legali.html">Note legali</a><br><span>© 2026 ZazoomTek</span></div></footer>'''

def editorial_header(active=""):
    return '<header><div class="wrap headrow"><a class="brand" href="/">ZazoomTek</a>'+editorial_nav(active)+'</div></header>'

def write_review_page(p):
    title=review_title(p)
    slug=review_slug(p)
    img=(f'<img src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+DETAIL_STYLE+'</head><body>'
        +editorial_header("recensioni")
        +f'<main class="wrap"><section class="hero">{img}<div class="hero-copy"><h1>{html.escape(title)}</h1>'
        +f'<div class="meta">{html.escape(p.get("published") or "")} · ZazoomTek</div></div></section>'
        +f'<article class="article">{review_body_html(p)}</article></main>'+legal_footer()+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_review_cards(posts, home=False):
    cards=[]
    for p in posts:
        title=review_title(p); slug=review_slug(p)
        im=f'<a href="{slug}"><img src="{html.escape(p["image"])}" alt="{html.escape(title)}" loading="lazy"></a>' if p.get("image") else ""
        cards.append(f'''    <article class="community-post-card">{im}<div class="community-post-copy"><p>{html.escape(title)}</p><small>{html.escape(p.get("published") or "")}</small><a href="{slug}">Leggi la recensione →</a></div></article>''')
    return "\n".join(cards)

def write_review_archive(reviews):
    cards=render_review_cards(reviews)
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>Recensioni | ZazoomTek</title>'
        '<meta name="description" content="Archivio delle recensioni scritte di ZazoomTek.">'
        '<link rel="canonical" href="https://zazoomtek.it/recensioni-scritte.html">'+ARCHIVE_STYLE+'</head><body>'
        +editorial_header("recensioni")
        +f'<main class="wrap"><h1>Recensioni</h1><p class="sub">Le recensioni scritte pubblicate da ZazoomTek, dalla più recente.</p><section class="community-posts-grid">{cards}</section></main>'+legal_footer()+'</body></html>'
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

def write_news_page(p):
    title=news_title(p)
    slug=news_slug(p)
    img=(f'<img src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+DETAIL_STYLE+'</head><body>'
        +editorial_header("news")
        +f'<main class="wrap"><section class="hero">{img}<div class="hero-copy"><h1>{html.escape(title)}</h1>'
        +f'<div class="meta">{html.escape(p.get("published") or "")} · ZazoomTek</div></div></section>'
        +f'<article class="article">{news_body_html(p)}</article></main>'+legal_footer()+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_news_cards(posts):
    cards=[]
    for p in posts:
        title=news_title(p); slug=news_slug(p)
        im=f'<a href="{slug}"><img src="{html.escape(p["image"])}" alt="{html.escape(title)}" loading="lazy"></a>' if p.get("image") else ""
        cards.append(f'''    <article class="community-post-card">{im}<div class="community-post-copy"><p><a href="{slug}">{html.escape(title)}</a></p><small>{html.escape(p.get("published") or "")}</small><a href="{slug}">Leggi la News →</a></div></article>''')
    return "\n".join(cards)

def write_news_archive(news):
    cards=render_news_cards(news)
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>News | ZazoomTek</title>'
        '<meta name="description" content="Le ultime News pubblicate da ZazoomTek.">'
        '<link rel="canonical" href="https://zazoomtek.it/news.html">'+ARCHIVE_STYLE+'</head><body>'
        +editorial_header("news")
        +f'<main class="wrap"><h1>News</h1><p class="sub">Le ultime News pubblicate da ZazoomTek.</p><section class="community-posts-grid">{cards}</section></main>'+legal_footer()+'</body></html>'
    )
    Path("news.html").write_text(page,encoding="utf-8")

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
            f'<div class="article-copy"><span class="article-kicker">{kind}</span>'
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

def main():
    posts=parse(fetch())
    if not posts:
        print("No public posts parsed; keeping current site unchanged.")
        return
    STATE.write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    reviews=[p for p in posts if is_review(p)]
    news=[p for p in posts if not is_review(p)]
    for p in reviews: write_review_page(p)
    write_review_archive(reviews)
    for p in news: write_news_page(p)
    write_news_archive(news)
    # sitemap.xml is manually approved; automatic YouTube sync must not rewrite it.
    s=INDEX.read_text(encoding="utf-8")
    s2=s
    ticker="<!-- NEWS_TICKER_START -->\n"+render_ticker(news)+"\n    <!-- NEWS_TICKER_END -->"
    s2=re.sub(r'<!-- NEWS_TICKER_START -->.*?<!-- NEWS_TICKER_END -->',ticker,s2,flags=re.S)

    featured="<!-- FEATURED_NEWS_START -->\n        "+render_featured_news(news)+"\n        <!-- FEATURED_NEWS_END -->"
    s2=re.sub(r'<!-- FEATURED_NEWS_START -->.*?<!-- FEATURED_NEWS_END -->',featured,s2,flags=re.S)

    feed="<!-- ARTICLE_FEED_START -->\n"+render_article_feed(posts[:20])+"\n          <!-- ARTICLE_FEED_END -->"
    s2=re.sub(r'<!-- ARTICLE_FEED_START -->.*?<!-- ARTICLE_FEED_END -->',feed,s2,flags=re.S)

    if s2!=s:INDEX.write_text(s2,encoding="utf-8")
    print("Synced",len(news),"YouTube Community news posts and",len(reviews),"review posts")

if __name__=="__main__":main()
