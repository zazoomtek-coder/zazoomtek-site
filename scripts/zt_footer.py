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

FOOTER_HTML = "<footer class=\"legal-footer zt-unified-footer\" data-zt-footer=\"20261010\">\n  <div class=\"zt-footer-content\">\n    <nav class=\"footer-links footer-main-nav\" aria-label=\"Menu del sito\">\n      <a href=\"/\">Home</a><a href=\"/news.html\">News</a><a href=\"/recensioni-scritte.html\">Recensioni</a><a href=\"/guide.html\">Guide</a><a href=\"/tech-today.html\">Tech Impact</a><a href=\"/gaming-today.html\">Gaming Inside</a><a href=\"https://www.youtube.com/@ZazoomTek/posts\" target=\"_blank\" rel=\"noopener noreferrer\">Community</a><a href=\"https://www.youtube.com/@ZazoomTek/videos\" target=\"_blank\" rel=\"noopener noreferrer\">Video</a>\n    </nav>\n    <div class=\"footer-links\">\n      <a href=\"https://www.youtube.com/@ZazoomTek\" target=\"_blank\" rel=\"noopener\">▶ YouTube</a><a href=\"https://www.patreon.com/ZazoomTek\" target=\"_blank\" rel=\"noopener\">❤️ Patreon</a><a href=\"https://www.tiktok.com/@zazoomtek\" target=\"_blank\" rel=\"noopener\">🎵 TikTok</a><a href=\"https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S\" target=\"_blank\" rel=\"noopener\">💬 WhatsApp</a><a href=\"/rss.xml\" title=\"Feed RSS delle News ZazoomTek\" aria-label=\"Feed RSS delle News ZazoomTek\" class=\"zt-rss-link\"><svg class=\"rss-icon\" width=\"15\" height=\"15\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" aria-hidden=\"true\"><circle cx=\"5\" cy=\"19\" r=\"1.5\" fill=\"currentColor\" stroke=\"none\"/><path d=\"M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16\"/></svg> RSS</a><a href=\"/contatti.html\">Contatti</a>\n    </div>\n    <div class=\"legal-links\">\n      <a href=\"/privacy.html\">Privacy Policy</a><a href=\"/cookie.html\">Cookie Policy</a><a href=\"/disclaimer.html\">Disclaimer</a><a href=\"/note-legali.html\">Note legali</a>\n    </div>\n    <div class=\"footer-copy\">© 2026 ZazoomTek · Tecnologia e gaming.</div>\n  </div>\n</footer>"

# The global footer contains ONLY legal/footer links. The community callout
# belongs inside the page's left/main content column.
FOOTER_HTML = FOOTER_HTML.replace('data-zt-footer="20261010"', 'data-zt-footer="20261011community-column"', 1)
COMMUNITY_START = "<!-- ZT_COMMUNITY_BANNER_START -->"
COMMUNITY_END = "<!-- ZT_COMMUNITY_BANNER_END -->"

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
_BANNER_MARKED = re.compile(
    re.escape(COMMUNITY_START) + r'[\s\S]*?' + re.escape(COMMUNITY_END), re.I
)
# Prefer editorial left columns, then a simple main for pages without a sidebar.
_LEFT_CONTENT = (
    re.compile(r'<(article)\b[^>]*class=["\'][^"\']*\barticle-main\b[^"\']*["\'][^>]*>', re.I),
    re.compile(r'<(section)\b[^>]*class=["\'][^"\']*\bnews-main\b[^"\']*["\'][^>]*>', re.I),
    re.compile(r'<(main)\b[^>]*>', re.I),
)


def _matching_close(content, start, tag):
    """Find a matching closing tag even with nested sections/articles."""
    tag_pattern = re.compile(r'</?' + re.escape(tag) + r'\b[^>]*>', re.I)
    depth = 1
    for match in tag_pattern.finditer(content, start):
        if match.group().startswith('</'):
            depth -= 1
        elif not match.group().endswith('/>'):
            depth += 1
        if depth == 0:
            return match.start()
    raise RuntimeError("Unbalanced " + tag + " in community banner target")


# Identify both automatically generated and manually curated related blocks.
# Match the <section> itself (not its nested cards), so insertion is immediately
# after the closing </section>, never after photo credits, other article links,
# or the right-hand editorial sidebar.
_RELATED_SECTION = re.compile(
    r'<section\b[^>]*class=["\'][^"\']*(?:\bzt-related-section\b|\brelated\b)'
    r'[^"\']*["\'][^>]*>', re.I
)


def _place_community_inside_left_column(content):
    for pattern in _LEFT_CONTENT:
        match = pattern.search(content)
        if not match:
            continue
        ending = _matching_close(content, match.end(), match.group(1).lower())
        insertion = ending
        # Only search inside the matched left content element.
        related = list(_RELATED_SECTION.finditer(content, match.end(), ending))
        if related:
            section = related[-1]
            # Insert after the complete related block, before any photo credits.
            insertion = _matching_close(content, section.end(), "section") + len("</section>")
            if insertion > ending:
                raise RuntimeError("Related articles are outside the content column")
        banner = COMMUNITY_START + '\n' + COMMUNITY_HTML + '\n' + COMMUNITY_END
        return content[:insertion] + '\n' + banner + '\n' + content[insertion:]
    return content  # Technical auxiliary HTML; no visible page container.


def unify_footer(html, *, include_community=True):
    """The community CTA stays inside the content column, NEVER in the footer."""
    if not re.search(r'</body\s*>', html, re.IGNORECASE):
        return html
    html = _remove_legacy_ctas(html)
    html = _BANNER_MARKED.sub("", html)
    html = _PATTERN.sub(lambda _: FOOTER_HTML, html, count=1)
    if not _PATTERN.search(html):
        html = re.sub(r'</body\s*>', lambda m: FOOTER_HTML + '\n' + m.group(),
                      html, count=1, flags=re.I)
    if include_community:
        html = _place_community_inside_left_column(html)
    return html
