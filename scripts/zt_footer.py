"""The approved, identical footer used by the homepage and every generated page."""
import re

FOOTER_HTML = "<footer class=\"legal-footer zt-unified-footer\" data-zt-footer=\"20261010\">\n  <div class=\"zt-footer-content\">\n    <nav class=\"footer-links footer-main-nav\" aria-label=\"Menu del sito\">\n      <a href=\"/\">Home</a><a href=\"/news.html\">News</a><a href=\"/recensioni-scritte.html\">Recensioni</a><a href=\"/guide.html\">Guide</a><a href=\"/tech-today.html\">Tech Impact</a><a href=\"/gaming-today.html\">Gaming Inside</a><a href=\"https://www.youtube.com/@ZazoomTek/posts\" target=\"_blank\" rel=\"noopener noreferrer\">Community</a><a href=\"https://www.youtube.com/@ZazoomTek/videos\" target=\"_blank\" rel=\"noopener noreferrer\">Video</a>\n    </nav>\n    <div class=\"footer-links\">\n      <a href=\"https://www.youtube.com/@ZazoomTek\" target=\"_blank\" rel=\"noopener\">▶ YouTube</a><a href=\"https://www.patreon.com/ZazoomTek\" target=\"_blank\" rel=\"noopener\">❤️ Patreon</a><a href=\"https://www.tiktok.com/@zazoomtek\" target=\"_blank\" rel=\"noopener\">🎵 TikTok</a><a href=\"https://whatsapp.com/channel/0029VbDDqHa7tkjDMTErqM2S\" target=\"_blank\" rel=\"noopener\">💬 WhatsApp</a><a href=\"/rss.xml\" title=\"Feed RSS delle News ZazoomTek\" aria-label=\"Feed RSS delle News ZazoomTek\" class=\"zt-rss-link\"><svg class=\"rss-icon\" width=\"15\" height=\"15\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.5\" stroke-linecap=\"round\" aria-hidden=\"true\"><circle cx=\"5\" cy=\"19\" r=\"1.5\" fill=\"currentColor\" stroke=\"none\"/><path d=\"M4 11a9 9 0 0 1 9 9M4 4a16 16 0 0 1 16 16\"/></svg> RSS</a><a href=\"/contatti.html\">Contatti</a><a href=\"/chi-sono.html\">Chi sono</a>\n    </div>\n    <div class=\"legal-links\">\n      <a href=\"/privacy.html\">Privacy Policy</a><a href=\"/cookie.html\">Cookie Policy</a><a href=\"/disclaimer.html\">Disclaimer</a><a href=\"/note-legali.html\">Note legali</a>\n    </div>\n    <div class=\"footer-copy\">© 2026 ZazoomTek · Tecnologia e gaming.</div>\n  </div>\n</footer>"

_PATTERN = re.compile(r'<footer\b[^>]*>[\s\S]*?</footer>', re.IGNORECASE)

def unify_footer(html):
    """Replace only the footer, preserving the page's article, header, scripts and links."""
    if not re.search(r'</body\s*>', html, re.IGNORECASE):
        return html
    updated, count = _PATTERN.subn(lambda _: FOOTER_HTML, html, count=1)
    return updated if count == 1 else html
