#!/usr/bin/env python3
"""Use the real Community NEWS article template as the sole featured NEWS frontend.

The template is taken from a checked-in, published Community article, never
from a guessed reproduction. Editorial content, cover licensing and SEO metadata
continue to come from the individual generators.
"""
from pathlib import Path
import html
import re

ROOT=Path(__file__).resolve().parent.parent
REFERENCE=ROOT/"news-UgkxMfJRp-TjYXmdrt2qXU5RVA1pbFYf1H16.html"

def _reference():
    page=REFERENCE.read_text(encoding="utf-8")
    css=re.search(r'<style>(.*?)</style>',page,re.S)
    header=re.search(r'(<header class="zt-header">.*?</header><div class="zt-strip">.*?</div></div>)<main',page,re.S)
    sidebar=re.search(r'(<aside class="article-side">.*?</aside>)',page,re.S)
    footer=re.search(r'(<footer class="legal-footer">.*?</footer>)',page,re.S)
    if not (css and header and sidebar and footer):
        raise RuntimeError("Community NEWS reference layout incomplete")
    return css.group(1),header.group(1),sidebar.group(1),footer.group(1)

def _sidebar_from_current_news(reference_sidebar, current_page):
    """Sidebar HTML and look are identical to Community NEWS pages.

    Prefer the current latest published article links from Home. Retain the
    reference if the local feed is absent, never invent a review or thumbnail.
    """
    index=(ROOT/"index.html")
    if not index.is_file():
        return reference_sidebar
    page=index.read_text(encoding="utf-8")
    start=page.find('<!-- ARTICLE_FEED_START -->')
    end=page.find('<!-- ARTICLE_FEED_END -->',start)
    if start<0 or end<0:return reference_sidebar
    candidates=[]
    rows=re.findall(r'<article class="article-row".*?</article>',page[start:end],re.S)
    for row in rows:
        href=re.search(r'<h3><a href="([^"]+)">([^<]+)</a>',row)
        image=re.search(r'<img[^>]+src="([^"]+)"',row)
        if href and image:
            url=href.group(1)
            if not url.startswith("/") and not url.startswith("http"):url="/"+url
            if url==current_page:continue
            candidates.append((url,html.unescape(href.group(2)),image.group(1)))
        if len(candidates)>=6:break
    if len(candidates)<3:return reference_sidebar
    def item(entry):
        url,title,img=entry
        esc=lambda s:html.escape(s,quote=True)
        return ('<a class="compact-item" href="'+esc(url)+'"><img src="'+esc(img)+'" alt="'+esc(title)+'" loading="lazy">'
                '<div><h3>'+esc(title)+'</h3></div></a>')
    sidebar=re.sub(r'(<div class="compact-list">).*?(</div></section></aside>)',
                   lambda m:m.group(1)+''.join(map(item,candidates[:5]))+m.group(2),
                   reference_sidebar,count=1,flags=re.S)
    return sidebar

