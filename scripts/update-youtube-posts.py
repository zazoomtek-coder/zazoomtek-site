#!/usr/bin/env python3
# Global scrollbar refresh marker
import json,re,html,time,urllib.error,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path

URL="https://www.youtube.com/@ZazoomTek/posts"
STATE=Path(".youtube-posts.json")
INDEX=Path("index.html")

def open_with_retry(req, *, timeout=30, parse_json=False, attempts=5):
    """Retry transient YouTube/network failures; never hide a partial sync."""
    last_error=None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as r:
                return json.load(r) if parse_json else r.read().decode("utf-8","replace")
        except urllib.error.HTTPError as err:
            last_error=err
            if err.code not in (408,425,429,500,502,503,504):
                raise
        except (urllib.error.URLError,ConnectionResetError,TimeoutError) as err:
            last_error=err
        if attempt<attempts-1:
            wait=min(16,2 ** (attempt+1))
            print(f"Temporary YouTube error ({last_error}); retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"YouTube request failed after {attempts} attempts: {last_error}")

def fetch():
    req=urllib.request.Request(
        URL,
        headers={
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept-Language":"it-IT,it;q=0.9,en;q=0.8",
            "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Cache-Control":"no-cache",
        }
    )
    last_problem="unknown"
    for attempt in range(5):
        page=open_with_retry(req,timeout=30,attempts=3)
        # A successful HTTP response can still be a transient YouTube
        # interstitial/challenge with no usable ytInitialData. Treat that as a
        # temporary failure and retry instead of publishing an empty feed.
        if initial_data(page):
            return page
        last_problem="YouTube page contained no usable ytInitialData"
        if attempt<4:
            wait=min(20,3*(attempt+1))
            print(f"{last_problem}; retrying in {wait}s...")
            time.sleep(wait)
    raise RuntimeError(f"Community page unavailable after retries: {last_problem}")

def initial_data(s):
    pats=[r'var ytInitialData = ({.*?});</script>',r'ytInitialData\s*=\s*({.*?});</script>']
    for p in pats:
        m=re.search(p,s,re.S)
        if m:
            try:return json.loads(m.group(1))
            except:pass
    return {}

def txt(v):
    if not isinstance(v,dict):return ""
    if "simpleText" in v:return v["simpleText"]
    return "".join(x.get("text","") for x in v.get("runs",[]) if isinstance(x,dict))

def stable_published_label(value):
    """Convert fast-changing recent relative times into a stable calendar date."""
    raw=(value or "").strip()
    low=raw.lower()
    now=datetime.now(timezone.utc)
    delta=None

    patterns=[
        (r"^(\d+)\s+second[oi]\s+fa$", "seconds"),
        (r"^(\d+)\s+minut[oi]\s+fa$", "minutes"),
        (r"^(\d+)\s+or[ae]\s+fa$", "hours"),
        (r"^(\d+)\s+giorn[oi]\s+fa$", "days"),
        (r"^(\d+)\s+settiman[ae]\s+fa$", "weeks"),
    ]
    singular={
        "un secondo fa":("seconds",1),"1 secondo fa":("seconds",1),
        "un minuto fa":("minutes",1),"1 minuto fa":("minutes",1),
        "un'ora fa":("hours",1),"un’ora fa":("hours",1),"1 ora fa":("hours",1),
        "un giorno fa":("days",1),"1 giorno fa":("days",1),"ieri":("days",1),
        "una settimana fa":("weeks",1),"1 settimana fa":("weeks",1),
    }

    if low in singular:
        unit,n=singular[low]
        delta=timedelta(**{unit:n})
    else:
        for pattern,unit in patterns:
            m=re.match(pattern,low)
            if m:
                delta=timedelta(**{unit:int(m.group(1))})
                break

    if delta is None:
        return raw

    dt=now-delta
    months=["gennaio","febbraio","marzo","aprile","maggio","giugno",
            "luglio","agosto","settembre","ottobre","novembre","dicembre"]
    return f"{dt.day} {months[dt.month-1]} {dt.year}"

def walk(x,out):
    if isinstance(x,dict):
        for k,v in x.items():
            if k in ("backstagePostRenderer","postRenderer") and isinstance(v,dict): out.append(v)
            walk(v,out)
    elif isinstance(x,list):
        for v in x:walk(v,out)

def normalize_youtube_image_url(url):
    """Prefer the full Community image instead of YouTube's pre-cropped fcrop64 variant."""
    u=(url or "").replace("\\u0026","&")
    if "yt3.ggpht.com" in u:
        # Community thumbnails often arrive as:
        #   =sNNN-c-fcrop64=...-rw-nd-v1
        # which bakes a crop into the source itself. Remove that crop and request
        # a larger uncropped rendition so text inside covers stays readable.
        u=re.sub(r"=s\d+(?:-[^?]*)?$","=s1600-rw-nd-v1",u)
    return u

def image_urls(p):
    """Return Community-post images in attachment order, one URL per image."""
    found=[]
    seen=set()

    def add(url):
        u=normalize_youtube_image_url(url)
        if not u or not u.startswith("http") or u in seen:
            return
        seen.add(u)
        found.append(u)

    def collect_thumb_groups(x):
        if isinstance(x,dict):
            thumbs=x.get("thumbnails")
            if isinstance(thumbs,list):
                valid=[t for t in thumbs if isinstance(t,dict) and str(t.get("url","")).startswith("http")]
                if valid:
                    best=max(valid,key=lambda t:(t.get("width",0) or 0)*(t.get("height",0) or 0))
                    add(best.get("url",""))
            for k,v in x.items():
                if k!="thumbnails":
                    collect_thumb_groups(v)
        elif isinstance(x,list):
            for v in x:
                collect_thumb_groups(v)

    # Stay inside the post attachment tree so avatars/channel artwork are not
    # accidentally imported as article images.
    for key in ("backstageAttachment","attachment","postMultiImageRenderer"):
        if isinstance(p,dict) and p.get(key):
            collect_thumb_groups(p[key])

    if found:
        return found

    # Fallback for renderer variants that do not expose a normal attachment.
    candidates=[]
    def fallback_walk(x):
        if isinstance(x,dict):
            thumbs=x.get("thumbnails")
            if isinstance(thumbs,list):
                for t in thumbs:
                    if isinstance(t,dict):
                        u=t.get("url","")
                        if isinstance(u,str) and u.startswith("http"):
                            candidates.append(((t.get("width",0) or 0)*(t.get("height",0) or 0),u))
            for v in x.values():
                fallback_walk(v)
        elif isinstance(x,list):
            for v in x:
                fallback_walk(v)
    fallback_walk(p)
    if candidates:
        add(max(candidates,key=lambda x:x[0])[1])
    return found

def image_url(p):
    imgs=image_urls(p)
    return imgs[0] if imgs else ""

def post_extra_images(p):
    """All post photos except the first cover image, with duplicates removed."""
    imgs=p.get("images") or ([p.get("image")] if p.get("image") else [])
    primary=p.get("image") or (imgs[0] if imgs else "")
    out=[]
    seen={primary} if primary else set()
    for u in imgs:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out

def distribute_inline_images(blocks,p,title):
    """Place Community photos cleanly between article sections.

    Default rule: images go only after the final paragraph of a section,
    never between normal paragraphs of the same section and never after
    Conclusioni. An internal slot is allowed only for an exceptionally long
    section (4+ paragraphs and over 5,000 visible characters).
    """
    extras=post_extra_images(p)
    if not extras or not blocks:
        return blocks

    conclusion_idx=next((
        i for i,b in enumerate(blocks)
        if b.lstrip().lower().startswith("<h2") and "conclusioni" in b.lower()
    ),len(blocks))

    heading_idxs=[
        i for i,b in enumerate(blocks[:conclusion_idx])
        if b.lstrip().lower().startswith("<h2")
    ]
    candidates=[]
    internal_candidates=[]

    for pos,hidx in enumerate(heading_idxs):
        next_h=heading_idxs[pos+1] if pos+1<len(heading_idxs) else conclusion_idx
        p_idxs=[
            i for i in range(hidx+1,next_h)
            if blocks[i].lstrip().startswith("<p>")
        ]
        if not p_idxs:
            continue

        # Main placement: after the section's last paragraph.
        candidates.append(p_idxs[-1])

        # Only very long sections may receive one additional image internally.
        visible_chars=sum(len(re.sub(r"<[^>]+>","",blocks[i])) for i in p_idxs)
        if len(p_idxs)>=4 and visible_chars>5000:
            internal_candidates.append(p_idxs[len(p_idxs)//2-1])

    # Keep normal articles visually clean. Add internal slots only when a
    # section is exceptionally long.
    candidates=sorted(set(candidates+internal_candidates))
    if not candidates:
        return blocks

    # Never stack several imported photos at one boundary. If the post contains
    # more photos than clean slots, use a representative subset.
    slot_count=min(len(extras),len(candidates))
    if slot_count<=0:
        return blocks

    if len(extras)==slot_count:
        chosen=extras
    else:
        chosen=[]
        for n in range(slot_count):
            src_idx=((n+1)*len(extras))//(slot_count+1)
            src_idx=max(0,min(len(extras)-1,src_idx))
            chosen.append(extras[src_idx])

    inserts={}
    for n,(idx,u) in enumerate(zip(candidates[:slot_count],chosen)):
        media=(
            f'<figure class="article-inline-media">'
            f'<img src="{html.escape(u)}" alt="{html.escape(title)} - immagine {n+2}" loading="lazy">'
            f'</figure>'
        )
        inserts[idx]=[media]

    out=[]
    for i,b in enumerate(blocks):
        out.append(b)
        out.extend(inserts.get(i,[]))
    return out

def continuation_tokens(x):
    out=[]
    def w(v):
        if isinstance(v,dict):
            cc=v.get("continuationCommand")
            if isinstance(cc,dict) and cc.get("token"): out.append(cc["token"])
            for z in v.values(): w(z)
        elif isinstance(v,list):
            for z in v: w(z)
    w(x)
    return out

def innertube_config(page):
    key=""
    ver=""
    m=re.search(r'"INNERTUBE_API_KEY":"([^"]+)"',page)
    if m:key=m.group(1)
    m=re.search(r'"INNERTUBE_CLIENT_VERSION":"([^"]+)"',page)
    if m:ver=m.group(1)
    return key,ver

def fetch_continuation(token,key,ver):
    if not key or not ver:return {}
    payload=json.dumps({
        "context":{"client":{"clientName":"WEB","clientVersion":ver,"hl":"it","gl":"IT"}},
        "continuation":token
    }).encode("utf-8")
    req=urllib.request.Request(
        "https://www.youtube.com/youtubei/v1/browse?key="+key,
        data=payload,
        headers={
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Content-Type":"application/json",
            "Accept-Language":"it-IT,it;q=0.9,en;q=0.8"
        }
    )
    return open_with_retry(req,timeout=30,parse_json=True)

def parse_nodes(data,posts,seen):
    nodes=[];walk(data,nodes)
    added=[]
    for p in nodes:
        pid=p.get("postId") or p.get("backstagePostId")
        if not pid or pid in seen:continue
        seen.add(pid)
        added.append(pid)
        body=txt(p.get("contentText",{})) or txt(p.get("backstagePostText",{}))
        when=stable_published_label(txt(p.get("publishedTimeText",{})))
        imgs=image_urls(p)
        posts.append({
            "id":pid,
            "text":body.strip(),
            "published":when,
            "image":imgs[0] if imgs else "",
            "images":imgs,
            "url":"https://www.youtube.com/post/"+pid
        })
    return added

def looks_like_review_post(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    first=lines[0].lower() if lines else ""
    body=(p.get("text") or "").lower()
    return (not first.startswith("news:")) and ("recensione" in first or "review" in first or "voto finale" in body)

def parse(s,known_ids=None):
    known_ids=set(known_ids or [])
    data=initial_data(s)
    posts=[];seen=set()
    first_ids=parse_nodes(data,posts,seen)
    key,ver=innertube_config(s)
    tokens=continuation_tokens(data)
    used=set()
    pages=0
    complete=True

    def reached_known_boundary(page_ids):
        if not known_ids or not page_ids:
            return False
        known=sum(1 for pid in page_ids if pid in known_ids)
        # Avoid stopping because of a single pinned/old post. Once a meaningful
        # part of a page is already known, the saved archive can safely supply
        # the older tail.
        return known>=max(3,len(page_ids)//3)

    if reached_known_boundary(first_ids):
        return posts,False

    # Continue only until we reconnect with the saved archive. On first
    # bootstrap (no known_ids) this naturally walks the complete history.
    while tokens and pages < 3000:
        token=next((t for t in tokens if t not in used),None)
        if not token:break
        used.add(token);pages+=1
        try:
            more=fetch_continuation(token,key,ver)
        except Exception as err:
            print(f"Community continuation failed after retries at page {pages}: {err}")
            complete=False
            break
        page_ids=parse_nodes(more,posts,seen)
        tokens.extend(t for t in continuation_tokens(more) if t not in used)
        if reached_known_boundary(page_ids):
            complete=False
            break

    if pages>=3000 and tokens:
        complete=False
        print("Community safety ceiling reached; preserving previous archive tail.")
    return posts,complete

def is_review(p):
    lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    first=lines[0].lower() if lines else ""
    body=(p.get("text") or "").lower()
    return (not first.startswith("news:")) and ("recensione" in first or "review" in first or "voto finale" in body)

def review_title(p):
    raw_lines=[x.strip() for x in (p.get("text") or "").splitlines() if x.strip()]
    lines=[clean_site_title(x) for x in raw_lines]
    # Ignore generic labels such as "Review:" and use the first real line
    # that identifies the reviewed product/game.
    for line in lines[:8]:
        if not line:
            continue
        low=line.lower().strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)
        if plain in ("review","recensione"):
            continue
        if "recensione" in low or "review" in low:
            return line
    for line in lines:
        if not line:
            continue
        low=line.lower().strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)
        if plain not in ("review","recensione"):
            return line
    return "Recensione ZazoomTek"

def review_slug(p):
    return "recensione-"+p["id"]+".html"

def review_body_html(p):
    # Build review content line-by-line so the Community title is never merged
    # with "Introduzione" or with the first paragraph.
    raw=p.get("text") or ""
    title=review_title(p)
    title_low=clean_site_title(title).lower().strip()

    standard_headings=[
        (("introduzione",), "Introduzione"),
        (("storia e campagna","storia"), "Storia e Campagna"),
        (("gameplay",), "Gameplay"),
        (("aspetto tecnico","aspetto tecnico su ps5","comparto tecnico","comparto tecnico ps5","comparto tecnico su ps5"), "Aspetto Tecnico"),
        (("esperienza complessiva",), "Esperienza Complessiva"),
        (("conclusioni",), "Conclusioni"),
        (("materiali e design",), "Materiali e Design"),
        (("hardware e prestazioni",), "Hardware e Prestazioni"),
        (("uso quotidiano","esperienza d'uso quotidiana","esperienza d’uso quotidiana"), "Uso Quotidiano"),
    ]
    legacy_headings={"la città","my player","my career","my nba, the w e my wnba","my team"}

    out=[]
    paragraph=[]

    def flush_paragraph():
        if paragraph:
            text=" ".join(paragraph).strip()
            if text:
                out.append(f"<p>{html.escape(text)}</p>")
            paragraph.clear()

    first_content_line=True
    for raw_line in raw.splitlines():
        stripped=(raw_line or "").strip()
        if not stripped:
            flush_paragraph()
            continue
        if stripped.startswith("#") or is_site_social_line(stripped):
            flush_paragraph()
            continue

        line=clean_site_line(stripped)
        if not line:
            continue
        line=strip_site_emojis(line).strip()
        low=line.lower().strip()
        low_nocolon=low.rstrip(":").strip()
        plain=re.sub(r'[^a-zà-ÿ]+','',low)

        # The first Community line is the review title. It belongs in H1 only,
        # never inside the article body.
        if first_content_line:
            first_content_line=False
            if low==title_low or "recensione" in low or "review" in low:
                continue

        if plain in ("review","recensione"):
            flush_paragraph()
            continue
        if low==title_low:
            flush_paragraph()
            continue

        vote_match=re.match(r'^voto\s+finale\s*:\s*(.+)$',line,flags=re.I|re.S)
        if vote_match:
            flush_paragraph()
            vote_text="Voto finale: "+vote_match.group(1).strip()
            out.append(f'<div class="review-score"><strong>{html.escape(vote_text)}</strong></div>')
            continue

        heading_label=None
        for keys,label in standard_headings:
            if low_nocolon in keys:
                heading_label=label
                break
        if heading_label:
            flush_paragraph()
            out.append(f'<h2><strong>{heading_label}</strong></h2>')
            continue

        merged_heading_label=None
        merged_heading_rest=None
        for keys,label in standard_headings:
            for key in sorted(keys,key=len,reverse=True):
                prefix=key+" "
                if low.startswith(prefix):
                    merged_heading_label=label
                    merged_heading_rest=line[len(key):].strip()
                    break
            if merged_heading_label:
                break
        if merged_heading_label and merged_heading_rest:
            flush_paragraph()
            out.append(f'<h2><strong>{merged_heading_label}</strong></h2>')
            out.append(f'<p>{html.escape(merged_heading_rest)}</p>')
            continue

        if low_nocolon in legacy_headings or (len(line)<60 and line.isupper()):
            flush_paragraph()
            out.append(f"<h2><strong>{html.escape(line.rstrip(':'))}</strong></h2>")
            continue

        paragraph.append(line)

    flush_paragraph()
    out=distribute_inline_images(out,p,title)
    return "\n".join(out)

DETAIL_STYLE = """<style>
:root{--orange:#D51232;--accent-blue:#D51232;--accent-mid:#D51232;--accent-red:#D51232;--accent-gradient:linear-gradient(90deg,#D51232 0%,#D51232 100%);--line:#ddd;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif;line-height:1.68}
.wrap{width:min(1100px,calc(100% - 32px));margin:auto}header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--accent-gradient) 1}
.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}
.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}
.nav a:hover{background:var(--orange)}a{color:inherit;text-decoration:none}
.hero{margin:26px 0 0;overflow:hidden;border:1px solid var(--line);background:#fff}.hero img{width:100%;aspect-ratio:16/9;max-height:none;object-fit:cover;object-position:center center;display:block;background:#111}
.hero-copy{padding:22px;border-top:5px solid transparent;border-image:var(--accent-gradient) 1}.hero h1{margin:0 0 8px;font-size:clamp(1.8rem,4vw,3rem);line-height:1.08}
.meta{color:var(--muted);font-size:.9rem}.article{background:#fff;border:1px solid var(--line);border-top:0;padding:28px;margin-bottom:36px}
.article{color:#111}.article h2{margin:30px 0 10px;border-left:6px solid var(--accent-blue);box-shadow:inset 2px 0 0 var(--accent-red);padding-left:10px;font-weight:900;color:#111}.article h2 strong{font-weight:900;color:#111}.article p,.article li{margin:0 0 18px;white-space:pre-line;color:#111!important;font-weight:500}
.review-score{margin-top:28px;padding:16px 18px;background:#202020;border-left:8px solid var(--accent-blue);box-shadow:inset 2px 0 0 var(--accent-red);color:#fff;font-size:1.35rem;font-weight:900}
@media(max-width:760px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.article{padding:20px}}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}</style>"""

ARCHIVE_STYLE = """<style>
:root{--orange:#D51232;--line:#ddd;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif}
.wrap{width:min(1320px,calc(100% - 36px));margin:auto}header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--accent-gradient) 1}
.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}
.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}
.nav a:hover,.nav a.active{background:var(--accent-gradient)}a{color:inherit;text-decoration:none}
main{background:#fff;padding:24px 24px 40px}h1{margin:4px 0 6px}.sub{color:var(--muted);margin-bottom:18px}
.community-posts-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.community-post-card{background:#fff;border:1px solid var(--line);border-top:5px solid transparent;border-image:var(--accent-gradient) 1;min-width:0}
.community-post-card img{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:center center;display:block;background:#111}.community-post-copy{padding:14px}.community-post-copy p{margin:0;font-size:1rem;line-height:1.35;font-weight:800}
.community-post-copy small{display:block;margin-top:9px;color:var(--muted);font-size:.72rem}.community-post-copy a{display:inline-block;margin-top:10px;background:var(--accent-gradient);color:#fff;padding:7px 10px;font-size:.72rem;font-weight:900}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}@media(max-width:900px){.community-posts-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.community-posts-grid{grid-template-columns:1fr}}
</style>"""


NEWS_COMMON = """
:root{--zt-blue:#D51232;--zt-mid:#D51232;--zt-red:#D51232;--zt-grad:linear-gradient(90deg,#D51232 0%,#D51232 100%);--zt-dark:#171717;--zt-line:#e3e3e3;--zt-text:#303030;--zt-muted:#777}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#ececec;color:var(--zt-text);font-family:Arial,Helvetica,sans-serif}a{color:inherit;text-decoration:none}
.zt-wrap{width:min(1460px,calc(100% - 28px));margin:auto}
.zt-header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--zt-grad) 1}
.zt-headrow{min-height:78px;display:grid;grid-template-columns:auto 1fr minmax(260px,370px);align-items:stretch}
.zt-brand{display:flex;align-items:center;gap:10px;padding:10px 24px 10px 0;border-right:1px solid #333}
.zt-brand img{width:52px;height:52px;object-fit:cover;border-radius:8px}.zt-brand strong{font-size:1.7rem}
.zt-nav{display:flex;align-items:stretch;flex-wrap:wrap}.zt-nav a{display:flex;align-items:center;padding:0 20px;font-weight:800;font-size:.82rem;border-right:1px solid #2d2d2d;text-transform:uppercase}
.zt-nav a:hover,.zt-nav a.active{background:var(--zt-grad);color:#fff}
.zt-tools{display:flex;flex-direction:column;justify-content:center;padding-left:16px}.zt-search{display:flex;width:100%;background:#303030;border:1px solid #444}.zt-search input{width:100%;border:0;background:transparent;color:#fff;padding:12px 14px;outline:none}.zt-search button{width:48px;border:0;background:var(--zt-grad);color:#fff;font-weight:900;cursor:pointer}
.zt-socials{display:flex;justify-content:flex-end;gap:9px;margin-top:7px}.zt-socials a{display:grid;place-items:center;width:35px;height:35px;border-radius:50%;background:#202020;border:1px solid #373737}.zt-socials img{width:24px;height:24px;object-fit:contain}
.zt-strip{background:#222;border-top:1px solid #2c2c2c;color:#ddd}.zt-strip .zt-wrap{display:flex;align-items:center;min-height:46px}.zt-strip strong{align-self:stretch;display:flex;align-items:center;padding:0 20px;background:var(--zt-grad);color:#fff;text-transform:uppercase}.zt-strip span{padding:0 16px;font-size:.86rem}
.module-title{height:48px;background:#202020;color:#fff;display:flex;align-items:center;border-left:7px solid var(--zt-blue);box-shadow:inset 2px 0 0 var(--zt-red);padding:0 16px;font-weight:900;text-transform:uppercase;letter-spacing:.01em}
.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}
@media(max-width:1080px){.zt-headrow{grid-template-columns:auto 1fr}.zt-tools{grid-column:1/-1;padding:10px 0 12px}.zt-socials{justify-content:flex-end}}
@media(max-width:720px){.zt-wrap{width:min(100% - 18px,1460px)}.zt-headrow{display:block}.zt-brand{justify-content:center;padding:10px 0;border-right:0}.zt-nav{justify-content:center}.zt-nav a{padding:12px 10px}.zt-tools{padding:10px 0 12px}.zt-socials{justify-content:center}}
"""

NEWS_ARCHIVE_STYLE = """<style>"""+NEWS_COMMON+"""
.news-page{background:#fff;padding:24px 0 40px}.news-layout{display:grid;grid-template-columns:minmax(0,1fr) 355px;gap:22px;align-items:start}
.news-main{min-width:0}.news-main-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;border-bottom:3px solid transparent;border-image:var(--zt-grad) 1}.news-main-head h1{font-size:1.65rem;margin:0;padding:0 0 10px;text-transform:uppercase}.news-filter{display:flex;gap:8px;flex-wrap:wrap;padding-bottom:10px}.news-filter span{font-size:.72rem;font-weight:900;text-transform:uppercase;color:#666}
.news-list{border:1px solid var(--zt-line);border-bottom:0}.news-row{display:grid;grid-template-columns:360px minmax(0,1fr);gap:20px;padding:18px;border-bottom:1px solid var(--zt-line);background:#fff;align-items:start}.news-row img{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:center center;display:block;background:#111}.news-copy h2{margin:0 0 8px;font-size:1.3rem;line-height:1.12}.news-meta{font-size:.76rem;color:#888;margin-bottom:9px}.news-copy p{margin:0 0 13px;color:#555;line-height:1.48;font-size:.93rem}.news-read{display:inline-block;background:var(--zt-grad);color:#fff;padding:10px 14px;font-size:.75rem;font-weight:900;text-transform:uppercase}
.news-sidebar{min-width:0;align-self:start;height:max-content;position:sticky;top:var(--zt-smart-sticky-top,16px)}.side-box{margin-bottom:18px;border:1px solid #ddd;background:#fff}.side-video{padding:10px}.side-video a.thumb{display:block;position:relative}.side-video img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover}.side-video a.thumb:after{content:"▶";position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:50px;height:36px;border-radius:8px;background:rgba(220,0,0,.92);display:grid;place-items:center;color:#fff}.side-video h3{margin:8px 2px 6px;font-size:.92rem;line-height:1.25}.side-video small{display:block;color:#888;margin:0 2px 6px}.amazon-mini{padding:16px}.amazon-mini h3{margin:0 0 8px}.amazon-mini p{font-size:.78rem;color:#666;line-height:1.4}.amazon-mini a{display:block;text-align:center;background:var(--zt-grad);color:#fff;padding:11px 8px;font-weight:900;font-size:.75rem}.archive-pagination{margin:28px 0 0;background:#202020;padding:20px;display:flex;gap:8px;justify-content:center;align-items:center;flex-wrap:wrap}.archive-pagination a,.archive-pagination span{min-width:52px;height:50px;padding:0 15px;border:1px solid #555;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.05rem}.archive-pagination .active{background:var(--zt-grad);border-color:transparent}.archive-pagination .next{min-width:92px}
@media(max-width:980px){.news-layout{grid-template-columns:1fr}.news-sidebar{position:static;top:auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.side-box{margin:0}}
@media(max-width:720px){.news-row{grid-template-columns:1fr;padding:14px}.news-sidebar{grid-template-columns:1fr}}
</style>"""

NEWS_DETAIL_STYLE = """<style>"""+NEWS_COMMON+"""
.news-detail-page{background:#fff;padding:24px 0 42px}.detail-grid{display:grid;grid-template-columns:minmax(0,1fr) 350px;gap:24px;align-items:start}.article-main{min-width:0}.breadcrumbs{font-size:.8rem;color:#777;border-bottom:1px solid #ddd;padding:0 0 13px;margin-bottom:16px}.article-main h1{font-size:clamp(2rem,3.3vw,3.25rem);line-height:1.05;margin:0 0 14px;letter-spacing:-.02em}.article-meta{display:flex;gap:16px;flex-wrap:wrap;color:#777;font-size:.86rem;margin-bottom:18px}.article-hero{width:100%;aspect-ratio:16/9;max-height:none;object-fit:cover;object-position:center center;display:block;margin-bottom:20px;background:#111}.article-body{font-size:1.05rem;line-height:1.65;color:#111!important;font-weight:500}.article-body p,.article-body li{margin:0 0 18px;white-space:pre-line;color:#111!important;font-weight:500}.article-inline-media{margin:30px 0 32px}.article-inline-media img{display:block;width:100%;max-height:780px;object-fit:contain;background:#f5f5f5;border:1px solid #e4e4e4}.article-side{min-width:0;align-self:start;height:max-content;position:sticky;top:var(--zt-smart-sticky-top,16px)}.compact-box{margin-bottom:18px}.compact-list{border:1px solid #ddd;border-top:0;background:#fff}.compact-item{display:grid;grid-template-columns:92px 1fr;gap:10px;padding:11px;border-bottom:1px solid #eee}.compact-item:last-child{border-bottom:0}.compact-item img{width:92px;height:52px;aspect-ratio:16/9;object-fit:cover;object-position:center center;background:#111}.compact-item h3{margin:0;font-size:.86rem;line-height:1.18}.compact-item small{display:block;margin-top:5px;color:#888;font-size:.7rem}.feature-card{border:1px solid #ddd;border-top:0;background:#fff;padding:10px}.feature-card img{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:center center;display:block;background:#111}.feature-card h3{margin:10px 2px 4px;font-size:1rem}.feature-card .cta{display:block;margin-top:10px;background:var(--zt-grad);color:#fff;text-align:center;padding:11px 8px;font-weight:900;font-size:.75rem}.follow-box{padding:14px;text-align:center;border:1px solid #ddd;border-top:0;background:#fff}.follow-box img{width:58px;height:58px;border-radius:12px}.follow-box strong{display:block;margin-top:6px}.follow-box a{display:inline-block;margin-top:9px;background:var(--zt-grad);color:#fff;padding:9px 12px;font-size:.74rem;font-weight:900}
.zt-subscribe-cta{margin-top:34px;padding:26px 30px;background:#050505;border-left:6px solid #D51232;color:#fff;display:flex;align-items:center;justify-content:space-between;gap:28px;box-shadow:0 4px 16px rgba(0,0,0,.10)}
.zt-subscribe-copy{min-width:0}.zt-subscribe-kicker{display:inline-block;margin-bottom:10px;color:#ff5b76;font-size:.72rem;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.zt-subscribe-copy h2{margin:0 0 10px;font-size:1.3rem;line-height:1.15;color:#fff}.zt-subscribe-copy p{margin:0;font-size:.95rem;line-height:1.5;color:#d3d3d3}
.zt-social-icons{display:flex;align-items:center;gap:18px;flex-shrink:0}.zt-social-icon{width:72px;height:72px;border-radius:999px;display:flex;align-items:center;justify-content:center;background:linear-gradient(180deg,#171717 0%,#101010 100%);border:1px solid rgba(255,255,255,.12);box-shadow:inset 0 0 0 1px rgba(255,255,255,.04),0 0 0 1px rgba(255,255,255,.03);transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease;text-decoration:none}.zt-social-icon:hover{transform:translateY(-2px);border-color:rgba(213,18,50,.55);box-shadow:inset 0 0 0 1px rgba(255,255,255,.05),0 0 0 1px rgba(213,18,50,.28)}.zt-social-icon img{width:38px;height:38px;object-fit:contain;display:block}
@media(max-width:1180px){.detail-grid{grid-template-columns:minmax(0,1fr) 330px}.article-side.middle{display:none}}
@media(max-width:820px){.detail-grid{grid-template-columns:1fr}.article-side{position:static;top:auto}.article-side.middle{display:block}.article-main h1{font-size:2rem}.zt-subscribe-cta{display:block;padding:22px 20px}.zt-social-icons{margin-top:20px;justify-content:flex-start;flex-wrap:wrap;gap:14px}.zt-social-icon{width:64px;height:64px}.zt-social-icon img{width:34px;height:34px}}
</style>"""

SMART_STICKY_SCRIPT = """<script>
function ztInitSmartSticky(selector,mobileWidth){
  const el=document.querySelector(selector);
  if(!el)return;
  function update(){
    if(window.innerWidth<=mobileWidth){
      el.style.removeProperty('--zt-smart-sticky-top');
      return;
    }
    const gap=16;
    const top=Math.min(gap,window.innerHeight-el.offsetHeight-gap);
    el.style.setProperty('--zt-smart-sticky-top',top+'px');
  }
  update();
  window.addEventListener('resize',update,{passive:true});
  if('ResizeObserver' in window){new ResizeObserver(update).observe(el);}
}
document.addEventListener('DOMContentLoaded',function(){
  ztInitSmartSticky('.news-sidebar',980);
  ztInitSmartSticky('.article-side',820);
});
</script>"""

def rich_editorial_header(active="news"):
    def nav(label, href, key):
        cls=' active' if active==key else ''
        ext=' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return f'<a class="{cls.strip()}" href="{href}"{ext}>{label}</a>' if cls else f'<a href="{href}"{ext}>{label}</a>'
    return (
        '<header class="zt-header"><div class="zt-wrap zt-headrow">'
        '<a class="zt-brand" href="/"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong></a>'
        '<nav class="zt-nav">'
        +nav("Home","/","home")+nav("News","/news.html","news")+nav("Recensioni","/recensioni-scritte.html","recensioni")
        +nav("Community","https://www.youtube.com/@ZazoomTek/posts","community")+nav("Video","https://www.youtube.com/@ZazoomTek/videos","video")
        +'</nav>'
        '<div class="zt-tools"><form class="zt-search" action="/cerca.html" method="get"><input name="q" type="search" placeholder="Cerca nel sito..." aria-label="Cerca nel sito"><button type="submit">⌕</button></form>'
        '<div class="zt-socials">'
        '<a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/youtube-play.png" alt="YouTube"></a>'
        '<a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/tiktok--v1.png" alt="TikTok"></a>'
        '<a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/whatsapp--v1.png" alt="WhatsApp"></a>'
        '</div></div></div></header>'
        '<div class="zt-strip"><div class="zt-wrap"><strong>News</strong><span>Notizie tech, gaming e novità dalla Community ZazoomTek</span></div></div>'
    )

def load_video_cache():
    p=Path(".youtube-latest.json")
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def latest_video_for(category):
    for v in load_video_cache():
        if v.get("category")==category and not v.get("short") and not v.get("live"):
            return v
    return None

def sidebar_video_box(title, category, link):
    v=latest_video_for(category)
    if not v:
        return ""
    vid=html.escape(v.get("id") or "")
    vt=html.escape(v.get("title") or "")
    return (
        f'<section class="side-box"><a class="module-title" href="{link}">{html.escape(title)}</a>'
        f'<div class="side-video"><a class="thumb" href="https://www.youtube.com/watch?v={vid}" target="_blank" rel="noopener">'
        f'<img src="https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" onerror="this.onerror=null;this.src=\'https://i.ytimg.com/vi/{vid}/hqdefault.jpg\'" alt="{vt}" loading="lazy"></a>'
        f'<h3>{vt}</h3><small>{html.escape(category.title())}</small></div></section>'
    )

def amazon_sidebar_box():
    return '''<section class="side-box"><div class="module-title">Su Amazon</div><div class="amazon-mini"><h3>I prodotti recensiti da ZazoomTek</h3><p>Link affiliato Amazon. In qualità di Affiliato Amazon ricevo un guadagno dagli acquisti idonei senza alcun costo per l’utente.</p><a href="https://www.amazon.it/gp/profile/amzn1.account.AE76ZMY5J56NNH3HUPWFJGVZEC5A?&amp;linkCode=ll2&amp;tag=zazoomtek-21&amp;linkId=d2dd9b9524bc6fb76da94e041a661201&amp;ref_=as_li_ss_tl" target="_blank" rel="nofollow sponsored noopener">VEDI I PRODOTTI SU AMAZON ›</a></div></section>'''

def news_video_sidebar(reviews=None):
    reviews=reviews or []
    return (
        amazon_sidebar_box()
        +sidebar_video_box("Video · Recensioni","recensioni","/recensioni.html")
        +sidebar_video_box("Video · Test","test","/test.html")
        +sidebar_video_box("Video · Unboxing","unboxing","/unboxing.html")
        +sidebar_video_box("Video · Gaming","gaming","/gaming.html")
        +sidebar_video_box("Video · AnalogikTek","analogiktek","https://www.youtube.com/playlist?list=PL7dvpppAJr02AQM7WP0D151c_JvKu_OaI")
    )

def compact_news_list(news, current_id="", limit=5):
    rows=[]
    for p in news:
        if p.get("id")==current_id:
            continue
        title=news_title(p); slug=news_slug(p); img=html.escape(p.get("image") or "/ChatGPT.png")
        rows.append(
            f'<a class="compact-item" href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy">'
            f'<div><h3>{html.escape(title)}</h3><small>{html.escape(p.get("published") or "")}</small></div></a>'
        )
        if len(rows)>=limit:
            break
    return "".join(rows)

def editorial_nav(active=""):
    def a(label, href, key):
        cls=' class="active"' if active==key else ""
        ext=' target="_blank" rel="noopener"' if href.startswith("http") else ""
        return f'<a{cls} href="{href}"{ext}>{label}</a>'
    return (
        '<nav class="nav">'
        +a("Home","/","home")
        +a("News","/news.html","news")
        +a("Recensioni","/recensioni-scritte.html","recensioni")
        +a("Community","https://www.youtube.com/@ZazoomTek/posts","community")
        +a("Video","https://www.youtube.com/@ZazoomTek/videos","video")
        +'</nav>'
    )


def subscribe_cta_box():
    return '''<section class="zt-subscribe-cta">
      <div class="zt-subscribe-copy">
        <span class="zt-subscribe-kicker">ZazoomTek Community</span>
        <h2>Non perderti le prossime recensioni e news</h2>
        <p>Segui ZazoomTek per ricevere nuovi contenuti su tecnologia, gaming, test e unboxing.</p>
      </div>
      <div class="zt-social-icons" aria-label="Canali ZazoomTek">
        <a class="zt-social-icon" href="https://www.youtube.com/@ZazoomTek?sub_confirmation=1" target="_blank" rel="noopener" aria-label="YouTube">
          <img src="https://img.icons8.com/color/96/youtube-play.png" alt="YouTube">
        </a>
        <a class="zt-social-icon" href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener" aria-label="TikTok">
          <img src="https://img.icons8.com/color/96/tiktok--v1.png" alt="TikTok">
        </a>
        <a class="zt-social-icon" href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener" aria-label="WhatsApp">
          <img src="https://img.icons8.com/color/96/whatsapp--v1.png" alt="WhatsApp">
        </a>
      </div>
    </section>'''

def legal_footer():
    return '''<footer class="legal-footer"><div class="wrap">
      <div class="footer-links"><a href="/">Home</a><a href="/news.html">News</a><a href="/recensioni-scritte.html">Recensioni scritte</a><a href="/recensioni.html">Video recensioni</a><a href="/test.html">Test</a><a href="/unboxing.html">Unboxing</a><a href="/gaming.html">Gaming</a></div>
      <div class="footer-links"><a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener">▶ YouTube</a><a href="https://www.patreon.com/ZazoomTek" target="_blank" rel="noopener">❤️ Patreon</a><a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener">🎵 TikTok</a><a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener">💬 WhatsApp</a><a href="/contatti.html">Contatti</a><a href="/chi-sono.html">Chi sono</a></div>
      <div class="legal-links"><a href="/privacy.html">Privacy Policy</a><a href="/cookie.html">Cookie Policy</a><a href="/disclaimer.html">Disclaimer</a><a href="/note-legali.html">Note legali</a></div>
      <div class="footer-copy">© 2026 ZazoomTek · Tecnologia e gaming.</div>
    </div></footer>'''
def editorial_header(active=""):
    return '<header><div class="wrap headrow"><a class="brand" href="/">ZazoomTek</a>'+editorial_nav(active)+'</div></header>'

def rich_review_header():
    return (
        '<header class="zt-header"><div class="zt-wrap zt-headrow">'
        '<a class="zt-brand" href="/"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong></a>'
        '<nav class="zt-nav">'
        '<a href="/">Home</a><a href="/news.html">News</a><a class="active" href="/recensioni-scritte.html">Recensioni</a>'
        '<a href="https://www.youtube.com/@ZazoomTek/posts" target="_blank" rel="noopener">Community</a>'
        '<a href="https://www.youtube.com/@ZazoomTek/videos" target="_blank" rel="noopener">Video</a>'
        '</nav>'
        '<div class="zt-tools"><form class="zt-search" action="/cerca.html" method="get">'
        '<input name="q" type="search" placeholder="Cerca nel sito..." aria-label="Cerca nel sito"><button type="submit">⌕</button></form>'
        '<div class="zt-socials">'
        '<a href="https://www.youtube.com/@ZazoomTek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/youtube-play.png" alt="YouTube"></a>'
        '<a href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/tiktok--v1.png" alt="TikTok"></a>'
        '<a href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener"><img src="https://img.icons8.com/color/48/whatsapp--v1.png" alt="WhatsApp"></a>'
        '</div></div></div></header>'
        '<div class="zt-strip"><div class="zt-wrap"><strong>Recensioni</strong><span>Recensioni scritte di tecnologia e gaming pubblicate da ZazoomTek</span></div></div>'
    )

def compact_review_list(reviews, current_id="", limit=5):
    rows=[]
    for p in reviews:
        if p.get("id")==current_id:
            continue
        title=review_title(p); slug=review_slug(p); img=html.escape(p.get("image") or "/ChatGPT.png")
        rows.append(
            f'<a class="compact-item" href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy">'
            f'<div><h3>{html.escape(title)}</h3><small>{html.escape(p.get("published") or "")}</small></div></a>'
        )
        if len(rows)>=limit:
            break
    return "".join(rows)

def latest_reviews_sidebar_box(reviews, current_id="", limit=5):
    items=compact_review_list(reviews,current_id,limit)
    if not items:
        return ""
    return '<section class="compact-box"><div class="module-title">Ultime recensioni</div><div class="compact-list">'+items+'</div></section>'

def write_review_page(p, all_reviews=None):
    all_reviews=all_reviews or []
    title=review_title(p)
    slug=review_slug(p)
    img=(f'<img class="article-hero" src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    recent=compact_review_list(all_reviews,p.get("id") or "",5)
    featured=next((x for x in all_reviews if x.get("id")!=p.get("id")),None)
    feature_html=""
    if featured:
        ft=review_title(featured); fs=review_slug(featured); fi=html.escape(featured.get("image") or "/ChatGPT.png")
        feature_html=(
            f'<section class="compact-box"><div class="module-title">In evidenza</div><div class="feature-card">'
            f'<a href="/{fs}"><img src="{fi}" alt="{html.escape(ft)}"></a><h3><a href="/{fs}">{html.escape(ft)}</a></h3>'
            f'<a class="cta" href="/{fs}">LEGGI LA RECENSIONE ›</a></div></section>'
        )
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+NEWS_DETAIL_STYLE+'</head><body>'
        +rich_review_header()
        +'<main class="news-detail-page"><div class="zt-wrap detail-grid">'
        +'<article class="article-main"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/recensioni-scritte.html">Recensioni</a> / '+html.escape(title)+'</div>'
        +f'<h1>{html.escape(title)}</h1><div class="article-meta"><span>👤 ZazoomTek</span><span>📅 {html.escape(p.get("published") or "")}</span><span>🏷 Recensione</span></div>'
        +img+f'<div class="article-body">{review_body_html(p)}</div>'+subscribe_cta_box()+'</article>'
        +'<aside class="article-side">'+feature_html
        +latest_reviews_sidebar_box(all_reviews,p.get("id") or "",5)
        +'<section class="compact-box"><div class="module-title">Segui ZazoomTek</div><div class="follow-box"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong><a href="https://www.youtube.com/@ZazoomTek?sub_confirmation=1" target="_blank" rel="noopener">ISCRIVITI SU YOUTUBE</a></div></section>'
        +'</aside></div></main>'+legal_footer()+SMART_STICKY_SCRIPT+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_review_rows(posts):
    rows=[]
    for p in posts:
        title=review_title(p); slug=review_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,250))
        rows.append(
            f'<article class="news-row" data-news-search="{html.escape((title+" "+(p.get("text") or "")).lower(),quote=True)}">'
            f'<a href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="news-copy"><h2><a href="/{slug}">{html.escape(title)}</a></h2>'
            f'<div class="news-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="news-read" href="/{slug}">Leggi la recensione ›</a></div></article>'
        )
    return "".join(rows)

REVIEW_PAGE_SIZE=20

def review_page_href(n):
    return "/recensioni-scritte.html" if n==1 else f"/recensioni-scritte-{n}.html"

def render_review_pagination(current,total):
    if total<=1:
        return ""
    items=[]
    for n in range(1,total+1):
        if n==current:
            items.append(f'<span class="active">{n}</span>')
        else:
            items.append(f'<a href="{review_page_href(n)}">{n}</a>')
    if current < total:
        items.append(f'<a class="next" href="{review_page_href(current+1)}">NEXT</a>')
    return '<nav class="archive-pagination" aria-label="Pagine Recensioni">'+"".join(items)+'</nav>'

def build_review_archive_page(review_chunk,page_num,total_pages,reviews):
    rows=render_review_rows(review_chunk)
    title="Recensioni | ZazoomTek" if page_num==1 else f"Recensioni - Pagina {page_num} | ZazoomTek"
    canonical="https://zazoomtek.it/recensioni-scritte.html" if page_num==1 else f"https://zazoomtek.it/recensioni-scritte-{page_num}.html"
    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>'+html.escape(title)+'</title>'
        '<meta name="description" content="Archivio delle recensioni scritte di ZazoomTek, ordinate dalla più recente alla più vecchia.">'
        '<link rel="canonical" href="'+canonical+'">'+NEWS_ARCHIVE_STYLE+'</head><body>'
        +rich_review_header()
        +'<main class="news-page"><div class="zt-wrap news-layout"><section class="news-main">'
        +'<div class="news-main-head"><h1>Recensioni</h1><div class="news-filter"><span>Tutte</span><span>Gaming</span><span>Tech</span><span>Hardware</span><span>Accessori</span></div></div>'
        +'<div class="news-list" id="reviewList">'+rows+'</div>'
        +render_review_pagination(page_num,total_pages)
        +'</section><aside class="news-sidebar">'+news_video_sidebar(reviews)+'</aside></div></main>'
        +legal_footer()+SMART_STICKY_SCRIPT
        +'''<script>(function(){const p=new URLSearchParams(location.search);const q=(p.get("q")||"").trim().toLowerCase();if(!q)return;document.querySelectorAll("[data-news-search]").forEach(function(x){x.style.display=(x.dataset.newsSearch||"").includes(q)?"grid":"none"})})();</script>'''
        +'</body></html>'
    )

def write_review_archive(reviews):
    total_pages=max(1,(len(reviews)+REVIEW_PAGE_SIZE-1)//REVIEW_PAGE_SIZE)

    # Remove obsolete numbered archive pages before rebuilding the complete set.
    for old in Path(".").glob("recensioni-scritte-[0-9]*.html"):
        try:
            old.unlink()
        except OSError:
            pass

    for page_num in range(1,total_pages+1):
        chunk=reviews[(page_num-1)*REVIEW_PAGE_SIZE:page_num*REVIEW_PAGE_SIZE]
        page=build_review_archive_page(chunk,page_num,total_pages,reviews)
        filename="recensioni-scritte.html" if page_num==1 else f"recensioni-scritte-{page_num}.html"
        Path(filename).write_text(page,encoding="utf-8")

def strip_site_emojis(text):
    """Remove decorative emoji/icons while preserving normal punctuation and words."""
    if not text:
        return ""
    out=[]
    for ch in text:
        cp=ord(ch)
        if (
            0x1F000 <= cp <= 0x1FAFF or
            0x2600 <= cp <= 0x26FF or
            0x2700 <= cp <= 0x27BF or
            0x1F1E6 <= cp <= 0x1F1FF or
            cp in (0xFE0E,0xFE0F,0x200D,0x20E3)
        ):
            continue
        out.append(ch)
    return "".join(out)

def clean_site_line(line):
    line=(line or "").strip()
    if not line:
        return ""

    # Remove URLs and bare web links copied from Community posts.
    line=re.sub(r'https?://\S+','',line,flags=re.I)
    line=re.sub(r'\bwww\.\S+','',line,flags=re.I)

    # Website articles must never display social hashtags.
    line=re.sub(r'(?<!\w)#[\wÀ-ÿ]+','',line,flags=re.UNICODE)

    # Remove decorative emoji/icons from visible site text.
    line=strip_site_emojis(line)

    # Normalize whitespace left behind by removed icons/links/hashtags.
    line=re.sub(r'[ \t]+',' ',line)
    line=re.sub(r'\s+([,.;:!?])',r'\1',line)
    return line.strip(" \t-–—|")

def is_site_social_line(line):
    # Normalize first so leading emoji/icons such as ▶ ❤️ 🎵 💬 cannot hide
    # a social footer from the filter.
    cleaned=clean_site_line(line)
    low=cleaned.lower().strip()
    if not low:
        return True

    # Social/CTA lines belong on YouTube, not inside the imported article.
    exact_prefixes=(
        "subscribe",
        "iscriviti",
        "youtube:",
        "patreon:",
        "tiktok:",
        "whatsapp:",
        "zazoomtek.it",
        "www.zazoomtek.it",
        "@zazoomtek",
    )
    if low.startswith(exact_prefixes):
        return True

    social_phrases=(
        "se ti piacciono tecnologia",
        "seguimi su zazoomtek",
        "seguici su zazoomtek",
        "segui zazoomtek",
        "subscribe to the channel",
        "iscriviti al canale",
        "video recensione completa",
        "videorecensione completa",
        "recensione completa scritta",
        "recensione completa",
        "canale youtube zazoomtek",
        "canale youtube",
        "guarda la recensione completa",
        "leggi la recensione completa",
    )
    if any(x in low for x in social_phrases):
        return True

    # Catch compact footer rows where several channel labels are on one line.
    social_labels=("youtube:","patreon:","tiktok:","whatsapp:")
    if any(x in low for x in social_labels):
        return True

    return False

def clean_site_blocks(raw):
    """Convert a Community post into clean editorial blocks for the website."""
    blocks=[x.strip() for x in re.split(r'\n\s*\n|⠀',raw or "") if x.strip()]
    cleaned=[]
    for block in blocks:
        # Work line-by-line so a social footer does not contaminate a valid paragraph.
        lines=[]
        for line in block.splitlines():
            if is_site_social_line(line):
                continue
            stripped=line.strip()
            if stripped.startswith("#"):
                # Hashtags belong to social posts, never to the website article.
                continue
            visible=clean_site_line(line)
            if visible:
                lines.append(visible)
        text=" ".join(lines).strip()
        if text:
            cleaned.append(text)
    return cleaned

def clean_site_title(line):
    return clean_site_line(line)

def news_title(p):
    lines=[clean_site_title(x) for x in (p.get("text") or "").splitlines() if clean_site_title(x)]
    if not lines:
        return "News ZazoomTek"
    first=lines[0].strip()
    if first.lower().rstrip(":")=="news" and len(lines)>1:
        return lines[1]
    return first

def news_slug(p):
    return "news-"+p["id"]+".html"

def news_body_html(p):
    blocks=clean_site_blocks(p.get("text") or "")
    title=news_title(p)
    cleaned=[]
    for b in blocks:
        if b==title:
            continue
        cleaned.append(b)
    rendered=[f"<p>{html.escape(b)}</p>" for b in cleaned]
    rendered=distribute_inline_images(rendered,p,title)
    return "\n".join(rendered)

def write_news_page(p, all_news=None):
    all_news=all_news or []
    title=news_title(p)
    slug=news_slug(p)
    img=(f'<img class="article-hero" src="{html.escape(p["image"])}" alt="{html.escape(title)}">' if p.get("image") else "")
    recent=compact_news_list(all_news,p.get("id") or "",5)
    featured=next((x for x in all_news if x.get("id")!=p.get("id")),None)
    feature_html=""
    if featured:
        ft=news_title(featured); fs=news_slug(featured); fi=html.escape(featured.get("image") or "/ChatGPT.png")
        feature_html=(
            f'<section class="compact-box"><div class="module-title">In evidenza</div><div class="feature-card">'
            f'<a href="/{fs}"><img src="{fi}" alt="{html.escape(ft)}"></a><h3><a href="/{fs}">{html.escape(ft)}</a></h3>'
            f'<a class="cta" href="/{fs}">SCOPRI DI PIÙ ›</a></div></section>'
        )
    page=(
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png">'
        f'<title>{html.escape(title)} | ZazoomTek</title><meta name="description" content="{html.escape(title)}">'
        f'<link rel="canonical" href="https://zazoomtek.it/{slug}">'+NEWS_DETAIL_STYLE+'</head><body>'
        +rich_editorial_header("news")
        +'<main class="news-detail-page"><div class="zt-wrap detail-grid">'
        +'<article class="article-main"><div class="breadcrumbs"><a href="/">Home</a> / <a href="/news.html">News</a> / '+html.escape(title)+'</div>'
        +f'<h1>{html.escape(title)}</h1><div class="article-meta"><span>👤 ZazoomTek</span><span>📅 {html.escape(p.get("published") or "")}</span><span>🏷 News</span></div>'
        +img+f'<div class="article-body">{news_body_html(p)}</div>'+subscribe_cta_box()+'</article>'
        +'<aside class="article-side">'+feature_html
        +'<section class="compact-box"><div class="module-title">Segui ZazoomTek</div><div class="follow-box"><img src="/ChatGPT.png" alt="ZazoomTek"><strong>ZazoomTek</strong><a href="https://www.youtube.com/@ZazoomTek?sub_confirmation=1" target="_blank" rel="noopener">ISCRIVITI SU YOUTUBE</a></div></section>'
        +'<section class="compact-box"><div class="module-title">Ultimi articoli</div><div class="compact-list">'+recent+'</div></section>'
        +'</aside></div></main>'+legal_footer()+SMART_STICKY_SCRIPT+'</body></html>'
    )
    Path(slug).write_text(page,encoding="utf-8")

def render_news_rows(posts):
    rows=[]
    for p in posts:
        title=news_title(p); slug=news_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,250))
        rows.append(
            f'<article class="news-row" data-news-search="{html.escape((title+" "+(p.get("text") or "")).lower(),quote=True)}">'
            f'<a href="/{slug}"><img src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="news-copy"><h2><a href="/{slug}">{html.escape(title)}</a></h2>'
            f'<div class="news-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="news-read" href="/{slug}">Leggi tutto ›</a></div></article>'
        )
    return "".join(rows)

