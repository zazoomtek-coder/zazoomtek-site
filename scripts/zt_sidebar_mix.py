#!/usr/bin/env python3
"""Keep internal archive sidebars editorially mixed, using real published content.

Reads the current News, Tech Impact, Gaming Inside HTML archives plus the
verified local YouTube cache. Changes only <aside class="news-sidebar">,
never homepage/video shelf, article copy or article-detail sidebars.
Run after Community sync and before each Firebase publish.
"""
from html import escape, unescape
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
ASIDE = re.compile(r'<aside class="news-sidebar">[\s\S]*?</aside>')
ROW = re.compile(r'<article class="news-row"\b[\s\S]*?</article>', re.I)
TITLE = re.compile(r'<h2[^>]*>\s*<a\s+href="([^"]+)"[^>]*>([\s\S]*?)</a>\s*</h2>', re.I)
IMG = re.compile(r'<img\s[^>]*src="([^"]+)"', re.I)
META = re.compile(r'<div class="news-meta"[^>]*>([\s\S]*?)</div>', re.I)
CLEAN = re.compile(r'<[^>]+>')

def news_rows(filename, max_count=10):
    file = ROOT / filename
    if not file.exists():
        return []
    markup = file.read_text(encoding="utf-8")
    result = []
    for row in ROW.finditer(markup):
        body = row.group()
        title = TITLE.search(body)
        if not title:
            continue
        link, name = unescape(title.group(1)), unescape(CLEAN.sub("", title.group(2))).strip()
        image = IMG.search(body)
        meta = META.search(body)
        if not link.startswith("/") or not name:
            continue
        result.append(dict(
            url=link, title=name,
            image=unescape(image.group(1)) if image else "/ChatGPT.png",
            date=unescape(CLEAN.sub("", meta.group(1))).strip() if meta else ""
        ))
        if len(result) >= max_count:
            break
    return result

def video_cache():
    file = ROOT / ".youtube-latest.json"
    if not file.exists():
        return []
    try:
        items = json.loads(file.read_text(encoding="utf-8"))
        return sorted(items, key=lambda x: x.get("publishedAt") or "", reverse=True)
    except (OSError, ValueError, TypeError):
        return []

def e(value):
    return escape(str(value or ""), quote=True)

def feature(heading, article, more):
    if not article:
        return ""
    image = e(article["image"])
    link = e(article["url"])
    title = e(article["title"])
    return (f'<section class="side-box zt-mix-feature">'
            f'<a class="module-title" href="{e(more)}">{e(heading)}</a>'
            f'<a href="{link}" class="zt-mix-feature-image"><img loading="lazy" src="{image}" alt="{title}"></a>'
            f'<div class="zt-mix-feature-copy"><h3><a href="{link}">{title}</a></h3>'
            f'<a class="zt-mix-read" href="{link}">LEGGI LA NOTIZIA ›</a></div></section>')

def mini_article(heading, article, section_url):
    if not article:
        return ""
    link = e(article["url"])
    title = e(article["title"])
    image = e(article["image"])
    return (f'<section class="side-box zt-mix-editorial">'
            f'<a class="module-title" href="{e(section_url)}">{e(heading)}</a>'
            f'<a class="zt-mix-editorial-row" href="{link}">'
            f'<img loading="lazy" src="{image}" alt="{title}">'
            f'<span>{title}</span></a></section>')

def recent_list(items):
    if not items:
        return ""
    rows = []
    seen = set()
    for item in items:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        rows.append(f'<a href="{e(item["url"])}" class="zt-mix-recent-row">'
                    f'<img loading="lazy" src="{e(item["image"])}" alt="">'
                    f'<span>{e(item["title"])}</span></a>')
        if len(rows) == 3:
            break
    return ('<section class="side-box zt-mix-recent">'
            '<a class="module-title" href="/news.html">Ultime News</a>'
            '<div class="zt-mix-recent-list">' + "".join(rows) + '</div></section>')