def decorate(page,section_label="News"):
    """Give a newly generated editorial page the actual Community NEWS frontend."""
    if 'class="news-detail-page"' in page:
        return page
    css,header,sidebar,footer=_reference()
    section_path={"Tech Impact":"/tech-today.html","Gaming Inside":"/gaming-today.html"}.get(section_label,"/news.html")
    if section_path!="/news.html":
        header=header.replace('<a class="active" href="/news.html">News</a>','<a href="/news.html">News</a>')
        header=header.replace('href="'+section_path+'">'+section_label+'</a>','class="active" href="'+section_path+'">'+section_label+'</a>')
        header=header.replace('<strong>News</strong>','<strong>'+section_label+'</strong>')
        header=header.replace('Notizie tech, gaming e novità dalla Community ZazoomTek','Articoli della sezione '+section_label)

    head=re.search(r'\A(.*?</head>)',page,re.S)
    main=re.search(r'<main\b[^>]*>(.*?)</main>',page,re.S)
    if not(head and main):
        raise RuntimeError("Cannot identify editorial article head/body")

    # Reference stylesheet is reused verbatim, except that article hero artwork
    # is never cropped. Light grey surround, header, sidebar, social CTA,
    # responsive breakpoints and typography all come from Community NEWS.
    css += """
.article-main figure.hero{margin:18px 0 22px}
.article-main figure.hero img{display:block;width:100%;height:auto;max-height:none;object-fit:contain;aspect-ratio:auto;margin:0}
.article-main figure.hero figcaption{font-size:12px;color:#777;line-height:1.45}
.article-main .eyebrow{font-size:12px;color:#c11734;text-transform:uppercase;font-weight:800;margin:0 0 12px}
.article-main .meta{color:#777;font-size:13px;margin:0 0 16px}
.article-main .lead{font-size:19px;line-height:1.65;color:#333}
.article-main .article-copy{font-size:1.05rem;line-height:1.65;color:#111}
.article-main .article-copy p{margin:0 0 18px}
.article-main .back-link{color:#c11734;font-weight:bold}
.article-main .image-credit,.article-main figcaption{font-size:12px;color:#777}
.article-main .image-credit a,.article-main figcaption a{color:#b7132a}
"""
    top=head.group(1)
    top,count=re.subn(r'<style>.*?</style>','<style>'+css+'</style>',top,count=1,flags=re.S)
    if count!=1:
        top=top.replace('</head>','<style>'+css+'</style></head>',1)
    article=main.group(1)
    title=re.search(r'<h1>(.*?)</h1>',article,re.S)
    title_plain=re.sub(r'<[^>]+>','',title.group(1)) if title else section_label
    breadcrumb=('<div class="breadcrumbs"><a href="/">Home</a> / <a href="'+section_path+'">'+html.escape(section_label)+'</a> / '
                +html.escape(html.unescape(title_plain))+'</div>')
    if section_path!="/news.html":
        article=article.replace('href="/news.html"','href="'+section_path+'"')
    # Preserve the original article body, image, captions and license credits.
    sidebar=_sidebar_from_current_news(sidebar,"")
    cta=('<section class="zt-subscribe-cta"><div class="zt-subscribe-copy">'
         '<span class="zt-subscribe-kicker">ZazoomTek Community</span>'
         '<h2>Non perderti le prossime recensioni e news</h2>'
         '<p>Segui ZazoomTek per ricevere nuovi contenuti su tecnologia, gaming, test e unboxing.</p></div>'
         '<div class="zt-social-icons" aria-label="Canali ZazoomTek">'
         '<a class="zt-social-icon" href="https://www.youtube.com/@ZazoomTek?sub_confirmation=1" target="_blank" rel="noopener" aria-label="YouTube">'
         '<img src="https://img.icons8.com/color/96/youtube-play.png" alt="YouTube"></a>'
         '<a class="zt-social-icon" href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener" aria-label="TikTok">'
         '<img src="https://img.icons8.com/color/96/tiktok--v1.png" alt="TikTok"></a>'
         '<a class="zt-social-icon" href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener" aria-label="WhatsApp">'
         '<img src="https://img.icons8.com/color/96/whatsapp--v1.png" alt="WhatsApp"></a>'
         '</div></section>')
    scripts=('<script>function ztInitSmartSticky(selector,mobileWidth){'
             'const el=document.querySelector(selector);if(!el)return;function update(){'
             'if(window.innerWidth<=mobileWidth){el.style.removeProperty("--zt-smart-sticky-top");return;}'
             'const gap=16;const top=Math.min(gap,window.innerHeight-el.offsetHeight-gap);'
             'el.style.setProperty("--zt-smart-sticky-top",top+"px");}update();'
             'window.addEventListener("resize",update,{passive:true});'
             'if("ResizeObserver" in window){new ResizeObserver(update).observe(el);}}'
             'document.addEventListener("DOMContentLoaded",function(){ztInitSmartSticky(".article-side",820);});</script>')
    result=(top+'<body>'+header+'<main class="news-detail-page"><div class="zt-wrap detail-grid">'
            '<article class="article-main">'+breadcrumb+article+cta+'</article>'+sidebar+'</div></main>'
            +footer+scripts+'</body></html>')
    for required in ('class="zt-header"','class="news-detail-page"','detail-grid',
                     'class="article-main"','class="article-side"','class="legal-footer"'):
        if required not in result:raise RuntimeError("Missing reference layout component: "+required)
    return result
