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
 raw=str(text).strip()
 # Preserve real headings from the original Community/Studio text.
 if re.fullmatch(r"\*\*[^*\n]{3,90}\*\*",raw):return clean_heading(raw)
 if re.fullmatch(r"#{1,3}\s+[^\n]{3,90}",raw):return clean_heading(raw)
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
  if isinstance(item,dict):
   raw=item.get("text") if isinstance(item.get("text"),str) else item.get("content")
   if not isinstance(raw,str) or not raw.strip():continue
   kind=str(item.get("type") or item.get("kind") or "").casefold()
   if kind in ("h2","heading","section-title","subtitle"):
    result.append("## "+clean_heading(raw))
   elif kind in ("paragraph","text","p"):
    result.extend(part.strip() for part in re.split(r"\n\s*\n",raw) if part.strip())
  elif isinstance(item,str) and item.strip():
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
 # A source paragraph may wrap across multiple lines; those are not HTML breaks.
 # Preserve real list formatting only for lines explicitly marked as list items.
 raw=str(text or "").replace("\r\n","\n").replace("\r","\n")
 is_list=bool(re.search(r"(?m)^\s*(?:[-•]|\d+[.)])\s+\S",raw))
 if is_list:
  safe=esc(raw)
  safe=re.sub(r"[ \t]*\n[ \t]*","<br>",safe)
 else:
  raw=re.sub(r"\s*\n\s*"," ",raw)
  safe=esc(re.sub(r"[ \t]{2,}"," ",raw).strip())
 return re.sub(r"\*\*(.+?)\*\*",r"<strong>\1</strong>",safe)

def compact_prose_html(parts):
 """Join short prose fragments into comfortable paragraphs, without touching H2s or lists.
 Source text is not shortened or rewritten. Source headings remain hard boundaries.
 """
 output=[];pending=[];pending_chars=0
 def flush():
  nonlocal pending_chars
  if pending:
   output.append("<p>"+" ".join(pending)+"</p>")
   pending.clear()
   pending_chars=0
 for element in parts:
  if not (element.startswith("<p>") and element.endswith("</p>")):
   flush()
   output.append(element)
   continue
  inside=element[3:-4].strip()
  if not inside:continue
  length=len(re.sub(r"<[^>]*>","",inside))
  # Explicit numbered/bulleted lists and source paragraphs of substantial length stay intact.
  if "<br>" in inside or length>=340:
   flush()
   output.append("<p>"+inside+"</p>")
   continue
  # Group only the source's short, adjacent paragraphs. Never glue a question to
  # preceding text, and never cross a heading (handled by the non-paragraph branch).
  question=bool(re.search(r"[?？]\s*$",re.sub(r"<[^>]*>","",inside)))
  if question:
   flush()
   output.append("<p>"+inside+"</p>")
   continue
  if pending and pending_chars+length>535:
   flush()
  pending.append(inside)
  pending_chars+=length
  if pending_chars>=350:flush()
 flush()
 return "".join(output)

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

ITALIAN_MONTHS=("","gennaio","febbraio","marzo","aprile","maggio","giugno",
                "luglio","agosto","settembre","ottobre","novembre","dicembre")
def meta(review):
 typ=category(review)
 label={"news-tech":"News Tech","news-gaming":"News Gaming",
        "recensioni-tech":"Recensioni Tech","recensioni-gaming":"Recensioni Gaming",
        "speciali":"Speciali","extra":"Extra","guide":"Guide"}.get(typ,"Articolo")
 d=plain(review.get("published_at") or review.get("date"))
 valid_date=bool(DATE.match(d))
 when="Data non disponibile"
 if valid_date:
  try:
   from datetime import date
   day=date.fromisoformat(d[:10])
   when=('<time datetime="'+esc(day.isoformat(),quote=True)+'">'+
         str(day.day)+" "+ITALIAN_MONTHS[day.month]+" "+str(day.year)+'</time>')
  except ValueError:pass
 return ('<div class="story-meta" aria-label="Informazioni sull’articolo">'
         '<span class="story-meta-author"><strong>Autore:</strong> '+esc(author(review))+'</span>'
         '<span class="story-meta-date"><strong>Data:</strong> '+when+'</span>'
         '<span class="story-meta-category"><strong>Categoria:</strong> '+esc(label)+'</span></div>')

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
  result.append('<figure class="story-figure">'+image+('<figcaption>'+esc(caption)+'</figcaption>' if caption else '')+'</figure>')
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

