"""Universal, source-faithful article templates for ZazoomTek.
Structured review metadata (rating, pro/contro, images) is optional.
Never synthesize editorial scores or pros/cons.
"""
import re
from html import escape as esc
from urllib.parse import urlparse

REVIEW_TECH=["Materiali e Design","Hardware e Prestazioni","Esperienza d'Uso","Conclusioni"]
REVIEW_GAMING=["Storia","Gameplay","Aspetto tecnico","Conclusioni"]
H2_NAMES=set(REVIEW_TECH+REVIEW_GAMING+[
 "Introduzione","Autonomia","Caratteristiche tecniche","Conclusione","Considerazioni finali",
 "Pro","Contro","Pro e Contro","Voto finale","Opinione finale",
])
SCORE=re.compile(r"(?:⭐\s*)?\b(?:voto\s*(?:finale)?|valutazione\s*finale|giudizio\s*finale)\s*[:\-]?\s*(10(?:[.,]0)?|[0-9](?:[.,][0-9])?)\s*(?:/\s*10)?\b",re.I)
ONLY_SCORE=re.compile(r"^\s*(?:⭐\s*)?(?:\*\*\s*)?(?:voto\s*(?:finale)?|valutazione\s*finale)\s*(?:\*\*)?\s*[:\-]?\s*(?:10(?:[.,]0)?|[0-9](?:[.,][0-9])?)\s*(?:/\s*10)?\s*$",re.I)
VIDEO_ID=re.compile(r"^[A-Za-z0-9_-]{11}$")
DATE=re.compile(r"^\d{4}-\d{2}-\d{2}")

def category(review):
 return str(review.get("category") or "")

def is_review(review):
 return category(review).startswith("recensioni-")

def plain(s):
 return re.sub(r"\s+"," ",str(s or "")).strip()

def clean_heading(value):
 s=str(value).strip()
 if s.startswith("#"):s=s.lstrip("#").strip()
 if s.startswith("**") and s.endswith("**"):s=s[2:-2].strip()
 if s.endswith(":"):s=s[:-1]
 return s.strip()

def named_section(text):
 title=clean_heading(text)
 if len(title)>85 or "\n" in title:return None
 normalized=title.casefold()
 if normalized in {name.casefold() for name in H2_NAMES}:return title
 if title.startswith(("1. ","2. ","3. ","4. ")) and len(title)<60:return title
 return None

def paragraphs(review):
 arr=review.get("body",[])
 if isinstance(arr,str):arr=re.split(r"\n\s*\n",arr)
 if not isinstance(arr,list):return []
 result=[]
 for item in arr:
  if isinstance(item,str) and item.strip():
   result.extend(part.strip() for part in re.split(r"\n\s*\n",item) if part.strip())
 return result

def author(review):
 value=review.get("author")
 return plain(value)[:100] if isinstance(value,str) and plain(value) else "Redazione ZazoomTek"

def date_label(review):
 value=plain(review.get("published_at") or review.get("date"))
 m=DATE.match(value)
 if not m:return "Data non disponibile"
 y,mon,d=map(int,m.group(0).split("-"))
 try:
  from datetime import date
  return date(y,mon,d).strftime("%d/%m/%Y")
 except ValueError:return "Data non disponibile"

def equipment(review):
 field=plain(review.get("platform") or review.get("device") or "")
 if field:return field[:130]
 title=plain(review.get("title"))
 if category(review)=="recensioni-gaming":
  for pattern in (r"\bPS5\s*Pro\b",r"\bPS5\b",r"\bPS4\b",r"\bPlayStation\s*5\b",
                  r"\bNintendo\s*Switch\s*2\b",r"\bNintendo\s*Switch\b",r"\bXbox\s*Series\s*[XS]\b",r"\bPC\b"):
   match=re.search(pattern,title,re.I)
   if match:return match.group(0)
  return "Piattaforma non indicata"
 # A Tech review names its subject in its title without claiming specific hardware.
 return re.sub(r"\s*[|–-]?\s*(?:recensione|review)\b.*$","",title,flags=re.I)[:130] or "Dispositivo non indicato"