NEWS_PAGE_SIZE=20
NEWS_MAX_PAGES=5

def news_page_href(n):
    return "/news.html" if n==1 else f"/news-{n}.html"

def render_news_pagination(current,total):
    if total<=1:
        return ""
    items=[]
    for n in range(1,total+1):
        if n==current:
            items.append(f'<span class="active">{n}</span>')
        else:
            items.append(f'<a href="{news_page_href(n)}">{n}</a>')
    if current < total:
        items.append(f'<a class="next" href="{news_page_href(current+1)}">NEXT</a>')
    return '<nav class="archive-pagination" aria-label="Pagine News">'+"".join(items)+'</nav>'

def build_news_archive_page(news_chunk,page_num,total_pages,reviews):
    rows=render_news_rows(news_chunk)
    title="News | ZazoomTek" if page_num==1 else f"News - Pagina {page_num} | ZazoomTek"
    canonical="https://zazoomtek.it/news.html" if page_num==1 else f"https://zazoomtek.it/news-{page_num}.html"
    return (
        '<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">'
        '<link rel="icon" type="image/png" href="/ChatGPT.png"><title>'+html.escape(title)+'</title>'
        '<meta name="description" content="Le ultime News pubblicate da ZazoomTek, in ordine cronologico.">'
        '<link rel="canonical" href="'+canonical+'">'+NEWS_ARCHIVE_STYLE+'</head><body>'
        +rich_editorial_header("news")
        +'<main class="news-page"><div class="zt-wrap news-layout"><section class="news-main">'
        +'<div class="news-main-head"><h1>Notizie</h1><div class="news-filter"><span>Tutte</span><span>Gaming</span><span>Tech</span><span>Hardware</span><span>Software</span></div></div>'
        +'<div class="news-list" id="newsList">'+rows+'</div>'
        +render_news_pagination(page_num,total_pages)
        +'</section><aside class="news-sidebar">'+news_video_sidebar(reviews)+'</aside></div></main>'
        +legal_footer()+SMART_STICKY_SCRIPT
        +'''<script>(function(){const p=new URLSearchParams(location.search);const q=(p.get("q")||"").trim().toLowerCase();if(!q)return;document.querySelectorAll("[data-news-search]").forEach(function(x){x.style.display=(x.dataset.newsSearch||"").includes(q)?"grid":"none"})})();</script>'''
        +'</body></html>'
    )

