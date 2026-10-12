#!/usr/bin/env python3
"""Ensure the site-wide CSS before Firebase deploy, including generated pages."""
from pathlib import Path
from zt_footer import unify_footer
from zt_sidebar_mix import refresh_sidebars
import re

root=Path(__file__).resolve().parents[1]
css_tag='<link rel="stylesheet" href="/zt-design.css?v=20261012compactboxes" data-zt-design="20261010">'
js_tag='<script src="/zt-visual.js?v=20261012compactboxes" defer></script>'
changed=0
for path in root.rglob('*.html'):
    if any(p in {'.git','node_modules','functions'} for p in path.relative_to(root).parts):
        continue
    html=path.read_text(encoding='utf-8')
    if '</head>' not in html.lower():
        continue
    original=html
    if 'href="/zt-design.css' in html:
        html=re.sub(r'(?<=href=")/zt-design[.]css(?:[?][^"]*)?',
                    "/zt-design.css?v=20261012compactboxes",html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:css_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    if 'src="/zt-visual.js' in html:
        html=re.sub(r'(?<=src=")/zt-visual[.]js(?:[?][^"]*)?',
                    "/zt-visual.js?v=20261012compactboxes",html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:js_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    # Ensure the official ZazoomTek.it masthead is applied to every generated
    # article and static page, including pages rebuilt by YouTube sync.
    home_old='<span class="brand-copy"><strong>ZazoomTek</strong><small>TECH · GAMING · COMMUNITY</small></span>'
    brand_markup="<span class=\"zt-brand-copy\"><strong class=\"zt-wordmark\" aria-label=\"ZazoomTek\"><span class=\"zt-mark-blue\" aria-hidden=\"true\">ZAZOOM</span><span class=\"zt-mark-red\" aria-hidden=\"true\">TEK</span></strong><small class=\"zt-brand-tagline\">TECH · GAMING · COMMUNITY</small></span>"
    # Strip the suffix from older published pages, too.
    html=html.replace('<span class="zt-mark-tld" aria-hidden="true">.it</span>','')
    html=html.replace('class="zt-wordmark" aria-label="ZazoomTek.it"','class="zt-wordmark" aria-label="ZazoomTek"')
    html=html.replace(home_old,brand_markup)
    html=re.sub(r'(?<=<img src="/ChatGPT.png" alt="ZazoomTek">)<strong>ZazoomTek</strong>(?=</a>)',brand_markup,html)
    # The Home must NOT display the community subscription banner.
    # All editorial articles and other site pages retain it.
    html=unify_footer(html, include_community=(path != root / "index.html"))
    if html!=original:
        path.write_text(html,encoding='utf-8')
        changed+=1
print(f"ZazoomTek: shared design ensured on {changed} HTML pages.")

# Keep archive columns editorially varied after every Firebase build.
refresh_sidebars()

# Rebuild related links for all real editorial articles, including special
# features and Guide pages, on every Hosting publication.
import runpy
runpy.run_path(str(root / 'scripts' / 'build-related-content.py'), run_name='__main__')

# Last pass: AFTER related generation, put the single approved Community banner
# directly underneath the final related section in EACH article's left column.
# Validate the final deployed HTML; fail the publish if a guide/news/review is
# missing its related links, banner, or correct ordering.
from zt_footer import COMMUNITY_START, COMMUNITY_END, _RELATED_SECTION, _matching_close
article_tag = re.compile(
    r'<article\b[^>]*class=["\'][^"\']*\barticle-main\b[^"\']*["\'][^>]*>', re.I
)
checked = 0
corrected = 0
witcher_checked = False
for path in sorted(root.glob('*.html')):
    if path.name == 'index.html' or path.name.startswith('preview-'):
        continue
    page = path.read_text(encoding='utf-8')
    match = article_tag.search(page)
    if not match:
        continue  # Static/overview pages do not have "Articoli correlati".
    original = page
    page = unify_footer(page)
    match = article_tag.search(page)
    article_end = _matching_close(page, match.end(), 'article')
    related = list(_RELATED_SECTION.finditer(page, match.end(), article_end))
    if not related:
        # Legacy imported stubs sometimes contain no article text at all;
        # they aren't editorial articles and can't have meaningful related
        # recommendations. Do not block real articles because of empty stubs.
        if re.search(r'<div\s+class=["\']article-body["\']\s*>\s*</div>', page, re.I):
            print(f"Skipped empty import stub (no related articles): {path.name}")
            continue
        raise RuntimeError(f"{path.name}: missing Articoli correlati; refusing to deploy")
    if len(related) != 1:
        raise RuntimeError(f"{path.name}: expected exactly one Articoli correlati section at the bottom of the article")
    last_related = related[-1]
    related_end = _matching_close(page, last_related.end(), 'section') + len('</section>')
    banner_at = page.find(COMMUNITY_START, match.end(), article_end)
    banner_end = page.find(COMMUNITY_END, match.end(), article_end)
    if banner_at < 0 or banner_end < 0 or banner_at <= related_end:
        raise RuntimeError(f"{path.name}: Community banner not below Articoli correlati")
    if page[related_end:banner_at].strip():
        raise RuntimeError(f"{path.name}: Community banner not IMMEDIATELY below related cards")
    if page.count(COMMUNITY_START) != 1 or page.count(COMMUNITY_END) != 1:
        raise RuntimeError(f"{path.name}: duplicate or missing Community banner")
    # Mandatory editorial sidebar, without Articoli correlati (which belong
    # exclusively at the bottom of the article).
    # Any new article without these boxes
    # aborts Firebase deployment instead of silently publishing incomplete.
    if page.count('data-zt-auto="editorial"') != 1:
        raise RuntimeError(f"{path.name}: missing right-column Dalla redazione; refusing to deploy")
    if 'data-zt-auto="related"' in page:
        raise RuntimeError(f"{path.name}: related articles found outside the bottom article section")
    # No editorial article can ship with only two minimal right-column boxes.
    # Require the fully populated shared sidebar as well as recommendations.
    aside = re.search(
        r'<aside\b[^>]*class=["\'][^"\']*(?:article-side|news-sidebar)[^"\']*["\'][^>]*>[\s\S]*?</aside>',
        page, re.I,
    )
    if not aside:
        raise RuntimeError(f"{path.name}: missing right editorial column")
    widgets = aside.group(0)
    # Mandatory visual order: featured news is first, not Dalla redazione.
    first_widget = re.match(
        r'\s*<section\b[^>]*class=["\'][^"\']*\bzt-mix-feature\b[^"\']*["\'][^>]*>',
        widgets[widgets.index(">") + 1:], re.I,
    )
    if not first_widget or "News in evidenza" not in widgets[:1300]:
        raise RuntimeError(f"{path.name}: News in evidenza must be FIRST in the right column")
    required = ('zt-mix-feature', 'zt-amazon-partner',
                'zt-mix-recent', 'data-zt-auto="editorial"')
    if any(token not in widgets for token in required):
        raise RuntimeError(f"{path.name}: incomplete right editorial column")
    if re.search(r'>\s*Articoli correlati\s*<', widgets, re.I):
        raise RuntimeError(f"{path.name}: Articoli correlati cannot appear in the right sidebar")
    if '<section class="zt-community-banner"' not in page[related_end:banner_end]:
        raise RuntimeError(f"{path.name}: missing black Community banner below related articles")

    if page != original:
        path.write_text(page, encoding='utf-8')
        corrected += 1
    checked += 1
    if path.name == 'guida-the-witcher-3-remastered-pc-aumentare-fps.html':
        witcher_checked = True
        print('Verified The Witcher 3: related articles followed immediately by Community banner in article column')
if not witcher_checked:
    raise RuntimeError('Witcher 3 guide not checked for related articles and Community banner')
# Validate all archives and Home pages too; generated pages cannot bypass the rule.
for check_path in sorted(root.glob('*.html')):
    if check_path.name.startswith("preview-"):
        continue
    checked_page = check_path.read_text(encoding='utf-8')
    for right in re.finditer(
        r'<aside\b[^>]*class=["\'][^"\']*\bzt-side-mix\b[^"\']*["\'][^>]*>',
        checked_page, re.I,
    ):
        if not re.match(
            r'\s*<section\b[^>]*class=["\'][^"\']*\bzt-mix-feature\b[^"\']*["\'][^>]*>',
            checked_page[right.end():], re.I,
        ):
            raise RuntimeError(f"{check_path.name}: first right widget must be News in evidenza")
    if check_path.name == "index.html" or re.fullmatch(r'pagina-\d+\.html', check_path.name):
        home_right = re.search(r'<aside\s+class="sidebar"[^>]*>', checked_page, re.I)
        if not home_right or not re.match(
            r'\s*<!-- ZT_HOME_SIDEBAR_FEATURE_START -->\s*<section\b[^>]*class=["\'][^"\']*\bzt-mix-feature\b[^"\']*["\'][^>]*>',
            checked_page[home_right.end():], re.I,
        ):
            raise RuntimeError(f"{check_path.name}: News in evidenza must be first on the Home")

if checked < 20:
    raise RuntimeError(f"Only {checked} editorial articles checked; expected all article pages")
print(f"Verified Community AFTER related articles: {checked} pages; reordered: {corrected}; Home excluded")

