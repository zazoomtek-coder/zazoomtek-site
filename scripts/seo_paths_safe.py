"""Shared safe path selection for all present and future ZazoomTek sections.

Only published-looking static HTML with its own canonical URL is eligible.
Never traverse dependency, data, tooling, draft, asset or preview folders.
"""
from pathlib import Path
from urllib.parse import quote

ORIGIN = "https://zazoomtek.it"
SKIP_DIRS = {
    ".git", ".github", ".venv", "__pycache__", "node_modules",
    "functions", "scripts", "assets", "tests", "test", "coverage",
    "tmp", "temp", "drafts", "staging", "backups", "backup",
}
SKIP_FILES = {"404.html", "googlea3c594e14c6f832d.html", "nba-2k27-recensione-ps5.html"}

def html_pages(root):
    root = Path(root)
    for page in sorted(root.rglob("*.html")):
        try:
            rel = page.relative_to(root)
        except ValueError:
            continue
        if not page.is_file() or page.name in SKIP_FILES:
            continue
        if page.name.startswith(("preview-", "anteprima-", "draft-")):
            continue
        if any(part.startswith(".") or part.lower() in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if page.name.startswith("."):
            continue
        yield page

def canonical_candidates(root, page):
    rel = page.relative_to(root)
    # Canonicals must name exactly the static content. Do not infer rewrites.
    raw = "/".join(quote(p, safe="-._~") for p in rel.parts)
    full = ORIGIN + "/" + raw
    if page.name == "index.html":
        directory = "/".join(quote(p, safe="-._~") for p in rel.parts[:-1])
        shortcut = ORIGIN + "/" + (directory + "/" if directory else "")
        return {shortcut, full}
    return {full}