def write_news_archive(news,reviews):
    news=news[:NEWS_PAGE_SIZE*NEWS_MAX_PAGES]
    total_pages=max(1,min(NEWS_MAX_PAGES,(len(news)+NEWS_PAGE_SIZE-1)//NEWS_PAGE_SIZE))
    for page_num in range(1,total_pages+1):
        chunk=news[(page_num-1)*NEWS_PAGE_SIZE:page_num*NEWS_PAGE_SIZE]
        page=build_news_archive_page(chunk,page_num,total_pages,reviews)
        filename="news.html" if page_num==1 else f"news-{page_num}.html"
        Path(filename).write_text(page,encoding="utf-8")



def post_kind(p):
    return "Recensione" if is_review(p) else "News"

def post_title(p):
    return review_title(p) if is_review(p) else news_title(p)

def post_slug(p):
    return review_slug(p) if is_review(p) else news_slug(p)

def post_excerpt(p, limit=220):
    text=" ".join(clean_site_blocks(p.get("text") or ""))
    title=post_title(p)
    if text.startswith(title):
        text=text[len(title):].strip(" :-–—")
    text=re.sub(r"\s+"," ",text).strip()
    return text if len(text)<=limit else text[:limit].rsplit(" ",1)[0]+"…"

def render_home_latest_reviews(reviews, limit=5):
    cards=[]
    for p in reviews[:limit]:
        title=html.escape(review_title(p))
        slug=review_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        when=html.escape(p.get("published") or "")
        cards.append(
            f'<article class="video-card zt-review-card">'
            f'<a class="video-thumb zt-review-thumb" href="/{slug}" aria-label="{title}"><img src="{img}" alt="{title}" loading="lazy"></a>'
            f'<h3><a href="/{slug}">{title}</a></h3>'
            f'<small>{when}</small>'
            f'</article>'
        )
    return ('<!-- HOME_LATEST_REVIEWS_MAIN_START -->\n'
            +"\n".join(cards)+'\n'
            '<!-- HOME_LATEST_REVIEWS_MAIN_END -->')

def render_ticker(news):
    rows=[]
    for i,p in enumerate(news[:5]):
        cls=' class="active"' if i==0 else ""
        rows.append(f'    <a{cls} href="{news_slug(p)}">{html.escape(news_title(p))}</a>')
    return "\n".join(rows)

def render_featured_news(news):
    news=news[:5]
    slides=[]
    tabs=[]
    for i,p in enumerate(news):
        title=html.escape(news_title(p))
        slug=news_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        active=" active" if i==0 else ""
        slides.append(
            f'            <article class="news-slide{active}" data-slide="{i}">'
            f'<a href="{slug}"><img src="{img}" alt="{title}"></a>'
            f'<div class="news-slide-copy"><span class="tag">News</span>'
            f'<h1><a href="{slug}">{title}</a></h1>'
            f'<p>{html.escape(post_excerpt(p,180))}</p></div></article>'
        )
        tabs.append(f'            <button class="news-tab{active}" data-go="{i}">{title}</button>')
    return (
        '<div class="news-slider" id="newsSlider">\n'
        '          <div class="news-slides">\n'+"\n".join(slides)+'\n          </div>\n'
        '          <div class="news-tabs">\n'+"\n".join(tabs)+'\n          </div>\n'
        '        </div>'
    )

def render_article_feed(posts):
    rows=[]
    for p in posts:
        kind=post_kind(p)
        title=post_title(p)
        slug=post_slug(p)
        img=html.escape(p.get("image") or "/ChatGPT.png")
        excerpt=html.escape(post_excerpt(p,230))
        search=html.escape((title+" "+kind+" "+(p.get("text") or ""))[:1200],quote=True)
        rows.append(
            f'          <article class="article-row" data-search="{search.lower()}">'
            f'<a href="{slug}"><img class="article-image" src="{img}" alt="{html.escape(title)}" loading="lazy"></a>'
            f'<div class="article-copy">'
            f'<h3><a href="{slug}">{html.escape(title)}</a></h3>'
            f'<div class="article-meta">ZazoomTek · {html.escape(p.get("published") or "")}</div>'
            f'<p>{excerpt}</p><a class="read-more" href="{slug}">Leggi tutto ›</a></div></article>'
        )
    return "\n".join(rows)

def render(posts):
    return render_news_cards(posts)


def update_sitemap():
    """Build one canonical, Google-friendly sitemap from the pages that are
    actually indexable on zazoomtek.it.  Deliberately omit priority/changefreq
    and synthetic lastmod values: inaccurate metadata is worse than no metadata.
    """
    origin="https://zazoomtek.it"
    urls=[]
    seen=set()

    # Only HTML pages with a self-canonical on the production domain are eligible.
    # noindex pages (privacy/legal pages, etc.) are intentionally excluded.
    for p in sorted(Path(".").glob("*.html")):
        if p.name in ("404.html","googlea3c594e14c6f832d.html","nba-2k27-recensione-ps5.html"):
            continue
        try:
            page=p.read_text(encoding="utf-8",errors="replace")
        except OSError:
            continue

        mrobots=re.search(r"<meta\\s+name=[\\\"']robots[\\\"']\\s+content=[\\\"']([^\\\"']+)[\\\"']",page,re.I)
        if mrobots and "noindex" in mrobots.group(1).lower():
            continue

        mcanonical=re.search(r"<link\\s+rel=[\\\"']canonical[\\\"']\\s+href=[\\\"']([^\\\"']+)[\\\"']",page,re.I)
        if not mcanonical:
            continue
        url=mcanonical.group(1).strip()
        if not (url==origin or url.startswith(origin+"/")):
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)

    # Home first, then stable alphabetical order for deterministic diffs.
    urls=sorted(urls,key=lambda u:(u!=origin+"/",u))

    rows="\\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in urls)
    xml=(
        '<?xml version="1.0" encoding="UTF-8"?>\\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\\n'
        +rows+
        '\\n</urlset>\\n'
    )
    Path("sitemap.xml").write_text(xml,encoding="utf-8")

    # Keep legacy sitemap endpoints coherent, but advertise only sitemap.xml.
    Path("google-sitemap.xml").write_text(xml,encoding="utf-8")
    Path("sitemap.txt").write_text("\\n".join(urls)+"\\n",encoding="utf-8")
    Path("robots.txt").write_text(
        "User-agent: *\\n"
        "Allow: /\\n\\n"
        "Sitemap: https://zazoomtek.it/sitemap.xml\\n",
        encoding="utf-8"
    )


PAGE_SIZE=20

PAGINATED_ARTICLE_STYLE = """<style>
:root{--blue:#D51232;--mid:#D51232;--red:#D51232;--grad:linear-gradient(90deg,#D51232 0%,#D51232 100%);--line:#e5e5e5;--text:#303030;--muted:#777}
*{box-sizing:border-box}body{margin:0;background:#ececec;color:var(--text);font-family:Arial,Helvetica,sans-serif}.wrap{width:min(1180px,calc(100% - 32px));margin:auto}
header{background:#171717;color:#fff;border-top:3px solid transparent;border-image:var(--grad) 1}.headrow{min-height:76px;display:flex;align-items:stretch}.brand{display:flex;align-items:center;font-size:1.5rem;font-weight:900;padding-right:22px}.nav{display:flex;align-items:stretch;flex-wrap:wrap}.nav a{display:flex;align-items:center;padding:0 14px;font-size:.76rem;font-weight:900;text-transform:uppercase;border-left:1px solid #2d2d2d}.nav a:hover,.nav a.active{background:var(--grad)}a{color:inherit;text-decoration:none}
main{background:#fff;padding:26px 0 40px}.archive-head{padding:0 22px 18px}.archive-head h1{margin:0 0 6px}.archive-head p{margin:0;color:var(--muted)}
.article-list{border-top:1px solid var(--line)}.article-row{display:grid;grid-template-columns:330px 1fr;gap:20px;padding:18px 22px;border-bottom:1px solid var(--line);align-items:start}.article-image{width:100%;aspect-ratio:16/9;object-fit:cover;object-position:center center;display:block;background:#111}.article-copy h3{font-size:1.18rem;line-height:1.18;margin:0 0 6px}.article-meta{font-size:.78rem;color:var(--muted);margin-bottom:8px}.article-copy p{margin:0 0 12px;line-height:1.45}.read-more{display:inline-block;background:var(--grad);color:#fff;padding:9px 13px;font-size:.76rem;font-weight:900;text-transform:uppercase}
.pagination{margin:28px 22px 0;background:#202020;padding:20px;display:flex;gap:7px;justify-content:center;align-items:center;flex-wrap:wrap}.pagination a,.pagination span{min-width:52px;height:50px;padding:0 15px;border:1px solid #555;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:1.05rem}.pagination .active{background:var(--grad);border-color:transparent}.pagination .next{min-width:92px}
@media(max-width:760px){.headrow{display:block}.brand{padding:12px 0;justify-content:center}.nav{justify-content:center}.nav a{padding:11px 8px}.article-row{grid-template-columns:1fr;padding:16px}.pagination{margin:22px 16px 0;padding:14px}.pagination a,.pagination span{min-width:42px;height:44px;padding:0 10px}}
</style>.legal-footer{margin-top:0;background:#161616;color:#aaa;padding:26px 16px;border-top:1px solid rgba(255,255,255,.07)}.legal-footer .wrap{width:min(1100px,calc(100% - 32px));margin:auto}.footer-links,.legal-links{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:12px}.footer-links a,.legal-links a{color:#ddd;font-size:.78rem;text-decoration:none}.footer-links a:hover,.legal-links a:hover{color:#fff}.footer-copy{text-align:center;font-size:.78rem;color:#aaa}"""

def page_href(n):
    return "/" if n==1 else f"/pagina-{n}.html"

def render_pagination(current,total):
    if total<=1:
        return ""
    # Show up to five numbered pages, as in the requested template.
    visible=list(range(1,min(total,5)+1))
    items=[]
    for n in visible:
        if n==current:
            items.append(f'<span class="active">{n}</span>')
        else:
            items.append(f'<a href="{page_href(n)}">{n}</a>')
    if current < total:
        items.append(f'<a class="next" href="{page_href(current+1)}">NEXT</a>')
    return '<nav class="pagination" aria-label="Pagine articoli">'+"".join(items)+'</nav>'

def write_article_pages(posts):
    total=max(1,(len(posts)+PAGE_SIZE-1)//PAGE_SIZE)
    total=min(total,5)

    # Reuse the real Home HTML as the template so pagina 2-5 keep exactly
    # the same header, colors, spacing, sidebar, footer and responsive layout.
    home_template=INDEX.read_text(encoding="utf-8")

    for page_num in range(2,total+1):
        chunk=posts[(page_num-1)*PAGE_SIZE:page_num*PAGE_SIZE]
        page=home_template

        # Page-specific SEO.
        page=re.sub(r'<title>.*?</title>',
                    f'<title>Articoli - Pagina {page_num} | ZazoomTek</title>',
                    page,count=1,flags=re.S)
        page=re.sub(r'<meta name="description" content="[^"]*">',
                    f'<meta name="description" content="Archivio ZazoomTek, pagina {page_num}: news e recensioni meno recenti.">',
                    page,count=1)
        page=re.sub(r'<link rel="canonical" href="[^"]+">',
                    f'<link rel="canonical" href="https://zazoomtek.it/pagina-{page_num}.html">',
                    page,count=1)

        # Replace only the article stream and pagination.
        feed="<!-- ARTICLE_FEED_START -->\n"+render_article_feed(chunk)+"\n          <!-- ARTICLE_FEED_END -->"
        page=re.sub(r'<!-- ARTICLE_FEED_START -->.*?<!-- ARTICLE_FEED_END -->',
                    feed,page,flags=re.S)

        pagination="<!-- ARTICLE_PAGINATION_START -->\n"+render_pagination(page_num,total)+"\n        <!-- ARTICLE_PAGINATION_END -->"
        if "<!-- ARTICLE_PAGINATION_START -->" in page:
            page=re.sub(r'<!-- ARTICLE_PAGINATION_START -->.*?<!-- ARTICLE_PAGINATION_END -->',
                        pagination,page,flags=re.S)
        else:
            page=page.replace('</div>\n      </section>\n    </div>\n\n    <aside class="sidebar">',
                              '</div>\n        '+pagination+'\n      </section>\n    </div>\n\n    <aside class="sidebar">',1)

        # Clear duplicated search query state and keep the Home visual shell unchanged.
        Path(f"pagina-{page_num}.html").write_text(page,encoding="utf-8")

    return total

def main():
    previous=[]
    if STATE.exists():
        try:
            previous=json.loads(STATE.read_text(encoding="utf-8"))
            if not isinstance(previous,list):
                previous=[]
        except Exception:
            previous=[]

    known_ids={
        p.get("id") for p in previous
        if isinstance(p,dict) and p.get("id")
    }
    posts,complete=parse(fetch(),known_ids)
    if not posts:
        raise RuntimeError("No public Community posts parsed; refusing to modify the site.")

    if not complete:
        if not previous:
            raise RuntimeError(
                "Community scan incomplete and no previous valid state is available; "
                "refusing to modify the site."
            )
        fresh_ids={p.get("id") for p in posts if isinstance(p,dict)}
        preserved=[p for p in previous if isinstance(p,dict) and p.get("id") not in fresh_ids]
        posts=posts+preserved
        print(
            f"Community scan was partial: merged {len(posts)-len(preserved)} fresh items "
            f"with {len(preserved)} preserved previous items."
        )

    # Safety guard: a transient parser/API issue must never replace a healthy
    # archive with a suspiciously small partial result.
    if previous:
        minimum=max(20,int(len(previous)*0.80))
        if len(posts)<minimum:
            raise RuntimeError(
                f"Community safety check failed: parsed {len(posts)} posts, "
                f"previous valid state had {len(previous)}. Site left unchanged."
            )

    reviews=[p for p in posts if is_review(p)]
    news=[p for p in posts if not is_review(p)]
    if not news:
        raise RuntimeError("Community safety check failed: zero news parsed.")

    STATE.write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for p in reviews: write_review_page(p,reviews)
    write_review_archive(reviews)
    for p in news: write_news_page(p,news)
    write_news_archive(news,reviews)
    total_article_pages=write_article_pages(posts)
    # Rebuild canonical sitemap after every content sync so Search Console always sees current URLs.
    update_sitemap()
    s=INDEX.read_text(encoding="utf-8")
    s2=s
    home_reviews=render_home_latest_reviews(reviews)
    if "<!-- HOME_LATEST_REVIEWS_MAIN_START -->" in s2:
        s2=re.sub(r'<!-- HOME_LATEST_REVIEWS_MAIN_START -->.*?<!-- HOME_LATEST_REVIEWS_MAIN_END -->',home_reviews,s2,flags=re.S)

    # The old sidebar reviews box was moved into the main content area.
    s2=re.sub(r'\s*<!-- HOME_LATEST_REVIEWS_START -->.*?<!-- HOME_LATEST_REVIEWS_END -->\s*','\n',s2,flags=re.S)

    ticker="<!-- NEWS_TICKER_START -->\n"+render_ticker(news)+"\n    <!-- NEWS_TICKER_END -->"
    s2=re.sub(r'<!-- NEWS_TICKER_START -->.*?<!-- NEWS_TICKER_END -->',ticker,s2,flags=re.S)

    featured="<!-- FEATURED_NEWS_START -->\n        "+render_featured_news(news)+"\n        <!-- FEATURED_NEWS_END -->"
    s2=re.sub(r'<!-- FEATURED_NEWS_START -->.*?<!-- FEATURED_NEWS_END -->',featured,s2,flags=re.S)

    feed="<!-- ARTICLE_FEED_START -->\n"+render_article_feed(posts[:PAGE_SIZE])+"\n          <!-- ARTICLE_FEED_END -->"
    s2=re.sub(r'<!-- ARTICLE_FEED_START -->.*?<!-- ARTICLE_FEED_END -->',feed,s2,flags=re.S)

    pagination="<!-- ARTICLE_PAGINATION_START -->\n"+render_pagination(1,total_article_pages)+"\n        <!-- ARTICLE_PAGINATION_END -->"
    if "<!-- ARTICLE_PAGINATION_START -->" in s2:
        s2=re.sub(r'<!-- ARTICLE_PAGINATION_START -->.*?<!-- ARTICLE_PAGINATION_END -->',pagination,s2,flags=re.S)
    else:
        s2=s2.replace('</div>\n      </section>\n    </div>\n\n    <aside class="sidebar">',
                      '</div>\n        '+pagination+'\n      </section>\n    </div>\n\n    <aside class="sidebar">',1)

    if s2!=s:INDEX.write_text(s2,encoding="utf-8")
    print("Synced",len(news),"YouTube Community news posts and",len(reviews),"review posts")

if __name__=="__main__":main()
