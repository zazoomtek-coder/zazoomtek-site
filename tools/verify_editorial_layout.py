"""Exhaustive build-time QA for all published ZazoomTek editorial pages.

Covers the actual generated articles, not a handful of mockup pages.
A new Studio article or YouTube Community import is checked at every build.
No original prose is rewritten by this verifier.
"""
from collections import Counter
from pathlib import Path
import re
from html import escape as esc, unescape

from article_templates import (
 editorial_blocks, is_review, named_section, source_plain_h2,
 rich_text, sectioned_body, merge_repeated_info_sections
)

def check_all(rows, output, stylesheet):
 output=Path(output)
 sheet=Path(stylesheet).read_text(encoding="utf-8")
 if "v43 — universal article/news template" not in sheet:
  raise AssertionError("Universal headline/cover/red-H2 stylesheet missing")
 if "border-left:4px solid #ed304b!important" not in sheet:
  raise AssertionError("Red-bar editorial subtitle rule missing")

 checked=Counter()
 heading_counts=Counter()
 fallback=0
 problems=[]
 for row in rows:
  slug=str(row.get("slug") or "")
  path=output/(slug+".html")
  try:
   if not path.is_file():raise AssertionError("Generated article file missing")
   page=path.read_text(encoding="utf-8")
   body=merge_repeated_info_sections(sectioned_body(row))
   title=esc(str(row.get("title") or "").strip())
   if not title or "<h1>"+title+"</h1>" not in page:
    raise AssertionError("Missing/incorrect primary headline")
   meta=page.find('class="story-meta"')
   cover=page.find('class="story-figure"')
   if cover<0:
    cover=page.find('class="story-cover-fallback"')
    if cover>=0:fallback+=1
   content=page.find('class="article-text"')
   if not (page.find("<h1>")>=0 and meta>=0 and cover>=0 and content>=0 and
           page.find("<h1>")<meta<cover<content):
    raise AssertionError("Incorrect H1 → metadata → cover → article content order")
   if body not in page:raise AssertionError("Rendered editorial content differs from shared template")
   h2s=re.findall(r"<h2>(.*?)</h2>",body,flags=re.S)
   if not h2s or any(not re.sub("<[^>]+>","",h).strip() for h in h2s):
    raise AssertionError("Article is missing editorial red-bar subtitles")
   if not re.search(r"<p>[^<\s]",body):
    raise AssertionError("Article has no readable paragraphs")
   if re.search(r"</h2>\s*<h2>",body):
    raise AssertionError("Consecutive orphan editorial subtitles")
   if re.search(r"<p>\s*(?:#{1,3}\s+|\*\*)[^<]+</p>",body):
    raise AssertionError("Markdown heading was not rendered structurally")

   if not is_review(row) and not row.get('studio_blocks'):
    # Catch the original defect: one giant wall of text under a single subtitle.
    # Every ordinary paragraph is bounded, and every section contains <=2
    # paragraphs. This check now rejects Expedition-style broken layouts.
    paragraphs=re.findall(r"<p>(.*?)</p>",body,flags=re.S)
    paragraphs=[unescape(re.sub(r"<[^>]+>","",p)) for p in paragraphs]
    if any(len(p)>430 for p in paragraphs):
     raise AssertionError("Giant paragraph exceeds 430 characters")
    blocks=re.findall(r"<(h2|p)>(.*?)</\1>",body,flags=re.S)
    paragraphs_before_heading=0
    paragraphs_in_section=0
    seen_heading=False
    current_heading=""
    for tag,text in blocks:
     if tag=="h2":
      seen_heading=True
      current_heading=unescape(re.sub(r"<[^>]+>","",text)).strip().casefold()
      paragraphs_in_section=0
     else:
      if seen_heading:
       paragraphs_in_section+=1
       if paragraphs_in_section>2 and current_heading!="ulteriori informazioni":
        raise AssertionError("More than two paragraphs under one red-bar heading")
      else:
       paragraphs_before_heading+=1
       if paragraphs_before_heading>2:
        raise AssertionError("More than two introductory paragraphs without a heading")
    # Full source prose must survive, in order, without added or omitted words.
    # Splitting paragraphs changes markup but must NOT change the source prose.
    source=editorial_blocks(row)
    original=[]
    for i,block in enumerate(source):
     if named_section(block):continue
     following=source[i+1] if i+1<len(source) else ""
     if source_plain_h2(block,following,i):continue
     original.append(block)
    expected=re.sub(r"\*\*(.*?)\*\*",r"\1"," ".join(original),flags=re.S)
    without_titles=re.sub(r"<h2>.*?</h2>"," ",body,flags=re.S)
    without_titles=re.sub(r"</p>|<br\s*/?>"," ",without_titles,flags=re.I)
    actual=unescape(re.sub(r"<[^>]*>","",without_titles))
    def norm(x):
     return re.sub(r"\s+"," ",x).strip()
    if norm(expected)!=norm(actual):
     raise AssertionError("Original prose differs after reformatting")
   category=str(row.get("category") or "other")
   checked[category]+=1
   heading_counts[category]+=len(h2s)
  except Exception as exc:
   problems.append((slug, str(exc)))

 if problems:
  sample="; ".join(slug+": "+issue for slug,issue in problems[:20])
  raise AssertionError("Global article-format audit FAILED for "+
   str(len(problems))+" of "+str(len(rows))+" articles: "+sample)
 if sum(checked.values())!=len(rows):
  raise AssertionError("Not all editorial pages were inspected")
 print("GLOBAL EDITORIAL FORMAT AUDIT PASS:",
       sum(checked.values()),"generated pages;",
       sum(heading_counts.values()),"H2 editorial sections;",
       fallback,"authentic-cover fallbacks;",dict(checked),flush=True)

if __name__=="__main__":
 raise SystemExit("Run after all articles are generated in tools/build.py")
