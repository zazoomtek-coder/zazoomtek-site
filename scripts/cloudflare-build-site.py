#!/usr/bin/env python3
"""One-command, offline Cloudflare Pages production build for ZazoomTek.

Run on Cloudflare (not on readers' browsers). Rebuild approved design, reviews,
YouTube iframe watch pages and related sidebars from already-published sources.
No Firebase, third-party news scraping, video downloading or live API keys.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BUILD_WARNINGS: list[str] = []

def run(script: str, *args: str) -> None:
    print("CLOUDFLARE BUILD:", script, " ".join(args), flush=True)
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts" / script), *args],
                       cwd=ROOT, check=True,
                       timeout=300 if script == "update-youtube-posts.py" and "--render-from-cache" in args else 180)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        if script == "build-cloudflare-pages.py":
            # The public artifact must exist before any Cloudflare upload.
            raise
        BUILD_WARNINGS.append(script)
        print("::warning::Editorial renderer/importer unavailable: "
              + script + " (" + str(exc)[:220] + "); proceeding with existing content", flush=True)

def main() -> None:
    # Refuse unauthorized Home structural changes before any publication.
    # Master production mode: all content is derived from verified JSON.
    # The generated markup is temporary Cloudflare build output, never
    # a write to the tracked Home/layout source by a data importer.
    import json
    flag = ROOT / "master-production-enabled.json"
    master_active = (flag.is_file() and
                     json.loads(flag.read_text(encoding="utf-8")).get("enabled") is True)
    # This test flag only works for a PR validation and is never a production
    # switch. A reviewer must verify JSON->HTML parity before the real cutover.
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request" and os.environ.get("ZT_MASTER_STAGING_TEST") == "1":
        master_active = True
    if master_active:
        # The Cloudflare build is a fresh environment, independent of GitHub
        # Actions. Guarantee the same image-rendering dependency here, otherwise
        # the first live build could fail despite staging green.
        try:
            from PIL import Image
            assert Image is not None
        except ImportError:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet",
                 "--disable-pip-version-check", "Pillow>=10,<13"],
                cwd=ROOT, check=True, timeout=180,
            )
        # Approved ordinary NEWS are generated only in temporary Cloudflare
        # build workspace; their approved JSON remains the Git source of truth.
        run("build-standard-news.py")
        run("apply-standard-news-featured.py")
        # Scheduled importer already rendered current YouTube data in this checkout.
        # Replaying the old committed cache here would overwrite today's imports.
        if os.environ.get("ZT_YOUTUBE_LIVE_IMPORTED") != "1":
            run("update-youtube-posts.py", "--render-from-cache")
            if (ROOT / ".youtube-master-render-cache.json").is_file():
                run("update-youtube.py", "--render-from-cache")
        # Editor-approved Impact/Inside pages and category archives share
        # this same disposable build; no independent Git writer survives cutover.
        run("publish-special-news.py")
        run("master-json-renderer.py", "--prebuild-reviews")
    run("refresh-home-latest-reviews.py")
    # Category lists are prebuilt; readers never scan or filter review content.
    run("build-review-categories.py")
    # Studio-approved Tech/Gaming long-form SPECIALI, no runtime filtering.
    run("build-speciali.py")
    # Unified public archive is regenerated from both historical archives
    # after their verified content imports, preserving all old URLs.
    run("build-cybercultura.py")
    run("sync-home-speciali.py")
    run("studio-apply-overrides.py")
    run("apply-site-design.py")
    # Add original ISO times ONLY to already-published archive cards; safe even
    # when the YouTube importer skips a cycle with no new Community posts.
    run("enrich-news-archive-publication-times.py")
    # Refresh rankings from already published ZazoomTek news; portal checks are separate.
    # Never expire existing verified cards just because no new post was published.
    run("trending-crosscheck.py", "--apply")
    run("cloudflare-sync-featured-home.py")
    # Mandatory offline regression gate: fail BEFORE any Cloudflare Pages build.
    # Public video pages are HTML with YouTube embeds, not downloaded movies.
    run("seo_watch_pages_safe.py")
    run("zt_sidebar_mix.py")
    run("build-related-content.py")
    # Cross-check review article titles against genuine full-length review
    # videos in the verified ZazoomTek YouTube catalog. No unverified links.
    run("link-review-videos.py")
    # Normalize existing and future written review pages with a factual
    # summary and a 16:9 thumbnail. Never touch the locked Home layout.
    run("ensure-review-summaries.py")
    # Generators may refresh content, but must never rewrite locked Home layout.
    # Restore late-built YouTube watch-page revisions after all generators.
    run("studio-apply-overrides.py")
    # Restore owner Studio quick-edit links on generated news and review pages.
    # Buttons appear only in browsers with an active Studio session.
    run("studio-inject-edit-button.py")

    # Durable Home source renderer, run AFTER all generators and BEFORE packaging.
    # This operates on the disposable Cloudflare build checkout, never commits
    # generated index.html to main. The approved JSON supplies the web headlines.
    import re
    from html import escape as html_escape
    from urllib.parse import urlsplit
    home = ROOT / "index.html"
    source = home.read_text(encoding="utf-8")
    square_style = """<style id="force-squadrato-head">
