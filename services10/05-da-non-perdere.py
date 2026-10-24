#!/usr/bin/env python3
"""Independent five-card 'Da non perdere' renderer; no legacy dependencies."""
from pathlib import Path
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

def cards_from_home(document: str) -> list[str]:
    found=[];seen=set();titles=set()
    if "<!-- ARTICLE_FEED_START -->" not in document:
        return []
    news=document.split("<!-- ARTICLE_FEED_START -->",1)[1].split("<!-- ARTICLE_FEED_END -->",1)[0]
    for article in re.findall(r'<article\b[^>]*class="article-row"[^>]*>[\s\S]*?</article>',news,re.I):
        if not re.search(r'data-post-category="tech"',article,re.I):
            continue
        title=re.search(r'<h3\b[^>]*>\s*<a\b[^>]*href="([^"]+)"[^>]*>([\s\S]*?)</a>',article,re.I)
        picture=re.search(r'<img\b[^>]*\bsrc="([^"]+)"',article,re.I)
        if not title or not picture:continue
        href=html.unescape(title.group(1))
        if not href.startswith("/"):href="/"+href
        if href in seen:continue
        seen.add(href)
        label=html.unescape(re.sub(r'<[^>]+>','',title.group(2))).strip()
        if not label:continue
        normalized=re.sub(r"\s+"," ",label).casefold()
        if normalized in titles:continue
        titles.add(normalized)
        cover=html.unescape(picture.group(1))
        found.append('<a class="zt-popular-article" href="'+html.escape(href,quote=True)+
                     '" title="'+html.escape(label,quote=True)+'"><img src="'+
                     html.escape(cover,quote=True)+'" alt="'+html.escape(label,quote=True)+
                     '" loading="lazy"><span class="zt-popular-copy"><span '+
                     'class="zt-popular-category">TECNOLOGIA</span><strong>'+
                     html.escape(label)+'</strong></span></a>')
        if len(found)==5:break
    return found

def update(root:Path=ROOT) -> int:
    page=root/"index.html"
    if not page.is_file():return 0
    document=page.read_text(encoding="utf-8")
    if START not in document or END not in document:return 0
    selected=cards_from_home(document)
    if selected:
        old=document.split(START,1)[1].split(END,1)[0]
        existing=re.findall(r'<a class="zt-popular-article"[\s\S]*?</a>',old)
        known={re.search(r'href="([^"]+)"',c).group(1) for c in selected}
        known_titles=set()
        for card in selected:
            title=re.search(r'<strong>([\s\S]*?)</strong>',card)
            if title:known_titles.add(re.sub(r"\s+"," ",html.unescape(title.group(1))).casefold())
        for card in existing:
            href=re.search(r'href="([^"]+)"',card)
            title=re.search(r'<strong>([\s\S]*?)</strong>',card)
            title_key=re.sub(r"\s+"," ",html.unescape(title.group(1))).casefold() if title else ""
            if href and href.group(1) not in known and title_key not in known_titles and len(selected)<5:
                selected.append(card);known.add(href.group(1));known_titles.add(title_key)
    else:
        selected=re.findall(r'<a class="zt-popular-article"[\s\S]*?</a>',
                            document.split(START,1)[1].split(END,1)[0])[:5]
    if selected:
        a=document.index(START)+len(START)
        b=document.index(END,a)
        document=document[:a]+"\n"+"\n".join(selected[:5])+"\n"+document[b:]
    for old_id in (STYLE_ID,'zt-services10-popular-eight'):
        document=re.sub(r'<style id="'+old_id+r'">[\s\S]*?</style>',"",document)
    document=document.replace("</head>",STYLE+"\n</head>",1)
    page.write_text(document,encoding="utf-8")
    print("Da non perdere:",min(len(selected),5),"unique visible Tech cards prepared")
    return min(len(selected),5)

if __name__=="__main__":
    update()
