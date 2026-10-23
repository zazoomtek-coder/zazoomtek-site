#!/usr/bin/env python3
"""Independent ZazoomTek component, intended for isolated build workspace.

Does not deploy to Cloudflare. No editorial approvals or central Master gateway.
"""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
def run(script,*args):
    subprocess.run([sys.executable,str(ROOT/"scripts"/script),*args],cwd=ROOT,check=True)
if __name__=="__main__":
    run("update-youtube-posts.py")
