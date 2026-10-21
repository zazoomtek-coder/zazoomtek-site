#!/usr/bin/env python3
"""Ensure the site-wide CSS before Firebase deploy, including generated pages."""
from pathlib import Path
from zt_footer import unify_footer, _matching_close
from zt_sidebar_mix import refresh_sidebars
import re
import html as html_utils

root=Path(__file__).resolve().parents[1]
# Repair legacy visible publication dates before verifying site-wide pages.
from zt_publication_dates import repair_publication_dates
fixed_dates, unresolved_dates, audited_dates = repair_publication_dates(root)
print(f"Publication dates audited: {audited_dates}; repaired: {fixed_dates}; without reliable source: {unresolved_dates}")


# SITE_NAV_CANONICAL_20261012 - Mandatory navigation on ALL HTML pages.
# Home is the source of truth: any change to its menu is inherited by all
# existing and newly generated editorial pages at every deployment.
home_source=(root / "index.html").read_text(encoding="utf-8")
home_match=re.search(r'<nav\s+class=["\']nav["\'][^>]*>([\s\S]*?)</nav>',home_source,re.I)
if not home_match:
    raise RuntimeError("Home main navigation missing; deployment blocked")
def nav_labels(markup):
    """Read actual link and dropdown-button labels in DOM order."""
    labels=[]
    for element in re.finditer(
        r'<(?:a|button)\b[^>]*>([\s\S]*?)</(?:a|button)>',
        markup,re.I,
    ):
        label=html_utils.unescape(re.sub(r'<[^>]*>',"",element.group(1))).strip()
        if label:
            labels.append(label)
    return tuple(labels)

def preserves_approved_routes(labels,required):
    """Existing routes must remain in order; extra safe menus are allowed."""
    position=0
    for label in labels:
        if position<len(required) and label==required[position]:
            position+=1
    return position==len(required)

home_labels=nav_labels(home_match.group(1))
required_nav=("Home","News","Recensioni","Guide","Cybercultura",
              "Speciali","Extra","Community","Video")
if (not preserves_approved_routes(home_labels,required_nav)
        or len(home_labels)!=len(set(home_labels))):
    raise RuntimeError("Home main navigation lost, reordered or duplicated an approved route")

# ONE fixed masthead source: the locked, approved Home, NOT news.html.
# Each page receives the actual Home header at build time (no browser fetch,
# no duplicate scripts, no second header, no page-specific menu sizes).
header_pattern=re.compile(r'<header\b[^>]*>[\s\S]*?</header>',re.I)
home_header_match=header_pattern.search(home_source)
if not home_header_match or 'class="shell topbar"' not in home_header_match.group():
    raise RuntimeError("Approved Home header missing; deployment blocked")
header_template=home_header_match.group()
nav_pattern=re.compile(r'<nav\b[^>]*class=["\']nav["\'][^>]*>[\s\S]*?</nav>',re.I)
if not nav_pattern.search(header_template) or 'ticker-video-links' not in header_template:
    raise RuntimeError("Locked Home navigation/ticker incomplete")

def active_nav_key(filename):
    name=filename.lower()
    if name=="speciali.html" or re.fullmatch(r"speciali-\d+[.]html",name):
        return "Speciali"  # Standalone archive in the top-level menu.
    if name=="cybercultura.html":
        return "Cybercultura"
    if name=="extra.html" or re.fullmatch(r"extra-\d+[.]html",name):
        return "Extra"
    # An Extra Community article keeps its stable news-ID URL, but belongs
    # solely to Extra. The category must win over the news filename prefix.
    if name.startswith("news-ugkx") and name.endswith(".html"):
        try:
            article=(root/filename).read_text(encoding="utf-8",errors="replace")
            if re.search(r'<a\s+href="/extra[.]html">Extra</a>',article,re.I):
                return "Extra"
        except OSError:
            pass
    if name.startswith(("news-","news.")) or name in ("news.html",):
        return "News"
    if (name.startswith(("recensione-","recensioni-","review-")) or
        "-recensione-" in name or name=="recensioni-scritte.html"):
        return "Recensioni"
    if name.startswith(("guida-","guide-")) or name=="guide.html":
        return "Guide"
    if name.startswith("tech-impact-") or name=="tech-today.html":
        return "Cybercultura"
    if name.startswith("gaming-inside-") or name=="gaming-today.html":
        return "Cybercultura"
    if name.startswith(("test-","unboxing-","gaming-")) or name in (
        "recensioni.html","test.html","unboxing.html","gaming.html"):
        return "Video"
    return None

