#!/usr/bin/env python3
import html
import re
import unicodedata
from pathlib import Path

ROOT = Path(".")
START = "<!-- RELATED_CONTENT_START -->"
END = "<!-- RELATED_CONTENT_END -->"
STYLE_ID = "zt-related-style"
LIMIT = 4
MIN_RELATED = 1
MIN_SCORE = 8.0

GENERIC_TITLE_TERMS = {
    "ps4","ps5","xbox","series","switch","nintendo","playstation","pc","steam","windows",
    "dlc","update","aggiornamento","trailer","video","gameplay","demo","beta","edition","complete",
    "enhanced","remastered","remake","accesso","anticipato","early","available","disponibile"
}

WEAK_TOPICS = {
    "playstation","xbox","nintendo","pcgaming","multiplayer","dlc"
}

FRANCHISE_ALIASES = {
    "gta": {"gta vi","gta 6","grand theft auto vi","grand theft auto 6","grand theft auto"},
    "risk_of_rain": {"risk of rain"},
    "transport_fever": {"transport fever"},
    "ace_combat": {"ace combat"},
    "battlefield": {"battlefield"},
    "call_of_duty": {"call of duty","cod"},
    "resident_evil": {"resident evil"},
    "final_fantasy": {"final fantasy"},
    "monster_hunter": {"monster hunter"},
    "marvel_wolverine": {"marvel's wolverine","marvel wolverine","wolverine"},
    "reolink": {"reolink"},
    "roomba": {"roomba","irobot"},
    "fritz": {"fritz!box","fritz box","fritz"},
    "realme": {"realme"},
    "70mai": {"70mai"},
    "epomaker": {"epomaker"},
    "scuf": {"scuf"},
}

FRANCHISE_TOPICS = {
    "transport_fever": {"transport_sim"},
    "risk_of_rain": {"roguelike","fps_shooter"},
    "battlefield": {"fps_shooter"},
    "call_of_duty": {"fps_shooter"},
    "ace_combat": {"simulation"},
    "gta": {"open_world"},
    "resident_evil": {"horror"},
    "final_fantasy": {"rpg"},
    "monster_hunter": {"rpg"},
    "roomba": {"robot_cleaning"},
    "reolink": {"camera_security"},
    "fritz": {"networking"},
    "70mai": {"dashcam"},
    "epomaker": {"keyboard"},
    "scuf": {"controller"},
    "realme": {"smartphone"},
}

TITLE_TOPIC_GROUPS = {
    "transport_sim": {
        "transport","transportation","railway","railroad","ferrovia","ferrovie","treno","treni",
        "logistics","logistica","airport","aeroporto"
    },
    "city_builder": {
        "city builder","city-building","construction simulator","construction","costruzione",
        "cities skylines","simcity"
    },
    "management_sim": {
        "tycoon","management","gestionale","economic simulator","economy simulator"
    },
    "simulation": {
        "simulator","simulation","simulatore","simulazione"
    },
    "fps_shooter": {
        "fps","shooter","sparatutto","battlefield","call of duty","cod","doom","serious sam",
        "delta force","counter-strike","valorant"
    },
    "rpg": {"rpg","jrpg","gdr","role-playing"},
    "roguelike": {"roguelike","roguelite","survivor","survivors"},
    "survival": {"survival","sopravvivenza"},
    "horror": {"horror"},
    "strategy": {"strategy","strategia","strategico","rts","4x"},
    "racing": {"racing","corse","rally","motorsport","sim racing"},
    "sports": {"football","calcio","basket","ufc","sport","sports"},
    "fighting": {"fighting","picchiaduro","tekken","street fighter","mortal kombat"},
    "platformer": {"platform","platformer"},
    "open_world": {"open world","open-world"},
    "camera_security": {"camera","telecamera","videosorveglianza","security","sicurezza","reolink"},
    "robot_cleaning": {"roomba","irobot","robot","aspirapolvere","lavapavimenti","pulizia"},
    "networking": {"router","wifi","wi-fi","ethernet","fibra","fritz!box","fritz box"},
    "audio": {"cuffie","headset","auricolari","earbuds","speaker","audio","microfono"},
    "keyboard": {"tastiera","keyboard","epomaker","keychron"},
    "controller": {"controller","gamepad","scuf","dualSense","dualsense"},
    "dashcam": {"dashcam","dash cam","70mai"},
    "smartphone": {"smartphone","telefono","android","iphone","realme"},
    "computer": {"notebook","laptop","mini pc","minipc","workstation","cpu","gpu","scheda video"},
}

