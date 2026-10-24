#!/usr/bin/env python3
"""Put an actual, visible Studio Modifica link in every interior HTML H1.

The editorial link is public. Studio's existing GitHub authentication controls
read/write access; no tokens or permissions are exposed in article HTML.
No reliance on localStorage or dynamic JavaScript for button visibility.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
TAG = '<script src="/studio/edit-button.js?v=20261024_visible" defer></script>'
SCRIPT_PATTERN = re.compile(
    r'<script\b[^>]*\bsrc=["\']/studio/edit-button\.js(?:\?[^"\']*)?["\'][^>]*></script>',
    re.I
)
H1_PATTERN = re.compile(r"(?is)<h1\b[^>]*>.*?</h1>")
MARKER = 'id="zt-studio-edit-title"'
STYLE = ('display:inline-flex;align-items:center;justify-content:center;gap:5px;'
         'margin:12px 0 18px;padding:10px 16px;min-height:38px;'
         'background:#202020;color:#fff!important;border:0;'
         'border-left:5px solid #d51232;border-radius:0;'
         'text-decoration:none;font:800 13px/1.2 Arial,Helvetica,sans-serif')


def inject(root: Path = ROOT) -> int:
    count = 0
    if not (root / "studio/edit-button.js").is_file():
        print("Studio client file missing; not editing any articles")
        return 0

    for page in root.rglob("*.html"):
        relative = page.relative_to(root).as_posix()
        if (relative == "index.html" or relative.startswith(
                ("dist/", "studio/", ".github/")) or
                "node_modules/" in relative or "/dist/" in relative):
            continue
        try:
            document = page.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        if "</body>" not in document.lower():
            continue
        if not ("<main" in document.lower() or "<article" in document.lower()):
            continue

        updated = document
        heading = H1_PATTERN.search(updated)
        if heading and MARKER not in updated:
            path = quote(relative, safe="")
            link = ('<a id="zt-studio-edit-title" class="zt-studio-edit-entry" '
                    'href="/studio/?edit=' + html.escape(path, quote=True) +
                    '" aria-label="Modifica questa pagina in ZazoomTek Studio" '
                    'style="' + STYLE + '">✎ Modifica</a>')
            updated = updated[:heading.end()] + "\n" + link + updated[heading.end():]

        # Replace old/cached JS tag(s) and install exactly one versioned
        # fallback beside the static button. JS is never required for visibility.
        updated = SCRIPT_PATTERN.sub("", updated)
        updated = re.sub(r"</body>", lambda _: TAG + "\n</body>", updated,
                         count=1, flags=re.I)

        if updated != document:
            page.write_text(updated, encoding="utf-8")
            count += 1
    print("Studio visible Modifica entry linked in", count,
          "interior pages; GitHub authentication remains in Studio")
    return count


if __name__ == "__main__":
    inject()