def nav_markup(filename):
    """Exact Home menu HTML with only the current page state changed."""
    active=active_nav_key(filename)
    original=nav_pattern.search(header_template)
    if not original:
        raise RuntimeError("Home navigation no longer exists")
    def change_link(match):
        attrs=match.group(1)
        label=html_utils.unescape(re.sub(r'<[^>]*>', '', match.group(2))).strip()
        href=re.search(r'\bhref=["\']([^"\']+)["\']',attrs,re.I)
        if not href:
            return match.group()
        # Preserve Home-only semantic classes, then toggle just its active state.
        classes=re.search(r'\bclass=["\']([^"\']*)["\']',attrs,re.I)
        remaining=[name for name in (classes.group(1).split() if classes else [])
                   if name!='active']
        attrs=re.sub(r'\s+class=["\'][^"\']*["\']','',attrs,count=1,flags=re.I)
        attrs=re.sub(r'\s+aria-current=["\'][^"\']*["\']','',attrs,flags=re.I)
        if label==active:
            remaining.append("active")
        if remaining:
            attrs+=' class="'+html_utils.escape(" ".join(remaining),quote=True)+'"'
        if label==active:
            attrs+=' aria-current="page"'
        return '<a'+attrs+'>'+match.group(2)+'</a>'
    nav=re.sub(r'<a\b([^>]*)>([\s\S]*?)</a>',change_link,original.group(),flags=re.I)
    # Home uses relative links; normalize to root on any article URL.
    nav=re.sub(r'(?<=href=")(?!/|https?://|#|mailto:)([^"]+)(?=")',
               lambda m:'/'+m.group(1).lstrip('./'),nav,flags=re.I)
    return nav

def home_masthead(filename):
    """Copy the REAL Home banner/logo/menu/ticker, unchanged except links/active."""
    source=nav_pattern.sub(lambda _:nav_markup(filename),header_template,count=1)
    source=source.replace('<header>','<header id="zt-site-home-header">',1)
    source=source.replace('src="ChatGPT.png"','src="/ChatGPT.png"')
    # A single ticker is allowed per document; Home keeps its original ID.
    source=source.replace('id="tickerTrack"','id="zt-page-tickerTrack"',1)
    source=re.sub(r'(?<=href=")(?!/|https?://|#|mailto:)([^"]+)(?=")',
                  lambda m:'/'+m.group(1).lstrip('./'),source,flags=re.I)
    return source

