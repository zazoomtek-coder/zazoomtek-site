"""Central, deterministic URL policy for new and legacy ZazoomTek articles."""
import re
import unicodedata

ALLOWED_PREFIXES = ("recensioni", "news", "speciali", "guide", "extra")
CATEGORY_PREFIX = {
    "recensioni-tech": "recensioni", "recensioni-gaming": "recensioni",
    "news-tech": "news", "news-gaming": "news",
    "speciali": "speciali", "guide": "guide", "extra": "extra",
}
STOP_WORDS = frozenset("""
a ad al alla alle allo ai agli all dalle dalla da di del della delle dei degli
in nel nello nella nei negli su sul sulla per tra fra con e ed il lo la i gli
le un uno una che come oggi nuovo nuova nuovi nuove the an and or of for to
on with by from at is are this that
""".split())
LEGACY_RE = re.compile(r"^/community-[a-z0-9]+(?:-[a-z0-9]+)*$")
PUBLIC_RE = re.compile(r"^/(recensioni|news|speciali|guide|extra)/[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_public_path(path):
    value = str(path or "").strip()
    if not value.startswith("/") or value.startswith("//") or "?" in value or "#" in value:
        raise ValueError("Public article path must be a same-origin absolute path")
    value = value.rstrip("/")
    if not PUBLIC_RE.fullmatch(value):
        raise ValueError("Public article path is outside the category whitelist: " + value)
    return value


def slugify_title(title, max_length=68):
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    words = re.findall(r"[a-z0-9]+", text)
    words = [word for word in words if word not in STOP_WORDS]
    if not words:
        words = re.findall(r"[a-z0-9]+", text)
    slug = "-".join(words)[:max_length].rstrip("-")
    if not slug:
        raise ValueError("Cannot create a public slug from an empty title")
    return slug


def unique_slug(title, occupied, max_length=68):
    base = slugify_title(title, max_length)
    candidate, number = base, 2
    while candidate in occupied:
        suffix = "-" + str(number)
        candidate = base[:max_length-len(suffix)].rstrip("-") + suffix
        number += 1
    occupied.add(candidate)
    return candidate


def build_article_url(article):
    """Legacy path is immutable; new paths require an explicit v2 marker."""
    if not isinstance(article, dict):
        raise TypeError("Article must be a mapping")
    for candidate in (article.get("legacy_path"), article.get("url")):
        candidate = str(candidate or "").strip()
        if candidate.startswith("/community-"):
            if not LEGACY_RE.fullmatch(candidate):
                raise ValueError("Invalid legacy Community path: " + candidate)
            return candidate
    if article.get("public_path"):
        return normalize_public_path(article["public_path"])
    if article.get("route_version") != "v2":
        raise ValueError("Article requires explicit route_version='v2' or legacy_path")
    category = str(article.get("category") or "")
    prefix = CATEGORY_PREFIX.get(category)
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError("Unsupported article category for public routing: " + category)
    slug = str(article.get("public_slug") or article.get("slug") or "")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        slug = slugify_title(article.get("title") or "")
    return normalize_public_path("/" + prefix + "/" + slug)
