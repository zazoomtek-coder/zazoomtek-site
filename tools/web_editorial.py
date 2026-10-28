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

def topic_similarity(web_title,original):
 """Conservative shared-subject matching, not generic keyword overlap."""
 external=important(web_title)
 own=important(original.get("title",""))
 if not external or not own:return 0
 ext=set(external)
 internal=set(own)
 common=ext & internal
 if len(common)<2:return 0
 # Two anchored distinct title words are required; plain 'gaming' or
 # standalone brands cannot make an unrelated article into a match.
 specificity=len(common)/max(2,min(len(ext),len(internal)))
 if specificity<.42:return 0
 # Score full source text as a tie-breaker, never instead of title matching.
 body=" ".join(str(x) if isinstance(x,str) else str(x.get("text",""))
               for x in (original.get("body") if isinstance(original.get("body"),list)
                         else [original.get("body") or ""]))
 body_terms=set(terms(body))
 title_overlap=min(6,len(common))
 prose_overlap=len(ext & body_terms)
 return round(100*specificity+12*title_overlap+min(prose_overlap,5),2)

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
 related=candidates[1:3] if match else []
 if not related:
  # If we have no exact original, show only genuinely topical items where
  # possible. A generic recent-content fallback is labelled honestly.
  key=set(important(title))
  pool=[]
  for row in original_articles:
   if row.get("category") not in CONTENT_TYPES:continue
   score=len(key & set(important(row.get("title",""))))
   if score:pool.append((score,str(row.get("date") or ""),row))
  pool.sort(key=lambda a:(a[0],a[1]),reverse=True)
  related=[r for _,_,r in pool if not match or r["slug"]!=match["slug"]][:3]
 if not related:
  related=[r for r in original_articles
           if r.get("category") in ("news-tech","news-gaming") and
           (not match or r["slug"]!=match["slug"])][:3]
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
  cta=('<section class="web-gateway-primary">'
       '<h2>La notizia e gli approfondimenti</h2>'
       '<p>La notizia è stata segnalata da '+esc(name)+'. '
       'Al momento non risulta un approfondimento originale ZazoomTek sullo stesso argomento.</p>'
       '<p>Puoi esplorare gli altri contenuti della redazione oppure consultare '
       'direttamente la fonte per leggere tutti i dettagli.</p></section>')
 related_html=('<section class="web-gateway-related"><h2>'
               +("Altri contenuti ZazoomTek sull'argomento" if candidates and related else
                 "Scopri altri contenuti ZazoomTek")
               +'</h2><ul>'+''.join(article_link(x) for x in related)+'</ul></section>'
               if related else '')
 return ('<article class="story-article web-gateway" data-web-gateway="1">'
         +headline+cta+related_html+
         '<p class="web-gateway-external">'+source_link+'</p>'
         '<p class="web-gateway-note">Fonte esterna citata e collegata: il testo dell’articolo'
         ' originale rimane sul sito dell’editore.</p>'
         '</article>')