# Header-only reset for the Home markup on pages with old local header styles.
# Other elements of the page, including all editorial layouts, are untouched.
FIXED_HEADER_STYLE="""<style id="zt-site-home-header-style">
#zt-site-home-header{display:block!important;position:relative!important;width:100%!important;
 margin:0!important;padding:0!important;background:#171717!important;color:#fff!important;
 border-top:3px solid #d51232!important;box-sizing:border-box!important}
#zt-site-home-header *,#zt-site-home-header *:before,#zt-site-home-header *:after{box-sizing:border-box}
#zt-site-home-header .shell{width:min(1460px,calc(100% - 28px));margin:0 auto}
#zt-site-home-header .topbar{min-height:78px;display:grid;
 grid-template-columns:max-content minmax(0,1fr) minmax(190px,265px);align-items:stretch}
#zt-site-home-header .brand{display:flex;align-items:center;gap:10px;
 padding:8px 12px 8px 0;border-right:1px solid #333;min-width:0;text-decoration:none}
#zt-site-home-header .brand-logo-img{display:block;width:54px;height:54px;max-width:54px;
 flex:0 0 54px;object-fit:contain;border-radius:8px}
#zt-site-home-header .zt-brand-copy{display:flex;flex-direction:column;justify-content:center;gap:5px;white-space:nowrap}
#zt-site-home-header strong.zt-wordmark{display:block;font:900 clamp(19px,1.55vw,23px)/1.05 Arial,Helvetica,sans-serif;
 letter-spacing:-.045em;white-space:nowrap}
#zt-site-home-header .zt-mark-blue{color:#58a8f0}
#zt-site-home-header .zt-mark-red{color:#e41b45}
#zt-site-home-header .zt-brand-tagline{display:block;color:#eee;
 font:400 10px/1.3 Arial,Helvetica,sans-serif;letter-spacing:.045em;white-space:nowrap}
#zt-site-home-header nav.nav{display:flex;align-items:stretch;min-height:78px;
 min-width:0;overflow-x:auto;overflow-y:hidden;flex-wrap:nowrap;white-space:nowrap}
#zt-site-home-header nav.nav>a{display:flex;flex:0 0 auto;align-items:center;justify-content:center;
 min-height:78px;padding:0 8px;border-right:1px solid #303030;
 font:800 11px/1.1 Arial,Helvetica,sans-serif;text-transform:uppercase;
 text-decoration:none;color:#fff;white-space:nowrap}
#zt-site-home-header nav.nav>a.active,#zt-site-home-header nav.nav>a:hover{background:#d51232;color:white}
#zt-site-home-header .search-wrap{min-width:0;display:flex;flex-direction:column;justify-content:center;padding:8px 0 8px 8px}
#zt-site-home-header .search-box{width:100%;display:flex;background:#303030;border:1px solid #444}
#zt-site-home-header .search-box input{flex:1;min-width:0;width:100%;background:transparent;border:0;color:#fff;padding:12px 14px}
#zt-site-home-header .search-box button{min-width:46px;background:#d51232;color:#fff;border:0}
#zt-site-home-header .top-socials{display:flex;justify-content:flex-end;gap:10px;margin-top:8px}
#zt-site-home-header .top-socials a{display:grid;place-items:center;width:40px;height:40px;
 border-radius:50%;border:1px solid #353535;background:#181818}
#zt-site-home-header .top-socials img{display:block;width:27px;height:27px;object-fit:contain}
#zt-site-home-header .ticker{display:block;background:#222;border-top:1px solid #2c2c2c}
#zt-site-home-header .ticker-inner{display:flex;align-items:center;min-height:46px;overflow:hidden}
#zt-site-home-header .ticker-label{background:#d51232;font-weight:900;padding:14px 20px;white-space:nowrap}
#zt-site-home-header .ticker-track{position:relative;flex:1;min-width:0;height:46px;overflow:hidden}
#zt-site-home-header .ticker-track a{position:absolute;inset:0;display:flex;align-items:center;
 padding:0 16px;opacity:0;color:#ddd;font-size:.86rem;text-decoration:none}
#zt-site-home-header .ticker-track a.active{opacity:1}
#zt-site-home-header .ticker-video-links{display:flex;align-items:center;justify-content:flex-end;
 gap:22px;flex:0 0 auto;margin-left:auto;white-space:nowrap}
#zt-site-home-header .ticker-video-links a{display:flex;align-items:center;height:46px;
 padding:0 2px;text-decoration:none;color:#fff;font:900 clamp(.82rem,.95vw,.96rem)/1.1 Arial,Helvetica,sans-serif;
 text-transform:uppercase}
@media(max-width:1330px){
 #zt-site-home-header .topbar{grid-template-columns:max-content minmax(0,1fr)}
 #zt-site-home-header .search-wrap{grid-column:1/-1;padding:8px 0}
 #zt-site-home-header .ticker-inner{flex-wrap:wrap}
 #zt-site-home-header .ticker-video-links{flex:0 0 100%;justify-content:flex-end;gap:14px}
}
@media(max-width:820px){
 #zt-site-home-header .topbar{display:flex;flex-direction:column}
 #zt-site-home-header .brand{justify-content:center;border-right:0;padding:10px 0}
 #zt-site-home-header nav.nav{width:100%;min-height:44px;max-width:100%}
 #zt-site-home-header nav.nav>a{min-height:44px;padding:12px 11px;font-size:11px}
 #zt-site-home-header .search-wrap{padding:8px 0}
 #zt-site-home-header .ticker-video-links{justify-content:flex-start;overflow-x:auto;gap:14px}
}
</style>"""

# REVIEW_LAYOUT_SESAME_20261012: every completed review adopts the approved
# 1460px/350px two-column layout during ALL publishing workflows.
def is_review_page(filename, page):
    name=filename.lower()
    if name.startswith("preview-") or name in ("recensioni-scritte.html","recensioni.html"):
        return False
    named=(name.startswith(("recensione-","review-"))
           or "-recensione-" in name)
    if not named:
        return False
    # Do not misrepresent short, noindex archival placeholders as full reviews.
    return bool(re.search(r'<div\b[^>]*class=["\'][^"\']*\bdetail-grid\b', page, re.I)
                or re.search(r'<div\b[^>]*class=["\'][^"\']*\blayout\b', page, re.I))


