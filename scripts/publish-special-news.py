#!/usr/bin/env python3
# Keep the featured layout identical to the Community NEWS reference, including metadata and sidebar.
# All featured NEWS use the published Community NEWS article frontend.
# Layout revision: the shared featured-article header keeps desktop navigation on one line.
"""Publish ONLY editor-approved original pieces in the isolated special sections.
Input is approved-special-articles.json, never unverified RSS candidates.
Safe to re-run: deterministic pages, no Community news/archive changes.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path
from featured_article_layout import decorate

ROOT=Path(__file__).resolve().parent.parent
APPROVED=ROOT/"approved-special-articles.json"
COVER_MANIFEST=ROOT/"special-cover-manifest.json"
SECTION_FILES={"tech":"tech-today.html","gaming":"gaming-today.html"}
PREFIX={"tech":"tech-impact","gaming":"gaming-inside"}
LABEL={"tech":"Tech Impact","gaming":"Gaming Inside"}
def esc(x):return html.escape(str(x),quote=True)
def valid(item):
    if not isinstance(item,dict) or item.get("section") not in PREFIX:return False
    slug=item.get("slug","")
    title=item.get("title","")
    intro=item.get("summary","")
    paragraphs=item.get("paragraphs")
    sources=item.get("sources")
    if not isinstance(slug,str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*",slug) or len(slug)>95:return False
    if not isinstance(title,str) or not 25<=len(title)<=170:return False
    if not isinstance(intro,str) or not 65<=len(intro)<=420:return False
    if not isinstance(paragraphs,list) or len(paragraphs)<3 or any(not isinstance(p,str) or len(p.strip())<65 for p in paragraphs):return False
    total_words=len(" ".join([title,intro]+paragraphs).split())
    body_words=len(" ".join(paragraphs).split())
    if not isinstance(sources,list) or not sources or any(not isinstance(u,str) or not u.startswith("https://") for u in sources):return False
    editorial=item.get("editor_approved") is True
    automatic=(item.get("auto_approved") is True and
               item.get("approval_method")=="strict_source_evidence" and
               isinstance(item.get("evidence_review"),dict) and
               item["evidence_review"].get("paragraphs_supported") is True and
               isinstance(item.get("source_fingerprints"),list) and
               bool(item["source_fingerprints"]))
    if not (editorial or automatic):return False
    if editorial and not 300<=total_words<=600:return False
    if not editorial and not 300<=body_words<=750:return False
    try:
        date=dt.date.fromisoformat(item.get("date",""))
        if date>dt.date.today()+dt.timedelta(days=1):return False
    except (ValueError,TypeError):return False
    return True
def save_if_changed(path,content):
    if not path.exists() or path.read_text(encoding="utf-8")!=content:
        path.write_text(content,encoding="utf-8")
        print("Updated:",path.name)
def make_page(x,filename,related):
    title=esc(x["title"])
    summary=esc(x["summary"])
    name=LABEL[x["section"]]
    url="https://zazoomtek.it/"+filename
    section_link="/"+SECTION_FILES[x["section"]]
    body="".join("<p>"+esc(p)+"</p>" for p in x["paragraphs"])
    # Research URLs stay in approved-special-articles.json, outside the public page.
    # Editorially required attribution belongs inside the original prose.
    related_rows="".join(
        '<li><a href="/'+esc(r["filename"])+'">'+esc(r["title"])+'</a></li>'
        for r in related[:3]
    )
    related_html=(
        '<section class="related"><h2>Articoli correlati</h2><ul>'+related_rows+'</ul></section>'
        if related_rows else ""
    )
    # Source links stay in the editorial JSON for verification; necessary
    # factual attribution remains in the prose. No automatic source footer.
    hero=x.get("image","")
    art=x.get("_cover_origin") or {}
    credit_html=""
    if isinstance(art,dict) and art.get("origin")=="Wikimedia Commons" and art.get("license","").upper().startswith("CC BY"):
        source=art.get("source_page","")
        licence=art.get("license_url","")
        artist=art.get("photographer") or "Autore indicato su Wikimedia Commons"
        if (source.startswith("https://commons.wikimedia.org/wiki/")
                and (licence.startswith("https://creativecommons.org/licenses/by/") or licence.startswith("https://creativecommons.org/licenses/by-sa/"))):
            credit_html=('<figcaption class="image-credit">Foto: '+esc(artist)
                +' · <a href="'+esc(source)+'" rel="noopener noreferrer">Wikimedia Commons</a>'
                +' · <a href="'+esc(licence)+'" rel="noopener noreferrer">'+esc(art["license"])
                +'</a> · immagine ritagliata ed elaborata graficamente da ZazoomTek.</figcaption>')
    hero_html=('<figure class="hero"><img src="'+esc(hero)+'" alt="'+esc(x["title"])+'" '
               'loading="eager" decoding="async"></figure>') if hero.startswith("/") else ""
    structured=json.dumps({
        "@context":"https://schema.org","@type":"NewsArticle",
        "headline":x["title"],"description":x["summary"],
        "mainEntityOfPage":url,"datePublished":x["date"],"dateModified":x["date"],
        "author":{"@type":"Organization","name":"ZazoomTek"},
        "publisher":{"@type":"Organization","name":"ZazoomTek"}
    },ensure_ascii=False).replace("<",r"\u003c")
    return f'''<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} | ZazoomTek</title><meta name="description" content="{summary}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{esc(url)}">
<style>body{{margin:0;background:#ededed;color:#222;font:17px/1.75 Arial,Helvetica,sans-serif}}
header{{background:#171717;color:#fff;padding:24px max(16px,calc((100vw - 1130px)/2));border-top:4px solid #d51232}}
header a{{color:#fff;text-decoration:none;font-weight:bold}}
main{{box-sizing:border-box;max-width:1130px;margin:26px auto;background:#fff;padding:clamp(20px,4vw,54px)}}
h1{{line-height:1.17;font-size:clamp(28px,4vw,43px);margin:15px 0}}
h2{{font-size:23px;color:#171717;font-weight:900}}a{{color:#b7132a}}.eyebrow{{font-size:13px;text-transform:uppercase;color:#b7132a;font-weight:bold}}
.lead{{font-size:21px;line-height:1.55;color:#444}}.meta{{color:#777;font-size:14px}}
.hero{{margin:20px 0 26px}}.hero img{{width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;display:block}}.image-credit{{font-size:12px;color:#666;line-height:1.45;margin-top:6px}}
.related{{margin-top:40px;border-top:1px solid #dedede;padding-top:20px}}.related ul{{padding-left:20px}}
.related li{{margin:0 0 13px}}.related h2{{color:#161616;font-weight:900}}
footer{{background:#171717;color:#ddd;text-align:center;padding:25px;font-size:14px}}
footer a{{color:#fff}}</style>
<script type="application/ld+json">{structured}</script></head>
<body><header><a href="/">ZAZOOMTEK</a> &nbsp; / &nbsp; <a href="{esc(section_link)}">{name}</a></header>
<main><div class="eyebrow">{name}</div><h1>{title}</h1>
<div class="meta">{esc(x["date"])} · Redazione ZazoomTek</div>
{hero_html}<p class="lead">{summary}</p>{body}
{related_html}
{('<details class="zt-photo-credits"><summary>Crediti fotografici</summary>'+credit_html+'</details>') if credit_html else ''}
<p><a href="{esc(section_link)}">← Torna a {name}</a></p></main>
<footer>© ZazoomTek · <a href="/privacy.html">Privacy</a></footer></body></html>'''

def main():
    raw=json.loads(APPROVED.read_text(encoding="utf-8"))
    items=raw.get("articles",[])
    if not isinstance(items,list):raise ValueError("articles must be a list")
    if len(items)>1500:raise ValueError("Too many articles")
    # Validate all input before writing any site file.
    for item in items:
        if not valid(item):raise ValueError("Invalid or not approved article: "+str(item.get("slug") if isinstance(item,dict) else item))
    # The cover generator writes its selections separately. The editorial source
    # JSON remains unchanged, so repeated publishes do not create deploy loops.
    cover_data={}
    if COVER_MANIFEST.exists():
        cover_data=json.loads(COVER_MANIFEST.read_text(encoding="utf-8")).get("articles",{})
    published=[];used=set()
    for item in items:
        if not valid(item):raise ValueError("Invalid or not approved article: "+str(item.get("slug") if isinstance(item,dict) else item))
        filename=PREFIX[item["section"]]+"-"+item["slug"]+".html"
        if filename in used:raise ValueError("Duplicate slug: "+filename)
        used.add(filename)
        article={**item,"filename":filename}
        if item.get("cover_mode")=="auto" or not article.get("image") or article["image"]=="/ChatGPT.png":
            info=cover_data.get(item["section"]+"/"+item["slug"],{})
            generated=info.get("path","")
            if (isinstance(generated,str) and generated.startswith("/assets/special/")
                    and (ROOT/generated.lstrip("/")).is_file()):
                article["image"]=generated
                article["_cover_origin"]=info.get("origin") or {}
            else:
                # Do not publish new stories with broken or generic hero images.
                raise RuntimeError("Missing generated cover for approved article: "+filename)
        published.append(article)
    published.sort(key=lambda x:(x["date"],x["filename"]),reverse=True)
    for item in published:
        related=[r for r in published if r["filename"]!=item["filename"] and r["section"]==item["section"]]
        if not related:
            related=[r for r in published if r["filename"]!=item["filename"]]
        page=make_page(item,item["filename"],related)
        save_if_changed(ROOT/item["filename"],decorate(page,LABEL[item["section"]]))
    # Editorially special topics only. Ordinary product/game announcements
    # live in NEWS + HOME, not in these dedicated analysis archives.
    for section,archive in SECTION_FILES.items():
        path=ROOT/archive;s=path.read_text(encoding="utf-8")
        rows=[]
        for x in (p for p in published if p["section"]==section):
            url="/"+x["filename"];title=esc(x["title"]);summary=esc(x["summary"])
            # Two topic-specific original covers for the category archive.
            # Leave article hero, Schema.org and approved source metadata untouched.
            archive_cover_overrides = {
                "tech-impact-le-norme-ue-sull-ia-affrontano-il-primo-test-con-i-laboratori.html":
                    "/assets/special/tech-impact-eu-ai-test-labs-original-20261014.svg",
                "tech-impact-california-nuova-legge-vieta-l-uso-di-bot-e-intelligenza-artificiale-nei-licenziament.html":
                    "/assets/special/tech-impact-california-ai-workplace-law-original-20261014.svg",
            }
            special_cover = archive_cover_overrides.get(x["filename"])
            if special_cover and not (ROOT / special_cover.lstrip("/")).is_file():
                raise RuntimeError("Missing unique Tech Impact archive image: "+special_cover)
            cover=esc(special_cover or x.get("image") or "/ChatGPT.png")
            rows.append('<article class="news-row"><a href="'+esc(url)+'"><img src="'+cover+'" alt="'+title+'" loading="lazy"></a><div class="news-copy"><h2><a href="'+esc(url)+'">'+title+'</a></h2><div class="news-meta">ZazoomTek · '+esc(x["date"])+'</div><p>'+summary+'</p><a class="news-read" href="'+esc(url)+'">Leggi tutto</a></div></article>')
        replacement='<div class="news-list" id="newsList" data-auto-articles="'+section+'">'+"\n".join(rows)+'</div>'
        # Community banner is inserted AFTER the closing news-list DIV.
        # Preserve the banner while replacing only the published articles.
        pattern=(r'<div class="news-list" id="newsList" data-auto-articles="'
                 +section+r'">.*?</div>(?=\s*(?:<!-- ZT_COMMUNITY_BANNER_START -->|</section>))')
        updated,count=re.subn(pattern,lambda match:replacement,s,count=1,flags=re.S)
        if count!=1:raise RuntimeError("Archive marker missing: "+archive)
        save_if_changed(path,updated)
    # Shared archive merger is idempotent: a special-news rebuild may never
    # erase an already imported Tech Impact / Gaming Inside Community post.
    from community_special_archive import sync as sync_community_special
    sync_community_special(ROOT)
    # Every verified article stays in its archive. Carousel placements are an
    # additional promotion: one independently fact-checked original report is
    # enough for a strong feature; corroboration remains a relevance signal.
    feature_path=ROOT/"special-featured.json"
    old_featured=json.loads(feature_path.read_text(encoding="utf-8")).get("items",[])
    chosen=[];new_trend_sections=[]
    # Only ONE Impact and ONE Inside article are nominated for the global
    # six-card Home carousel. All other verified reports are published above
    # to their complete category archives; never discard them.
    for sec,max_items in (("tech",1),("gaming",1)):
        current=[x for x in old_featured if x.get("section")==sec
                 and (ROOT/x.get("slug","")).is_file()
                 and (ROOT/x.get("image","").lstrip("/")).is_file()]
        # Editorial and automated original reporting may be promoted with
        # one documented source; prefer prominent headlines for a given day.
        # All approved, published, source-checked articles are eligible for
        # the one category slot. A "featured" flag is not a publication
        # condition, nor a reason to hide other articles from the archives.
        trending=[x for x in published if x["section"]==sec
                  and (x.get("editor_approved") is True
                       or x.get("auto_approved") is True)]
        # New verified reports take precedence over old manual selections.
        trending.sort(key=lambda x:(x["date"],
                                   int(x.get("featured_priority") or 0),
                                   x.get("home_featured") is True,
                                   x.get("evidence_review",{}).get("verified_at",""),
                                   x.get("evidence_review",{}).get("source_count",0),
                                   x["filename"]),reverse=True)
        if trending:
            newest=trending[0]
            lead={"section":sec,"slug":newest["filename"],
                  "title":newest["title"],"image":newest["image"]}
            current=[lead]+[x for x in current if x["slug"]!=lead["slug"]]
            new_trend_sections.append(sec)
        # Backfill only missing historical slots; never displace the leading
        # old special story with an uncorroborated new one.
        for x in published:
            if len(current)>=max_items:break
            if x["section"]!=sec or any(v["slug"]==x["filename"] for v in current):continue
            current.append({"section":sec,"slug":x["filename"],
                            "title":x["title"],"image":x["image"]})
        chosen.extend(current[:max_items])
    if len(chosen)==2 and new_trend_sections:
        save_if_changed(feature_path,json.dumps({"items":chosen},ensure_ascii=False,indent=2)+"\n")
    print("Approved:",len(published),"/ category-archive totals:",
          {sec:sum(x["section"]==sec for x in published) for sec in ("tech","gaming")},
          "/ newest featured sections:",
          new_trend_sections if new_trend_sections else "previous carousel preserved")
if __name__=="__main__":main()
