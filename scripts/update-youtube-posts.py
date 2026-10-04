#!/usr/bin/env python3
import json,re,html,urllib.request
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
    while len([p for p in posts if is_review(p)])<5 and tokens and pages<40:
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

def write_review_page(p):
    title=review_title(p)
    slug=review_slug(p)
    img=(f'<img src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    page=f'''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}"><link rel="canonical" href="https://zazoomtek.web.app/{slug}"><style>:root{{--panel:#0b1626;--line:rgba(111,148,204,.24);--text:#f7f9ff;--muted:#9ca9bd;--cyan:#20d9ff;--blue:#2588ff}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#07111f,#050b14);color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.68}}.wrap{{width:min(980px,calc(100% - 32px));margin:auto}}header{{padding:18px 0;border-bottom:1px solid var(--line)}}a{{color:inherit;text-decoration:none}}.back{{display:block;margin-top:8px;color:#7de9ff;font-weight:800}}.hero{{margin:26px 0 18px;border-radius:18px;overflow:hidden;border:1px solid var(--line);background:var(--panel)}}.hero img{{width:100%;max-height:560px;object-fit:cover;display:block}}.hero-copy{{padding:22px}}.hero h1{{margin:0 0 8px;font-size:clamp(1.8rem,4vw,3rem);line-height:1.08}}.meta{{color:var(--muted);font-size:.9rem}}.article{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:28px;margin-bottom:36px}}.article h2{{margin:30px 0 10px;color:#8beeff}}.article p{{margin:0 0 18px;white-space:pre-line}}.review-score{{margin-top:28px;padding:16px 18px;border-radius:14px;background:linear-gradient(135deg,var(--cyan),var(--blue));color:#04101c;font-size:1.35rem;font-weight:900}}</style></head><body><header><div class="wrap"><strong><a href="/">ZazoomTek</a></strong><a class="back" href="recensioni-scritte.html">← Tutte le recensioni</a></div></header><main class="wrap"><section class="hero">{img}<div class="hero-copy"><h1>{html.escape(title)}</h1><div class="meta">{html.escape(p.get("published") or "")} · ZazoomTek</div></div></section><article class="article">{review_body_html(p)}</article></main></body></html>'''
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
    page=f'''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Recensioni | ZazoomTek</title><meta name="description" content="Archivio delle recensioni scritte di ZazoomTek."><link rel="canonical" href="https://zazoomtek.web.app/recensioni-scritte.html"><style>:root{{--panel:#0b1626;--line:rgba(111,148,204,.24);--text:#f7f9ff;--muted:#9ca9bd}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#07111f,#050b14);color:var(--text);font-family:Arial,Helvetica,sans-serif}}.wrap{{width:min(1420px,calc(100% - 36px));margin:auto}}header{{padding:18px 0;border-bottom:1px solid var(--line)}}a{{color:inherit;text-decoration:none}}h1{{margin:28px 0 6px}}.sub{{color:var(--muted)}}.community-posts-grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:18px 0 40px}}.community-post-card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;min-width:0}}.community-post-card img{{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}}.community-post-copy{{padding:14px}}.community-post-copy p{{margin:0;font-size:.86rem;line-height:1.45}}.community-post-copy small{{display:block;margin-top:10px;color:var(--muted);font-size:.72rem}}.community-post-copy a{{display:inline-block;margin-top:10px;color:#77e8ff;font-size:.78rem;font-weight:900}}@media(max-width:1000px){{.community-posts-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:600px){{.community-posts-grid{{grid-template-columns:1fr}}}}</style></head><body><header><div class="wrap"><strong><a href="/">ZazoomTek</a></strong></div></header><main class="wrap"><h1>Recensioni</h1><p class="sub">Le recensioni scritte pubblicate da ZazoomTek, dalla più recente.</p><section class="community-posts-grid">{cards}</section></main></body></html>'''
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
    page=f'''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}"><link rel="canonical" href="https://zazoomtek.web.app/{slug}"><style>:root{{--panel:#0b1626;--line:rgba(111,148,204,.24);--text:#f7f9ff;--muted:#9ca9bd;--cyan:#20d9ff;--blue:#2588ff}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#07111f,#050b14);color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.68}}.wrap{{width:min(980px,calc(100% - 32px));margin:auto}}header{{padding:18px 0;border-bottom:1px solid var(--line)}}a{{color:inherit;text-decoration:none}}.back{{display:block;margin-top:8px;color:#7de9ff;font-weight:800}}.hero{{margin:26px 0 18px;border-radius:18px;overflow:hidden;border:1px solid var(--line);background:var(--panel)}}.hero img{{width:100%;max-height:560px;object-fit:cover;display:block}}.hero-copy{{padding:22px}}.hero h1{{margin:0 0 8px;font-size:clamp(1.8rem,4vw,3rem);line-height:1.08}}.meta{{color:var(--muted);font-size:.9rem}}.article{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:28px;margin-bottom:36px}}.article p{{margin:0 0 18px;white-space:pre-line}}</style></head><body><header><div class="wrap"><strong><a href="/">ZazoomTek</a></strong><a class="back" href="news.html">← Tutte le News</a></div></header><main class="wrap"><section class="hero">{img}<div class="hero-copy"><h1>{html.escape(title)}</h1><div class="meta">{html.escape(p.get("published") or "")} · ZazoomTek</div></div></section><article class="article">{news_body_html(p)}</article></main></body></html>'''
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
    page=f'''<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>News | ZazoomTek</title><meta name="description" content="Le ultime News pubblicate da ZazoomTek."><link rel="canonical" href="https://zazoomtek.web.app/news.html"><style>:root{{--panel:#0b1626;--line:rgba(111,148,204,.24);--text:#f7f9ff;--muted:#9ca9bd}}*{{box-sizing:border-box}}body{{margin:0;background:linear-gradient(180deg,#07111f,#050b14);color:var(--text);font-family:Arial,Helvetica,sans-serif}}.wrap{{width:min(1420px,calc(100% - 36px));margin:auto}}header{{padding:18px 0;border-bottom:1px solid var(--line)}}a{{color:inherit;text-decoration:none}}h1{{margin:28px 0 6px}}.sub{{color:var(--muted)}}.community-posts-grid{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:18px 0 40px}}.community-post-card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;overflow:hidden;min-width:0}}.community-post-card img{{width:100%;aspect-ratio:1/1;object-fit:cover;display:block}}.community-post-copy{{padding:14px}}.community-post-copy p{{margin:0;font-size:.86rem;line-height:1.45}}.community-post-copy small{{display:block;margin-top:10px;color:var(--muted);font-size:.72rem}}.community-post-copy a{{display:inline-block;margin-top:10px;color:#77e8ff;font-size:.78rem;font-weight:900}}@media(max-width:1000px){{.community-posts-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}@media(max-width:600px){{.community-posts-grid{{grid-template-columns:1fr}}}}</style></head><body><header><div class="wrap"><strong><a href="/">ZazoomTek</a></strong></div></header><main class="wrap"><h1>News</h1><p class="sub">Le ultime News pubblicate da ZazoomTek.</p><section class="community-posts-grid">{cards}</section></main></body></html>'''
    Path("news.html").write_text(page,encoding="utf-8")

