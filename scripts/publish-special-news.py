#!/usr/bin/env python3
"""Publish ONLY editor-approved original pieces in the isolated special sections.
Input is approved-special-articles.json, never unverified RSS candidates.
Safe to re-run: deterministic pages, no Community news/archive changes.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
APPROVED=ROOT/"approved-special-articles.json"
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
    if not isinstance(paragraphs,list) or len(paragraphs)<3 or any(not isinstance(p,str) or len(p.strip())<100 for p in paragraphs):return False
    # Editorial target: 300–600 words total, including title and summary.
    word_count=len(" ".join([title,intro]+paragraphs).split())
    if not 300<=word_count<=600:return False
    if not isinstance(sources,list) or not sources or any(not isinstance(u,str) or not u.startswith("https://") for u in sources):return False
    if not item.get("editor_approved",False):return False
    try:
        date=dt.date.fromisoformat(item.get("date",""))
        if date>dt.date.today()+dt.timedelta(days=1):return False
    except (ValueError,TypeError):return False
    return True
def save_if_changed(path,content):
    if not path.exists() or path.read_text(encoding="utf-8")!=content:
        path.write_text(content,encoding="utf-8")
        print("Updated:",path.name)
def make_page(x,filename):
    title=esc(x["title"])
    summary=esc(x["summary"])
    name=LABEL[x["section"]]
    url="https://www.zazoomtek.it/"+filename
    section_link="/"+SECTION_FILES[x["section"]]
    body="".join("<p>"+esc(p)+"</p>" for p in x["paragraphs"])
    sources="".join('<li><a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer nofollow">'+esc(u)+'</a></li>' for u in x["sources"])
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
h2{{font-size:23px}}a{{color:#b7132a}}.eyebrow{{font-size:13px;text-transform:uppercase;color:#b7132a;font-weight:bold}}
.lead{{font-size:21px;line-height:1.55;color:#444}}.meta{{color:#777;font-size:14px}}
.sources{{overflow-wrap:anywhere;border-top:1px solid #ddd;padding-top:20px}}
footer{{background:#171717;color:#ddd;text-align:center;padding:25px;font-size:14px}}
footer a{{color:#fff}}</style>
<script type="application/ld+json">{structured}</script></head>
<body><header><a href="/">ZAZOOMTEK</a> &nbsp; / &nbsp; <a href="{esc(section_link)}">{name}</a></header>
<main><div class="eyebrow">{name}</div><h1>{title}</h1>
<div class="meta">{esc(x["date"])} · Redazione ZazoomTek</div>
<p class="lead">{summary}</p>{body}
<div class="sources"><h2>Documenti e fonti consultate</h2><ul>{sources}</ul></div>
<p><a href="{esc(section_link)}">← Torna a {name}</a></p></main>
<footer>© ZazoomTek · <a href="/privacy.html">Privacy</a></footer></body></html>'''

def main():
    raw=json.loads(APPROVED.read_text(encoding="utf-8"))
    items=raw.get("articles",[])
    if not isinstance(items,list):raise ValueError("articles must be a list")
    if len(items)>1500:raise ValueError("Too many articles")
    published=[];used=set()
    for item in items:
        if not valid(item):raise ValueError("Invalid or not approved article: "+str(item.get("slug") if isinstance(item,dict) else item))
        filename=PREFIX[item["section"]]+"-"+item["slug"]+".html"
        if filename in used:raise ValueError("Duplicate slug: "+filename)
        used.add(filename)
        save_if_changed(ROOT/filename,make_page(item,filename))
        published.append({**item,"filename":filename})
    published.sort(key=lambda x:(x["date"],x["filename"]),reverse=True)
    for section,archive in SECTION_FILES.items():
        path=ROOT/archive;s=path.read_text(encoding="utf-8")
        rows=[]
        for x in (p for p in published if p["section"]==section):
            url="/"+x["filename"];title=esc(x["title"]);summary=esc(x["summary"])
            rows.append('<article class="news-row"><a href="'+esc(url)+'"><img src="/ChatGPT.png" alt="ZazoomTek" loading="lazy"></a><div class="news-copy"><h2><a href="'+esc(url)+'">'+title+'</a></h2><div class="news-meta">ZazoomTek · '+esc(x["date"])+'</div><p>'+summary+'</p><a class="news-read" href="'+esc(url)+'">Leggi tutto</a></div></article>')
        replacement='<div class="news-list" id="newsList" data-auto-articles="'+section+'">'+"\n".join(rows)+'</div>'
        pattern=r'<div class="news-list" id="newsList" data-auto-articles="'+section+r'">.*?</div>(?=</section>)'
        updated,count=re.subn(pattern,lambda match:replacement,s,count=1,flags=re.S)
        if count!=1:raise RuntimeError("Archive marker missing: "+archive)
        save_if_changed(path,updated)
    chosen=[p for p in published if p["section"]=="tech"][:4]+[p for p in published if p["section"]=="gaming"][:2]
    if len(chosen)==6:
        # Only replace when both editorial sections have a complete set.
        payload={"items":[{"section":x["section"],"slug":x["filename"],"title":x["title"],"image":"/ChatGPT.png"} for x in chosen]}
        save_if_changed(ROOT/"special-featured.json",json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    print("Approved:",len(published)," / highlighted:",len(chosen) if len(chosen)==6 else "previous selection preserved")
if __name__=="__main__":main()