# Content-backed, editorially reviewed descriptions of the eight imported
# reviews. These are drawn from their existing texts; no gameplay, benchmark,
# opinion, rating or test result is invented by the formatting process.
REVIEW_PROS_CONS = {
    "recensione-Ugkx1MzCpfD6F193kzdDtyqQU2ErUHi6FEu1.html": (
        "Boss rush impegnativo in cui schivata e attacco sono strettamente collegati.",
        ["Combattimenti che premiano precisione e riflessi",
         "Boss dalle fasi differenti e un sistema di schivata e attacco integrato",
         "Requisiti hardware molto contenuti"],
        ["Elevata difficoltà e necessità di ripetere spesso gli scontri",
         "Assenza della lingua italiana",
         "Utilizzo dichiarato dell'IA generativa per buona parte della grafica"],
    ),
    "recensione-UgkxHri44VrpYrRtskxdyK_msdY_oNiaK4aj.html": (
        "Un'avventura rilassante tra volo, esplorazione e costruzione.",
        ["Arcipelago colorato da esplorare anche in idrovolante",
         "Crafting, costruzione e raccolta di risorse",
         "Libertà di seguire la storia o esplorare senza fretta"],
        ["Ritmo poco adatto a chi cerca azione frenetica",
         "Meccaniche survival volutamente poco complesse"],
    ),
    "recensione-UgkxPQVLBegGEPWvHmDjVq-rA5b8EwFeFrtk.html": (
        "Dogfight velocissimi e una formula di volo ricca di nuove possibilità.",
        ["Controlli di volo reattivi e combattimenti aerei rapidi",
         "Missioni varie, Joker Flight e nuove possibilità tattiche",
         "Comparto audiovisivo spettacolare e storia più presente"],
        ["Qualche texture secondaria poco definita",
         "Sporadiche flessioni del frame rate",
         "Sistema stagionale online dalla struttura più commerciale"],
    ),
    "recensione-UgkxUyzI3zn3urxvkpRPcd349swqkNqHFXEK.html": (
        "Basket profondo e divertente, con ProPLAY e molte modalità.",
        ["ProPLAY e migliore equilibrio tra attacco e difesa",
         "MyCAREER Eras e MyNBA Legacy ampliano i contenuti",
         "Partite coinvolgenti e gameplay ricco di possibilità"],
        ["Badge, progressioni e valute possono disorientare all'inizio",
         "Aspetti economici di MyTEAM ancora controversi"],
    ),
    "recensione-UgkxguG9cYYVBHc9hJSR5xDsjFePliUGScQg.html": (
        "Smart glasses leggeri e ricchi di funzioni, con alcuni compromessi.",
        ["Montatura relativamente leggera e discreta",
         "Fotocamera da 13 MP, audio open-ear e controlli touch",
         "Funzioni AI e traduzione in tempo reale"],
        ["Registrazione Full HD a 30 fps limitata in condizioni di luce difficili",
         "Autonomia ridotta con uso intensivo della fotocamera",
         "Funzioni AI dipendenti dall'applicazione e dalla connessione"],
    ),
    "recensione-Ugkxq4wPsbAKxSo1aB0OptleaGIR5iyfIuyz.html": (
        "Un'avventura di Logan intensa, aggressiva e cinematografica.",
        ["Combattimento aggressivo con Furia e fattore rigenerante",
         "Storia più concentrata e cinematografica",
         "Buon impatto tecnico su PS5"],
        ["Alcune attività opzionali meno memorabili",
         "Qualche situazione meno intensa del resto dell'avventura"],
    ),
    "recensione-Ugkxs-Pzxksjwszh4KPPFAG-h-xZxJgFc1js.html": (
        "Una dash cam dual-channel completa con doppio 4K e HDR.",
        ["Registrazione 4K sia anteriore sia posteriore e doppio HDR",
         "GPS, ADAS, Wi-Fi 6 e registrazione di emergenza",
         "Supercondensatore adatto all'installazione in automobile"],
        ["Sorveglianza completa in parcheggio con Hardwire Kit separato",
         "Controllo vocale non disponibile in italiano",
         "Alcune funzioni 4G Cloud+ 2.0 legate ad aggiornamenti OTA"],
    ),
    "recensione-Ugkxvpi4bKV_hiuDy7XJQb0-qw7CTJc5Is33.html": (
        "Una simulazione dei trasporti profonda e gratificante su PS5.",
        ["Oltre 275 veicoli e numerose possibilità di collegamento",
         "Catene produttive e logistica più profonde",
         "Mod multipiattaforma e grande libertà di progettazione",
         "Formula gestionale capace di assorbire molte ore"],
        ["Curva di apprendimento impegnativa",
         "Menu meno comodi con molte linee da gestire su PS5",
         "Margini di miglioramento delle prestazioni"],
    ),
}

