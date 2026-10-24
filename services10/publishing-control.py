#!/usr/bin/env python3
"""ZazoomTek publishing override: import continues, scheduled release can pause.

The ONLY persistent switch is services10/automation-control.json on main.
"Ci penso io" => publishing="manual"; editor approval => "automatic".
This gate checks remote main immediately before a production deploy, so a
manual stop given while a long job is running still takes effect.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG="services10/automation-control.json"

def read_config():
    local=json.loads((ROOT/CONFIG).read_text(encoding="utf-8"))
    if local.get("publishing") not in ("automatic","manual"):
        raise ValueError("Invalid publishing control mode")
    return local

def latest_config():
    if not os.environ.get("GITHUB_ACTIONS"):
        return read_config()
    # Fetch only the current control file's ref, not the whole repository.
    fetched=subprocess.run(
        ["git","fetch","--quiet","origin","refs/heads/main"],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=40)
    if fetched.returncode:
        raise RuntimeError("Unable to verify the current manual stop on main")
    shown=subprocess.run(
        ["git","show","FETCH_HEAD:"+CONFIG],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15)
    if shown.returncode:
        raise RuntimeError("Production control missing from main")
    config=json.loads(shown.stdout)
    if config.get("publishing") not in ("automatic","manual"):
        raise ValueError("Invalid remote publishing mode")
    return config

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--github-output",action="store_true")
    args=parser.parse_args()
    try:
        cfg=latest_config()
        ready=(cfg["publishing"]=="automatic")
        reason="automatic_slot" if ready else "editor_manual_hold"
    except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
        # Never override a potential editor stop when the control cannot
        # be verified. YouTube ingestion and local rendering remain unaffected.
        ready=False
        reason="manual_stop_verification_unavailable"
        print("Release gate cannot verify control:",type(error).__name__,file=sys.stderr)
    if args.github_output:
        target=os.getenv("GITHUB_OUTPUT")
        if not target:
            raise RuntimeError("GITHUB_OUTPUT missing")
        with open(target,"a",encoding="utf-8") as file:
            file.write("publish="+("true" if ready else "false")+"\n")
            file.write("reason="+reason+"\n")
    print("ZazoomTek publication gate:",reason,"publish:",ready)
    return 0

if __name__=="__main__":
    sys.exit(main())
