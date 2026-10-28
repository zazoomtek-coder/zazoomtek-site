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
 assert 'id="studio-setup-link"' in page,"Studio setup link must be available"
 assert 'id="studio-retry"' in page,"Studio must support retry after Access configuration"
 assert 'id="studio-gate-setup"' in page,"Studio must describe the missing Access configuration"
 assert '/assets/js/studio.js?v=2' in page,"Studio must invalidate old browser JS"
 assert (root/"assets/js/studio.js").is_file(),"Studio JS not copied"
 assert (root/"assets/css/studio.css").is_file(),"Studio CSS not copied"
 data=json.loads(catalog.read_text(encoding="utf-8"))
 assert len(data.get("posts",[]))==len(rows),"Studio catalog must include EVERY article"
 assert {x.get("slug") for x in data["posts"]}=={x.get("slug") for x in rows},"Incomplete Studio article catalog"
 sitejs=(root/"assets/js/site.js").read_text(encoding="utf-8")
 assert '"/api/studio/session"' in sitejs
 assert 'session?.admin!==true' in sitejs
 studiojs=(root/"assets/js/studio.js").read_text(encoding="utf-8")
 assert 'ACCESS_CONFIGURATION_REQUIRED' in studiojs,"Missing admin setup error handling"
 assert 'studio-gate-setup' in studiojs,"Missing activation screen handling"
 assert 'studio-retry' in studiojs,"Missing reconnect button handling"
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
 assert 'CF_ACCESS_TEAM_DOMAIN' not in page and 'STUDIO_GITHUB_TOKEN' not in page,"Credentials embedded in HTML"
 print("STUDIO AUDIT PASS:",len(rows),"editable articles; blocks/media and admin controls verified",flush=True)