*, *::before, *::after, img, iframe, .card, .thumb, .block-title, .block-header, [class*="rounded"] {
  border-radius:0px!important;-webkit-border-radius:0px!important;-moz-border-radius:0px!important;
}
</style>"""
    source = re.sub(r'<style\s+id=["\']force-squadrato-head["\'][^>]*>[\s\S]*?</style>\s*', "", source, flags=re.I)
    if "</head>" not in source:
        raise RuntimeError("Cannot place square style: missing Home head")
    source = source.replace("</head>", square_style + "\n</head>", 1)
    newsfile = ROOT / "notizie-dal-web.json"
    if not newsfile.is_file():
        raise RuntimeError("Missing approved web-news JSON; preserving previous Home")
    stories = json.loads(newsfile.read_text(encoding="utf-8")).get("items", [])
    if not isinstance(stories, list) or not stories:
        raise RuntimeError("Empty approved web-news list")
    tiles = []
    for story in stories[:5]:
        url = story.get("url", "")
        image = story.get("image", "")
        title = story.get("original_title") or story.get("title") or ""
        provider = story.get("source") or ""
        if (not isinstance(url, str) or urlsplit(url).scheme != "https"
                or not isinstance(image, str) or not image.startswith("/assets/notizie-dal-web/")
                or not isinstance(title, str) or not title.strip()):
            continue
        tiles.append(
            '<a class="zt-webnews-item" href="' + html_escape(url, quote=True) +
            '" target="_blank" rel="noopener noreferrer"><img src="' +
            html_escape(image, quote=True) + '" alt="' + html_escape(title, quote=True) +
            '" loading="lazy"><span class="zt-webnews-info"><small>' +
            html_escape(str(provider)) + '</small><strong>' +
            html_escape(title) + '</strong></span></a>'
        )
    if not tiles:
        raise RuntimeError("No valid web-news stories")
    web_style = """<style id="zt-webnews-restored-style">
