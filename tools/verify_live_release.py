#!/usr/bin/env python3
"""Check the EXACT deployed source over the public domain before release receipt.

Wrangler success alone is not enough. The live page must reference the
freshly built stylesheet, and Cloudflare must serve its exact bytes.
A new query key and no-cache requests reduce stale edge/browser responses.
"""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlencode
import hashlib,re,time,urllib.request,urllib.error,sys,os

ROOT=Path(__file__).resolve().parents[1]
DIST=ROOT/"dist"
SITE=os.getenv("ZAZOOMTEK_PUBLIC_SITE","https://zazoomtek.it").rstrip("/")
INDEX=DIST/"index.html"
STYLES=DIST/"assets/css/spotnews.css"
MAX_ATTEMPTS=10

def get(url,timeout=16):
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (compatible; ZazoomTekReleaseVerifier/1.0)",
        "Cache-Control":"no-cache","Pragma":"no-cache","Accept":"*/*"
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200:raise RuntimeError("Unexpected HTTP "+str(response.status))
        return response.read(4000000)

def verify():
    built=INDEX.read_bytes()
    stylesheet=STYLES.read_bytes()
    assert built and stylesheet
    m=re.search(rb'/assets/css/spotnews\.css\?v=([0-9a-f]{8,64})',built)
    if not m:raise RuntimeError("Generated HTML does not link versioned CSS")
    version=m.group(1).decode()
    css_hash=hashlib.sha256(stylesheet).hexdigest()
    if not css_hash.startswith(version):
        raise RuntimeError("Generated CSS version does not match CSS bytes")
    last=""
    for attempt in range(1,MAX_ATTEMPTS+1):
        nonce=str(int(time.time()))+"-"+str(attempt)
        try:
            actual=get(SITE+"/?zazoomtek_release_verification="+nonce)
            if b'/assets/css/spotnews.css?v='+m.group(1) not in actual:
                found=re.search(rb'/assets/css/spotnews\\.css\\?v=([0-9a-f]{8,64})',actual)
                remote=found.group(1).decode() if found else "MISSING"
                raise RuntimeError("Homepage CSS version stale: live="+remote+
                                   " expected="+version)
            remote_css=get(SITE+"/assets/css/spotnews.css?v="+version+
                           "&zazoomtek_release_verification="+nonce)
            if hashlib.sha256(remote_css).hexdigest()!=css_hash:
                raise RuntimeError("Live CSS SHA256 mismatch: live="+hashlib.sha256(remote_css).hexdigest()[:16]+" expected="+css_hash[:16])
            print("PUBLIC DOMAIN VERIFIED",SITE,"attempt",attempt,
                  "HTML",len(actual),"CSS_SHA256",css_hash,
                  "at",datetime.now(timezone.utc).isoformat(),flush=True)
            summary=os.getenv("GITHUB_STEP_SUMMARY")
            if summary:
                with open(summary,"a",encoding="utf-8") as f:
                    f.write("\n✅ **Cloudflare release verified on public domain:** "+
                            SITE+" | CSS SHA256 `"+css_hash[:16]+"`\n")
            return
        except (OSError,TimeoutError,ValueError,RuntimeError) as e:
            last=type(e).__name__+": "+str(e)
            print("PUBLIC VERIFY RETRY",attempt,last,flush=True)
            if attempt<MAX_ATTEMPTS:time.sleep(6)
    raise RuntimeError("Cloudflare deployment may have uploaded, but public site"+
                       " cannot be confirmed; release receipt NOT authorized: "+last)

if __name__=="__main__":
    verify()