def video_box(category, caption, link, cache):
    v = next((v for v in cache if v.get("category") == category
              and not v.get("short") and not v.get("live")
              and not v.get("completedLive") and v.get("id")), None)
    if not v:
        return ""
    ident = e(v["id"])
    title = e(v.get("title"))
    return (f'<section class="side-box zt-mix-video">'
            f'<a class="module-title" href="{e(link)}">Video · {e(caption)}</a>'
            f'<a class="zt-mix-video-row" href="https://www.youtube.com/watch?v={ident}" target="_blank" rel="noopener">'
            f'<span class="zt-mix-video-thumb"><img src="https://i.ytimg.com/vi/{ident}/hqdefault.jpg" alt="{title}" loading="lazy"></span>'
            f'<span>{title}</span></a></section>')

def amazon():
    return ('<section class="side-box"><div class="module-title">Su Amazon</div>'
            '<div class="amazon-mini"><h3>I prodotti recensiti da ZazoomTek</h3>'
            '<p>Link affiliato Amazon. In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei senza alcun costo per l’utente.</p>'
            '<a href="https://www.amazon.it/gp/profile/amzn1.account.AE76ZMY5J56NNH3HUPWFJGVZEC5A?&amp;linkCode=ll2&amp;tag=zazoomtek-21&amp;linkId=d2dd9b9524bc6fb76da94e041a661201&amp;ref_=as_li_ss_tl" target="_blank" rel="nofollow sponsored noopener">VEDI I PRODOTTI SU AMAZON ›</a></div></section>')

def build_sidebar(kind, news, tech, gaming, videos):
    if not news:
        return None # Never wipe the existing column on a partial import.
    featured = feature("In evidenza",news[0],"/news.html")
    recent = recent_list(news[1:5])
    tech_module = mini_article("Tech Impact",tech[0] if tech else None,"/tech-today.html")
    gaming_module = mini_article("Gaming Inside",gaming[0] if gaming else None,"/gaming-today.html")
    reviews = video_box("recensioni","Recensioni","/recensioni.html",videos)
    tests = video_box("test","Test","/test.html",videos)
    unboxing = video_box("unboxing","Unboxing","/unboxing.html",videos)
    gaming_video = video_box("gaming","Gaming","/gaming.html",videos)
    choices={
        "news":[featured,reviews,recent,tech_module,gaming_video,gaming_module],
        "reviews":[featured,tests,recent,gaming_module,unboxing,tech_module],
        "tech":[tech_module,reviews,recent,gaming_module,tests,featured],
        "gaming":[gaming_module,gaming_video,recent,tech_module,reviews,featured],
        "guides":[featured,recent,tech_module,unboxing,gaming_module,reviews],
    }
    return '<aside class="news-sidebar zt-side-mix">' + amazon() + "".join(x for x in choices[kind] if x) + '</aside>'

def page_kind(filename):
    if re.fullmatch(r'news(?:-\d+)?\.html',filename):
        return "news"
    if re.fullmatch(r'recensioni-scritte(?:-\d+)?\.html',filename):
        return "reviews"
    if filename == "tech-today.html": return "tech"
    if filename == "gaming-today.html": return "gaming"
    if filename == "guide.html": return "guides"
    return None

def refresh_sidebars():
    news = news_rows("news.html")
    tech = news_rows("tech-today.html",3)
    gaming = news_rows("gaming-today.html",3)
    videos = video_cache()
    changed = 0
    for path in sorted(ROOT.glob("*.html")):
        kind = page_kind(path.name)
        if not kind:
            continue
        original = path.read_text(encoding="utf-8")
        if not ASIDE.search(original):
            continue
        sidebar = build_sidebar(kind,news,tech,gaming,videos)
        if not sidebar:
            continue
        output = ASIDE.sub(lambda _:sidebar,original,count=1)
        if output != original:
            path.write_text(output,encoding="utf-8")
            changed += 1
    print(f"Mixed archive sidebars refreshed: {changed} pages, {len(news)} current news.")

if __name__ == "__main__":
    refresh_sidebars()