def _review_source_points(body):
    """Fallback for FUTURE Community reviews: reuse real source sentences.
    Do not make up Pro/Contro or ratings in new automatically imported posts.
    """
    visible=html_utils.unescape(re.sub(r'<[^>]+>', ' ', body))
    visible=re.sub(r'\s+', ' ', visible).strip()
    sentences=re.split(r'(?<=[.!?])\s+(?=[A-ZÀÈÉÌÒÙ])', visible)
    pro_re=re.compile(r'\b(?:riesce|offre|permette|migliora|convincente|divertente|qualità|varietà|profondità|completo|interessante|ottimo|reattiv[oi])\b',re.I)
    con_re=re.compile(r'\b(?:limiti|compromessi|problemi|difficolt[àa]|meno comodo|carenz[ae]|assenza|manca|peccato|miglioramento|difetti|non supporta|richiede)\b',re.I)
    def collect(pattern):
        selected=[]
        for sentence in sentences:
            sentence=sentence.strip()
            if 35<=len(sentence)<=190 and pattern.search(sentence) and sentence not in selected:
                selected.append(sentence)
            if len(selected)>=3:
                break
        return selected
    return collect(pro_re),collect(con_re)

def unify_review_final_panel(page, filename):
    """Render the SAME end-of-review components as the approved Sesame Street
    template: question, rating panel, Pro/Contro, related links, Community banner.
    Score is copied from the original review verbatim, never guessed.
    """
    if not is_review_page(filename,page):
        return page
    start=re.search(r'<div\b[^>]*class=["\'][^"\']*\barticle-body\b[^"\']*["\'][^>]*>',page,re.I)
    if not start:
        return page  # The independently designed Sesame Street review.
    end=_matching_close(page,start.end(),'div')
    if end < start.end():
        raise RuntimeError(f"{filename}: invalid review article-body markup")
    content=page[start.end():end]
    # All published pages will be reprocessed on future builds.
    if 'data-zt-review-end="sesame-v1"' in content:
        return page

    score_pattern=re.compile(
        r'<p\b[^>]*>\s*(?:⭐\s*)?Voto\s+finale\s*:\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*/\s*10\s*</p>'
        r'|<div\b[^>]*class=["\']review-score["\'][^>]*>\s*<strong>'
        r'\s*(?:⭐\s*)?Voto\s+finale\s*:\s*(\d{1,2}(?:[.,]\d{1,2})?)\s*/\s*10\s*</strong>\s*</div>',
        re.I,
    )
    found=score_pattern.search(content)
    if not found:
        return page  # Reviews without a published score must not gain one.
    score=(found.group(1) or found.group(2)).replace(',','.')
    if not (0<=float(score)<=10):
        raise RuntimeError(f"{filename}: invalid original review score")
    content=content[:found.start()]+content[found.end():]
    # Remove generic label only; the original introduction paragraphs remain.
    content=re.sub(r'<h2>\s*(?:<strong>)?\s*Introduzione\s*(?:</strong>)?\s*</h2>\s*','',content,flags=re.I)
    # No fabricated lists. Curated items are explicitly backed by the original
    # review; future pages can extract only actual sentences from their own text.
    description,pros,cons=REVIEW_PROS_CONS.get(filename,("",[],[]))
    if not description:
        pros,cons=_review_source_points(content)
    esc=html_utils.escape
    rating_html=(
        '<div class="rating zt-review-rating" data-zt-review-end="sesame-v1">'
        '<div><small>VOTO FINALE</small>'
        f'<strong>{esc(score)}<span>/10</span></strong></div>'
        + (f'<p>{esc(description)}</p>' if description else '')
        + '</div>'
    )
    def category(name,cls,points):
        if not points:
            # No invented evaluative claims when a future review lacks data.
            return ('<section class="'+cls+'"><h2>'+name+'</h2>'
                    '<p>Non specificati nel testo originale.</p></section>')
        return ('<section class="'+cls+'"><h2>'+name+'</h2><ul>'
                +''.join('<li>'+esc(point)+'</li>' for point in points)
                +'</ul></section>')
    procons='<div class="proscons zt-review-proscons">'+category("Pro","pros",pros)+category("Contro","cons",cons)+'</div>'
    # Original reader question is left where it was, now BEFORE the vote box.
    content=content.rstrip()+rating_html+procons
    return page[:start.end()]+content+page[end:]

