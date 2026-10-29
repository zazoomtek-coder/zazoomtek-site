#!/usr/bin/env python3
"""Studio editorial-release data tests. Never accesses Cloudflare or GitHub."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scheduled_editorial_import as pipeline


def article(slug, image, stamp):
    return {
        "slug": slug, "title": "Recensione approfondita originale ZazoomTek",
        "category": "recensioni-tech", "source": "studio-editor",
        "image": "/assets/uploads/" + slug + "/" + image,
        "body": [{"type": "paragraph", "text": "Contenuto editoriale originale. " * 20}],
        "updated_at": stamp,
    }


def test():
    public = article("nuova-recensione-prova", "a.png", "2026-10-29T14:00:00Z")
    edit = article("recensione-esistente", "b.png", "2026-10-29T14:00:00Z")
    old_edit = article("recensione-esistente", "b.png", "2026-10-28T13:00:00Z")
    unapproved = article("bozza-non-pubblicata", "c.png", "2026-10-29T14:00:00Z")
    assert pipeline._valid_studio_row(public)
    assert not pipeline._valid_studio_row({**public, "source": "draft"})
    assert not pipeline._valid_studio_row({**public, "slug": "../escape"})

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        data = base / "data"
        data.mkdir()
        (data / "studio_posts.json").write_text('{"posts":[]}', encoding="utf-8")
        (data / "studio_overrides.json").write_text(
            json.dumps({"overrides": {"recensione-esistente": old_edit}}), encoding="utf-8")
        (data / "studio_v2_drafts.json").write_text(
            json.dumps({"drafts": {unapproved["slug"]: {"record": unapproved}}}), encoding="utf-8")

        def fake_git(args, **kwargs):
            source = args[-1]
            if source == "origin/editorial-queue:data/studio_overrides.json":
                return json.dumps({"overrides": {edit["slug"]: edit}}).encode()
            if source.startswith("origin/editorial-queue:assets/uploads/"):
                if "bozza-non-pubblicata" in source:
                    raise AssertionError("Draft media must NEVER be copied")
                return b"mock-image-bytes"
            raise AssertionError("Unexpected Git operation " + str(args))

        with patch.object(pipeline, "DATA", data), \
             patch.object(pipeline, "read_queue", return_value=[public]), \
             patch.object(pipeline.subprocess, "check_output", side_effect=fake_git):
            assert pipeline.sync_studio_publications() == 2
            assert pipeline.sync_studio_assets() == 2
            assert pipeline.sync_studio_publications() == 0
            assert pipeline.sync_studio_assets() == 0
            posts = json.loads((data / "studio_posts.json").read_text())["posts"]
            overrides = json.loads((data / "studio_overrides.json").read_text())["overrides"]
            assert len(posts) == 1 and posts[0]["slug"] == public["slug"]
            assert overrides["recensione-esistente"]["updated_at"] == edit["updated_at"]
            assert not list(base.glob("assets/uploads/bozza-non-pubblicata/*"))
            assert (data / "studio_v2_drafts.json").exists()
            assert (base / "assets/uploads/nuova-recensione-prova/a.png").read_bytes() == b"mock-image-bytes"
            assert (base / "assets/uploads/recensione-esistente/b.png").read_bytes() == b"mock-image-bytes"
    print("STUDIO PUBLISH BRIDGE PASS: new+edited publication, 2 images, no drafts, idempotent, no deploy", flush=True)


if __name__ == "__main__":
    test()
