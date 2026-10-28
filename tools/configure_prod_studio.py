#!/usr/bin/env python3
"""Configure the missing Studio V2 Production session secret; never deploy."""
import json, os, secrets, urllib.request, urllib.error

account=os.environ["CF_ACCOUNT"]
token=os.environ["CF_TOKEN"]
url=f"https://api.cloudflare.com/client/v4/accounts/{account}/pages/projects/zazoomtek-site"

def query(method,payload=None):
 data=json.dumps(payload).encode("utf-8") if payload is not None else None
 headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
 if data is not None:headers["Content-Type"]="application/json"
 req=urllib.request.Request(url,data=data,headers=headers,method=method)
 try:
  with urllib.request.urlopen(req,timeout=25) as response:obj=json.load(response)
 except urllib.error.HTTPError as exc:
  raise RuntimeError(f"Cloudflare API {method} failed (HTTP {exc.code}); no configuration confirmed") from exc
 if not obj.get("success"):raise RuntimeError(f"Cloudflare API {method} returned failure")
 return obj["result"]

project=query("GET")
if project.get("name")!="zazoomtek-site":raise RuntimeError("Wrong Pages project")
source=(project.get("source") or {}).get("config") or {}
if source.get("production_deployments_enabled") is not False or source.get("preview_deployment_setting")!="none":
 raise RuntimeError("Cloudflare Git automatic builds are not disabled; abort")
config=((project.get("deployment_configs") or {}).get("production") or {})
variables=config.get("env_vars") or {}
entry=variables.get("STUDIO_SESSION_SECRET")
if entry and entry.get("type")=="secret_text":
 print("Studio production session secret already exists; preserving current sessions")
elif entry:
 raise RuntimeError("Studio session secret exists with unexpected type; refusing to overwrite")
else:
 # This value never appears in GitHub logs or repository files.
 value=secrets.token_urlsafe(48)
 query("PATCH",{"deployment_configs":{"production":{"env_vars":{
  "STUDIO_SESSION_SECRET":{"type":"secret_text","value":value}
 }}}})
 print("Created encrypted STUDIO_SESSION_SECRET in Cloudflare Pages Production")
updated=query("GET")
current=(((updated.get("deployment_configs") or {}).get("production") or {}).get("env_vars") or {})
status=(current.get("STUDIO_SESSION_SECRET") or {}).get("type")
if status!="secret_text":raise RuntimeError("Production secret was not confirmed after write")
cfg=(updated.get("source") or {}).get("config") or {}
if cfg.get("production_deployments_enabled") is not False or cfg.get("preview_deployment_setting")!="none":
 raise RuntimeError("Production Git build controls changed unexpectedly")
print("CONFIRMED: production secret is encrypted and Cloudflare Git auto builds remain disabled")
try:
 req=urllib.request.Request("https://zazoomtek.it/api/studio/session",headers={"Cache-Control":"no-cache"})
 try:
  with urllib.request.urlopen(req,timeout=20) as response:code=response.status
 except urllib.error.HTTPError as exc:code=exc.code
 print("Current LIVE Studio session endpoint HTTP:",code)
 if code==503:print("Cloudflare Pages requires the next approved deployment to bind the production secret")
 if code==401:print("Studio V2 login service is ready for administrator authentication")
except Exception as exc:
 print("Could not verify live session endpoint:",type(exc).__name__)
