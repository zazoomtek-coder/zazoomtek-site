#!/usr/bin/env python3
"""Canonical visible headlines for ZazoomTek without removing editorial content.

Classification remains in a separate category field. These prefixes are
service labels, never part of the article or video title. Only LEADING labels
are removed; inner mentions of "News Tech" remain untouched.
"""
from __future__ import annotations
import html
import re

PREFIX=re.compile(
    r"^\s*(?:\*{1,2}|#{1,3}\s*)?"
    r"(?:(?:news|notizie)\s*[-–—:]?\s*)?"
    r"(?:tech\s+impact|gaming\s+inside|inside\s+the\s+game|tech\s+in\s+back|"
    r"speciali|speciale|extra|gaming|tech|recensioni|review|reviews)"
    r"\s*[:\-–—|]\s*",
    re.I)
NEWS=re.compile(r"^\s*(?:\*{1,2})?news\s*[:\-–—|]\s*",re.I)

def clean_title(value:str)->str:
    if not value:return ""
    candidate=html.unescape(str(value)).strip()
    for _ in range(3):
        original=candidate
        candidate=PREFIX.sub("",candidate,count=1)
        candidate=NEWS.sub("",candidate,count=1)
        if candidate==original:break
    # Remove Markdown wrappers, never ordinary punctuation or internal words.
    candidate=candidate.strip().strip("*").strip()
    return candidate or html.unescape(str(value)).strip()