def rich_text(text):
 safe=esc(str(text)).replace("\n","<br>")
 return re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",safe)

def score(review,blocks):
 candidate=review.get("score",review.get("rating",review.get("vote")))
 if isinstance(candidate,dict):candidate=candidate.get("value")
 if candidate is not None and not isinstance(candidate,bool):
  try:
   numeric=float(str(candidate).replace(",",".").replace("/10","").strip())
   if 0<=numeric<=10:return (f"{numeric:g}").replace(".",",")
  except ValueError:pass
 for value in reversed(blocks):
  match=SCORE.search(value)
  if match:return match.group(1).replace(".",",")
 return None

def short_points(review,key):
 raw=review.get(key)
 if isinstance(raw,str):raw=[x.strip() for x in raw.split("\n") if x.strip()]
 if not isinstance(raw,list):return []
 return [plain(x) for x in raw if isinstance(x,str) and plain(x)][:8]

def meta(review):
 typ=category(review)
 label={"news-tech":"News Tech","news-gaming":"News Gaming",
        "recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming",
        "speciali":"Speciali","extra":"Extra","guide":"Guide"}.get(typ,"Articolo")
 d=plain(review.get("date") or review.get("published_at"))
 valid_date=bool(DATE.match(d))
 when='<time datetime="'+esc(d[:10],quote=True)+'">'+esc(date_label(review))+'</time>' if valid_date else '<span>Data non disponibile</span>'
 return ('<div class="story-meta"><span class="story-badge">'+esc(label)+'</span>'
         '<span><strong>Autore:</strong> '+esc(author(review))+'</span>'
         '<span><strong>Data:</strong> '+when+'</span>'
         '<span><strong>Categoria:</strong> '+esc(label)+'</span></div>')

def image_block(review,image_validator,extra=False):
 candidates=[]
 if not extra:candidates=[{"src":review.get("image",""),"caption":review.get("image_caption","")}]
 else:
  images=review.get("images",[])
  if isinstance(images,list):candidates=[i for i in images if isinstance(i,dict)]
 result=[]
 for item in candidates[:6]:
  src=image_validator(item.get("src",""))
  if not src:continue
  caption=plain(item.get("caption",""))
  image='<img loading="lazy" src="'+esc(src,quote=True)+'" alt="'+esc(caption or plain(review.get("title")),quote=True)+'">'
  result.append('<figure class="story-figure">'+image+'<figcaption>'+esc(caption if caption else 'Immagine in evidenza: '+plain(review.get('title')))+'</figcaption></figure>')
 return ''.join(result)

def video(review):
 vid=plain(review.get("youtube_id"))
 url=plain(review.get("video_url"))
 if not VIDEO_ID.fullmatch(vid) and url:
  parsed=urlparse(url)
  host=(parsed.hostname or "").lower()
  if parsed.scheme=="https" and host in ("www.youtube.com","youtube.com","youtu.be","m.youtube.com"):
   if host=="youtu.be":vid=parsed.path.strip("/")
   else:
    from urllib.parse import parse_qs
    vid=parse_qs(parsed.query).get("v",[""])[0]
 if not VIDEO_ID.fullmatch(vid):return ""
 url="https://www.youtube.com/watch?v="+vid
 title=esc(plain(review.get("title")) or "Videorecensione",quote=True)
 return ('<div class="review-video"><a class="review-video-link" href="'+url+'" target="_blank" rel="noopener noreferrer">'
         'Guarda la videorecensione su YouTube</a>'
         '<div class="player"><button type="button" class="video-start" data-youtube-id="'+vid+'" aria-label="Riproduci su YouTube: '+title+'">'
         '<img loading="lazy" src="https://i.ytimg.com/vi/'+vid+'/hqdefault.jpg" alt="">'
         '<span class="video-start-label">▶ Riproduci il video</span></button></div></div>')

