"""Normalize editorial class labels at the start of imported article titles.

Only known category prefixes are removed; the headline itself is preserved.
"""
import re

_PREFIX = re.compile(
    r"^\s*(?:NEWS\s+(?:GUIDE|TECH|GAMING|SPECIALI|EXTRA)|"
    r"REVIEW\s+(?:TECH|GAMING)|RECENSIONE\s+(?:TECH|GAMING)|"
    r"GUIDE|SPECIALI|EXTRA)\s*(?:[-–—:|])\s*",
    re.IGNORECASE,
)


def clean_imported_title(value):
    if not isinstance(value, str):
        return value
    return _PREFIX.sub("", value, count=1).strip()
