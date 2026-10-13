#!/usr/bin/env python3
"""Fail closed but recover from temporary Gemini 503/429 for source-checked reporting.
Use only models listed for this user's key. Do not expand to expensive models
unless specifically configured; never skip article/fact verification.
"""
import json,os,re,time,urllib.error,urllib.request
from functools import lru_cache
RETRY={408,429,500,502,503,504}
class GeminiRequestError(RuntimeError):pass

def choose(configured,available,extra=""):
    names=[configured,extra,"gemini-2.5-flash-lite","gemini-3.5-flash-lite","gemini-3.5-flash","gemini-2.5-flash"]
    return [m for m in dict.fromkeys(names) if m in available
            and re.fullmatch(r"gemini-[a-z0-9.-]+",str(m or ""))]

@lru_cache(maxsize=2)
def catalog(key):
    try:
        req=urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=100",
            headers={"x-goog-api-key":key})
        with urllib.request.urlopen(req,timeout=25) as response:
            data=json.load(response)
    except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,ValueError) as exc:
        raise GeminiRequestError("Model catalog unavailable: "+type(exc).__name__) from None
    return {m.get("name","").removeprefix("models/") for m in data.get("models",[])
            if "generateContent" in m.get("supportedGenerationMethods",[])}

def one(model,key,prompt,settings,timeout):
    url="https://generativelanguage.googleapis.com/v1beta/models/"+model+":generateContent"
    request=urllib.request.Request(url,method="POST",
        headers={"Content-Type":"application/json","x-goog-api-key":key},
        data=json.dumps({"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":settings}).encode("utf-8"))
    with urllib.request.urlopen(request,timeout=timeout) as response:
        payload=json.load(response)
    text="".join(p.get("text","") for c in payload.get("candidates",[])
        for p in c.get("content",{}).get("parts",[]))
    value=json.loads(text)
    if not isinstance(value,dict):raise ValueError("Non-object JSON")
    return value

def recover(models,send,sleep=time.sleep):
    issues=[]
    for model in models:
        for attempt in range(2):
            try:return send(model),model
            except urllib.error.HTTPError as exc:
                if exc.code in (404,410):
                    # A listed API model can still lack generateContent on the
                    # active endpoint. Skip it, do not abort the whole pipeline.
                    issues.append(f"{model}: model endpoint unavailable ({exc.code})")
                    break
                if exc.code not in RETRY:
                    raise GeminiRequestError(f"Gemini {model} HTTP {exc.code} (not retryable)") from None
                issues.append(f"{model}: HTTP {exc.code}")
            except (urllib.error.URLError,TimeoutError,OSError) as exc:
                issues.append(f"{model}: {type(exc).__name__}")
            except (TypeError,ValueError,KeyError):
                issues.append(f"{model}: invalid JSON")
            if attempt==0:sleep(3)
        if len(models)>1:print("Transient Gemini failure; switching to authorized lightweight fallback")
    raise GeminiRequestError("No verified AI response after bounded recovery: "+", ".join(issues[-4:]))

def call_json(prompt,key,configured,settings,timeout=75):
    if not key:raise GeminiRequestError("GEMINI_API_KEY missing; publication safely blocked")
    models=choose(configured,catalog(key),os.environ.get("GEMINI_FALLBACK_MODEL",""))
    if not models:raise GeminiRequestError("No configured/fallback Gemini text model available")
    return recover(models,lambda m:one(m,key,prompt,settings,timeout))

def self_test():
    assert choose("gemini-3.5-flash-lite",{"gemini-2.5-flash-lite","gemini-3.5-flash-lite"})==[
        "gemini-3.5-flash-lite","gemini-2.5-flash-lite"]
    events=[]
    def fake(m):
        events.append(m)
        if m=="gemini-3.5-flash-lite":
            raise urllib.error.HTTPError("https://invalid.example",503,"busy",{},None)
        return {"drafts":[]}
    value,model=recover(["gemini-3.5-flash-lite","gemini-2.5-flash-lite"],fake,lambda _:None)
    assert model=="gemini-2.5-flash-lite" and value=={"drafts":[]} and len(events)==3
    checks=[]
    def missing(m):
        checks.append(m)
        if m=="gemini-2.5-flash-lite":
            raise urllib.error.HTTPError("https://invalid.example",404,"missing",{},None)
        return {"drafts":[]}
    value,model=recover(["gemini-2.5-flash-lite","gemini-3.5-flash"],missing,lambda _:None)
    assert model=="gemini-3.5-flash" and len(checks)==2
    try:
        recover(["gemini-2.5-flash-lite"],lambda m:
            (_ for _ in ()).throw(urllib.error.HTTPError("https://invalid.example",403,"forbidden",{},None)),lambda _:None)
    except GeminiRequestError as exc:assert "not retryable" in str(exc)
    else:raise AssertionError("403 must stop safely")
    print("PASS Gemini 503 retry/fallback, 403 safety stop")
if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv:self_test()