def unify_review_layout(page, filename):
    if not is_review_page(filename,page):
        return page
    match=re.search(r'<body\b([^>]*)>',page,re.I)
    if not match:
        raise RuntimeError(f"{filename}: review has no <body> tag")
    body_tag=match.group()
    cls=re.search(r'\bclass=(["\'])(.*?)\1',body_tag,re.I|re.S)
    if cls:
        classes=cls.group(2).split()
        if 'zt-review-sesame-layout' not in classes:
            classes.append('zt-review-sesame-layout')
            newtag=body_tag[:cls.start(2)]+" ".join(classes)+body_tag[cls.end(2):]
        else:
            newtag=body_tag
    else:
        newtag=body_tag[:-1]+' class="zt-review-sesame-layout">'
    result=page[:match.start()]+newtag+page[match.end():]
    return result

# ZT EDITORIAL TITLE/SUBTITLE RULE 2026-10-12:
# In visible headings only, a real descriptive subtitle after "|" is always
# a separate, normal-weight line. Preserve the primary title verbatim.
# Titles/SEO metadata remain unchanged; a category label is NOT a subtitle.
def split_editorial_title_h1(page, filename):
    if filename.startswith("preview-"):
        return page
    if not re.search(r'<(?:main|article)\b',page,re.I):
        return page

    def replace_title(match):
        start,original,end=match.groups()
        # Only plain-text H1 text; do not restructure headings with child links.
        if '<' in original or '>' in original or ' | ' not in original:
            return match.group(0)
        first,sub=original.split(' | ',1)
        if not first.strip() or not sub.strip():
            return match.group(0)
        word_count=len(sub.strip().split())
        # "Game Name | Recensione PS5" or "News | Tech" = no subtitle.
        if word_count < 4 or re.fullmatch(
            r'(?:Recensione|Review|Test|News|Unboxing|Gameplay|Guide)'
            r'(?:\s+(?:PS5|PS4|PC|Xbox|Switch|Nintendo|202[0-9]))*',
            html_utils.unescape(sub.strip()),re.I,
        ):
            return match.group(0)
        # No text of the principal title/subtitle is rewritten.
        return (start+'<span class="zt-title-main">'+first.rstrip()+'</span>'
                +'<span class="zt-title-subtitle">'+sub.lstrip()+'</span>'+end)

    return re.sub(r'(<h1\b[^>]*>)([^<]*?)(</h1>)',
                  replace_title,page,count=1,flags=re.I|re.S)


def unify_site_navigation(page, filename):
    """Static shared Home masthead on all editorial pages, never rewrite Home."""
    if filename=="index.html":
        return page
    # Pagination pages are complete Home copies already; keep their locked shell.
    if re.fullmatch(r'pagina-\d+\.html',filename):
        canonical_home=nav_pattern.search(home_source)
        actual=nav_pattern.search(page)
        if not canonical_home or not actual:
            raise RuntimeError(filename+": missing Home pagination menu")
        nav=nav_markup(filename)
        return page[:actual.start()]+nav+page[actual.end():]

    first=header_pattern.search(page)
    if not first:
        return page
    old=first.group()
    if not ("/ChatGPT.png" in old or "ChatGPT.png" in old or
            "ZAZOOM" in old.upper()):
        return page  # not a ZazoomTek site header
    page=page[:first.start()]+home_masthead(filename)+page[first.end():]
    # Remove only the superseded standalone category/news strip, if directly
    # adjacent to the replaced header; never touch article content or sidebars.
    end=page.index('</header>',first.start())+len('</header>')
    tail=page[end:]
    strip=re.match(r'\s*<div\b[^>]*class=["\'][^"\']*\b(?:zt-strip|news-ticker)\b[^"\']*["\'][^>]*>',tail,re.I)
    if strip:
        close=_matching_close(tail,strip.end(),"div")+len('</div>')
        page=page[:end]+tail[close:]
    # The previous async header swap is obsolete and can produce flashes and
    # mismatched menu widths. Remove only that script from the built page.
    page=re.sub(r'<script\b[^>]*src=["\'][^"\']*zt-unified-header\.js(?:\?[^"\']*)?["\'][^>]*>\s*</script>\s*',
                '',page,flags=re.I)
    # This scoped style controls only the Home header clone, never the page.
    page=re.sub(r'<style\b[^>]*id=["\']zt-site-home-header-style["\'][^>]*>[\s\S]*?</style>\s*',
                '',page,flags=re.I)
    return re.sub(r'</head>',lambda m:FIXED_HEADER_STYLE+'\n'+m.group(),page,count=1,flags=re.I)

