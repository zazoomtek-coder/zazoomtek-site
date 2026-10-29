"""First-party prioritization for imported Web news.

Select authoritative original ZazoomTek editorial coverage before offering
an external publisher. Never copy the feed article or invent source text.
The internal Web-news gateway is a nonindexable editorial navigation page.
"""
import hashlib,re
from html import escape as esc
from urllib.parse import urlparse
from seo import terms,plain

# Generic news/marketing terms do not establish that two stories are the same.
GENERIC=set(("tech","gaming","gamer","videogiochi","videogioco","game","games",
 "notizie","novita","novità","annuncia","annunciato","annunciata","arriva",
 "prezzo","costa","euro","aggiornamento","aggiornamenti","disponibile",
 "ufficiale","svela","mostra","scopri","recensione","guida","gioco",
 "presenta","primo","nuovo","nuova","nuovi","nuove","italia","italiano",
 "2026","2027","oggi","domani","ieri","sito","online","prime","first",
 "migliori","migliore","milioni","tutte","tutti","altre","altri",
 "come","senza","secondo","primi","seconda","grande","grandi","piu","più",
 "suo","sua","perché","possibile","ora","aiuto")).union(
 {"pro","max","plus","ultra","lite","mini","mobile","pc","ps5","ps4","xbox",
  "switch","google","apple","microsoft","nvidia","sony","samsung","amazon"})
CONTENT_TYPES={"news-tech","news-gaming","recensioni-tech","recensioni-gaming",
               "guide","speciali","extra"}
def important(title):
 return [word for word in terms(title) if word not in GENERIC and len(word)>2]

def subject_anchors(title):
 """Detect shared subject across synonyms like GTA VI / GTA 6, not just GTA."""
 t=plain(title).casefold()
 compact=re.sub(r"[^a-z0-9]+"," ",t)
 anchors=set()
 if re.search(r"\\bgta\\s*(?:6|vi)\\b",compact):anchors.add("gta-6")
 if re.search(r"\\bgta\\s*(?:4|iv)\\b",compact):anchors.add("gta-4")
 if "wolf among us" in compact:anchors.add("wolf-among-us")
 return anchors


def topic_similarity(web_title,original):
 """High-confidence SAME NEWS matching, never just a common game brand."""
 external=important(web_title)
 own=important(original.get("title",""))
 if not external or not own:return 0
 ext=set(external)
 internal=set(own)
 common=ext & internal
 anchors=subject_anchors(web_title)&subject_anchors(original.get("title",""))
 # On a recognisable named subject, one other distinctive shared headline
 # element is enough: GTA VI + meme is the SAME story; GTA VI alone is not.
 subject_words={"gta","meme","wolf","among"}
 distinctive=(common-{"gta","wolf","among"})
 if anchors and distinctive:
  return round(160+8*len(distinctive)+3*len(anchors),2)
 if len(common)<2:return 0
 specificity=len(common)/max(2,min(len(ext),len(internal)))
 if specificity<.42:return 0
 body=" ".join(str(x) if isinstance(x,str) else str(x.get("text",""))
               for x in (original.get("body") if isinstance(original.get("body"),list)
                         else [original.get("body") or ""]))
 body_terms=set(terms(body))
 return round(100*specificity+12*min(6,len(common))+min(len(ext & body_terms),5),2)


def related_subject(web_title,articles,exclude="",limit=3):
 """Less strict than SAME NEWS, but never a random latest-story fallback."""
 key=set(important(web_title))
 anchor=subject_anchors(web_title)
 ranked=[]
 for row in articles:
  if row.get("slug")==exclude or row.get("category") not in CONTENT_TYPES:
   continue
  own=set(important(row.get("title","")))
  common=key & own
  anchored=bool(anchor & subject_anchors(row.get("title","")))
  # A shared named game with a different headline remains an appropriate
  # *related topic*, not a claim that ZazoomTek reported this exact news.
  if not anchored and (len(common)<2 or len(common)<.35*min(len(key),len(own))):
   continue
  ranked.append((bool(anchored),len(common),str(row.get("published_at") or row.get("date") or ""),row))
 ranked.sort(key=lambda x:(x[0],x[1],x[2]),reverse=True)
 used=set()
 found=[]
 for _,_,_,row in ranked:
  if row["slug"] not in used:
   found.append(row);used.add(row["slug"])
  if len(found)==limit:break
 return found