def render(posts):
    return render_news_cards(posts)


def update_sitemap():
    base=["","recensioni.html","test.html","unboxing.html","gaming.html","news.html","recensioni-scritte.html","chi-sono.html","contatti.html"]
    dynamic=sorted([p.name for p in Path(".").glob("news-*.html")]+[p.name for p in Path(".").glob("recensione-*.html")])
    urls=[]
    seen=set()
    for n in base+dynamic:
        if n in seen: continue
        seen.add(n)
        urls.append(f"  <url><loc>https://zazoomtek.web.app/{html.escape(n)}</loc></url>")
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+"\n".join(urls)+'\n</urlset>\n'
    Path("sitemap.xml").write_text(xml,encoding="utf-8")

def main():
    posts=parse(fetch())
    if not posts:
        print("No public posts parsed; keeping current site unchanged.")
        return
    STATE.write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    reviews=[p for p in posts if is_review(p)][:5]
    news=[p for p in posts if not is_review(p)][:5]
    for p in reviews: write_review_page(p)
    write_review_archive(reviews)
    for p in news: write_news_page(p)
    write_news_archive(news)
    update_sitemap()

    s=INDEX.read_text(encoding="utf-8")
    repl="<!-- COMMUNITY_POSTS_START -->\n  <section class=\"community-posts-grid\" id=\"community-posts-grid\">\n"+render(news)+"\n  </section>\n  <!-- COMMUNITY_POSTS_END -->"
    s2=re.sub(r'<!-- COMMUNITY_POSTS_START -->.*?<!-- COMMUNITY_POSTS_END -->',repl,s,flags=re.S)

    home_reviews=reviews[:5]
    rrepl="<!-- PATREON_REVIEWS_START -->\n  <section class=\"community-posts-grid\" id=\"patreon-reviews-grid\">\n"+render_review_cards(home_reviews,True)+"\n  </section>\n  <!-- PATREON_REVIEWS_END -->"
    s2=re.sub(r'<!-- PATREON_REVIEWS_START -->.*?<!-- PATREON_REVIEWS_END -->',rrepl,s2,flags=re.S)
    s2=s2.replace('href="https://www.patreon.com/c/ZazoomTek/posts" target="_blank" rel="noopener">Vedi tutte →</a>','href="recensioni-scritte.html">Vedi tutte →</a>')
    s2=s2.replace('href="https://www.youtube.com/@ZazoomTek/posts" target="_blank" rel="noopener">Vedi tutti →</a>','href="news.html">Vedi tutti →</a>')
    if s2!=s:INDEX.write_text(s2,encoding="utf-8")
    print("Synced",len(news),"YouTube Community news posts and",len(reviews),"review posts")

if __name__=="__main__":main()
