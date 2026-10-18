#!/usr/bin/env python3
"""Regression: every editorial news box picks newer genuine posts before older."""
import importlib.util
from pathlib import Path
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
def load(path, name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

home=load("scripts/refresh-home-editorial-boxes.py","zt_editorial_refresh")
sidebar=load("scripts/zt_sidebar_mix.py","zt_sidebar_recommend")

stories=[
    {"url":"/old15.html","date":"ZazoomTek · 15 ottobre 2026"},
    {"url":"/new17.html","date":"ZazoomTek · 17 ottobre 2026"},
    {"url":"/mid16.html","date":"ZazoomTek · 16 ottobre 2026"},
    {"url":"/new18.html","date":"ZazoomTek · 2026-10-18"},
    {"url":"/mid16b.html","published_at":"2026-10-16T13:02:29Z"},
]
expected=["/new18.html","/new17.html","/mid16b.html","/mid16.html","/old15.html"]
for order in (stories, list(reversed(stories)),stories[1:]+stories[:1]):
    fresh=home.choose(order,5,date(2026,10,18))
    side=sidebar.rotated(order,"news.html","featured",count=5,bucket=99999)
    assert [p["url"] for p in fresh]==expected, ("Home selection",fresh)
    assert [p["url"] for p in side]==expected, ("Sidebar selection",side)
assert [p["url"] for p in home.choose(stories,2,date(2026,10,19))] == expected[:2]
excluded=sidebar.rotated(stories,"news.html","news",count=4,excluded={"/new18.html"})
assert excluded[0]["url"]=="/new17.html" and excluded[1]["url"]=="/mid16b.html"
assert [p["url"] for p in sidebar.rotated(stories,"a","news",count=3,bucket=1)] == [p["url"] for p in sidebar.rotated(stories,"b","news",count=3,bucket=9999)]
assert home.publication_key({"date":"ZazoomTek · 16 ottobre 2026"})>home.publication_key({"date":"ZazoomTek · 15 ottobre 2026"})
print("PASS: today > yesterday > older; stable dates, no random page/24-hour jumps, no duplicates")