STOPWORDS = {
    "alla","alle","allo","anche","ancora","avere","come","con","contro","cosa","dalla","dalle","dallo",
    "degli","della","delle","dello","dentro","dopo","dove","essere","fino","fra","gli","hanno","il","in",
    "la","le","lo","ma","mentre","nel","nella","nelle","nello","non","oltre","per","piu","prima","quale",
    "quali","quando","questa","queste","questi","questo","senza","sono","sua","sue","sul","sulla","sulle",
    "tra","tutto","una","uno","verso","news","recensione","review","zazoomtek","nuovo","nuova","nuovi","nuove",
    "arriva","ecco","mostra","disponibile","ufficiale","oggi","ora","finale"
}

GAMING_TERMS = {
    "playstation","ps4","ps5","xbox","nintendo","switch","steam","videogioco","videogiochi","gaming",
    "gameplay","dlc","espansione","multiplayer","coop","co-op","rpg","jrpg","roguelike","roguelite",
    "shooter","fps","survival","horror","strategia","strategy","simulatore","simulazione","racing",
    "picchiaduro","adventure","avventura","action","gdr","console","demo","beta","early access"
}
TECH_TERMS = {
    "smartphone","tablet","notebook","laptop","monitor","display","router","wifi","wi-fi","ethernet",
    "tastiera","keyboard","mouse","cuffie","headset","auricolari","earbuds","speaker","audio","microfono",
    "webcam","dashcam","camera","telecamera","ssd","hard disk","minipc","mini pc","processore","cpu","gpu",
    "scheda video","robot","roomba","aspirapolvere","lavapavimenti","domotica","smart home","wearable",
    "smartwatch","occhiali smart","powerbank","caricatore","batteria","stampante","rete","fibra"
}

TOPIC_GROUPS = {
    "playstation": {"playstation","ps4","ps5"},
    "xbox": {"xbox","series x","series s"},
    "nintendo": {"nintendo","switch"},
    "pcgaming": {"steam","pc gaming","windows"},
    "rpg": {"rpg","jrpg","gdr","role-playing"},
    "roguelike": {"roguelike","roguelite"},
    "shooter": {"shooter","fps","sparatutto"},
    "survival": {"survival","sopravvivenza"},
    "horror": {"horror"},
    "strategy": {"strategia","strategy","strategico"},
    "racing": {"racing","corse","sim racing"},
    "sports": {"calcio","football","basket","ufc","sports","sportivo"},
    "multiplayer": {"multiplayer","coop","co-op","online"},
    "dlc": {"dlc","espansione","update","aggiornamento"},
    "phone": {"smartphone","telefono","android","iphone"},
    "audio": {"cuffie","headset","auricolari","earbuds","speaker","audio","microfono"},
    "network": {"router","wifi","wi-fi","ethernet","fibra","rete"},
    "camera": {"camera","telecamera","dashcam","webcam"},
    "storage": {"ssd","hard disk","nvme","archiviazione"},
    "computer": {"notebook","laptop","mini pc","minipc","cpu","gpu","processore","scheda video"},
    "robot_home": {"robot","roomba","aspirapolvere","lavapavimenti","pulizia"},
    "wearable": {"smartwatch","wearable","occhiali smart"},
}

