#!/usr/bin/env python3
"""Independent YouTube pipeline guard: never allow a release without both live YouTube sources."""
import ast
import re
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "tools/scheduled_editorial_import.py"],
    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
print(result.stdout, end="", flush=True)
if result.returncode:
    raise SystemExit("IMPORT FAILED: scheduled editorial importer returned " + str(result.returncode))
match = re.search(r"^LIVE SOURCES:\s*(\{.*\})\s*$", result.stdout, re.MULTILINE)
if not match:
    raise SystemExit("IMPORT FAILED: source status receipt missing; refusing publication")
try:
    status = ast.literal_eval(match.group(1))
except (ValueError, SyntaxError):
    raise SystemExit("IMPORT FAILED: source status receipt is invalid")
if status.get("videos") is not True or status.get("community") is not True:
    raise SystemExit("IMPORT FAILED: both YouTube video RSS and Community import must succeed; got " + repr(status))
print("YOUTUBE IMPORT VERIFIED: video RSS and Community both succeeded.", flush=True)
