#!/usr/bin/env python3
"""Offline-only tests: no deployment, no GitHub writes, no live-site mutation."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import editorial_slot_gate as gate
import verify_live_release as live

rome=ZoneInfo("Europe/Rome")
assert gate.event_slot(datetime(2026,10,29,19,21,tzinfo=rome)).hour==19
assert gate.event_slot(datetime(2026,10,29,19,38,tzinfo=rome)).hour==19
assert gate.event_slot(datetime(2026,10,29,19,46,tzinfo=rome)) is None
assert gate.event_slot(datetime(2027,6,1,12,38,tzinfo=rome)).hour==12
print("RELEASE WINDOW: primary and late recovery, CET and CEST OK",flush=True)

original=gate.digest()
target=Path(__file__).resolve().parents[1]/"assets/js/site.js"
old=target.read_bytes()
try:
 target.write_bytes(old+b"\n// fingerprint test only\n")
 assert original!=gate.digest(),"site.js must trigger next approved release"
finally:
 target.write_bytes(old)
assert original==gate.digest(),"Restoring unchanged JS must restore digest"
print("FINGERPRINT: approved site.js modifications trigger release",flush=True)

# Regression test: verify_live_release validates local HTML AND byte-for-byte CSS.
index=(live.DIST/"index.html").read_bytes()
css=(live.DIST/"assets/css/spotnews.css").read_bytes()
original_get=live.get
try:
 def good(url,timeout=16):
  return css if "/assets/css/spotnews.css" in url else index
 live.get=good
 live.verify()
 def wrong(url,timeout=16):
  return css+b"wrong" if "/assets/css/spotnews.css" in url else index
 live.get=wrong
 live.MAX_ATTEMPTS=1
 try:
  live.verify()
 except RuntimeError as err:
  assert "cannot be confirmed" in str(err),err
 else:
  raise AssertionError("Mismatched public CSS was accepted")
finally:
 live.get=original_get
print("LIVE VERIFIER: matching CSS accepted, wrong CSS refused",flush=True)