STYLE = """<style id="zt-related-style">
.zt-related-section{margin:34px 0 4px;padding-top:4px}
.zt-related-head{display:flex;align-items:center;gap:12px;margin:0 0 16px;border-bottom:3px solid #d51232;padding-bottom:10px}
.zt-related-head h2{margin:0!important;border:0!important;box-shadow:none!important;padding:0!important;font-size:1.35rem!important;line-height:1.15;color:#171717!important}
.zt-related-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.zt-related-card{min-width:0;border:1px solid #e0e0e0;background:#fff;transition:transform .16s ease,box-shadow .16s ease}
.zt-related-card:hover{transform:translateY(-2px);box-shadow:0 7px 20px rgba(0,0,0,.10)}
.zt-related-card>a{display:block}
.zt-related-card img{display:block;width:100%;aspect-ratio:16/9;object-fit:cover;object-position:center;background:#111}
.zt-related-copy{padding:12px 13px 14px}
.zt-related-kind{display:inline-block;margin-bottom:7px;color:#d51232;font-size:.68rem;font-weight:900;letter-spacing:.06em;text-transform:uppercase}
.zt-related-card h3{margin:0!important;font-size:1rem!important;line-height:1.23!important;color:#222!important}
.zt-related-card h3 a{color:#222!important;text-decoration:none}
@media(max-width:620px){.zt-related-grid{grid-template-columns:1fr}.zt-related-card{display:grid;grid-template-columns:120px minmax(0,1fr)}.zt-related-card>a{align-self:stretch}.zt-related-card img{height:100%;min-height:92px;aspect-ratio:auto}.zt-related-copy{padding:11px 12px}.zt-related-card h3{font-size:.94rem!important}}
</style>"""

def clean_text(value):
    value = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def without_related(content):
    content = re.sub(
        re.escape(START) + r"[\s\S]*?" + re.escape(END),
        "",
        content,
        flags=re.I,
    )
    content = re.sub(
        r'<style\s+id=["\']zt-related-style["\'][^>]*>[\s\S]*?</style>',
        "",
        content,
        flags=re.I,
    )
    return content