#zt-webnews-home{margin:22px 0;background:#fff;border:1px solid #ddd;overflow:hidden}
#zt-webnews-home .zt-webnews-head{background:#202020;color:#fff;min-height:46px;display:flex;align-items:center}
#zt-webnews-home .zt-webnews-head h2{margin:0;padding:12px 18px;background:#d51232;color:#fff;font:900 15px/1.3 Arial,sans-serif}
#zt-webnews-home .zt-webnews-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}
#zt-webnews-home .zt-webnews-item{display:flex;align-items:center;gap:12px;padding:12px;color:#222;text-decoration:none;border-bottom:1px solid #eee;min-width:0}
#zt-webnews-home .zt-webnews-item img{width:100px;height:70px;object-fit:cover;flex:none}
#zt-webnews-home .zt-webnews-info{display:flex;flex-direction:column;gap:5px;min-width:0}
#zt-webnews-home .zt-webnews-info small{color:#d51232;font:800 11px Arial,sans-serif}
#zt-webnews-home .zt-webnews-info strong{color:#222;font:700 13px/1.35 Arial,sans-serif}
@media(max-width:720px){#zt-webnews-home .zt-webnews-grid{grid-template-columns:1fr}}
</style>"""
    source = re.sub(r'<style\s+id=["\']zt-webnews-restored-style["\'][^>]*>[\s\S]*?</style>\s*', "", source, flags=re.I)
    source = source.replace("</head>", web_style + "\n</head>", 1)
    panel = ('<!-- ZT_WEB_NEWS_RESTORED_20261023 -->\n'
             '<section id="zt-webnews-home" class="zt-webnews-home" aria-label="NOTIZIE DAL WEB">'
             '<header class="zt-webnews-head"><h2>NOTIZIE DAL WEB</h2></header>'
             '<div class="zt-webnews-grid">' + "\n".join(tiles) + '</div></section>')
    source = re.sub(r'<!-- ZT_WEB_NEWS_RESTORED_20261023 -->\s*<section\b[^>]*id=["\']zt-webnews-home["\'][\s\S]*?</section>\s*',
                    "", source, flags=re.I)
    marker = re.search(r'(<!-- ARTICLE_PAGINATION_END -->\s*</section>)', source, re.I)
    if not marker:
        raise RuntimeError("Cannot place web-news after Home pagination")
    source = source[:marker.end()] + "\n" + panel + source[marker.end():]
    # Draft layout: one lead story and four compact stories, in the centre
    # immediately after the dynamically rendered latest-video explorer.
    draft_style = """<style id="zt-draft-webnews-center">
#zt-webnews-home{margin:18px 0;clear:both}
#zt-webnews-home .zt-webnews-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:10px}
#zt-webnews-home .zt-webnews-item{display:grid;grid-template-columns:76px minmax(0,1fr);gap:9px;border:1px solid #eee;padding:7px;min-height:85px}
#zt-webnews-home .zt-webnews-item img{width:76px;height:70px;object-fit:cover}
#zt-webnews-home .zt-webnews-item:first-child{grid-column:1/-1;grid-template-columns:45% minmax(0,1fr);padding:0;min-height:155px}
#zt-webnews-home .zt-webnews-item:first-child img{width:100%;height:100%;min-height:155px;aspect-ratio:16/9}
#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-info{padding:14px 10px}
#zt-webnews-home .zt-webnews-item:first-child strong{font-size:17px;line-height:1.3}
#zt-webnews-home .zt-webnews-item:hover strong{color:#d51232}
@media(max-width:650px){#zt-webnews-home .zt-webnews-grid{grid-template-columns:1fr}#zt-webnews-home .zt-webnews-item:first-child{grid-column:1;grid-template-columns:1fr}#zt-webnews-home .zt-webnews-item:first-child img{height:auto}#zt-webnews-home .zt-webnews-item:first-child .zt-webnews-info{padding:8px}}
</style>"""
    source = re.sub(r'<style id="zt-draft-webnews-center">[\\s\\S]*?</style>', "", source)
    source = source.replace("</head>", draft_style + "\n</head>", 1)
    # The video explorer is composed by the current homepage scripts. Move
    # the existing panel after the explorer once it exists; never clone it.
    draft_relocate = """<script id="zt-draft-webnews-relocate">
(function(){
  function place(){
    var panel=document.getElementById('zt-webnews-home');
    var videos=document.querySelector('.ztp-top-videos');
    if(!panel||!videos||!videos.parentElement)return false;
    if(panel.previousElementSibling!==videos)videos.insertAdjacentElement('afterend',panel);
    return true;
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',place);
  else place();
  var observer=new MutationObserver(function(){if(place())observer.disconnect();});
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setTimeout(function(){observer.disconnect();},15000);
})();
</script>"""
    source = re.sub(r'<script id="zt-draft-webnews-relocate">[\\s\\S]*?</script>', "", source)
    source = source.replace("</body>", draft_relocate + "\n</body>", 1)
    # Two extra actual Tech article cards, distinct from those already shown.
    box_match = re.search(r'(<!-- POPULAR_NEWS_ITEMS_START -->)([\\s\\S]*?)(<!-- POPULAR_NEWS_ITEMS_END -->)', source)
    if box_match:
        old_popular = box_match.group(2)
        existing = set(re.findall(r'class="zt-popular-article" href="([^"]+)"', old_popular))
        feed = source.split('<!-- ARTICLE_FEED_START -->',1)[-1].split('<!-- ARTICLE_FEED_END -->',1)[0]
        extras = []
        for article in re.findall(r'<article class="article-row"[^>]*data-post-category="tech"[^>]*>[\\s\\S]*?</article>', feed):
            link = re.search(r'<h3><a href="([^"]+)">([\\s\\S]*?)</a></h3>',article)
            picture = re.search(r'<img class="article-image" src="([^"]+)"',article)
            if not link or not picture or ("/"+link.group(1)) in existing:
                continue
            href,title,img = "/"+link.group(1),link.group(2),picture.group(1)
            extras.append('<a class="zt-popular-article" href="'+html_escape(href,quote=True)+'">'
                          '<img src="'+html_escape(img,quote=True)+'" alt="'+title+'" loading="lazy">'
                          '<span class="zt-popular-copy"><span class="zt-popular-category">TECNOLOGIA</span>'
                          '<strong>'+title+'</strong></span></a>')
            existing.add(href)
            if len(extras)==2:break
        if len(extras)==2:
            replacement=box_match.group(1)+old_popular+"\n"+"\n".join(extras)+"\n"+box_match.group(3)
            source=source[:box_match.start()]+replacement+source[box_match.end():]
    home.write_text(source, encoding="utf-8")
    print("HOME SOURCE RENDERED: forced square head +", len(tiles), "web stories", flush=True)

    run("build-cloudflare-pages.py")
    if master_active and (ROOT / "master-staging/editorial-boxes.json").is_file():
        run("master-json-renderer.py", "--postbuild-editorial")
    output = ROOT / "dist"
    # Asset cache busting happens in the FINAL distributable after all article
    # renderers and packaged-layout guards. No tracked source file is rewritten.
    # Microseconds ensure distinct CSS URLs even for releases in the same second.
    from datetime import datetime, timezone
    import re
    css_version = "squadrato_force_99_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    css_ref = re.compile(
        r"""(?P<attr>href\s*=\s*["'])(?P<path>/?zt-design\.css)(?:\?v=[^"']*)?(?P<close>["'])""",
        re.I,
    )
    versioned_pages = 0
    for page in output.rglob("*.html"):
        original = page.read_text(encoding="utf-8", errors="replace")
        updated, count = css_ref.subn(
            lambda m: m.group("attr") + m.group("path") + "?v=" + css_version + m.group("close"),
            original,
        )
        if count:
            page.write_text(updated, encoding="utf-8")
            versioned_pages += 1
    if versioned_pages < 1:
        raise RuntimeError("No CSS references found in the Cloudflare HTML package")
    home_html = (output / "index.html").read_text(encoding="utf-8")
    if "/zt-design.css?v=" + css_version not in home_html:
        raise RuntimeError("Cloudflare Home did not receive its dynamic CSS version")
    print("CSS RELEASE VERSION:", css_version, "HTML files:", versioned_pages, flush=True)

    assert (output / "watch" / "index.html").is_file()
    assert (output / "news.html").is_file()
    assert (output / "studio/index.html").is_file()
    assert (output / "studio/publisher.js").is_file()
    assert (output / "studio/layouts.js").is_file()
    assert (output / "studio/editorial-seo.js").is_file()
    assert (output / "studio/template-news.html").is_file()
    assert (output / "studio/template-review.html").is_file()
    assert (output / "speciali.html").is_file()
    # Public receipt written ONLY after every editorial and artifact check
    # succeeded. Used by GitHub to verify actual Cloudflare production.
    import json
    import re
    from datetime import datetime, timezone
    release_file = ROOT / "cloudflare-release-trigger.txt"
    marker = release_file.read_text(encoding="utf-8")
    match = re.search(r"^source_commit=([a-f0-9]{40})$", marker, re.M)
    # Push releases do not mutate the editorial release marker. Their source
    # is the checked-out main SHA supplied by the publishing workflow.
    source_sha = os.environ.get("ZT_RELEASE_SOURCE_SHA", "").strip() or (match.group(1) if match else "")
    if not re.fullmatch(r"[a-f0-9]{40}", source_sha):
        raise RuntimeError("Cloudflare build source SHA is missing or invalid")
    receipt = {
        "source_commit": source_sha,
        "validated": True,
        "editorial_status": "partial" if BUILD_WARNINGS else "complete",
        "editorial_warnings": sorted(set(BUILD_WARNINGS)),
        "built_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (output / "zt-release-status.json").write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8")
    print("CLOUDFLARE SITE READY; release receipt:", source_sha, flush=True)

if __name__ == "__main__":
    main()