def editorial_blocks(review):
 """Keep the author's article; remove social-signature and hashtag tails from main editorial content."""
 pieces=paragraphs(review)
 cleaned=[]
 for p in pieces:
  p=p.strip()
  # Social boilerplate belongs in navigation, not in the text of an article.
  p=re.split(r"(?im)^\s*(?:Subscribe\b|Iscriviti\b|🌐\s*zazoomtek\.it\b|▶\ufe0f?\s*YouTube\s*:|#\w+(?:\s+#\w+){2,}\s*$)",p,maxsplit=1)[0].strip()
  if not p:break
  if re.fullmatch(r"(?i)(?:Foto|Photo|Immagine|Picture)\s*(?:n[.°]\s*)?\d+",clean_heading(p)):continue
  if re.match(r"(?i)^#(?:\w+)(?:\s+#\w+)*\s*$",p):break
  cleaned.append(p)
 # Remove duplicate headline/category prefix inside the opening paragraph, not the real prose.
 if cleaned:
  first=cleaned[0]
  first=re.sub(r"(?i)^\s*(?:(?:News|Review|Recensione)(?:\s+(?:Tech|Gaming|Extra))?|Articolo)\s*:\s*","",first)
  title=plain(review.get("title",""))
  lines=first.split("\n",1)
  if len(lines)>1 and re.sub(r"[^a-z0-9]","",lines[0].casefold())==re.sub(r"[^a-z0-9]","",title.casefold()):
   first=lines[1].strip()
  if first:cleaned[0]=first
 return cleaned

def source_plain_h2(block,following,position):
 """Promote an existing *isolated source line*, never generate new section text."""
 raw=str(block).strip()
 if position==0 or not isinstance(following,str) or len(following.strip())<115:return False
 if not 12<=len(raw)<=95 or "\n" in raw or len(raw.split())>15:return False
 if raw.startswith(("#","-","•","http","www.","⭐")):return False
 if re.search(r"(?:!|…|;)$",raw):return False
 if raw.count(".")>1:return False
 if re.fullmatch(r"(?i)(?:Subscribe|Iscriviti|Commenta|Seguici).*",raw):return False
 if not raw[0].isupper():return False
 # A standalone line before detailed prose is source-provided editorial structure.
 return True

def supplied_h2(review):
 """Optional exact positions/titles carried by Studio or archived source materials."""
 headings={}
 for entry in review.get("headings",[]) if isinstance(review.get("headings"),list) else []:
  if not isinstance(entry,dict):continue
  idx=entry.get("before_paragraph")
  title=entry.get("title")
  if isinstance(idx,int) and not isinstance(idx,bool) and idx>=0 and isinstance(title,str):
   label=clean_heading(title)
   if 3<=len(label)<=95 and "\n" not in label:headings[idx]=label
 return headings

def news_body(review,blocks):
 result=[]
 headings=supplied_h2(review)
 for i,paragraph in enumerate(blocks):
  heading=named_section(paragraph)
  if i in headings and (not heading or clean_heading(heading).casefold()!=headings[i].casefold()):
   result.append('<h2>'+esc(headings[i])+'</h2>')
  if heading and heading.casefold() not in ("voto finale","pro","contro"):
   result.append('<h2>'+esc(heading)+'</h2>')
  elif source_plain_h2(paragraph,blocks[i+1] if i+1<len(blocks) else "",i):
   result.append('<h2>'+esc(clean_heading(paragraph))+'</h2>')
  else:
   result.append('<p>'+rich_text(paragraph)+'</p>')
 return compact_prose_html(result)

