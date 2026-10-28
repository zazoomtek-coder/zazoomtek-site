"""Studio integration audit: catalog, source-faithful rich blocks, admin security."""
from pathlib import Path
from html.parser import HTMLParser
import json

def verify_studio(output,rows):
 root=Path(output)
 ui=root/"studio/index.html"
 catalog=root/"studio/catalog.json"
 assert ui.is_file() and catalog.is_file(),"Studio UI and catalog missing"
 page=ui.read_text(encoding="utf-8")
 assert 'name="robots" content="noindex,nofollow' in page,"Studio must be noindex"
 assert 'id="studio-app" hidden' in page,"Studio UI must default hidden"
 assert '/assets/js/studio.js' in page,"Studio editor JS missing"
 assert "/cdn-cgi/access/login" not in page,"Broken Cloudflare login link must not be rendered"
 assert 'id="studio-auth"' in page,"New login gate missing"
 assert 'id="studio-login-form"' in page,"First-time GitHub login UI missing"
 assert 'id="studio-setup"' in page,"One-time server session-secret setup missing"
 assert 'id="studio-check-again"' in page,"Setup retry missing"
 assert 'id="studio-app" hidden' in page,"Studio must be hidden until authenticated"
 assert '/assets/js/studio.js?v=20261028-studio-fresh-2' in page,"New Studio JS cache version missing"
 assert '/cdn-cgi/access/login' not in page,"Legacy Zero Trust login URL detected"
 assert 'CF_ACCESS_' not in page,"Zero Trust secrets may not appear"
 assert (root/"assets/js/studio.js").is_file(),"Studio JS not copied"
 assert (root/"assets/css/studio.css").is_file(),"Studio CSS not copied"
 data=json.loads(catalog.read_text(encoding="utf-8"))
 assert len(data.get("posts",[]))==len(rows),"Studio catalog must include EVERY article"
 assert {x.get("slug") for x in data["posts"]}=={x.get("slug") for x in rows},"Incomplete Studio article catalog"
 sitejs=(root/"assets/js/site.js").read_text(encoding="utf-8")
 assert '"/api/studio/session"' in sitejs
 assert 'session?.admin!==true' in sitejs
 studiojs=(root/"assets/js/studio.js").read_text(encoding="utf-8")
 for required in ('SETUP_REQUIRED','studio-login-form','studio-token','studio-setup',
                  'studio-check-again','studio-logout','studio-new','studio-save',
                  'studio-blocks','studio-preview'):
  assert required in studiojs,"New Studio JS missing "+required
 assert 'localStorage' not in studiojs and 'sessionStorage' not in studiojs,"Browser must never store GitHub tokens"
 # Keep all admin modifications on GitHub's preview branch; the Pages
 # Function verifies the GitHub owner and decrypts HttpOnly cookies server-side.
 api_source=(Path(__file__).resolve().parents[1]/"functions/api/studio/[[path]].js").read_text(encoding="utf-8")
 for required in ('__Host-zzt-studio','HttpOnly; Secure; SameSite=Strict',
                  'STUDIO_SESSION_SECRET','github_pat_','branch:BRANCH',
                  'AES-GCM','renewed:true','setCookie(await seal(renewed,env),AGE)'):
  assert required in api_source,"Studio secure session missing "+required
 assert 'CF_ACCESS_TEAM_DOMAIN' not in api_source,"Old Zero Trust service must be removed"
 assert 'studio-admin-edit' in sitejs
 from article_templates import sectioned_body,render
 original={
  "slug":"studio-sample-rich-content","category":"news-tech",
  "title":"Studio sample test content for the editorial block renderer",
  "image":"/assets/images/amazon-laptop.svg","studio_blocks":True,
  "body":[
   {"type":"heading","text":"Nuove caratteristiche"},
   {"type":"paragraph","text":"L'articolo contiene una descrizione completa con [link verificabile](https://zazoomtek.it/guide) e **grassetto**."},
   {"type":"image","url":"/assets/images/amazon-laptop.svg","alt":"Foto nell'articolo","caption":"Didascalia originale"},
   {"type":"video","url":"https://youtu.be/dQw4w9WgXcQ"},
   {"type":"button","url":"https://zazoomtek.it","text":"Approfondisci"},
   {"type":"quote","text":"Citazione editoriale."}
  ]
 }
 html=sectioned_body(original)
 for expected in ('<h2>Nuove caratteristiche</h2>',
                  'href="https://zazoomtek.it/guide"',
                  'class="story-figure studio-content-image"',
                  'data-youtube-id="dQw4w9WgXcQ"',
                  'class="studio-content-action"',
                  'class="studio-content-quote"'):
  assert expected in html,"Studio block not rendered: "+expected
 assert "javascript:" not in html,"Unsafe links cannot pass to rendered articles"
 assert 'data-studio-slug="studio-sample-rich-content"' in render(original,lambda x:x)
 # A public article carries NO editable/admin button unless session is verified in JS.
 generated=next((root/(r["slug"]+".html") for r in rows if (root/(r["slug"]+".html")).is_file()),None)
 assert generated and 'studio-admin-edit' not in generated.read_text(encoding="utf-8"),"Public Admin button leak"
 assert 'STUDIO_SESSION_SECRET' not in page or 'serve soltanto' in page,"Server setup status should not contain the secret itself"
 print("STUDIO AUDIT PASS:",len(rows),"editable articles; blocks/media and admin controls verified",flush=True)
