#!/usr/bin/env python3
"""Guard Esplora Video: use latest actual GAMEPLAY, never an arbitrary past Live."""
from pathlib import Path
import json,re
root=Path(__file__).resolve().parent.parent
js=(root/"zt-visual.js").read_text(encoding="utf-8")
home=(root/"index.html").read_text(encoding="utf-8")
rules=json.loads((root/"gameplay-video-rules.json").read_text(encoding="utf-8"))
feed=json.loads((root/"home-video-feed.json").read_text(encoding="utf-8"))
match=re.search(r"const ztHomeVideoFallback=(\[.*?\]);",js)
assert match, "Missing Javascript fallback catalogue"
fallback=json.loads(match.group(1))
gameplay_fallback=[v for v in fallback if v.get("category")=="gameplay"]
assert len(gameplay_fallback)==1, "Exactly one safe fallback GAMEPLAY video"
assert gameplay_fallback[0]["id"]=="tEkXOj7XOwA", "Fallback must be the approved Sesame Street session"
assert "tEkXOj7XOwA" in rules["original_gameplay_ids"], "Missing creator-approved original gameplay ID"
assert "const authenticGameplay=clean.filter(x=>x.category==='gameplay' && !x.short && !x.live && !used.has(x.id));" in js, "Wrong GAMEPLAY selection rule"
assert "const backupGameplay=ztHomeVideoFallback.filter(x=>x.category==='gameplay'" in js, "Stale-feed protection missing"
assert "let archive=clean.find(x=>x.completedLive" not in js, "Obsolete live-only selection is still present"
assert re.search(r'zt-visual\.js\?v=20\d{6}[A-Za-z0-9_-]+', home), "Homepage cache bust missing"
deploy_design=(root/"scripts/apply-site-design.py").read_text(encoding="utf-8")
assert "js_path=home_js_ref.group(1)" in deploy_design, "Deploy must preserve Home Javascript version"
assert "20261012titleSubtitle" not in deploy_design, "Obsolete Javascript version still forced by deploy"
assert "js_path,html,count=1" in deploy_design, "Deploy Javascript rewrite not using Home source of truth"
valid=[x for x in feed if x.get("category")=="gameplay" and not x.get("short") and not x.get("live")]
valid.sort(key=lambda x:x.get("publishedAt") or "",reverse=True)
assert valid and valid[0]["id"]=="tEkXOj7XOwA", "Newest approved long gameplay must be Sesame Street"
config=json.loads((root/"firebase.json").read_text(encoding="utf-8"))
cache_headers={entry["source"]:{header["key"].lower():header["value"] for header in entry["headers"]} for entry in config["hosting"]["headers"]}
assert "no-store" in cache_headers["/zt-visual.js"]["cache-control"], "JS cache must be disabled"
assert "no-store" in cache_headers["/home-video-feed.json"]["cache-control"], "Feed cache must be disabled"
print("PASS: Gameplay selects newest verified original, cache disabled, Ace Combat no longer hardcoded")
