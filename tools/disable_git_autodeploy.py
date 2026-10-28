#!/usr/bin/env python3
"""One-time, non-deploying enforcement of Cloudflare Pages Git-build controls."""
import json, os, sys, urllib.request, urllib.error

ACCOUNT = os.environ["CF_ACCOUNT"]
TOKEN = os.environ["CF_TOKEN"]
PROJECT = "zazoomtek-site"
URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT}/pages/projects/{PROJECT}"

def request(method, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Authorization": "Bearer " + TOKEN, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(URL, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = json.load(response)
    except urllib.error.HTTPError as err:
        details = err.read(800).decode("utf-8", "replace")
        raise RuntimeError(f"Cloudflare Pages API {method} failed: status {err.code}: {details}") from err
    if not raw.get("success"):
        raise RuntimeError("Cloudflare Pages API returned an error: " + repr(raw.get("errors")))
    return raw["result"]

project = request("GET")
if project.get("name") != PROJECT:
    raise RuntimeError("Unexpected Pages project; no change made")
source = project.get("source")
if not source or not isinstance(source, dict):
    print("No Pages Git source configured; direct Wrangler deployment is independent.")
    sys.exit(0)
provider = source.get("type")
if provider not in ("github", "gitlab"):
    print("No active supported Git integration; found:", provider)
    sys.exit(0)
config = source.get("config") or {}
print("Before: provider", provider, "| production automatic", config.get("production_deployments_enabled"), "| preview mode", config.get("preview_deployment_setting"))
if config.get("production_deployments_enabled") is not False or config.get("preview_deployment_setting") != "none":
    request("PATCH", {"source": {"type": provider, "config": {
        "production_deployments_enabled": False,
        "preview_deployment_setting": "none",
        "deployments_enabled": False
    }}})
updated = request("GET")
newsource = updated.get("source") or {}
newconfig = newsource.get("config") or {}
print("After: production automatic", newconfig.get("production_deployments_enabled"), "| preview mode", newconfig.get("preview_deployment_setting"))
if newconfig.get("production_deployments_enabled") is not False or newconfig.get("preview_deployment_setting") != "none":
    raise RuntimeError("Git auto-deploy disable not confirmed; review project settings")
print("CONFIRMED: Git auto production and preview deploys are disabled. Wrangler direct deployments remain available.")
