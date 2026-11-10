#!/usr/bin/env python3
"""Optional source-grounded SEO metadata enrichment for new Community imports."""
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DATA = Path(__file__).resolve().parents[1] / "data"
API_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"
TIMEOUT_SECONDS = 25


def _plain(value):
    value = re.sub(r"<[^>]*>", " ", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()


def _valid_text(value, minimum, maximum):
    return isinstance(value, str) and minimum <= len(_plain(value)) <= maximum


def validate_result(result, post):
    if not isinstance(result, dict):
        raise ValueError("SEO response must be a JSON object")
    seo_title = _plain(result.get("seo_title"))
    description = _plain(result.get("meta_description"))
    primary = _plain(result.get("primary_keyword"))
    related = result.get("related_keywords")
    if not _valid_text(seo_title, 15, 60):
        raise ValueError("SEO title must contain 15–60 characters")
    if not _valid_text(description, 70, 155):
        raise ValueError("Meta description must contain 70–155 characters")
    if not _valid_text(primary, 2, 80):
        raise ValueError("Primary keyword is missing or invalid")
    if not isinstance(related, list) or not 2 <= len(related) <= 4:
        raise ValueError("Expected 2–4 related keywords")
    related = [_plain(item) for item in related]
    if any(not _valid_text(item, 2, 60) for item in related):
        raise ValueError("A related keyword is invalid")
    if len({item.casefold() for item in related + [primary]}) != len(related) + 1:
        raise ValueError("SEO keywords must be unique")
    corpus = (_plain(post.get("title")) + " " + _plain(post.get("text"))).casefold()
    if not all(token.casefold() in corpus for token in primary.split() if len(token) > 2):
        raise ValueError("Primary keyword is not grounded in the source")
    for phrase in related:
        if not all(token.casefold() in corpus for token in phrase.split() if len(token) > 2):
            raise ValueError("A related keyword is not grounded in the source")
    has_image = bool(post.get("image") or post.get("images"))
    image_alt = _plain(result.get("image_alt"))
    if has_image and not _valid_text(image_alt, 5, 160):
        raise ValueError("Image ALT is required for an existing image")
    if not has_image:
        image_alt = ""
    return {
        "seo_title": seo_title,
        "meta_description": description,
        "primary_keyword": primary,
        "related_keywords": related,
        **({"image_alt": image_alt} if image_alt else {}),
    }


def _request_metadata(post, api_key, model):
    title = _plain(post.get("title"))
    body = _plain(post.get("text"))[:9000]
    has_image = bool(post.get("image") or post.get("images"))
    prompt = (
        "Sei un SEO editor italiano per ZazoomTek. Crea SOLO metadati SEO per la pagina "
        "web che pubblicherà questo post YouTube Community. NON riscrivere il testo, "
        "NON aggiungere sezioni o fatti e NON dichiarare verifiche non fornite. "
        "Usa esclusivamente titolo e testo sorgente. Mantieni nomi, numeri, date e significato. "
        "Restituisci un JSON con seo_title (15-60 caratteri), meta_description (70-155 caratteri), "
        "primary_keyword (frase breve presente nel contenuto), related_keywords (2-4 frasi "
        "pertinenti e supportate dal testo)"
        + (", image_alt (5-160 caratteri, descrive solo l'immagine esistente)" if has_image else "")
        + ". Evita keyword stuffing, formule generiche e informazioni non presenti. Lingua italiana.\n\n"
        + "TITOLO ORIGINALE:\n" + title + "\n\nTESTO ORIGINALE:\n" + body
    )
    payload = {
        "model": model, "temperature": 0.2, "max_tokens": 450,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Rispondi esclusivamente con JSON valido. Non modificare il contenuto sorgente."},
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        API_URL, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        raw = response.read(100000).decode("utf-8")
    envelope = json.loads(raw)
    content = envelope["choices"][0]["message"]["content"]
    return validate_result(json.loads(content), post)


def optimize_new_community_posts(before_ids, path=None, environ=None):
    """Enrich new complete Community records and retry pending ones; all errors fail open."""
    env = os.environ if environ is None else environ
    target = Path(path) if path else DATA / "community_imported.json"
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
        posts = document.get("posts")
        if not isinstance(posts, list):
            raise ValueError("Invalid Community import document")
    except Exception as exc:
        print("SEO AI skipped: cannot read Community data:", type(exc).__name__, flush=True)
        return {"optimized": 0, "skipped": 0, "failed": 1, "reason": "invalid_input"}

    known = {str(item) for item in before_ids}
    api_key = str(env.get("OPENAI_API_KEY") or "").strip()
    stats = {"optimized": 0, "skipped": 0, "failed": 0}
    changed = False
    eligible = []
    for post in posts:
        if not isinstance(post, dict):
            continue
        post_id = str(post.get("id") or "")
        is_new = bool(post_id and post_id not in known)
        if not post_id or not (is_new or post.get("seo_pending")):
            continue
        if not post.get("text_complete") or not isinstance(post.get("text"), str) or len(post["text"]) < 60:
            stats["skipped"] += 1
            continue
        if isinstance(post.get("seo"), dict) and post.get("seo_optimized_at"):
            post.pop("seo_pending", None)
            changed = True
            stats["skipped"] += 1
            continue
        eligible.append(post)

    if not api_key:
        for post in eligible:
            if not post.get("seo_pending"):
                post["seo_pending"] = True
                changed = True
        if changed:
            temporary = target.with_name(target.name + ".seo-tmp")
            temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temporary.replace(target)
        print("SEO AI skipped: OPENAI_API_KEY not configured; new posts remain pending", flush=True)
        stats["skipped"] += len(eligible)
        stats["reason"] = "missing_api_key"
        return stats

    model = str(env.get("ZAZOOMTEK_SEO_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    for post in eligible:
        post_id = str(post.get("id") or "")
        try:
            post["seo"] = _request_metadata(post, api_key, model)
            post["seo_optimized_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            post.pop("seo_pending", None)
            stats["optimized"] += 1
            changed = True
            print("SEO AI optimized Community post:", post_id, flush=True)
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError,
                KeyError, IndexError, TypeError) as exc:
            post["seo_pending"] = True
            changed = True
            stats["failed"] += 1
            print("SEO AI failed open for Community post:", post_id,
                  type(exc).__name__, str(exc)[:150], flush=True)
        except Exception as exc:
            post["seo_pending"] = True
            changed = True
            stats["failed"] += 1
            print("SEO AI unexpected failure; source preserved:", post_id,
                  type(exc).__name__, str(exc)[:150], flush=True)
    if changed:
        temporary = target.with_name(target.name + ".seo-tmp")
        temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(target)
    return stats
