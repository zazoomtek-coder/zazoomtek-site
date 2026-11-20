"""Extract only explicitly labelled PRO / CONTRO lists from YouTube review text.

Never infer opinions. Source YouTube Community text stays complete and unchanged.
The parser feeds the existing .review-verdict two-column HTML template.
"""
import re

_HEADING = re.compile(
    r"^\s*(?:#{1,4}\s*)?(?:\*\*|__)?\s*"
    r"(?P<label>pro|contro|punti\s+di\s+forza|punti\s+deboli|"
    r"aspetti\s+positivi|aspetti\s+negativi)"
    r"\s*:?(?:\*\*|__)?\s*$", re.IGNORECASE
)
_STOP = re.compile(
    r"^(?:#{1,4}\s*)?(?:\*\*)?\s*(?:"
    r"voto(?:\s+finale)?|valutazione\s+finale|conclusioni|"
    r"conclusione|subscribe|se\s+ti\s+piacciono|"
    r"youtube|patreon|tiktok|whatsapp|hashtag|link\s+utili"
    r")\b", re.IGNORECASE
)
_BULLET = re.compile(r"^\s*(?:[-*•●✓✔✅❌➕➖]\s*|\d{1,2}[.)]\s*)+")
_PRO = {"pro", "punti di forza", "aspetti positivi"}
_CON = {"contro", "punti deboli", "aspetti negativi"}


def extract(text, limit=16):
    """Return {'pros': [...], 'cons': [...]} or empty lists if not labelled."""
    items = {"pros": [], "cons": []}
    active = None
    seen = {"pros": set(), "cons": set()}
    raw = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        marker = _HEADING.fullmatch(line)
        if marker:
            name = re.sub(r"\s+", " ", marker.group("label")).casefold()
            active = "pros" if name in _PRO else "cons"
            continue
        if active is None:
            continue
        if line.startswith("#") or _STOP.match(line):
            active = None
            continue
        line = _BULLET.sub("", line).strip()
        # A paragraph is not a bullet list: resist consuming the whole
        # review if an unrelated section follows an isolated "Pro" line.
        if not line or len(line) > 220:
            active = None
            continue
        fingerprint = line.casefold()
        if fingerprint not in seen[active] and len(items[active]) < limit:
            seen[active].add(fingerprint)
            items[active].append(line)
    return items


def attach(post):
    """Create metadata for Community imported reviews, without editing text."""
    if str(post.get("type") or "").casefold() not in {"review", "recensione"}:
        return post
    fields = extract(post.get("text"))
    for key, values in fields.items():
        if values:
            post[key] = values
    return post