def meta(content, name=None, prop=None):
    key = name or prop
    attr = "name" if name else "property"
    patterns = [
        rf'<meta[^>]+{attr}=["\']{re.escape(key)}["\'][^>]+content=["\']([^"\']*)',
        rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+{attr}=["\']{re.escape(key)}["\']',
    ]
    for pattern in patterns:
        m = re.search(pattern, content, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""

def title_of(content):
    title = meta(content, prop="og:title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", content, re.I | re.S)
        title = clean_text(m.group(1)) if m else ""
    title = re.sub(r"\s*\|\s*ZazoomTek\s*$", "", title, flags=re.I).strip()
    return title

def body_of(content):
    m = re.search(r'<div\s+class=["\']article-body["\'][^>]*>([\s\S]*?)</div>', content, re.I)
    if m:
        return clean_text(m.group(1))
    m = re.search(r"<article\b[^>]*>([\s\S]*?)</article>", content, re.I)
    return clean_text(m.group(1)) if m else ""

def image_of(content):
    image = meta(content, prop="og:image")
    if image:
        return image
    m = re.search(r'<img\s+class=["\']article-hero["\'][^>]+src=["\']([^"\']+)', content, re.I)
    return html.unescape(m.group(1)).strip() if m else "/ChatGPT.png"

def normalized_words(text):
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    words = re.findall(r"[a-z0-9][a-z0-9+.-]{1,}", text)
    return {
        w for w in words
        if len(w) >= 3 and w not in STOPWORDS and not w.isdigit()
    }

def strong_title_tokens(text):
    return {
        w for w in normalized_words(text)
        if w not in GENERIC_TITLE_TERMS
    }

def title_bigrams(text):
    words=[
        w for w in re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKD", text.lower()))
        if len(w)>=3 and w not in STOPWORDS and w not in GENERIC_TITLE_TERMS
    ]
    return {" ".join(words[i:i+2]) for i in range(len(words)-1)}

def phrase_present(text, phrase):
    text = text.lower()
    if " " in phrase or "-" in phrase:
        return phrase in text
    return re.search(r"(?<![a-z0-9])"+re.escape(phrase)+r"(?![a-z0-9])", text) is not None

def franchise_for(title):
    sample=unicodedata.normalize("NFKD", title.lower())
    sample="".join(ch for ch in sample if not unicodedata.combining(ch))
    found=set()
    for franchise, aliases in FRANCHISE_ALIASES.items():
        if any(phrase_present(sample, alias) for alias in aliases):
            found.add(franchise)
    return found

def domain_for(title):
    sample=title.lower()
    gaming=sum(1 for term in GAMING_TERMS if phrase_present(sample, term))
    tech=sum(1 for term in TECH_TERMS if phrase_present(sample, term))

    # Known game franchises are always gaming; known hardware brands/products
    # remain tech unless the title itself is clearly about a videogame.
    franchises=franchise_for(title)
    game_franchises={
        "gta","risk_of_rain","transport_fever","ace_combat","battlefield",
        "call_of_duty","resident_evil","final_fantasy","monster_hunter","marvel_wolverine"
    }
    tech_franchises={"reolink","roomba","fritz","realme","70mai","epomaker","scuf"}
    if franchises & game_franchises:
        return "gaming"
    if franchises & tech_franchises:
        return "tech"
    if gaming > tech:
        return "gaming"
    if tech > gaming:
        return "tech"
    return "mixed"

def topics_for(title):
    sample=unicodedata.normalize("NFKD", title.lower())
    sample="".join(ch for ch in sample if not unicodedata.combining(ch))
    topics={
        topic for topic, terms in TITLE_TOPIC_GROUPS.items()
        if any(phrase_present(sample, term.lower()) for term in terms)
    }
    for franchise in franchise_for(title):
        topics.update(FRANCHISE_TOPICS.get(franchise,set()))
    return topics

def kind_for(path):
    name = path.name.lower()
    return "Recensione" if name.startswith("recensione-") or "recensione" in name else "News"

def eligible_paths():
    found = {}
    for pattern in ("news-Ugkx*.html", "recensione-Ugkx*.html", "*-recensione-*.html"):
        for path in ROOT.glob(pattern):
            if path.is_file():
                found[path.name] = path
    return [found[k] for k in sorted(found)]

def article_record(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    content = without_related(raw)
    title = title_of(content)
    body = body_of(content)
    if kind_for(path) == "News" and title.strip().lower() == "news":
        m = re.search(r'<div\s+class=["\']article-body["\'][^>]*>([\s\S]*?)</div>', content, re.I)
        if m:
            first_p = re.search(r'<p[^>]*>([\s\S]*?)</p>', m.group(1), re.I)
            if first_p:
                candidate = clean_text(first_p.group(1))
                if candidate:
                    title = candidate
    if not title or not body:
        return None
    title_tokens = normalized_words(title)
    strong_tokens = strong_title_tokens(title)
    bigrams = title_bigrams(title)
    body_tokens = normalized_words(body[:8000])
    return {
        "path": path,
        "name": path.name,
        "raw": raw,
        "clean": content,
        "title": title,
        "body": body,
        "image": image_of(content),
        "kind": kind_for(path),
        "domain": domain_for(title),
        "topics": topics_for(title),
        "franchises": franchise_for(title),
        "title_tokens": title_tokens,
        "strong_tokens": strong_tokens,
        "bigrams": bigrams,
        "body_tokens": body_tokens,
    }

def relevance(current, candidate):
    # Never mix clear gaming and clear tech.
    if (
        current["domain"] != "mixed"
        and candidate["domain"] != "mixed"
        and current["domain"] != candidate["domain"]
    ):
        return -999.0

    franchise_overlap=current["franchises"] & candidate["franchises"]
    strong_overlap=current["strong_tokens"] & candidate["strong_tokens"]
    bigram_overlap=current["bigrams"] & candidate["bigrams"]
    topic_overlap=current["topics"] & candidate["topics"]

    # Ranking is deliberately TITLE-ONLY. Body copy is ignored.
    score=(
        len(franchise_overlap) * 100.0
        + len(bigram_overlap) * 30.0
        + len(strong_overlap) * 14.0
        + len(topic_overlap) * 12.0
    )
    if current["kind"] == candidate["kind"]:
        score += 0.5
    return score

def related_for(current, records, limit=LIMIT):
    ranked=[]
    for candidate in records:
        if candidate["name"] == current["name"]:
            continue

        franchise_overlap=current["franchises"] & candidate["franchises"]
        strong_overlap=current["strong_tokens"] & candidate["strong_tokens"]
        bigram_overlap=current["bigrams"] & candidate["bigrams"]
        topic_overlap=current["topics"] & candidate["topics"]

        # A platform alone (PS5/Xbox/PC/Switch) is never a reason to relate.
        # Require one of:
        # - same franchise/product family;
        # - a meaningful two-word title phrase;
        # - at least two strong title terms;
        # - a specific title-derived genre/category.
        if franchise_overlap:
            tier=0
        elif bigram_overlap:
            tier=1
        elif len(strong_overlap) >= 2:
            tier=2
        elif topic_overlap:
            tier=3
        else:
            continue

        score=relevance(current,candidate)
        if score < MIN_SCORE:
            continue
        ranked.append((tier,-score,candidate["name"],candidate))

    ranked.sort(key=lambda item:(item[0],item[1],item[2]))
    return [item[3] for item in ranked[:limit]]

def render_related(items):
    cards = []
    for item in items:
        title = html.escape(item["title"])
        image = html.escape(item["image"] or "/ChatGPT.png", quote=True)
        href = "/" + html.escape(item["name"], quote=True)
        kind = html.escape(item["kind"])
        cards.append(
            '<article class="zt-related-card">'
            f'<a href="{href}" aria-label="{title}"><img src="{image}" alt="{title}" loading="lazy"></a>'
            '<div class="zt-related-copy">'
            f'<span class="zt-related-kind">{kind}</span>'
            f'<h3><a href="{href}">{title}</a></h3>'
            '</div></article>'
        )
    return (
        START
        + '<section class="zt-related-section" aria-labelledby="zt-related-title">'
        + '<div class="zt-related-head"><h2 id="zt-related-title">Articoli correlati</h2></div>'
        + '<div class="zt-related-grid">'
        + "".join(cards)
        + '</div></section>'
        + END
    )

def inject(record, block):
    content = record["clean"]
    if not block:
        return content
    if f'id="{STYLE_ID}"' not in content:
        pos = content.lower().find("</head>")
        if pos < 0:
            raise RuntimeError(f"{record['name']}: missing </head>")
        content = content[:pos] + STYLE + "\n" + content[pos:]

    marker = '<section class="zt-subscribe-cta">'
    pos = content.find(marker)
    if pos >= 0:
        content = content[:pos] + block + content[pos:]
    else:
        pos = content.lower().rfind("</article>")
        if pos < 0:
            raise RuntimeError(f"{record['name']}: missing article insertion point")
        content = content[:pos] + block + content[pos:]
    return content

def main():
    records = []
    for path in eligible_paths():
        record = article_record(path)
        if record:
            records.append(record)

    if len(records) < 20:
        raise RuntimeError(f"Too few editorial articles found: {len(records)}")

    changed = 0
    with_blocks = 0
    total_links = 0
    for record in records:
        related = related_for(record, records, LIMIT)
        block = render_related(related) if len(related) >= MIN_RELATED else ""
        output = inject(record, block)
        if block:
            with_blocks += 1
            total_links += len(related)
            if output.count(START) != 1 or output.count(END) != 1:
                raise RuntimeError(f"{record['name']}: invalid related-content markers")
        elif START in output or END in output:
            raise RuntimeError(f"{record['name']}: stale related-content markers")
        if output != record["raw"]:
            record["path"].write_text(output, encoding="utf-8")
            changed += 1

    print(
        f"Title-based related content evaluated for {len(records)} articles; "
        f"{with_blocks} pages have strong matches, {total_links} links total; "
        f"{changed} files updated."
    )

if __name__ == "__main__":
    main()