def sectioned_body(review):
 blocks=editorial_blocks(review)
 if not blocks:return "<p>Il testo integrale dell'articolo non è ancora disponibile nell'archivio.</p>"
 if not is_review(review):
  return news_body(review,blocks)

 # The score and final reader question follow the actual conclusion in original Community reviews.
 marker=next((idx for idx,p in enumerate(blocks) if ONLY_SCORE.fullmatch(p.strip()) or
              (p.strip().startswith(("⭐","Voto finale:")) and SCORE.search(p))),len(blocks))
 prose=blocks[:marker]
 prose=[p for p in prose if not ONLY_SCORE.fullmatch(p.strip())]
 if not prose:prose=["Recensione archivistica in attesa del testo integrale."]
 # Use the original conclusion, not the last comment-call-to-action or hashtags.
 editorial_conclusion=review.get("conclusion")
 explicit_indices=[idx for idx,p in enumerate(prose) if named_section(p) and clean_heading(p).casefold() in ("conclusioni","conclusione")]
 if explicit_indices:
  split=explicit_indices[-1]
  core=[p for p in prose[:split] if p.strip()]
  ending=[p for p in prose[split+1:] if p.strip() and not named_section(p)]
  conclusion=([editorial_conclusion] if editorial_conclusion else ending)
 elif editorial_conclusion:
  core=prose
  conclusion=[editorial_conclusion]
 else:
  # Long-form reviews may have multi-paragraph conclusions; preserve all of them.
  n=len(prose)
  num=4 if n>=27 else (3 if n>=19 else 1)
  num=min(num,max(1,n-1))
  core=prose[:-num]
  conclusion=prose[-num:]
  if not core:core=prose;conclusion=[]
 # Prevent duplicated concluding text when source already has the same conclusion.
 if editorial_conclusion:
  conclusion=[editorial_conclusion]
  core=[p for p in core if p.strip()!=str(editorial_conclusion).strip()]
 rendered=[]
 if any(named_section(x) for x in core):
  for p in core:
   heading=named_section(p)
   if heading:
    if heading.casefold() in ("voto finale","pro","contro","conclusioni"):continue
    rendered.append('<h2>'+esc(heading)+'</h2>')
   else:rendered.append('<p>'+rich_text(p)+'</p>')
 else:
  # Four native review blocks with factual text kept in the original order.
  outline=REVIEW_GAMING if category(review)=="recensioni-gaming" else REVIEW_TECH
  if core:
   rendered.extend(['<h2>Introduzione</h2>','<p>'+rich_text(core[0])+'</p>'])
   middle=core[1:]
   groups=[[] for _ in range(3)]
   for idx,p in enumerate(middle):
    groups[min(2,(idx*3)//max(1,len(middle)))].append(p)
   for heading,group in zip(outline[:3],groups):
    if group:
     rendered.append('<h2>'+esc(heading)+'</h2>')
     rendered.extend('<p>'+rich_text(p)+'</p>' for p in group)
 if conclusion:
  rendered.append('<h2>Conclusioni</h2>')
  rendered.extend('<p>'+rich_text(p)+'</p>' for p in conclusion)
 return compact_prose_html(rendered)

def verdict(review):
 value=score(review,paragraphs(review))
 pros=short_points(review,"pros")
 cons=short_points(review,"cons")
 def list_points(items,label):
  if items:return '<ul>'+''.join('<li>'+esc(x)+'</li>' for x in items)+'</ul>'
  return '<p class="review-data-missing">Nessun elemento verificato nel testo attualmente disponibile.</p>'
 label=value+'/10' if value is not None else "Voto non disponibile"
 return ('<section class="review-verdict" aria-label="Valutazione finale">'
         '<div class="verdict-heading"><h2>Voto finale</h2><strong class="verdict-score">'+esc(label)+'</strong></div>'
         '<div class="verdict-grid"><div class="verdict-pro"><h3>Pro</h3>'+list_points(pros,"pro")+'</div>'
         '<div class="verdict-con"><h3>Contro</h3>'+list_points(cons,"contro")+'</div></div></section>')

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
 source_notes=review.get("ending_notes",[]) if reviews else []
 if not isinstance(source_notes,list):source_notes=[]
 retained_notes=compact_prose_html(['<p>'+rich_text(line)+'</p>' for line in source_notes if isinstance(line,str) and line.strip()])
 return ('<article class="article story-article '+("review-article" if reviews else "news-article")+'">'
         +'<h1>'+title+'</h1>'+meta(review)+machine+media
         +video(review)+notice+'<div class="article-text">'+sectioned_body(review)+retained_notes+extra+'</div>'
         +(verdict(review) if reviews else '')+'</article>')
