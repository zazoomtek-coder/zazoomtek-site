#!/usr/bin/env python3
"""Save the LAST VERIFIED production revision, never the pending unshipped HEAD.

Before a scheduled Cloudflare deploy:
- read the previous SUCCESSFUL receipt and its deployed source commit
- on legacy receipts use the independently verified 29 Oct baseline branch
- store an immutable named Git backup branch with that exact source commit
- write a real ZIP of source, assets, and editorial JSON for external retention

The archive is a Git snapshot, not a Cloudflare deployment. Rollbacks also
require redeploying it with the release tools, and live verification.
"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import os
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BASELINE="backup/production-live-exact-20261029-1930"
ROME=ZoneInfo("Europe/Rome")


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT,text=True).strip()


def receipt():
    with (ROOT/"data/editorial_release_state.json").open(encoding="utf-8") as f:
        obj=json.load(f)
    if not obj.get("finished_at"):
        raise ValueError("No confirmed production receipt; backup refused")
    return obj


def confirmed_commit():
    state=receipt()
    sha=state.get("deployed_commit")
    if sha:
        if not re.fullmatch(r"[a-f0-9]{40}",sha):
            raise ValueError("Invalid deployed_commit in release receipt")
        subprocess.run(["git","fetch","--no-tags","origin",sha],
                       cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    else:
        # Baseline was created explicitly after verifying the successful
        # 19:30 deployment; do NOT replace it with HEAD (which can be queued).
        git("fetch","--no-tags","origin",
            "refs/heads/"+BASELINE+":refs/remotes/origin/"+BASELINE)
        sha=git("rev-parse","refs/remotes/origin/"+BASELINE)
    git("cat-file","-e",sha+"^{commit}")
    return sha


def main():
    mode=sys.argv[1] if len(sys.argv)>1 else "inspect"
    if mode not in ("inspect","backup","backup-manual"):
        raise SystemExit("Usage: release_backup.py inspect|backup")
    state=receipt()
    sha=confirmed_commit()
    if mode=="inspect":
        print("LAST VERIFIED RELEASE",state["slot"],"COMMIT",sha,flush=True)
        return
    target=(datetime.now(ROME).isoformat() if mode=="backup-manual"
            else os.environ.get("EDITORIAL_TARGET"))
    if not target:
        raise ValueError("No editorial slot to attach the backup to")
    slot=datetime.fromisoformat(target).astimezone(ROME)
    if mode!="backup-manual" and (slot.hour not in (12,19) or slot.minute!=30):
        raise ValueError("Unexpected release slot")
    name=("backup/predeploy-manual-"+slot.strftime("%Y%m%d-%H%M%S")
          if mode=="backup-manual" else
          "backup/predeploy-"+slot.strftime("%Y%m%d-%H%M")+"-"+sha[:12])
    # Idempotent: a second runner using the same slot must not overwrite it.
    remote=subprocess.run(["git","ls-remote","--heads","origin",name],
                          cwd=ROOT,check=True,capture_output=True,text=True).stdout.strip()
    if remote:
        if not remote.split()[0]==sha:
            raise RuntimeError("Existing backup branch does not match verified release")
    else:
        git("push","origin",sha+":refs/heads/"+name)
    zip_name="ZazoomTek_WORKING_BACKUP_"+slot.strftime("%Y%m%d_%H%M%S")+".zip"
    artifact=ROOT/zip_name
    subprocess.run(["git","archive","--format=zip","--output="+str(artifact),sha],
                   cwd=ROOT,check=True)
    import zipfile
    with zipfile.ZipFile(artifact) as z:
        names=set(z.namelist())
        needed={"tools/build.py","tools/editorial_slot_gate.py",
                "data/community_imported.json","data/videos.json",
                "assets/css/spotnews.css","assets/js/site.js"}
        assert needed.issubset(names),needed-names
        assert z.testzip() is None
        print("VERIFIED SOURCE BACKUP",name,sha,len(names),
              "files",artifact.stat().st_size,"bytes",flush=True)
    with (ROOT/"data/backup-verification.txt").open("w",encoding="utf-8") as f:
        f.write("PREVIOUS SUCCESSFUL RELEASE\n"+state["slot"]+
                "\nSOURCE SHA\n"+sha+"\nGITHUB BACKUP BRANCH\n"+name+"\n")
    with (ROOT/"data/backup-file-path.txt").open("w",encoding="utf-8") as f:
        f.write(zip_name+"\n")


if __name__=="__main__":
    main()
