#!/usr/bin/env python3
"""Structural checks for all five fixed Europe/Rome publishing slots."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/services10-scheduled-cloudflare.yml"

def main():
    source=WORKFLOW.read_text(encoding="utf-8")
    expected=["15 10 * * *","45 12 * * *","15 15 * * *",
              "45 17 * * *","15 20 * * *"]
    found=re.findall(r'^\s+- cron: ["\x27]([^"\x27]+)["\x27]\s*$',source,re.M)
    assert found==expected,(found,expected)
    assert len(re.findall(r'^\s+timezone:\s*["\x27]?Europe/Rome',source,re.M))==5
    assert "services10/01-community.py" in source
    assert "services10/02-video-16x9.py" in source
    assert "services10/03-home.py" in source
    assert "services10/09-layout.py" in source
    assert "services10/10-cloudflare-publish.py" in source
    expected_workflows={"services10-offline-tests.yml","services10-scheduled-cloudflare.yml",
                        "manual-direct-publish.yml","cloudflare-site-health.yml"}
    present={f.name for f in WORKFLOW.parent.glob("*.yml")}
    assert present==expected_workflows, ("Unexpected legacy workflow remains",present)
    assert "scripts/cloudflare-build-site.py" not in source
    assert "--branch main --production" in source
    assert "uses: actions/download-artifact@v4" in source
    manual=(WORKFLOW.parent/"manual-direct-publish.yml").read_text(encoding="utf-8")
    assert "branches: [main]" in manual
    assert "scripts/cloudflare-build-site.py" not in manual
    assert "master-orchestrator" not in manual
    assert "--branch main --production" in manual
    assert "cloudflare-purge-after-release.py" in manual
    assert "needs.video.result != 'success'" in source, "Video source must not block production"
    print("PASS: five Rome slots, fail-soft videos, independent Cloudflare production and direct manual")

if __name__=="__main__":
    main()
