"""Offline tests for live SEO auditor: no production requests or changes."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree.ElementTree import Element, SubElement, tostring

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seo_live_audit as audit

BASE = "https://zazoomtek.it"


def fixture(broken=False):
    urlset = Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    for path in ("/", "/news", "/news-tech", "/news-gaming", "/recensioni-tech",
                 "/recensioni-gaming", "/guide", "/speciali", "/extra", "/cybercultura",
                 "/community-ugkxhw4e98tezptpdc7opr4e9dcs53bsioey",
                 "/community-ugkxbplv8ezectqusjybr33rtc48zl8cdbto"):
        item = SubElement(urlset, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        SubElement(item, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = BASE + path
    xml = tostring(urlset)
    def respond(url):
        if url.endswith("/robots.txt"):
            return 200, url, ("User-agent: *\\nAllow: /\\nSitemap: " + BASE +
                                   "/sitemap.xml\\n").replace("\\n", "\n").encode(), {}
        if url.endswith("/sitemap.xml"):
            return 200, url, xml, {}
        if url.endswith(".html"):
            clean = url.removesuffix(".html")
            return 200, clean, ('<link rel="canonical" href="' + clean + '">').encode(), {}
        if broken and url == BASE + "/news":
            return 404, url, b"Not found", {}
        return 200, url, ('<html><head><title>Title</title><link rel="canonical" href="' + url +
                          '"><meta name="robots" content="index,follow"></head><body><h1>Title</h1></body></html>').encode(), {}
    return respond


class LiveAuditTests(unittest.TestCase):
    def test_clean_site_passes(self):
        with patch.object(audit, "request", side_effect=fixture()):
            result = audit.audit(BASE, sample=2)
        self.assertEqual(result["errors"], [])

    def test_broken_public_page_fails(self):
        with patch.object(audit, "request", side_effect=fixture(broken=True)):
            result = audit.audit(BASE, sample=2)
        self.assertTrue(any("HTTP 404" in error for error in result["errors"]))

    def test_invalid_canonical_fails(self):
        original = fixture()
        def respond(url):
            data = original(url)
            if url == BASE + "/news":
                return 200, url, b'<link rel="canonical" href="https://example.com/">', {}
            return data
        with patch.object(audit, "request", side_effect=respond):
            result = audit.audit(BASE, sample=2)
        self.assertTrue(any("canonical mismatch" in error for error in result["errors"]))

    def test_noindex_fails(self):
        original = fixture()
        def respond(url):
            data = original(url)
            if url == BASE + "/news":
                return 200, url, (b'<link rel="canonical" href="https://zazoomtek.it/news">'
                                  b'<meta name="robots" content="noindex,follow">'), {}
            return data
        with patch.object(audit, "request", side_effect=respond):
            result = audit.audit(BASE, sample=2)
        self.assertTrue(any("noindex" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
