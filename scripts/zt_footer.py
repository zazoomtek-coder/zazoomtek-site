"""The approved, identical footer used by the homepage and every generated page."""
import re


# One canonical community banner, shared across every page and generated article.
COMMUNITY_HTML = """<div class="zt-community-area">
  <section class="zt-community-banner" aria-labelledby="zt-community-title">
    <div class="zt-community-copy">
      <span class="zt-community-kicker">ZAZOOMTEK COMMUNITY</span>
      <h2 id="zt-community-title">Non perderti le prossime recensioni e news</h2>
      <p>Segui ZazoomTek per ricevere nuovi contenuti su tecnologia, gaming, test e unboxing.</p>
    </div>
    <div class="zt-community-social" aria-label="Seguici sui social">
      <a class="zt-community-icon" href="https://www.youtube.com/@ZazoomTek?sub_confirmation=1" target="_blank" rel="noopener noreferrer" aria-label="Iscriviti su YouTube" title="Iscriviti su YouTube"><img src="https://img.icons8.com/color/96/youtube-play.png" alt="YouTube" loading="lazy" width="46" height="46"></a>
      <a class="zt-community-icon" href="https://www.tiktok.com/@zazoomtek" target="_blank" rel="noopener noreferrer" aria-label="Segui ZazoomTek su TikTok" title="Seguici su TikTok"><img src="https://img.icons8.com/color/96/tiktok--v1.png" alt="TikTok" loading="lazy" width="46" height="46"></a>
      <a class="zt-community-icon" href="https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S" target="_blank" rel="noopener noreferrer" aria-label="Segui il canale WhatsApp di ZazoomTek" title="Seguici su WhatsApp"><img src="https://img.icons8.com/color/96/whatsapp--v1.png" alt="WhatsApp" loading="lazy" width="46" height="46"></a>
    </div>
  </section>
</div>"""

FOOTER_HTML = "<footer class=\"legal-footer zt-unified-footer\" data-zt-footer=\"20261010\">\n  <div class=\"zt-footer-content\">\n    <nav class=\"footer-links footer-main-nav\" aria-label=\"Menu del sito\">\n      <a href=\"/\">Home</a><a href=\"/news.html\">News</a><a href=\"/recensioni-scritte.html\">Recensioni</a><a href=\"/guide.html\">Guide</a><a href=\"/tech-today.html\">Tech Impact</a><a href=\"/gaming-today.html\">Gaming Inside</a><a href=\"https://www.youtube.com/@ZazoomTek/posts\" target=\"_blank\" rel=\"noopener noreferrer\">Community</a><a href=\"https://www.youtube.com/@ZazoomTek/videos\" target=\"_blank\" rel=\"noopener noreferrer\">Video</a>\n    </nav>\n    <div class=\"footer-links\">\n      <a href=\"https://www.youtube.com/@ZazoomTek\" target=\"_blank\" rel=\"noopener\">▶ YouTube</a><a href=\"https://www.patreon.com/ZazoomTek\" target=\"_blank\" rel=\"noopener\">❤️ Patreon</a><a href=\"https://www.tiktok.com/@zazoomtek\" target=\"_blank\" rel=\"noopener\">🎵 TikTok</a><a href=\"https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S\" target=\"_blank\" rel=\"noopener\">💬 WhatsApp</a><a href=\"/rss.xml\" title=\"Feed RSS delle News ZazoomTek\" aria-label=\"Feed RSS delle News ZazoomTek\" class=\"zt-rss-link\"><svg class=\"rss-icon\" width=\"15\" height=\"15\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" aria-hidden=\"true\"><circle cx=\"5\" cy=\"19\" r=\"1.5\" fill=\"currentColor\" stroke=\"none\"/><path d=\"M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16\"/></svg> RSS</a><a href=\"/contatti.html\">Contatti</a><a href=\"/chi-sono.html\">Chi sono</a>\n    </div>\n    <div class=\"legal-links\">\n      <a href=\"/privacy.html\">Privacy Policy</a><a href=\"/cookie.html\">Cookie Policy</a><a href=\"/disclaimer.html\">Disclaimer</a><a href=\"/note-legali.html\">Note legali</a>\n    </div>\n    <div class=\"footer-copy\">© 2026 ZazoomTek · Tecnologia e gaming.</div>\n  </div>\n</footer>"

# Place the banner before the legal/footer links, keeping a single site-wide source.
FOOTER_HTML = FOOTER_HTML.replace(
    '  <div class="zt-footer-content">',
    COMMUNITY_HTML + '\n  <div class="zt-footer-content">',
    1,
)
FOOTER_HTML = FOOTER_HTML.replace('data-zt-footer="20261010"', 'data-zt-footer="20261011community"', 1)

# Previous article templates include either a <div> or <section> with the old
# subscription CTA. Remove only those blocks (including nested divs); do not
# touch the article text, any related links, or boxes in the right sidebar.
_LEGACY_CTA = re.compile(
    r'<(div|section)\b[^>]*\bclass\s*=\s*["\'][^"\']*\bzt-subscribe-cta\b[^"\']*["\'][^>]*>',
    re.I,
)
_TAG = re.compile(r'<(/?)([a-z][\w:-]*)\b[^>]*>', re.I | re.S)


def _remove_legacy_ctas(content):
    start = 0
    while True:
        match = _LEGACY_CTA.search(content, start)
        if not match:
            return content
        tag = match.group(1).lower()
        depth = 1
        ending = None
        for item in _TAG.finditer(content, match.end()):
            if item.group(2).lower() != tag:
                continue
            if item.group(1):
                depth -= 1
            elif not item.group(0).endswith('/>'):
                depth += 1
            if depth == 0:
                ending = item.end()
                break
        if ending is None:
            raise RuntimeError("Incomplete legacy ZazoomTek subscription banner")
        content = content[:match.start()] + content[ending:]
        start = match.start()


_PATTERN = re.compile(r'<footer\b[^>]*>[\s\S]*?</footer>', re.IGNORECASE)

def unify_footer(html, *, include_community=True):
    """Use the shared footer; omit the community banner on the Home only."""
    if not re.search(r'</body\s*>', html, re.IGNORECASE):
        return html
    html = _remove_legacy_ctas(html)
    footer = FOOTER_HTML if include_community else FOOTER_HTML.replace(COMMUNITY_HTML, "", 1)
    updated, count = _PATTERN.subn(lambda _: footer, html, count=1)
    if count == 1:
        return updated
    # Support newly generated pages that do not yet have the legal footer.
    return re.sub(r'</body\s*>', lambda m: footer + '\n' + m.group(0),
                  updated, count=1, flags=re.I)
