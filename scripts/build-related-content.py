#!/usr/bin/env python3
import html
import math
import re
import unicodedata
from collections import Counter
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
    "enhanced","remastered","remake","accesso","anticipato","early","available","disponibile",
    "data","uscita","preorder","pre-order","annuncia","annunciato","presenta","presentato","svela",
    "prime","primo","prima","nuove","nuovi","novita","versione","modalita","contenuti","arrivo",
    "ottobre","settembre","novembre","dicembre","gennaio","febbraio","marzo","aprile","maggio",
    "giugno","luglio","agosto","2025","2026","2027"
}

WEAK_TOPICS = {
    "playstation","xbox","nintendo","pcgaming","multiplayer","dlc"
}

GAMING_TOPICS = {
    "transport_sim","city_builder","management_sim","simulation","fps_shooter","third_person_shooter","console_hardware",
    "action_adventure","open_world","rpg","action_rpg","soulslike","roguelike","survivors_like",
    "survival","horror","strategy","tactical","racing","sports","fighting","platformer","metroidvania",
    "puzzle","party_game","cozy","multiplayer","mmo","deckbuilder","stealth","flight_combat"
}
TECH_TOPICS = {
    "camera_security","robot_cleaning","networking","audio","keyboard","mouse","controller","dashcam",
    "smartphone","tablet","computer","storage","monitor","smart_home","wearable","power","printer","air_quality"
}

BROAD_TOPICS = {
    "simulation","action_adventure","multiplayer","computer","smart_home"
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
    "logitech": {"logitech"},
    "fossibot": {"fossibot"},
    "keychron": {"keychron"},
    "ulefone": {"ulefone"},
    "blackview": {"blackview"},
    "doogee": {"doogee"},
    "cubot": {"cubot"},
    "levoit": {"levoit"},
    "trust": {"trust"},
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
    "logitech": {"audio"},
    "fossibot": {"smartphone"},
    "keychron": {"keyboard"},
    "ulefone": {"smartphone"},
    "blackview": {"smartphone"},
    "doogee": {"smartphone"},
    "cubot": {"smartphone"},
    "levoit": {"air_quality"},
    "trust": {"audio"},
}