def relevant(web_title,articles,limit=3):
 ranked=[]
 for entry in articles:
  if entry.get("category") not in CONTENT_TYPES:continue
  score=topic_similarity(web_title,entry)
  if score:
   ranked.append((score,str(entry.get("published_at") or entry.get("date") or ""),entry))
 ranked.sort(key=lambda x:(x[0],x[1]),reverse=True)
 unique=set()
 found=[]
 for score,_,entry in ranked:
  if entry["slug"] in unique:continue
  unique.add(entry["slug"])
  found.append(entry)
  if len(found)>=limit:break
 return found

def gateway_path(entry):
 """Stable URL independent of changing title, feed fetch or list position."""
 source=str(entry.get("url") or "").strip()
 if not source.startswith("https://"):return ""
 # Stable relative route; changing feed headlines doesn't invalidate matches.
 parsed=urlparse(source)
 stable=(parsed.hostname or "").lower()+parsed.path.rstrip("/")
 if parsed.query:stable+="?"+parsed.query
 return "/notizia-web-"+hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]

def attach_links(web_items,original_articles):
 for item in web_items:
  if item.get("source_only"):continue
  if not item.get("url") or not gateway_path(item):continue
  item["internal_path"]=gateway_path(item)
  item["original_matches"]=relevant(item.get("title",""),original_articles)
 return web_items

def gateway_html(entry,original_articles):
 """Clearly labelled editorial gateway, not a republished third-party story."""
 title=plain(entry.get("title"))
 name=plain(entry.get("source"))
 date=str(entry.get("date") or "")
 external=str(entry.get("url") or "")
 candidates=entry.get("original_matches")
 if candidates is None:candidates=relevant(title,original_articles)
 match=candidates[0] if candidates else None
 related=(candidates[1:3] if match else []) or related_subject(title,original_articles,exclude=match["slug"] if match else "",limit=3)
 # The SAME title wins first. Otherwise only genuinely relevant subject pages
 # are offered. Never attach arbitrary unrelated headlines from the archive.
 def article_link(row):
  return ('<li><a href="/'+esc(row["slug"],quote=True)+'">'
          +esc(plain(row["title"]))+'</a></li>')
 source_link=('<a class="web-gateway-source-link" href="'+esc(external,quote=True)+'"'
              ' target="_blank" rel="noopener noreferrer external">'
              'Leggi la notizia sul sito originale: '+esc(name)+'</a>')
 headline=('<h1>'+esc(title)+'</h1>'
           '<p class="web-gateway-byline">Notizie dal Web · Fonte: '+esc(name)
           +(' · '+esc(date) if date else '')+'</p>')
 if match:
  cta=('<section class="web-gateway-primary">'
       '<h2>Approfondimento originale ZazoomTek</h2>'
       '<p>ZazoomTek ha già pubblicato un contenuto dedicato allo stesso argomento.'
       ' Per un approfondimento della redazione, parti dal nostro articolo originale.</p>'
       '<p><a class="web-gateway-main-cta" href="/'+esc(match["slug"],quote=True)+'">'
       'Leggi su ZazoomTek: '+esc(plain(match["title"]))+'</a></p></section>')
 else:
  # No false claims about coverage; no empty thin generic paragraphs.
  cta=''
 related_html=('<section class="web-gateway-related"><h2>'
               +("Altri articoli ZazoomTek sullo stesso argomento")
               +'</h2><ul>'+''.join(article_link(x) for x in related)+'</ul></section>'
               if related else '')
 return ('<article class="story-article web-gateway" data-web-gateway="1">'
         +headline+cta+related_html+
         '<p class="web-gateway-external">'+source_link+'</p>'
         '<p class="web-gateway-note">Fonte esterna citata e collegata: il testo dell’articolo'
         ' originale rimane sul sito dell’editore.</p>'
         '</article>')
