import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from route_link_cleanup import strip_orphan_community_anchors


class OrphanCommunityLinkTests(unittest.TestCase):
    def test_orphan_community_anchor_is_unwrapped_and_text_preserved(self):
        html = '<p>Vai alla <a class="old" href="/community-abc123">recensione <strong>storica</strong></a>.</p>'
        cleaned, warnings = strip_orphan_community_anchors(html, set())
        self.assertEqual(cleaned, '<p>Vai alla recensione <strong>storica</strong>.</p>')
        self.assertEqual(warnings, ["/community-abc123"])

    def test_existing_community_page_is_not_changed(self):
        html = '<a href="/community-abc123">articolo</a>'
        cleaned, warnings = strip_orphan_community_anchors(html, {"community-abc123"})
        self.assertEqual(cleaned, html)
        self.assertEqual(warnings, [])

    def test_non_community_and_external_links_are_not_changed(self):
        html = '<a href="/old-flat">legacy</a><a href="https://example.com">external</a>'
        cleaned, warnings = strip_orphan_community_anchors(html, set())
        self.assertEqual(cleaned, html)
        self.assertEqual(warnings, [])

    def test_trailing_slash_and_html_alias_are_normalized_for_existence(self):
        html = '<a href="/community-abc123/">one</a><a href="/community-def456.html">two</a>'
        cleaned, warnings = strip_orphan_community_anchors(html, {"community-abc123", "community-def456"})
        self.assertEqual(cleaned, html)
        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
