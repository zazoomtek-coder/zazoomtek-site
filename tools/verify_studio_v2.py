"""Opt-in Studio V2 acceptance audit: no modification of original Studio."""
from pathlib import Path
import hashlib
import json,re
from seo import title_tag,description,keywords,metadata

def verify_studio_v2(output,rows):
 output=Path(output)
 root=output/"studio-v2"
 page=(root/"index.html").read_text(encoding="utf-8")
 data=json.loads((root/"catalog.json").read_text(encoding="utf-8"))
 assert 'noindex,nofollow' in page
 # A review cannot be published without a valid final score: both the editor
 # and the server enforce the rule, while draft saving remains independent.
 repo=Path(__file__).resolve().parents[1]
 studio_js=(repo/"assets/js/studio-v2.js").read_text(encoding="utf-8")
 studio_api=(repo/"functions/api/studio/[[path]].js").read_text(encoding="utf-8")
 assert 'mode==="publish"&&row.category.startsWith("recensioni-")&&!validReviewScore(row.category,row.score)' in studio_js
 assert 'inserisci un voto finale valido da 0 a 10' in studio_js
 assert 'safeCategory.startsWith("recensioni-")&&score===null' in studio_api
 assert 'una recensione deve avere un voto finale valido da 0 a 10' in studio_api
 assert 'if(mode==="draft")' in studio_api, "Draft saving must remain available before the review is complete"
 assert 'scoreText' in studio_api and 'Number.isFinite(parsed)&&parsed>=0&&parsed<=10' in studio_api, "API score parser must validate numeric scores"
 assert 'id="v2-home"' in page and 'id="v2-editor" class="v2-editor-view" hidden' in page
 assert 'id="v2-append-block"' in page and 'id="v2-cover-edit"' in page
 assert all('id="'+name+'"' in page for name in
            ("v2-new-from-editor","v2-new-from-editor-bottom","v2-preview-top","v2-preview-bottom","v2-save-draft","v2-cancel-draft","v2-cancel-draft-bottom","v2-publish",
             "v2-draft-bottom","v2-publish-bottom","v2-close-preview",
             "v2-article-preview","v2-autosave-status"))
 assert 'id="v2-modal"' in page and 'id="v2-category"' in page
 assert 'spotnews.css' in page and 'id="v2-live-meta"' in page
 expected_spotnews=hashlib.sha256((Path(__file__).resolve().parents[1]/"assets/css/spotnews.css").read_bytes()).hexdigest()[:12]
 expected_studio=hashlib.sha256((Path(__file__).resolve().parents[1]/"assets/css/studio-v2.css").read_bytes()).hexdigest()[:12]
 assert f"/assets/css/spotnews.css?v={expected_spotnews}" in page, "Studio V2 must use a cache-busted current SpotNews stylesheet"
 assert f"/assets/css/studio-v2.css?v={expected_studio}" in page, "Studio V2 must use a cache-busted current Patreon-like stylesheet"
 assert 'id="v2-live-equipment"' in page and 'id="v2-live-verdict"' in page
 assert 'id="v2-seo-status"' in page and 'AUTOMATICO' in page
 assert 'id="v2-content-list"' not in page # new implementation uses v2-list
 assert 'id="v2-list"' in page
 assert len(data["posts"])==len(rows),("V2 must include EVERY article",len(data["posts"]),len(rows))
 # Editor must faithfully display editorial text/heading order instead of
 # debug-style block fields and a separate "+" for every paragraph.
 assert all(isinstance(p.get("editor_blocks"),list) and p["editor_blocks"]
            for p in data["posts"]),"Empty rich editorial body in Studio"
 # YouTube reviews without source-authored H2 must stay as plain source
 # paragraphs in Studio; no synthetic review outline or "Approfondimento".
 from studio_v2_build import editorial_blocks_for_editor
 from article_templates import studio_sectioned_body
 youtube_review={"slug":"community-youtube-review-source-test","source":"youtube-community","title":"Recensione prodotto importata da YouTube",
  "category":"recensioni-tech","body":[
   "Apertura originale della recensione importata da YouTube.",
   "Secondo paragrafo originale con i dettagli del prodotto e dell'esperienza d'uso.",
   "Terzo paragrafo originale che continua la valutazione senza un titolo aggiunto."
  ]}
 source_blocks=editorial_blocks_for_editor(youtube_review)
 assert len(source_blocks)==3 and all(b["type"]=="paragraph" for b in source_blocks),source_blocks
 assert [b["text"] for b in source_blocks]==youtube_review["body"],"Studio changed source review text/order"
 studio_review={"slug":"community-youtube-review-source-test","source":"youtube-community","category":"recensioni-tech","studio_blocks":True,
  "body":[{"type":"paragraph","text":x} for x in youtube_review["body"]]}
 assert "<h2>Approfondimento</h2>" not in studio_sectioned_body(studio_review),"Synthetic heading still added to published review"
 manual_review={"slug":"manual-review-source-test","source":"manual-editorial","category":"recensioni-tech",
  "studio_blocks":True,"body":[{"type":"paragraph","text":"Testo di una recensione manuale."}]}
 assert "Approfondimento" not in studio_sectioned_body(manual_review),"Synthetic filler heading must not appear in Studio articles"
 guide=next((p for p in rows if p.get("slug")=="iphone-con-memoria-piena-come-liberare-spazio-senza-perdere-foto-e-dati"),None)
 assert guide is not None,"Published iPhone storage guide missing from the article catalog"
 guide_html=studio_sectioned_body(guide)
 for filler in ("Approfondimento","Tutti i dettagli","Gli elementi principali","Altri dettagli","Il quadro completo","Ulteriori informazioni"):
  assert "<p>"+filler+"</p>" not in guide_html and "<h2>"+filler+"</h2>" not in guide_html,"Filler label leaked into public guide: "+filler
 for heading in ("Prima di cancellare, individua il vero responsabile","Foto e video: la precauzione più importante",
                 "App: rimuovere o disinstallare mantenendo i dati","Messaggi, download e documenti dimenticati",
                 "Le operazioni da evitare quando hai fretta","Una piccola manutenzione per non ritrovarsi al punto di partenza"):
  assert heading in guide_html,"Guide subtitle text missing from rendered article: "+heading
 example=next((p for p in data["posts"] if p.get("slug")==
               "speciale-videogiochi-minori-italia-unione-europea"),None)
 if example:
  assert len(example["editor_blocks"])>=12,"Speciale text was truncated"
  assert any("EU KIDS Act: perché riguarda anche il gioco online." in b.get("text","") for b in example["editor_blocks"]),"Original section title missing from editor blocks"
  assert any("Tra mozione italiana ed EU KIDS Act" in b.get("text","")
             for b in example["editor_blocks"]),"Opening text changed"

 assert len({r["slug"] for r in data["posts"]})==len(rows),"Duplicate Studio V2 content"
 assert all(isinstance(r["seo_lock"]["title"],str) and
            isinstance(r["seo_lock"]["description"],str) and
            isinstance(r["seo_lock"]["keywords"],list) for r in data["posts"])
 assert (output/"studio/index.html").is_file(),"Original Studio must remain intact"
 css=(output/"assets/css/studio-v2.css").read_text(encoding="utf-8")
 script=(output/"assets/js/studio-v2.js").read_text(encoding="utf-8")
 for marker in ("v2-home-intro","v2-list-item","v2-block-row","v2-settings","v2-modal",
                "v2-plus","v2-cover-stage","v2-article-preview","v2-preview-article","v2-html-block","v2-html-live-preview"): 
  assert marker in css,"V2 CSS missing "+marker
 for marker in ('async function cancelDraft()',
                'api("v2-draft-delete",{slug})',
                'window.confirm("Vuoi cancellare la bozza',
                'save("draft")',
                "showArticlePreview","formattedTextBlocks","restoreBackup","syncArticleChrome",
                "scheduleBackup","pagehide","editorialBodyForDisplay",
                "openMenu","editCover","editMedia","showHome","startNew",
                 "detectEditorialCategory","categoryTouched","skipBackup","v2-new-from-editor-bottom",
                "async function refreshLibrary()","refreshLibrary();","__queued:!liveSlugs.has(item.slug)"):
  assert marker in script,"V2 JS missing "+marker
 for marker in ("function richContent(", "function cursorHere(", "function insertPosition(", "function inlineLink(", "function safePaste(", "state.coverPreview"):
  assert marker in script,"WYSIWYG features missing: "+marker
 assert 'function addTextAfterBlock(i)' in script,"Images must support inserting a paragraph immediately after them"
 assert 'actionButton("＋ Testo dopo",()=>addTextAfterBlock(i))' in script,"Image text-after action missing"
 assert 'editable.focus();' in script and 'selection.addRange(range);' in script,"New paragraph must receive editing focus"
 assert 'const row=S("div","v2-block-row")' not in script,"Repeated +/- debug rows must be removed"
 assert 'data-kind="link"' in page
 assert 'data-kind="html"' in page, "Studio must expose a custom HTML block in Add Content"
 assert "function updateAutoCategory()" in script, "Category detection must run independently of long-paste conditions"
 assert 'if(row.source==="studio-editor"&&Array.isArray(row.body)&&row.body.length)' in script, "Saved Studio body must override stale editor blocks from the live catalog"
 assert 'const useImportedBlocks=!!originalBlocks&&row.source!=="studio-editor";' in script, "Reopening a Studio override must not restore old imported paragraphs"
 assert 'state.current?.updated_at||state.current?.published_at||state.current?.date' in script, "Stale local recovery must not replace a newer server article"
 assert 'updateAutoCategory();syncArticleChrome({...state.current,...collect()})' in script, "Pasting or editing the title must refresh the inferred category"
 assert 'updateAutoCategory();renderBlocks();seoStatus();scheduleBackup();' in script, "Pasting body text must refresh category and preserve the edit"
 assert "function safeHtmlFragment(source)" in script, "Studio preview must sanitize custom HTML before rendering"
 assert 'new Option("Bozze / Main","__main-pending__")' in script, "Studio must expose Bozze / Main inside the content category dropdown"
 assert 'mainOnly?!!r.__queued' in script, "Bozze / Main must hide items automatically once present in the published catalog"
 assert 'setAttribute("sandbox","allow-scripts allow-forms allow-popups")' in script, "Third-party HTML embeds must run inside a sandbox"
 assert 'id="v2-new-from-editor"' in page and 'id="v2-new-from-editor-bottom"' in page, "Create-new controls must be available inside the editor"
 assert 'state.categoryTouched=true;E("v2-author")' in script, "Manual category selection must take precedence over automatic detection for new and existing articles"
 assert 'category_touched:!!state.categoryTouched' in script, "Manual category choice must survive autosave"
 assert 'showEditor({title:"",slug:"",category:"news-tech",author:"Gimmi",body:[{type:"paragraph",text:""}]},true,true)' in script, "Starting a new article must not overwrite the previous article backup"
 expected_script=hashlib.sha256((Path(__file__).resolve().parents[1]/"assets/js/studio-v2.js").read_bytes()).hexdigest()[:12]
 assert f"/assets/js/studio-v2.js?v={expected_script}" in page,"Browser must load the current Studio V2 JavaScript bundle"
 assert 'zazoomtek:studio-v2:local-drafts' in script
 assert 'if(Object.keys(state.drafts).length)localStorage.setItem(draftKey,JSON.stringify(state.drafts));' in script, "Publishing one article must preserve other local drafts"
 assert 'async function api(endpoint,data)' in script
 assert 'api("session")' in script and 'api("v2-pending")' in script
 assert 'api("v2-save",{mode:"publish",creating:state.newContent,record:row})' in script
 assert 'in attesa del primo slot editoriale disponibile' in script and 'result.deploy_requested' not in script
 assert 'async function uploadLocalAsset(value,slug)' in script, "Studio V2 asset upload helper missing"
 assert 'api("upload",{slug,mime,base64})' in script, "Studio V2 must upload normalized Base64 assets"
 assert 'async function uploadRecordMedia(row)' in script, "Studio V2 must normalize cover and image-block uploads before publishing"
 assert 'block.url||block.src||block.preview||block.image||block.file||""' in script, "Studio V2 must recover image URLs from the editor preview when needed"
 assert 'data:([^;,]+)(?:;[^,]*)*;base64' in script, "Studio V2 must accept data URLs with optional MIME parameters"
 assert 'row.image=await uploadLocalAsset(row.image,row.slug)' in script, "Cover image must be uploaded before saving"
 assert 'Salvataggio e pubblicazione non dipendono dalla presenza' in script and 'const normalized=[]' in script, "Media upload failures must never block saving or publishing"
 assert 'E("v2-publish").onclick=()=>save("publish")' in script
 assert 'E("v2-publish-bottom").onclick=()=>save("publish")' in script
 assert 'Solo anteprima' not in page and '>Pubblica</button>' in page
 assert 'primo slot editoriale disponibile' in page and 'Pubblica salva articolo e media su main' in page
 assert 'previewFinalArticle' in script
 assert 'image.src=b.preview||previewMediaUrl(b.url)||""' in script, "Studio editor must load saved image blocks through the authenticated GitHub media preview endpoint"
 assert 'cover.loading="eager"' in script and 'cover.fetchPriority="high"' in script
 preview=script.split("function showArticlePreview",1)[1].split("function closeArticlePreview",1)[0]
 assert "review-topline" not in preview, "Studio preview adds a label absent from the live article template"
 order=[preview.find('article.append(S("h1"'),preview.find("article.append(meta)"),
        preview.find('S("figure","story-figure")'),preview.find("article.append(text)")]
 assert all(position>=0 for position in order) and order==sorted(order), "Studio preview order differs from live article template"
 build=(Path(__file__).resolve().parents[1]/"tools/build.py").read_text(encoding="utf-8")
 assert "from article_templates import render" in build and "render(page,safe_image)" in build, "Studio pages must use the live shared editorial article template"
 # Only article BODY text may be recovered locally; never GitHub auth data.
 assert 'localStorage.setItem(backupKey(),JSON.stringify(payload))' in script
 assert 'record:collect()' in script
 assert '"token":' not in script and 'localStorage.setItem("token"' not in script
 assert 'sessionStorage' not in script
 from article_templates import sanitize_studio_html, studio_sectioned_body
 unsafe_html=('<p>Prodotto <a href="https://www.amazon.it/dp/B000000000">Amazon</a>'
              '<script>alert(1)</script><a href="javascript:alert(1)">link non sicuro</a>'
              '<img src="https://m.media-amazon.com/example.jpg" onerror="alert(1)"></p>'
              '<iframe src="//ws-eu.amazon-adsystem.com/widgets/q" title="Amazon" width="120" height="240"></iframe>')
 sanitized=sanitize_studio_html(unsafe_html)
 assert 'href="https://www.amazon.it/dp/B000000000" target="_blank" rel="noopener noreferrer external"' in sanitized
 assert 'src="https://m.media-amazon.com/example.jpg"' in sanitized and "onerror" not in sanitized
 assert 'src="https://ws-eu.amazon-adsystem.com/widgets/q"' in sanitized and 'sandbox="allow-scripts allow-forms allow-popups"' in sanitized
 assert "<script>" not in sanitized and "alert(1)" not in sanitized and "javascript:" not in sanitized
 html_article={"category":"news-tech","studio_blocks":True,"body":[{"type":"html","html":unsafe_html}]}
 rendered_html=studio_sectioned_body(html_article)
 assert "amazon.it/dp/B000000000" in rendered_html and "javascript:" not in rendered_html and "<script>" not in rendered_html
 api=(Path(__file__).resolve().parents[1]/"functions/api/studio/[[path]].js").read_text(encoding="utf-8")
 assert '"html"' in api and 'if(type==="html")' in api, "Studio API must preserve custom HTML blocks"
 assert 'const uploadedPath=/^assets\\/uploads\\/' in api, "Studio API must normalize repository upload paths in image blocks"
 for marker in ('/api/studio/v2-drafts','/api/studio/v2-draft-delete','/api/studio/v2-save',
                'data/studio_v2_drafts.json','STUDIO_SESSION_SECRET','record.seo_lock=',
                'const PUBLISH_BRANCH="main";','status:"saved-main"','branch==="main"?"[CF-Pages-Skip] "',
                'branch:PUBLISH_BRANCH','[CF-Pages-Skip] ',
                'readFile(token,"data/studio_posts.json",BRANCH)',
                'readFile(token,"data/studio_overrides.json",BRANCH)'):
  assert marker in api,"V2 backend missing "+marker
 gate=(Path(__file__).resolve().parents[1]/"tools/editorial_slot_gate.py").read_text(encoding="utf-8")
 assert '((12, 30), (16, 0), (19, 30))' in gate, "16:00 editorial release gate missing"
 assert 'EDITORIAL_COLLECTIONS = {' in gate, "Editorial collections must be fingerprinted semantically"
 for collection in ('"data/community_imported.json": "posts"',
                    '"data/videos.json": "videos"',
                    '"data/web.json": "items"',
                    '"data/studio_posts.json": "posts"',
                    '"data/studio_overrides.json": "overrides"'):
  assert collection in gate, "Editorial collection missing from release fingerprint: "+collection
 assert '"updated"' in gate and '"updated_at"' in gate, "Generated service metadata must be excluded from release fingerprint"
 assert "Approved editorial media is missing" in gate and 'path.read_bytes()' in gate, "Referenced Studio media must remain part of the release fingerprint"
 from editorial_slot_gate import editorial_value
 metadata_only_a={"updated":"2026-11-12","items":[{"title":"Nuovo articolo","updated_at":"2026-11-12T10:00:00Z"}]}
 metadata_only_b={"updated":"2026-11-13","items":[{"title":"Nuovo articolo","updated_at":"2026-11-13T10:00:00Z"}]}
 assert editorial_value(metadata_only_a)==editorial_value(metadata_only_b), "Service metadata must not change the editorial fingerprint"
 changed_article={"updated":"2026-11-13","items":[{"title":"Titolo modificato"}]}
 assert editorial_value(metadata_only_b)!=editorial_value(changed_article), "Actual editorial changes must change the fingerprint"
 cron=(Path(__file__).resolve().parents[1]/"cloudflare/cron-publisher/src/index.js").read_text(encoding="utf-8")
 assert '["queued", "in_progress"]' in cron, "Cloudflare Worker must avoid overlapping collection and release runs"
 assert 'GITHUB_COLLECT_WORKFLOW || "editorial-collect.yml"' in cron, "Five-minute YouTube collector workflow missing"
 assert 'GITHUB_PUBLISH_WORKFLOW || "editorial-publish.yml"' in cron, "Dedicated editorial publisher workflow missing"
 assert '["12:30", "16:00", "19:30"].includes(localTime)' in cron, "Worker must publish only in the three Rome slots"
 assert 'dispatchWorkflow(env, repo, collector)' in cron, "Worker must dispatch collection every five minutes"
 assert 'dispatchWorkflow(env, repo, publisher, { release_slot: localTime })' in cron, "Worker must dispatch publication only at a validated slot"
 cron_config=(Path(__file__).resolve().parents[1]/"cloudflare/cron-publisher/wrangler.toml").read_text(encoding="utf-8")
 assert 'crons = ["*/5 * * * *"]' in cron_config, "Cloudflare Cron must poll every five minutes"
 collector=(Path(__file__).resolve().parents[1]/".github/workflows/editorial-collect.yml").read_text(encoding="utf-8")
 assert 'cron: "*/5 * * * *"' in collector, "GitHub fallback must collect every five minutes"
 assert "python3 tools/queue_collect.py" in collector and "git push origin HEAD:editorial-queue" in collector, "Five-minute collector must persist a non-publishing queue"
 publisher=(Path(__file__).resolve().parents[1]/".github/workflows/editorial-publish.yml").read_text(encoding="utf-8")
 assert '"12:30"|"16:00"|"19:30"' in publisher and '"poll"' not in publisher, "Publisher must reject polling and accept only the three slots"
 for cron in ('30 10,11 * * *','0 14,15 * * *','30 17,18 * * *'):
  assert cron in publisher, "Scheduled publisher is missing a CET/CEST UTC slot candidate: "+cron
 assert 'EVENT_NAME: ${{ github.event_name }}' in publisher and 'TZ=Europe/Rome date +%s' in publisher, "Scheduled publisher must validate the Europe/Rome local slot"
 live_check=(Path(__file__).resolve().parents[1]/"tools/verify_editorial_live.py").read_text(encoding="utf-8")
 assert 'rows("studio_overrides.json", "overrides")' in live_check and 'is_today(row.get("updated_at"))' in live_check, "Live release verification must check Studio edits as well as new articles"
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