"""Resolve review covers from ZazoomTek's own archives, not from arbitrary similarly named products."""
import json
import re
import unicodedata
from pathlib import Path

EXTENSIONS={".jpg",".jpeg",".png",".webp",".avif"}
IGNORE={"recensione","review","prova","test","completa","completo","ps5","ps4","pc",
        "gaming","tech","videorecensione","e","di","da","il","la","con","per","su","the","of"}
def tokens(value):
 raw=unicodedata.normalize("NFKD",str(value or ""))
 raw="".join(ch for ch in raw if not unicodedata.combining(ch))
 return [x for x in re.findall(r"[a-z0-9]+",raw.lower()) if x not in IGNORE]

def product_identity(row):
 v=str(row.get("product_name") or row.get("device") or "")
 if not v:v=str(row.get("title") or "").split("|",1)[0]
 return list(dict.fromkeys(tokens(v)))

def agrees(subject,candidate):
 src=product_identity(subject)
 available=set(tokens(candidate))
 # Two distinct exact model/brand tokens are the minimum; no fuzzy substitutions.
 return len(src)>=2 and set(src).issubset(available)

def local_image(root,row):
 # Search only a project's own checked-in assets, with an exact product/model match.
 root=root/"assets"
 if not root.is_dir():return ""
 preferred=[]
 for path in root.rglob("*"):
  if not path.is_file() or path.suffix.lower() not in EXTENSIONS:continue
  relative=path.relative_to(root).as_posix()
  if agrees(row,relative.replace("/"," ")):
   preferred.append(path)
 if not preferred:return ""
 preferred.sort(key=lambda p:(0 if "cover" in p.stem.lower() else 1,len(p.name),str(p)))
 return "/"+preferred[0].relative_to(root.parent).as_posix()

def youtube_thumbnail(video):
 vid=video.get("id","")
 if not isinstance(vid,str) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",vid):return ""
 return "https://i.ytimg.com/vi/"+vid+"/hqdefault.jpg"

def find_archive_cover(row,root,videos,post_archive,community_archive,curated):
 # Explicit user-supplied image is never replaced; this function handles only missing/invalid covers.
 local=local_image(root,row)
 if local:return local,"local asset name/model"
 slug=row.get("slug","")
 for x in curated:
  if x.get("review_slug")==slug and agrees(row,x.get("product_name","")):
   match=next((v for v in videos if v.get("id")==x.get("video_id")),None)
   if match and agrees(row,match.get("title","")):
    candidate=youtube_thumbnail(match)
    if candidate:return candidate,"first-party ZazoomTek archive (exact product match)"
 # Written reviews may match a full original Community article cover by EXACT model and title.
 for entry in community_archive:
  if agrees(row,entry.get("title","")):
   url=str(entry.get("image") or "")
   if url.startswith(("https://yt3.ggpht.com/","https://i.ytimg.com/")):
    return url,"original ZazoomTek Community image"
 # Match the last first-party review thumbnail, not unrelated similarly named hardware.
 suitable=[v for v in videos if agrees(row,v.get("title","")) and youtube_thumbnail(v)]
 suitable.sort(key=lambda v:(v.get("kind")=="review",str(v.get("date") or "")),reverse=True)
 if suitable:return youtube_thumbnail(suitable[0]),"first-party ZazoomTek video archive"
 for entry in post_archive:
  if entry.get("slug")==slug:continue
  if agrees(row,entry.get("title","")):
   url=entry.get("image","")
   if isinstance(url,str) and url.startswith(("https://yt3.ggpht.com/","https://i.ytimg.com/")):
    return url,"ZazoomTek related editorial image"
 return "","not found: requires a verified original cover"

def populate_review_covers(rows,project_root,image_validator):
 root=Path(project_root)
 videos=json.loads((root/"data/videos.json").read_text(encoding="utf-8")).get("videos",[])
 archived=json.loads((root/"data/community_full.json").read_text(encoding="utf-8")).get("posts",[])
 localposts=json.loads((root/"data/posts.json").read_text(encoding="utf-8")).get("posts",[])
 db_path=root/"data/review_image_index.json"
 curated=json.loads(db_path.read_text(encoding="utf-8")).get("entries",[]) if db_path.exists() else []
 found=0;missing=[]
 for row in rows:
  if not str(row.get("category") or "").startswith("recensioni-"):continue
  current=image_validator(row.get("image") or "")
  if current:
   row["image"]=current
   continue
  chosen,provenance=find_archive_cover(row,root,videos,localposts,archived,curated)
  if chosen and image_validator(chosen):
   row["image"]=chosen
   row["image_source"]=provenance
   found+=1
  elif row.get("source")=="manual-editorial":
   missing.append(row.get("slug"))
 print("Review archive cover matching:",found,"matched;",len(missing),"written reviews still need a verified photo",flush=True)
 if missing:print("Unresolved covers:",", ".join(missing),flush=True)
