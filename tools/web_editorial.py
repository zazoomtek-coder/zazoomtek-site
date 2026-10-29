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
 if re.search(r"\bgta\s*(?:6|vi)\b",compact):anchors.add("gta-6")
 if re.search(r"\bgta\s*(?:4|iv)\b",compact):anchors.add("gta-4")
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

def web_gateway_suggestions(entry,articles,exact_matches=None,limit=3):
 """Choose REAL first-party coverage first; never imply a random item covers exact news.

 Exact articles are linked above as primary and excluded from these three cards.
 If a niche topic has fewer than 3 relevant pieces, fill with the newest
 articles in its Tech/Gaming section and use an honest general section title.
 """
 title=plain(entry.get("title"))
 exact_matches=exact_matches if exact_matches is not None else relevant(title,articles)
 primary=exact_matches[0] if exact_matches else None
 excluded={primary["slug"]} if primary else set()
 chosen=[];used=set(excluded)
 def take(row):
  slug=str(row.get("slug") or "")
  if not slug or slug in used or row.get("category") not in CONTENT_TYPES:return False
  used.add(slug);chosen.append(row)
  return True
 for row in exact_matches[1:]:
  take(row)
  if len(chosen)>=limit:return chosen,True
 for row in related_subject(title,articles,exclude=primary["slug"] if primary else "",limit=20):
  take(row)
  if len(chosen)>=limit:return chosen,True
 strictly_related=len(chosen)
 gaming=bool(re.search(r"(?i)\b(?:playstation|ps5|ps4|xbox|nintendo|switch|videogioch[io]|gaming|gameplay|gta|steam|videogame)\b",title))
 preferred="news-gaming" if gaming else "news-tech"
 # A brand shared with the original title is a useful weak signal,
 # not proof of reporting this exact outside story.
 brand_words={"sony","dji","apple","samsung","google","microsoft","nvidia",
              "intel","amd","meta","xiaomi","realme","lenovo","asus"}
 brands=brand_words & set(terms(title))
 def relevance(row):
  overlap=len(set(terms(row.get("title","")))&set(terms(title)))
  brand_overlap=len(brands&set(terms(row.get("title",""))))
  return (int(row.get("category")==preferred),brand_overlap,overlap,
          str(row.get("published_at") or row.get("date") or ""))
 ordered=sorted((r for r in articles if r.get("category") in CONTENT_TYPES),
                key=relevance,reverse=True)
 for row in ordered:
  take(row)
  if len(chosen)>=limit:break
 # Nothing in the code creates fake content or invents source links.
 return chosen[:limit],bool(strictly_related and strictly_related==len(chosen))


def gateway_html(entry,original_articles,image_validator=None):
 """Full-width original-source gateway followed by 3 distinct first-party cards."""
 title=plain(entry.get("title"))
 name=plain(entry.get("source"))
 date=str(entry.get("date") or "")
 external=str(entry.get("url") or "")
 candidates=entry.get("original_matches")
 if candidates is None:candidates=relevant(title,original_articles)
 match=candidates[0] if candidates else None
 suggested,all_related=web_gateway_suggestions(entry,original_articles,candidates,limit=3)
 entry["gateway_recommendation_slugs"]=[r["slug"] for r in suggested]
 if match:entry["gateway_recommendation_slugs"].append(match["slug"])
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
 else:cta=''
 cards=[]
 for row in suggested:
  url="/"+str(row["slug"])
  safe=image_validator(row.get("image","")) if image_validator else ""
  image=('<img loading="lazy" decoding="async" src="'+esc(safe,quote=True)+'" alt="">' if safe
         else '<span class="web-gateway-card-fallback" aria-hidden="true">ZazoomTek</span>')
  day=str(row.get("date") or row.get("published_at") or "")[:10]
  when=('<time datetime="'+esc(day,quote=True)+'">'+esc(day[8:10]+"/"+day[5:7]+"/"+day[:4])+'</time>'
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}",day) else "")
  cards.append('<article class="web-gateway-card">'
               '<a class="web-gateway-card-cover" href="'+esc(url,quote=True)+'">'+image+'</a>'
               '<h3><a href="'+esc(url,quote=True)+'">'+esc(plain(row["title"]))+'</a></h3>'+when
               +'</article>')
 section_title="Altri articoli ZazoomTek sullo stesso argomento" if all_related else "Leggi anche su ZazoomTek"
 related_html=('<section class="web-gateway-related" aria-label="Articoli suggeriti ZazoomTek">'
               '<h2>'+section_title+'</h2>'
               '<div class="web-gateway-cards">'+''.join(cards)+'</div></section>' if cards else '')
 # The external source is ALWAYS visible before the cards, matching approved page.
 return ('<article class="story-article web-gateway" data-web-gateway="1">'
         +headline+cta+
         '<p class="web-gateway-external">'+source_link+'</p>'
         '<p class="web-gateway-note">Fonte esterna citata e collegata: il testo dell’articolo'
         ' originale rimane sul sito dell’editore.</p>'
         +related_html+'</article>')
