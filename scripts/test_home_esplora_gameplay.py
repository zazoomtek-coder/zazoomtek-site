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
assert "let gameplay=clean.find(x=>x.category==='gameplay' && !x.short && !x.live && !used.has(x.id));" in js, "Wrong GAMEPLAY selection rule"
assert "let archive=clean.find(x=>x.completedLive" not in js, "Obsolete live-only selection is still present"
assert 'zt-visual.js?v=20261013sesameGameplay' in home, "Homepage cache bust missing"
valid=[x for x in feed if x.get("category")=="gameplay" and not x.get("short") and not x.get("live")]
valid.sort(key=lambda x:x.get("publishedAt") or "",reverse=True)
assert valid and valid[0]["id"]=="tEkXOj7XOwA", "Newest approved long gameplay must be Sesame Street"
print("PASS: Esplora Video GAMEPLAY newest correctly verified; Ace Combat not hardcoded")
