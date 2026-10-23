#!/usr/bin/env python3
"""Offline check of Cloudflare Pages real Wrangler deploy invocation.

No actual network transfer; the isolated deployment to Cloudflare's preview
branch will be separately exercised before any production merge.
"""
import importlib.util,os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("publisher",HERE/"10-cloudflare-publish.py")
publisher=importlib.util.module_from_spec(spec);spec.loader.exec_module(publisher)

def main():
    with TemporaryDirectory() as temp:
        directory=Path(temp);(directory/"index.html").write_text("<html>Home</html>")
        with patch.dict(os.environ,{"CLOUDFLARE_API_TOKEN":"test",
                                    "CLOUDFLARE_ACCOUNT_ID":"test"}):
            with patch.object(publisher.subprocess,"run") as run:
                publisher.publish(directory,project="test-project",
                                  branch="zt-services10-review")
                run.assert_called_once()
                args=run.call_args.args[0]
                assert "wrangler@3" in args
                assert "pages" in args and "deploy" in args
                assert "--project-name=test-project" in args
                assert "--branch=zt-services10-review" in args
                assert "--branch=main" not in args
            with patch.object(publisher.subprocess,"run") as run:
                publisher.publish(directory,project="test-project",
                                  branch="zt-services10-review",dry_run=True)
                run.assert_not_called()
        try:
            publisher.publish(directory/"missing",project="test-project",
                              branch="zt-services10-review",dry_run=True)
        except RuntimeError:
            pass
        else:
            raise AssertionError("Expected detection of missing HTML build")
    print("PASS: Cloudflare preview uses real Wrangler deploy command; no production upload")

if __name__=="__main__":
    main()
