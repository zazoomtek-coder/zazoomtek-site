#!/usr/bin/env python3
"""Independent five-card 'Da non perdere' renderer; no legacy dependencies."""
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from editorial_workday import editorial_order, FALLBACK
import html
import re

ROOT=Path(__file__).resolve().parents[1]
START="<!-- POPULAR_NEWS_ITEMS_START -->"
END="<!-- POPULAR_NEWS_ITEMS_END -->"
STYLE_ID="zt-services10-popular-five"
STYLE='''<style id="zt-services10-popular-five">
/* Five visible Tech stories, no legacy three-card clipping. */
html body #zt-popular-box .zt-popular-list>.zt-popular-article:nth-of-type(-n+5)
{display:grid!important;visibility:visible!important}
html body #zt-popular-box .zt-popular-list>.zt-popular-article:nth-of-type(n+6)
{display:none!important}
#zt-popular-box .zt-popular-list{max-height:none!important;height:auto!important;overflow:visible!important}
</style>'''

def deduplicate_cards(document:str)->list[dict]:
    """One recent Tech story per normalized URL/title, newest first."""
    if "<!-- ARTICLE_FEED_START -->" not in document or "<!-- ARTICLE_FEED_END -->" not in document:return []
    section=document.split("<!-- ARTICLE_FEED_START -->",1)[1].split("<!-- ARTICLE_FEED_END -->",1)[0]
    rows=[]
    for article in re.findall(r'<article\b[^>]*class="article-row"[^>]*>[\s\S]*?</article>',section,re.I):
        if not re.search(r'data-post-category=["\']tech["\']',article,re.I):continue
        title=re.search(r'<h3\b[^>]*>\s*<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>([\s\S]*?)</a>',article,re.I)
        picture=re.search(r'<img\b[^>]*\bsrc=["\']([^"\']+)',article,re.I)
        date=re.search(r'data-published-at=["\'](20\d\d-\d\d-\d\d)',article,re.I)
        if not title:continue
        href=html.unescape(title.group(1)).split("?",1)[0].strip()
        if not href.startswith("/"):href="/"+href
        label=re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>","",title.group(2)))).strip()
        cover=html.unescape(picture.group(1)) if picture else FALLBACK
        if label:rows.append(dict(url=href,title=label,image=cover,date=date.group(1) if date else ""))
    ranked=editorial_order(
        [{**row,"published":row.get("date") or ""} for row in rows],
        group="tech",page="home-popular")
    return ranked

def cards_from_home(document:str)->list[str]:
    out=[]
    for item in deduplicate_cards(document)[:5]:
        href=html.escape(item["url"],quote=True)
        label=html.escape(item["title"],quote=True)
        image=html.escape(item["image"],quote=True)
        out.append('<a class="zt-popular-article zt-home-editorial-card" href="'+href+'" title="'+label+
                   '"><img src="'+image+'" alt="'+label+
                   '" loading="lazy" onerror="this.onerror=null;this.src=\''+FALLBACK+
                   '\'"><span class="zt-popular-copy"><span '+
                   'class="zt-popular-category">TECNOLOGIA</span><strong>'+
                   label+'</strong></span></a>')
    return out

def update(root:Path=ROOT)->int:
    page=root/"index.html"
    if not page.is_file():return 0
    original=page.read_text(encoding="utf-8")
    if START not in original or END not in original:return 0
    selected=cards_from_home(original)
    a=original.index(START)+len(START)
    b=original.index(END,a)
    document=original[:a]+"\n"+"\n".join(selected)+"\n"+original[b:]
    for old_id in (STYLE_ID,"zt-services10-popular-eight"):
        document=re.sub(r'<style id="'+old_id+r'">[\s\S]*?</style>',"",document)
    document=document.replace("</head>",STYLE+"\n</head>",1)
    if document!=original:page.write_text(document,encoding="utf-8")
    print("Da non perdere: same-day plus rotating latest Tech stories:",len(selected))
    return len(selected)

if __name__=="__main__":
    update()