TITLE_TOPIC_GROUPS = {
    # Gaming
    "transport_sim": {"transport","transportation","railway","railroad","ferrovia","ferrovie","treno","treni","logistics","logistica","airport","aeroporto"},
    "city_builder": {"city builder","city-building","cities skylines","simcity","urbanistica","citta","costruzione citta"},
    "management_sim": {"tycoon","management","gestionale","economy","economico","gestione","manageriale"},
    "simulation": {"simulator","simulation","simulatore","simulazione"},
    "fps_shooter": {"fps","shooter","sparatutto","gunplay","battlefield","call of duty","cod","doom","serious sam","delta force","counter-strike","valorant"},
    "third_person_shooter": {"third person shooter","third-person shooter","tps"},
    "action_adventure": {"action adventure","action-adventure","azione","avventura","adventure"},
    "open_world": {"open world","open-world","mondo aperto"},
    "rpg": {"rpg","jrpg","gdr","role-playing","gioco di ruolo"},
    "action_rpg": {"action rpg","action-rpg","arpg"},
    "soulslike": {"soulslike","souls-like","soulsborne"},
    "roguelike": {"roguelike","rogue-like","roguelite","rogue-lite"},
    "survivors_like": {"survivors-like","survivor-like","bullet heaven","vampire survivors"},
    "survival": {"survival","sopravvivenza"},
    "horror": {"horror","survival horror","orrore"},
    "strategy": {"strategy","strategia","strategico","rts","4x","turn-based strategy","strategia a turni"},
    "tactical": {"tactical","tattico","tattica"},
    "racing": {"racing","corse","rally","motorsport","sim racing","automobilismo"},
    "sports": {"football","calcio","basket","basketball","ufc","sport","sports","tennis"},
    "fighting": {"fighting","picchiaduro","tekken","street fighter","mortal kombat"},
    "platformer": {"platform","platformer","platforming"},
    "metroidvania": {"metroidvania"},
    "puzzle": {"puzzle","rompicapo"},
    "party_game": {"party game","minigiochi","mini giochi"},
    "cozy": {"cozy","rilassante","relaxing"},
    "multiplayer": {"multiplayer","co-op","coop","cooperativa","online"},
    "mmo": {"mmo","mmorpg"},
    "deckbuilder": {"deckbuilder","deck-builder","deck building","deck-building","carte"},
    "stealth": {"stealth","furtivo","infiltrazione"},
    "flight_combat": {"flight combat","combattimento aereo","aerei","aviazione"},
    "console_hardware": {"playstation 5","playstation 6","ps5 pro","ps5","ps6","xbox series","nintendo switch","switch 2","console"},
    # Tech
    "camera_security": {"camera","telecamera","videosorveglianza","security camera","sicurezza","nvr","reolink"},
    "robot_cleaning": {"roomba","irobot","robot aspirapolvere","aspirapolvere robot","lavapavimenti","pulizia pavimenti","robot cleaning"},
    "networking": {"router","wifi","wi-fi","ethernet","fibra","mesh","modem","fritz!box","fritz box"},
    "audio": {"cuffie","headset","auricolari","earbuds","speaker","audio","microfono","soundbar"},
    "keyboard": {"tastiera","keyboard","switch meccanici","meccanica","epomaker","keychron"},
    "mouse": {"mouse","sensore ottico","dpi"},
    "controller": {"controller","gamepad","scuf","dualsense","dual sense"},
    "dashcam": {"dashcam","dash cam","70mai"},
    "smartphone": {"smartphone","telefono","android","iphone","realme","fossibot","rugged phone","smartphone rugged","display amoled","fotocamera smartphone"},
    "tablet": {"tablet","ipad"},
    "computer": {"notebook","laptop","mini pc","minipc","workstation","cpu","gpu","scheda video","processore"},
    "storage": {"ssd","nvme","hard disk","archiviazione","storage"},
    "monitor": {"monitor","display gaming","hz","refresh rate"},
    "smart_home": {"smart home","domotica","matter","zigbee","casa intelligente"},
    "wearable": {"smartwatch","wearable","fitness tracker","smart glasses","occhiali smart"},
    "power": {"powerbank","power bank","caricatore","charger","batteria"},
    "printer": {"stampante","printer"},
    "air_quality": {"purificatore","purificatore aria","air purifier","qualita aria"},
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

def title_token_sequence(text):
    text=unicodedata.normalize("NFKD", html.unescape(text).lower())
    text="".join(ch for ch in text if not unicodedata.combining(ch))
    text=re.sub(r"^\s*news\s*:\s*","",text)
    raw=re.findall(r"[a-z0-9]+",text)
    out=[]
    for token in raw:
        if token in STOPWORDS or token in GENERIC_TITLE_TERMS:
            continue
        # Keep sequel/model numbers (e.g. GTA 6, Transport Fever 3, A900),
        # but discard years and large standalone numbers.
        if token.isdigit() and (len(token)>2 or int(token)>99):
            continue
        if len(token)>=2 or token.isdigit():
            out.append(token)
    return out[:14]

def entity_phrases(text):
    """Extract title entities/product names as ordered 2-4 token phrases."""
    words=title_token_sequence(text)
    phrases=set()
    for size in (4,3,2):
        for i in range(len(words)-size+1):
            chunk=words[i:i+size]
            # A phrase made only of generic numbers/short tokens is useless.
            if sum(1 for x in chunk if not x.isdigit() and len(x)>=3) < 1:
                continue
            phrases.add(" ".join(chunk))
    return phrases

def title_bigrams(text):
    words=title_token_sequence(text)
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

def topic_hits(title, body):
    # Title weighs most, while the first part of the article is used only to
    # understand its editorial category. This improves coverage without making
    # unrelated body words create false matches.
    title_sample=unicodedata.normalize("NFKD", title.lower())
    title_sample="".join(ch for ch in title_sample if not unicodedata.combining(ch))
    body_sample=unicodedata.normalize("NFKD", body[:2200].lower())
    body_sample="".join(ch for ch in body_sample if not unicodedata.combining(ch))

    scores=Counter()
    for topic, terms in TITLE_TOPIC_GROUPS.items():
        for term in terms:
            term=term.lower()
            if phrase_present(title_sample,term):
                scores[topic]+=4
            elif phrase_present(body_sample,term):
                scores[topic]+=1

    for franchise in franchise_for(title):
        for topic in FRANCHISE_TOPICS.get(franchise,set()):
            scores[topic]+=5
    return scores

def domain_for(title, body, topics):
    franchises=franchise_for(title)
    game_franchises={
        "gta","risk_of_rain","transport_fever","ace_combat","battlefield",
        "call_of_duty","resident_evil","final_fantasy","monster_hunter","marvel_wolverine"
    }
    tech_franchises={"reolink","roomba","fritz","realme","70mai","epomaker","scuf","logitech","fossibot","keychron","ulefone","blackview","doogee","cubot","levoit","trust"}
    if franchises & game_franchises:
        return "gaming"
    if franchises & tech_franchises:
        return "tech"

    gaming_score=sum(score for topic,score in topics.items() if topic in GAMING_TOPICS)
    tech_score=sum(score for topic,score in topics.items() if topic in TECH_TOPICS)

    sample=(title+" "+body[:900]).lower()
    gaming_score += sum(1 for term in GAMING_TERMS if phrase_present(sample,term))
    tech_score += sum(1 for term in TECH_TERMS if phrase_present(sample,term))

    if gaming_score > tech_score:
        return "gaming"
    if tech_score > gaming_score:
        return "tech"
    return "mixed"

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
    entities = entity_phrases(title)
    body_tokens = normalized_words(body[:2200])
    topic_scores = topic_hits(title,body)
    topics = {topic for topic,score in topic_scores.items() if score >= 1}
    return {
        "path": path,
        "name": path.name,
        "raw": raw,
        "clean": content,
        "title": title,
        "body": body,
        "image": image_of(content),
        "kind": kind_for(path),
        "domain": domain_for(title,body,topic_scores),
        "topics": topics,
        "topic_scores": topic_scores,
        "franchises": franchise_for(title),
        "title_tokens": title_tokens,
        "strong_tokens": strong_tokens,
        "bigrams": bigrams,
        "entities": entities,
        "body_tokens": body_tokens,
    }

def build_idf(records):
    total=max(1,len(records))
    df=Counter()
    for record in records:
        for token in record["strong_tokens"]:
            df[token]+=1
    return {
        token: math.log((1+total)/(1+freq))+1.0
        for token,freq in df.items()
    }

def build_entity_idf(records):
    total=max(1,len(records))
    df=Counter()
    for record in records:
        for entity in record["entities"]:
            df[entity]+=1
    return {
        entity: math.log((1+total)/(1+freq))+1.0
        for entity,freq in df.items()
    }

def entity_overlap_score(current,candidate,entity_idf):
    shared=current["entities"] & candidate["entities"]
    if not shared:
        return 0.0,set()
    score=0.0
    for entity in shared:
        length=len(entity.split())
        score += entity_idf.get(entity,1.0) * (length**2)
    return score,shared

def rare_title_overlap(current,candidate,idf):
    shared=current["strong_tokens"] & candidate["strong_tokens"]
    return sum(idf.get(token,1.0) for token in shared)

def title_cosine(current,candidate,idf):
    a={t:idf.get(t,1.0) for t in current["strong_tokens"]}
    b={t:idf.get(t,1.0) for t in candidate["strong_tokens"]}
    if not a or not b:
        return 0.0
    dot=sum(a[t]*b.get(t,0.0) for t in a)
    na=math.sqrt(sum(v*v for v in a.values()))
    nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0

def topic_similarity(current,candidate):
    shared=current["topics"] & candidate["topics"]
    if not shared:
        return 0.0
    score=0.0
    for topic in shared:
        score += min(current["topic_scores"].get(topic,0),candidate["topic_scores"].get(topic,0))
    return score

def primary_topics(record):
    """Return only the strongest, specific editorial categories."""
    scores=record["topic_scores"]
    if not scores:
        return set()
    allowed = GAMING_TOPICS if record["domain"] == "gaming" else TECH_TOPICS if record["domain"] == "tech" else (GAMING_TOPICS | TECH_TOPICS)
    relevant={topic:score for topic,score in scores.items() if topic in allowed and score>0}
    if not relevant:
        return set()

    # If a specific category exists, broad umbrellas such as "simulation",
    # "multiplayer" or generic "computer" must not drive recommendations.
    specific={topic:score for topic,score in relevant.items() if topic not in BROAD_TOPICS}
    pool=specific if specific else relevant

    best=max(pool.values())
    return {topic for topic,score in pool.items() if score >= max(2,best-1)}

def relevance(current,candidate,idf,entity_idf):
    # Cross vertical recommendations are never allowed.
    if current["domain"] in {"gaming","tech"} and candidate["domain"] in {"gaming","tech"}:
        if current["domain"] != candidate["domain"]:
            return -999.0

    entity_score,_=entity_overlap_score(current,candidate,entity_idf)
    franchise_overlap=current["franchises"] & candidate["franchises"]
    bigram_overlap=current["bigrams"] & candidate["bigrams"]
    rare_overlap=rare_title_overlap(current,candidate,idf)
    cosine=title_cosine(current,candidate,idf)
    topic_score=topic_similarity(current,candidate)

    score=(
        entity_score*30.0
        + len(franchise_overlap)*220.0
        + len(bigram_overlap)*38.0
        + rare_overlap*12.0
        + cosine*35.0
        + topic_score*12.0
    )
    if current["domain"] == candidate["domain"] and current["domain"] != "mixed":
        score += 4.0
    if current["kind"] == candidate["kind"]:
        score += 1.0
    return score

def related_for(current, records, idf, entity_idf, limit=LIMIT):
    ranked=[]
    current_primary=primary_topics(current)

    for candidate in records:
        if candidate["name"] == current["name"]:
            continue

        if current["domain"] in {"gaming","tech"} and candidate["domain"] in {"gaming","tech"}:
            if current["domain"] != candidate["domain"]:
                continue

        entity_score,entity_overlap=entity_overlap_score(current,candidate,entity_idf)
        franchise_overlap=current["franchises"] & candidate["franchises"]
        bigram_overlap=current["bigrams"] & candidate["bigrams"]
        rare_overlap=rare_title_overlap(current,candidate,idf)
        cosine=title_cosine(current,candidate,idf)
        candidate_primary=primary_topics(candidate)
        primary_overlap=current_primary & candidate_primary
        shared_topics=current["topics"] & candidate["topics"]
        topic_score=topic_similarity(current,candidate)
        score=relevance(current,candidate,idf,entity_idf)

        # Zazoom-style editorial hierarchy:
        # 0 exact title entity/product/game overlap
        # 1 known franchise/brand/product family
        # 2 strong rare title similarity
        # 3 same specific primary category
        # 4 secondary category only with supporting title similarity
        if entity_overlap:
            tier=0
        elif franchise_overlap:
            tier=1
        elif bigram_overlap or rare_overlap >= 4.5:
            tier=2
        elif primary_overlap:
            tier=3
            score += len(primary_overlap)*30
        elif (
            shared_topics
            and not (shared_topics <= BROAD_TOPICS)
            and topic_score >= 3
            and (cosine >= 0.12 or rare_overlap >= 1.8)
        ):
            tier=4
        else:
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

    idf=build_idf(records)
    entity_idf=build_entity_idf(records)
    changed = 0
    with_blocks = 0
    total_links = 0
    no_match=[]
    for record in records:
        related = related_for(record, records, idf, entity_idf, LIMIT)
        block = render_related(related) if len(related) >= MIN_RELATED else ""
        if not related:
            no_match.append(record["name"])
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

    coverage=(with_blocks/len(records))*100 if records else 0
    print(
        f"Entity-first related content evaluated for {len(records)} articles; "
        f"{with_blocks} pages have matches ({coverage:.1f}% coverage), "
        f"{total_links} links total; {changed} files updated."
    )
    if no_match:
        print("Pages without a safe related match:", ", ".join(no_match[:20]))
    if coverage < 70:
        print(
            f"NOTICE: related-content coverage is {coverage:.1f}%; "
            "quality filter kept weak or cross-topic recommendations out."
        )

if __name__ == "__main__":
    main()