css_tag='<link rel="stylesheet" href="/zt-design.css?v=20261019siteMenuSquare1" data-zt-design="20261010">'
# The Home owns the CURRENT Javascript URL. Never force an outdated query
# version during deployment: it would silently reload cached old VIDEO shelves.
home_js_ref=re.search(r'src="(/zt-visual[.]js[?]v=[^"]+)"',home_source)
if not home_js_ref:
    raise RuntimeError("Home video Javascript version is missing; refusing stale deploy")
js_path=home_js_ref.group(1)
js_tag=f'<script src="{js_path}" defer></script>'
changed=0
for path in root.rglob('*.html'):
    if any(p in {'.git','node_modules','functions','studio'} for p in path.relative_to(root).parts):
        continue
    html=path.read_text(encoding='utf-8')
    if '</head>' not in html.lower():
        continue
    original=html
    if 'href="/zt-design.css' in html:
        html=re.sub(r'(?<=href=")/zt-design[.]css(?:[?][^"]*)?',
                    "/zt-design.css?v=20261019siteMenuSquare1",html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:css_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    if 'src="/zt-visual.js' in html:
        html=re.sub(r'(?<=src=")/zt-visual[.]js(?:[?][^"]*)?',
                    js_path,html,count=1)
    else:
        html=re.sub(r"</head>",lambda m:js_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    # Rotating sidebar data is generated from real published content below.
    # A tiny deferred script refreshes only right-column recommendations
    # on every site page, without touching SEO article text or the homepage.
    sidebar_tag='<script src="/zt-sidebar-live.js" defer></script>'
    html=re.sub(r'<script\b[^>]*src="/zt-sidebar-live[.]js"[^>]*>\s*</script>\s*',
                '',html,flags=re.I)
    if re.search(r'<aside\b[^>]*class="[^"]*(?:sidebar|article-side|news-sidebar)',html,re.I):
        html=re.sub(r'</head>',lambda m:sidebar_tag+'\n'+m.group(0),html,count=1,flags=re.I)
    # Apply LAST in the head to every existing and newly generated page.
    thumb_tag='<link rel="stylesheet" href="/zt-thumbnails.css?v=20261013textPriorityCover5" data-zt-thumbnails="center">'
    html=re.sub(r'<link[^>]*zt-thumbnails[.]css[^>]*>\s*',
                '',html,flags=re.I)
    html=re.sub(r'</head>',lambda m:thumb_tag+"\n"+m.group(0),html,count=1,flags=re.I)
    # Approved per-image crop focal points are scoped to the three-column Home.
    # Keep this stylesheet AFTER shared CSS, never apply to two-column pages.
    if path == root / 'index.html':
        focus_tag = "<link rel=\"stylesheet\" href=\"/zt-home-cover-focus.css?v=20261013editorialFix3\" data-zt-home-cover-focus=\"only-home\">"
        html=re.sub(r'<link[^>]*zt-home-cover-focus[.]css[^>]*>\s*',
                    '',html,flags=re.I)
        html=re.sub(r'</head>',lambda m:focus_tag+'\n'+m.group(0),
                    html,count=1,flags=re.I)
    html=unify_site_navigation(html,path.name)
    html=unify_review_layout(html,path.name)
    html=unify_review_final_panel(html,path.name)
    html=split_editorial_title_h1(html,path.name)
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

# The explicitly approved Sesame Street title must never render the subtitle
# in the main title's bold type or on the same line.
sesame = (root / "sesame-street-amici-e-risate-recensione-ps5.html").read_text(encoding="utf-8")
if not re.search(
    r'<h1[^>]*><span class="zt-title-main">'
    r'Sesame Street: Amici e risate Recensione PS5</span>'
    r'<span class="zt-title-subtitle">'
    r'Un quartiere colorato tra amicizia, giochi e avventure in famiglia</span></h1>',
    sesame,
):
    raise RuntimeError("Sesame Street: main title/subtitle must render separately")
print("Approved main title preserved; subtitles on separate normal-weight line")


# Never publish a partial/legacy five-button navigation again.
nav_checked=0
for nav_path in sorted(root.glob('*.html')):
    if nav_path.name.startswith("preview-"):
        continue
    nav_content=nav_path.read_text(encoding="utf-8")
    first=header_pattern.search(nav_content)
    if not first:
        continue
    header=first.group()
    match=nav_pattern.search(header)
    if not match:
        if "ZAZOOM" in header.upper() or "ChatGPT.png" in header:
            raise RuntimeError(f"{nav_path.name}: missing full navigation header")
        continue
    # An authorized menu/box may be added if the approved routes survive.
    # Every published page must inherit exactly the SAME real Home menu.
    labels=nav_labels(match.group())
    if labels!=home_labels:
        raise RuntimeError(
            f"{nav_path.name}: navigation differs from the verified Home: {labels}")
    if 'href="/zt-design.css?v=20261019siteMenuSquare1"' not in nav_content:
        raise RuntimeError(
            f"{nav_path.name}: shared stylesheet absent or outdated")
    nav_checked+=1
if nav_checked<20:
    raise RuntimeError(f"Only {nav_checked} pages with full site navigation verified")
print(f"Verified preserved Home routes and all {len(home_labels)} current navigation controls on {nav_checked} site pages")

# Make it impossible to deploy a new complete review in the old narrow layout.
reviews_checked=0
for review_path in sorted(root.glob("*.html")):
    review_doc=review_path.read_text(encoding="utf-8")
    if not is_review_page(review_path.name,review_doc):
        continue
    if not re.search(r'<body\b[^>]*class=["\'][^"\']*\bzt-review-sesame-layout\b',review_doc,re.I):
        raise RuntimeError(f"{review_path.name}: missing approved Sesame Street review layout")
    if not re.search(r'class=["\'][^"\']*(?:detail-grid|\blayout\b)',review_doc,re.I):
        raise RuntimeError(f"{review_path.name}: missing two-column review grid")
    if '<div class="article-body"' in review_doc and (
        re.search(r'<p\b[^>]*>\s*(?:⭐\s*)?Voto finale\s*:',review_doc,re.I)
        or '<div class="review-score">' in review_doc):
        raise RuntimeError(f"{review_path.name}: legacy unformatted review score still visible")
    if review_path.name.startswith("recensione-Ugkx"):
        if review_doc.count('data-zt-review-end="sesame-v1"') != 1:
            raise RuntimeError(f"{review_path.name}: missing final rating panel in Sesame format")
        if '<div class="proscons zt-review-proscons">' not in review_doc:
            raise RuntimeError(f"{review_path.name}: missing two-column Pro/Contro block")
    reviews_checked+=1
if reviews_checked < 8:
    raise RuntimeError(f"Expected at least 8 completed reviews, found {reviews_checked}")
print(f"Approved Sesame Street layout verified on {reviews_checked} complete reviews")



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
    if check_path.name == "index.html":
        # HOME ONLY: Ultimi Video must be first in the right-hand column.
        # The main six-cover carousel is already the featured-news section.
        home_right = re.search(r'<aside\s+class="sidebar"[^>]*>', checked_page, re.I)
        if not home_right or not re.match(
            r'\s*<div\b[^>]*class=["\'][^"\']*\bzt-video-stack\b',
            checked_page[home_right.end():], re.I,
        ):
            raise RuntimeError("Home right column must start with Ultimi Video")
        if "ZT_HOME_SIDEBAR_FEATURE_START" in checked_page:
            raise RuntimeError("Duplicate News in evidenza sidebar box on Home")
    elif re.fullmatch(r'pagina-\d+\.html', check_path.name):
        home_right = re.search(r'<aside\s+class="sidebar"[^>]*>', checked_page, re.I)
        if not home_right or not re.match(
            r'\s*<!-- ZT_HOME_SIDEBAR_FEATURE_START -->\s*<section\b[^>]*class=["\'][^"\']*\bzt-mix-feature\b[^"\']*["\'][^>]*>',
            checked_page[home_right.end():], re.I,
        ):
            raise RuntimeError(f"{check_path.name}: featured news missing on paginated page")

if checked < 20:
    raise RuntimeError(f"Only {checked} editorial articles checked; expected all article pages")
print(f"Verified Community AFTER related articles: {checked} pages; reordered: {corrected}; Home excluded")

