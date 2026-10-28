"""Opt-in Studio V2 acceptance audit: no modification of original Studio."""
from pathlib import Path
import json,re
from seo import title_tag,description,keywords,metadata

def verify_studio_v2(output,rows):
 output=Path(output)
 root=output/"studio-v2"
 page=(root/"index.html").read_text(encoding="utf-8")
 data=json.loads((root/"catalog.json").read_text(encoding="utf-8"))
 assert 'noindex,nofollow' in page
 assert 'id="v2-home"' in page and 'id="v2-editor" class="v2-editor-view" hidden' in page
 assert 'id="v2-append-block"' in page and 'id="v2-cover-edit"' in page
 assert 'id="v2-save-draft"' in page and 'id="v2-publish"' in page
 assert 'id="v2-modal"' in page and 'id="v2-category"' in page
 assert 'id="v2-seo-status"' in page and 'AUTOMATICO' in page
 assert 'id="v2-content-list"' not in page # new implementation uses v2-list
 assert 'id="v2-list"' in page
 assert len(data["posts"])==len(rows),("V2 must include EVERY article",len(data["posts"]),len(rows))
 assert len({r["slug"] for r in data["posts"]})==len(rows),"Duplicate Studio V2 content"
 assert all(isinstance(r["seo_lock"]["title"],str) and
            isinstance(r["seo_lock"]["description"],str) and
            isinstance(r["seo_lock"]["keywords"],list) for r in data["posts"])
 assert (output/"studio/index.html").is_file(),"Original Studio must remain intact"
 css=(output/"assets/css/studio-v2.css").read_text(encoding="utf-8")
 script=(output/"assets/js/studio-v2.js").read_text(encoding="utf-8")
 for marker in ("v2-home-intro","v2-list-item","v2-block-row","v2-settings","v2-modal",
                "v2-plus","v2-cover-stage"):
  assert marker in css,"V2 CSS missing "+marker
 for marker in ("v2-save","v2-drafts","save(\"draft\")","save(\"publish\")",
                "openMenu","editCover","editMedia","showHome","startNew"):
  assert marker in script,"V2 JS missing "+marker
 assert "localStorage" not in script and "sessionStorage" not in script
 api=(Path(__file__).resolve().parents[1]/"functions/api/studio/[[path]].js").read_text(encoding="utf-8")
 for marker in ('/api/studio/v2-drafts','/api/studio/v2-save',
                'data/studio_v2_drafts.json','STUDIO_SESSION_SECRET','record.seo_lock='):
  assert marker in api,"V2 backend missing "+marker
 # Existing original SEO is frozen when an article is edited; brand-new
 # articles still receive automatic content-derived SEO.
 original=next((r for r in rows if len(str(r.get("title") or ""))>20),None)
 assert original is not None
 locked={"title":title_tag(original),"description":description(original),
         "keywords":keywords(original)}
 changed={"title":"Titolo cambiato dopo modifiche di redazione",
          "body":[{"type":"paragraph","text":"Un testo completamente diverso sull'innovazione digitale e l'hardware."}],
          "category":original["category"],"image":original.get("image"),
          "seo_lock":locked}
 assert title_tag(changed)==locked["title"]
 assert description(changed)==locked["description"]
 assert keywords(changed)==locked["keywords"]
 fresh={"title":"Nuova guida hardware per sistemi gaming moderni",
        "body":[{"type":"paragraph","text":"Questa guida spiega i componenti hardware gaming e la scelta delle configurazioni più adatte alle esigenze moderne."}]}
 assert title_tag(fresh)!="ZazoomTek | Tecnologia e Gaming"
 assert description(fresh).startswith("Questa guida")
 print("STUDIO V2 AUDIT PASS:",len(rows),"editable published items, SEO lock, drafts, opt-in interface",flush=True)
