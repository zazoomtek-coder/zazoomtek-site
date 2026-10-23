#!/usr/bin/env python3
"""Check that archives survive Actions job restarts and concurrent Git writes.

All tests use a temporary local bare Git remote, never GitHub production.
"""
import importlib.util
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("data_archive", ROOT / "state.py")
state = importlib.util.module_from_spec(spec)
spec.loader.exec_module(state)

def git(root, *cmd, capture=False):
    result = subprocess.run(["git", *cmd], cwd=root, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.stdout.decode() if capture else None

def main():
    with TemporaryDirectory() as folder:
        parent = Path(folder)
        remote = parent / "remote.git"
        local = parent / "worker"
        second = parent / "other-worker"
        local.mkdir()
        git(parent, "init", "--bare", str(remote))
        git(local, "init")
        git(local, "config", "user.name", "Test User")
        git(local, "config", "user.email", "ci@example.test")
        git(local, "commit", "--allow-empty", "-m", "base")
        git(local, "remote", "add", "origin", str(remote))
        git(local, "push", "origin", "HEAD:refs/heads/zt-services10-state")
        state.ROOT = local
        data = local / "services10-data" / "videos.json"
        data.parent.mkdir(parents=True)
        data.write_text(json.dumps([{"id": "video1", "title": "First", "type": "landscape_video"}]))
        state.save("videos")
        response = git(local, "show",
                       "refs/remotes/origin/zt-services10-state:services10-data/videos.json",
                       capture=True)
        assert {x["id"] for x in json.loads(response)} == {"video1"}

        git(parent, "clone", "--branch", "zt-services10-state", str(remote), str(second))
        git(second, "config", "user.name", "Other User")
        git(second, "config", "user.email", "ci@example.test")
        other_data = second / "services10-data" / "videos.json"
        other_data.write_text(json.dumps([{"id": "video1", "title": "First"},
                                          {"id": "video2", "title": "Second"}]))
        git(second, "add", "services10-data/videos.json")
        git(second, "commit", "-m", "another writer")
        git(second, "push", "origin", "HEAD:refs/heads/zt-services10-state")

        data.write_text(json.dumps([{"id": "video3", "title": "Third"}]))
        state.save("videos")
        git(local, "fetch", "origin", "zt-services10-state")
        combined = json.loads(git(local, "show", "FETCH_HEAD:services10-data/videos.json",
                                  capture=True))
        assert {x["id"] for x in combined} == {"video1", "video2", "video3"}

        data.unlink()
        state.restore("videos")
        assert {x["id"] for x in json.loads(data.read_text())} == {
            "video1", "video2", "video3"}

        community = local / "services10-data" / "community.json"
        community.write_text(json.dumps([{"id": "post1", "title": "News"}]))
        state.save("community")
        git(local, "fetch", "origin", "zt-services10-state")
        assert json.loads(git(local, "show",
                              "FETCH_HEAD:services10-data/community.json",
                              capture=True))[0]["id"] == "post1"
        assert len(json.loads(git(local, "show",
                                 "FETCH_HEAD:services10-data/videos.json",
                                 capture=True))) == 3
    print("PASS: Git archival restore, concurrent writer merge and isolated datasets")

if __name__ == "__main__":
    main()
