"""Separate release-critical new/v2 content checks from historical diagnostics."""
import json
from pathlib import Path

MANIFEST = ".editorial-import-manifest.json"


def imported_ids(project_root):
    path = Path(project_root) / MANIFEST
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload.get("strict_ids", [])
        return {str(value) for value in values if value}
    except (OSError, ValueError, TypeError, AttributeError):
        return set()


def row_ids(row):
    if not isinstance(row, dict):
        return set()
    return {str(row.get(key)) for key in ("id", "source_post_id") if row.get(key)}


def is_release_critical(row, strict_ids=()):
    """V2 routes are always strict; legacy rows are strict only when just imported."""
    version = row.get("route_version") if isinstance(row, dict) else None
    return version in (2, "2", "v2") or bool(row_ids(row) & set(strict_ids))


def record_issue(errors, warnings, message, critical):
    (errors if critical else warnings).append(message)
