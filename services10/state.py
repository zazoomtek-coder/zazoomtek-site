#!/usr/bin/env python3
"""Durable YouTube archives stored on a GitHub data branch, never on main.

The importer remains independent from both this backup operation and deploys.
Concurrent writers retry a non-force push and merge newer archived records.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRANCH = os.environ.get("ZT_DATA_BRANCH", "zt-services10-state")
FILES = {"community": "services10-data/community.json",
         "videos": "services10-data/videos.json",
         "pending": "services10-data/pending-videos.json"}

def git(*args: str, input: bytes | None = None, env=None, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, input=input, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=check)

def union(older, newer):
    by_id = {}
    for item in (older if isinstance(older, list) else []) + (newer if isinstance(newer, list) else []):
        if isinstance(item, dict) and item.get("id"):
            by_id[str(item["id"])] = item
    return list(by_id.values())

def remote_ref():
    git("fetch", "origin", "refs/heads/" + BRANCH + ":refs/remotes/origin/" + BRANCH)
    return git("rev-parse", "refs/remotes/origin/" + BRANCH).stdout.decode().strip()

def from_branch(commit: str, path: str):
    response = git("show", f"{commit}:{path}", check=False)
    if response.returncode:
        return []
    try:
        value = json.loads(response.stdout)
        return value if isinstance(value, list) else []
    except ValueError:
        return []

def atomic_write(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                     dir=path.parent, delete=False) as file:
        json.dump(rows, file, ensure_ascii=False, indent=2)
        tmp = file.name
    os.replace(tmp, path)

def published_video_ids(commit: str) -> set[str]:
    """Reconcile approved uploads before restoring/merging pending review items."""
    local = ROOT / FILES["videos"]
    try:
        cached = json.loads(local.read_text(encoding="utf-8")) if local.is_file() else []
    except (ValueError, OSError):
        cached = []
    return {str(row["id"]) for row in union(from_branch(commit, FILES["videos"]), cached)
            if row.get("type") == "landscape_video" and row.get("id")}

def restore(kind: str):
    path = FILES[kind]
    try:
        commit = remote_ref()
        saved = from_branch(commit, path)
        if not saved and kind != "pending":
            print("No saved data for", kind)
            return
        local = ROOT / path
        existing = json.loads(local.read_text(encoding="utf-8")) if local.is_file() else []
        restored = union(saved, existing)
        if kind == "pending":
            verified = published_video_ids(commit)
            restored = [row for row in restored if row.get("id") not in verified]
        atomic_write(local, restored)
        print("Restored", kind, "records:", len(restored))
    except Exception as err:
        # A backup service outage must not stop an independent import.
        print("Archive restore unavailable, continuing:", str(err)[:180])

def save(kind: str):
    path = FILES[kind]
    local = ROOT / path
    if not local.is_file():
        print("No", kind, "changes to back up")
        return
    try:
        imported = json.loads(local.read_text(encoding="utf-8"))
        if not isinstance(imported, list):
            return
    except ValueError:
        print("Unreadable local archive; previous remote archive preserved")
        return
    for attempt in range(1, 6):
        alt_index = None
        try:
            commit = remote_ref()
            data = union(from_branch(commit, path), imported)
            if kind == "pending":
                verified = published_video_ids(commit)
                data = [row for row in data if row.get("id") not in verified]
            payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            blob = git("hash-object", "-w", "--stdin", input=payload).stdout.decode().strip()
            with tempfile.NamedTemporaryFile(prefix="zt-services10-git-index-", delete=False) as index:
                alt_index = index.name
            os.unlink(alt_index)
            env = os.environ.copy()
            env["GIT_INDEX_FILE"] = alt_index
            env["GIT_AUTHOR_NAME"] = env["GIT_COMMITTER_NAME"] = "ZazoomTek Archive"
            env["GIT_AUTHOR_EMAIL"] = env["GIT_COMMITTER_EMAIL"] = "actions@users.noreply.github.com"
            git("read-tree", commit, env=env)
            git("update-index", "--add", "--cacheinfo", "100644", blob, path, env=env)
            tree = git("write-tree", env=env).stdout.decode().strip()
            new_commit = git("commit-tree", tree, "-p", commit, "-m",
                             "Archive independent " + kind + " import", env=env).stdout.decode().strip()
            pushed = git("push", "origin", new_commit + ":refs/heads/" + BRANCH,
                         env=env, check=False)
            if pushed.returncode == 0:
                atomic_write(local, data)
                print("Saved", len(data), kind, "records to", BRANCH)
                return
            print("Archive branch moved; retry", attempt)
        except Exception as err:
            print("Archive backup attempt", attempt, "failed:", str(err)[:150])
        finally:
            if alt_index:
                try: os.unlink(alt_index)
                except OSError: pass
    print("Archive backup delayed; imported data remain in this run's artifact")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=["restore", "save"])
    parser.add_argument("kind", choices=sorted(FILES))
    options = parser.parse_args()
    if options.operation == "restore":
        restore(options.kind)
    else:
        save(options.kind)
