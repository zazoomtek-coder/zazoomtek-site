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
REVIEW_LABELS = frozenset({"review", "reviews", "recensione", "recensioni"})
REVIEW_PREFIX_LABELS = frozenset({"gaming", "tech"})
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


def _title_tokens(title):
    text = unicodedata.normalize("NFKD", str(title or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()
    return re.findall(r"[a-z0-9]+", text)


def slugify_title(title, max_length=68):
    words = [word for word in _title_tokens(title) if word not in STOP_WORDS]
    if not words:
        words = _title_tokens(title)
    slug = "-".join(words)[:max_length].rstrip("-")
    if not slug:
        raise ValueError("Cannot create a public slug from an empty title")
    return slug


def slugify_review_title(title, max_length=68):
    """Create review slugs from the subject/platform, never editorial labels."""
    words = _title_tokens(title)
    if words and words[0] in REVIEW_LABELS:
        words.pop(0)
        if words and words[0] in REVIEW_PREFIX_LABELS:
            words.pop(0)
    elif len(words) > 1 and words[0] in REVIEW_PREFIX_LABELS and words[1] in REVIEW_LABELS:
        words = words[2:]
    words = [word for word in words if word not in REVIEW_LABELS and word not in STOP_WORDS]
    if not words:
        raise ValueError("Cannot create a public review slug from an empty title")
    slug = "-".join(words)[:max_length].rstrip("-")
    if not slug:
        raise ValueError("Cannot create a public review slug from an empty title")
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


def is_review(article):
    return str(article.get("category") or "") in ("recensioni-tech", "recensioni-gaming")


def build_article_url(article):
    """Return the immutable original URL for legacy rows and v2 URL for new rows."""
    if not isinstance(article, dict):
        raise TypeError("Article must be a mapping")
    legacy_value = article.get("legacy_path")
    legacy = legacy_value if isinstance(legacy_value, str) else ""
    if legacy:
        if not legacy.startswith("/") or legacy.startswith("//") or "?" in legacy or "#" in legacy:
            raise ValueError("Invalid explicit legacy path: " + legacy)
        return legacy
    for candidate in (article.get("url"),):
        candidate = candidate if isinstance(candidate, str) else ""
        if candidate.startswith("/community-"):
            if not LEGACY_RE.fullmatch(candidate):
                raise ValueError("Invalid legacy Community path: " + candidate)
            return candidate
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
        existing = normalize_public_path(article["public_path"])
        if is_review(article):
            existing_slug = existing.rsplit("/", 1)[-1]
            existing_words = existing_slug.split("-")
            has_editorial_label = any(word in REVIEW_LABELS for word in existing_words) or (
                len(existing_words) > 1 and existing_words[0] in REVIEW_PREFIX_LABELS
                and existing_words[1] in REVIEW_LABELS
            )
            if has_editorial_label:
                return normalize_public_path("/recensioni/" + slugify_review_title(article.get("title") or ""))
        return existing
    category = str(article.get("category") or "")
    prefix = CATEGORY_PREFIX.get(category)
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError("Unsupported article category for public routing: " + category)
    slug = str(article.get("public_slug") or "")
    if not SLUG_RE.fullmatch(slug):
        slug = slugify_review_title(article.get("title") or "") if is_review(article) else slugify_title(article.get("title") or "")
    return normalize_public_path("/" + prefix + "/" + slug)


def assign_public_routes(rows):
    """Persist canonical v2 paths; review routes are normalized from title + platform."""
    occupied = set()
    review_rows = []
    for row in rows:
        if not isinstance(row, dict) or not is_v2(row) or row.get("legacy_path"):
            continue
        category = str(row.get("category") or "")
        prefix = CATEGORY_PREFIX.get(category)
        if prefix not in ALLOWED_PREFIXES:
            raise ValueError("Unsupported v2 article category: " + category)
        if is_review(row):
            review_rows.append(row)
            continue
        if not row.get("public_path"):
            raise ValueError(
                "New route_version v2 article has no persisted public_path; "
                "allocate and save its immutable URL in the creation/import pipeline: "
                + str(row.get("title") or row.get("slug") or "<untitled>")
            )
        path = normalize_public_path(row["public_path"])
        if path in occupied:
            raise ValueError("Duplicate immutable public_path in category: " + path)
        occupied.add(path)

    for row in review_rows:
        prefix = CATEGORY_PREFIX[str(row["category"])]
        slug = slugify_review_title(row.get("title") or "")
        base = slug
        number = 2
        path = "/" + prefix + "/" + slug
        while path in occupied:
            suffix = "-" + str(number)
            slug = base[:68-len(suffix)].rstrip("-") + suffix
            path = "/" + prefix + "/" + slug
            number += 1
        row["public_slug"] = slug
        row["public_path"] = path
        occupied.add(path)

    for row in rows:
        if not isinstance(row, dict) or not is_v2(row) or row.get("legacy_path") or is_review(row):
            continue
        row["public_path"] = normalize_public_path(row["public_path"])
    return rows
