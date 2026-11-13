"""Central, deterministic URL policy for new and historical ZazoomTek articles."""
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
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def unique_slug(title, occupied, max_length=68, prefix=None):
    """Allocate a slug against existing sibling slugs or paths in one category."""
    base = slugify_title(title, max_length)
    candidate, number = base, 2
    while (candidate in occupied if prefix is None else "/" + prefix + "/" + candidate in occupied) or any(
        isinstance(path, str) and (prefix is None or path.startswith("/" + prefix + "/"))
        and path.rsplit("/", 1)[-1] == candidate for path in occupied
    ):
        suffix = "-" + str(number)
        candidate = base[:max_length-len(suffix)].rstrip("-") + suffix
        number += 1
    occupied.add(candidate if prefix is None else "/" + prefix + "/" + candidate)
    return candidate


def is_v2(article):
    return article.get("route_version") in (2, "2", "v2")


def build_article_url(article):
    """Return the immutable original URL for legacy rows and v2 URL for new rows."""
    if not isinstance(article, dict):
        raise TypeError("Article must be a mapping")
    # Explicit legacy_path is authoritative and must be returned byte-for-byte.
    legacy_value = article.get("legacy_path")
    legacy = legacy_value if isinstance(legacy_value, str) else ""
    if legacy:
        if not legacy.startswith("/") or legacy.startswith("//") or "?" in legacy or "#" in legacy:
            raise ValueError("Invalid explicit legacy path: " + legacy)
        return legacy
    # Preserve historical Community URLs even when they have no explicit marker.
    for candidate in (article.get("url"),):
        candidate = candidate if isinstance(candidate, str) else ""
        if candidate.startswith("/community-"):
            if not LEGACY_RE.fullmatch(candidate):
                raise ValueError("Invalid legacy Community path: " + candidate)
            return candidate
    # Missing route_version means historic content: never derive a new slug.
    if not is_v2(article):
        original_value = article.get("url")
        original = original_value if isinstance(original_value, str) else ""
        if original.startswith("/") and not original.startswith("//"):
            return original
        slug = str(article.get("slug") or "").strip()
        if not slug:
            raise ValueError("Legacy article has no original path or slug")
        return "/" + slug.removesuffix(".html")
    if article.get("public_path"):
        return normalize_public_path(article["public_path"])
    category = str(article.get("category") or "")
    prefix = CATEGORY_PREFIX.get(category)
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError("Unsupported article category for public routing: " + category)
    slug = str(article.get("public_slug") or "")
    if not SLUG_RE.fullmatch(slug):
        slug = slugify_title(article.get("title") or "")
    return normalize_public_path("/" + prefix + "/" + slug)


def assign_public_routes(rows):
    """Assign once to v2 rows; existing public_path values are immutable."""
    occupied = set()
    for row in rows:
        if not isinstance(row, dict) or not is_v2(row) or not row.get("public_path"):
            continue
        path = normalize_public_path(row["public_path"])
        if path in occupied:
            raise ValueError("Duplicate immutable public_path in category: " + path)
        occupied.add(path)
    for row in rows:
        if not isinstance(row, dict) or not is_v2(row):
            continue
        if row.get("legacy_path"):
            continue
        if row.get("public_path"):
            row["public_path"] = normalize_public_path(row["public_path"])
            continue
        category = str(row.get("category") or "")
        prefix = CATEGORY_PREFIX.get(category)
        if prefix not in ALLOWED_PREFIXES:
            raise ValueError("Unsupported v2 article category: " + category)
        slug = unique_slug(row.get("title") or row.get("slug") or "", occupied, prefix=prefix)
        path = normalize_public_path("/" + prefix + "/" + slug)
        row["public_slug"] = slug
        row["public_path"] = path
        occupied.add(path)
    return rows