def sectioned_body(review):
 blocks=paragraphs(review)
 if not blocks:return "<p>Il testo dell’articolo non è ancora disponibile.</p>"
 explicit=any(named_section(p) for p in blocks)
 filtered=[block for block in blocks if not (is_review(review) and ONLY_SCORE.fullmatch(block.strip()))]
 if explicit:
  out=[]
  for block in filtered:
   heading=named_section(block)
   if heading and heading.lower() not in ("pro","contro","voto finale"):
    out.append('<h2>'+esc(heading)+'</h2>')
   elif heading and heading.lower() in ("pro","contro","voto finale"):
    # Original text is preserved in the article; score also appears in the review box.
    out.append('<h2>'+esc(heading)+'</h2>')
   else:out.append('<p>'+rich_text(block)+'</p>')
  return ''.join(out)
 if not is_review(review):
  content=[]
  for i,p in enumerate(filtered):
   if i==2:content.append('<h2>Approfondimento</h2>')
   if i==5:content.append('<h2>Contesto e dettagli</h2>')
   content.append('<p>'+rich_text(p)+'</p>')
  return ''.join(content)
 # Existing unheaded full-text reviews: preserve paragraph order and group in the native ZazoomTek format.
 if len(filtered)<4:return ''.join('<p>'+rich_text(p)+'</p>' for p in filtered)
 outline=REVIEW_GAMING if category(review)=="recensioni-gaming" else REVIEW_TECH
 middle=filtered[1:-1]
 groups=[[] for _ in range(3)]
 for idx,p in enumerate(middle):
  portion=min(2,(idx*3)//len(middle))
  groups[portion].append(p)
 result=['<h2>Introduzione</h2>','<p>'+rich_text(filtered[0])+'</p>']
 for heading,group in zip(outline[:3],groups):
  if group:result.append('<h2>'+esc(heading)+'</h2>')
  result.extend('<p>'+rich_text(p)+'</p>' for p in group)
 result.extend(['<h2>Conclusioni</h2>','<p>'+rich_text(filtered[-1])+'</p>'])
 return ''.join(result)

def verdict(review):
 blocks=paragraphs(review)
 value=score(review,blocks)
 pros=short_points(review,"pros")
 cons=short_points(review,"cons")
 def list_points(items):
  if items:return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in items)+'</ul>'
  return '<p class="review-data-missing">Non specificati nel testo originale.</p>'
 label=value+'/10' if value is not None else "Non assegnato"
 return ('<section class="review-verdict" aria-label="Valutazione finale">'
         '<div class="verdict-heading"><h2>Voto finale</h2><strong class="verdict-score">'+esc(label)+'</strong></div>'
         '<div class="verdict-grid"><div class="verdict-pro"><h3>Pro</h3>'+list_points(pros)+'</div>'
         '<div class="verdict-con"><h3>Contro</h3>'+list_points(cons)+'</div></div></section>')

def render(review,image_validator):
 reviews=is_review(review)
 title=esc(plain(review.get("title")) or "Senza titolo")
 heading=('<div class="review-topline">'+esc("Recensioni Gaming" if category(review)=="recensioni-gaming" else "Recensioni Tech")
          +'</div>' if reviews else "")
 machine=('<p class="review-equipment"><strong>'+("Piattaforma" if category(review)=="recensioni-gaming" else "Dispositivo")+':</strong> '
          +esc(equipment(review))+'</p>' if reviews else "")
 media=image_block(review,image_validator)
 if not media:
  media=('<div class="story-cover-fallback" role="img" aria-label="Copertina editoriale senza fotografia originale">'
         '<span>'+esc("Recensione" if reviews else "Articolo")+'</span><strong>'+title+'</strong></div>')
 extra=image_block(review,image_validator,extra=True)
 notice='<p class="excerpt-notice">Questo contenuto proviene da un estratto di archivio: il testo originale completo non è disponibile.</p>' if review.get("is_excerpt") else ""
 return ('<article class="article story-article '+("review-article" if reviews else "news-article")+'">'
         +heading+meta(review)+'<h1>'+title+'</h1>'+machine+media
         +video(review)+notice+'<div class="article-text">'+sectioned_body(review)+extra+'</div>'
         +(verdict(review) if reviews else '')+'</article>')
