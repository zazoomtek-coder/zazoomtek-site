"""Verify every generated HTML page has clean, nonduplicated media cards."""
from html.parser import HTMLParser
from pathlib import Path

VOID={"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
MEDIA_TARGETS={"editorial-media-frame","tile-link","video-start"}

class ScanMedia(HTMLParser):
 def __init__(self,filename):
  super().__init__(convert_charrefs=True)
  self.filename=filename
  self.stack=[]
  self.checked=0
  self.issues=[]
 def handle_starttag(self,tag,attrs):
  attr=dict(attrs)
  names=set((attr.get("class") or "").split())
  if names.intersection({"editorial-media-bg","spotlight-cover-backdrop","smart-cover-front","smart-cover-frame"}):
   self.issues.append("Legacy duplicated-media class found: "+str(names))
  if "style" in attr and "--smart-cover-art" in str(attr["style"]):
   self.issues.append("Injected duplicate background image detected")
  if tag=="img":
   for open_tag in self.stack:
    if open_tag["target"]:open_tag["images"].append(attr.get("src") or "")
  if tag not in VOID:
   self.stack.append({
    "tag":tag,
    "target":bool(names.intersection(MEDIA_TARGETS)),
    "images":[],
    "fallback":"is-fallback" in names,
    "name":next(iter(names.intersection(MEDIA_TARGETS)),"")
   })
 def handle_startendtag(self,tag,attrs):
  self.handle_starttag(tag,attrs)
  if tag not in VOID:self.handle_endtag(tag)
 def handle_endtag(self,tag):
  # HTMLParser does not enforce a closing sequence; only inspect actual
  # frame closing tags and leave unrelated semantic HTML untouched.
  index=next((i for i in range(len(self.stack)-1,-1,-1)
              if self.stack[i]["tag"]==tag),None)
  if index is None:return
  opened=self.stack[index:]
  self.stack=self.stack[:index]
  for entry in opened:
   if not entry["target"]:continue
   self.checked+=1
   if len(entry["images"])>1:
    self.issues.append(
     entry["name"]+" contains "+str(len(entry["images"]))+" images instead of one")
   if len(entry["images"])!=len(set(entry["images"])):
    self.issues.append(entry["name"]+" repeats the same original picture")

def check_media(output,stylesheet,script):
 root=Path(output)
 css=Path(stylesheet).read_text(encoding="utf-8")
 js=Path(script).read_text(encoding="utf-8")
 if "v50 — ONE image per box" not in css:raise AssertionError("Single-cover layout CSS missing")
 for forbidden in ("/* v47 —","/* v49 —","--smart-cover-art","img.spotlight-cover-backdrop"):
  if forbidden in css:raise AssertionError("Old double-art CSS remains: "+forbidden)
 for forbidden in ("--smart-cover-art","fitArtwork","smart-cover-frame"):
  if forbidden in js:raise AssertionError("Old double-art Javascript remains: "+forbidden)
 htmls=sorted(root.rglob("*.html"))
 if not htmls:raise AssertionError("No HTML outputs to inspect")
 frames=0
 problems=[]
 for file in htmls:
  checker=ScanMedia(file.relative_to(root))
  checker.feed(file.read_text(encoding="utf-8"))
  checker.close()
  frames+=checker.checked
  problems.extend(str(file.relative_to(root))+": "+issue for issue in checker.issues)
 if problems:raise AssertionError(
  "FAIL duplicate-media audit: "+str(len(problems))+" violations: "+"; ".join(problems[:20]))
 if frames<20:raise AssertionError("Unexpectedly few media frames checked: "+str(frames))
 print("MEDIA AUDIT PASS:",len(htmls),"HTML pages,",frames,
       "media frames, no duplicated images or injected backgrounds",flush=True)

if __name__=="__main__":
 raise SystemExit("Run through tools/build.py after HTML generation")
