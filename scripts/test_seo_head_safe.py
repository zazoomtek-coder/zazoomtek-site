#!/usr/bin/env python3
"""Safety tests for optional SEO metadata, no live site access."""
import importlib.util
import json
import re
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('meta', Path(__file__).with_name('seo_head_safe.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HeadSeoTests(unittest.TestCase):
    def test_add_article_schema_and_image_permission_without_touching_body(self):
        head = '<html><head><link rel="canonical" href="https://zazoomtek.it/news-example.html"><meta property="og:type" content="article"><meta property="og:title" content="Notizia &amp; analisi"><meta name="description" content="Testo verificato"><meta name="author" content="ZazoomTek"><meta property="og:image" content="https://zazoomtek.it/cover.jpg"><meta property="article:published_time" content="2026-10-14T09:00:00+02:00"></head>'
        source = head + '<body><h1>Non modificare</h1><script>var x=1</script></body></html>'
        out = mod.transform('news-example.html',source)
        self.assertEqual(source.split('</head>')[1],out.split('</head>')[1])
        self.assertIn('max-image-preview:large',out)
        data=json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>',out).group(1))
        self.assertEqual(data['@type'],'NewsArticle')
        self.assertEqual(data['headline'],'Notizia & analisi')
        self.assertEqual(mod.transform('news-example.html',out),out)

    def test_preserve_existing_schema_and_preview_controls(self):
        source = '<head><link rel="canonical" href="https://zazoomtek.it/recensione-example.html"><meta name="robots" content="max-image-preview:standard"><meta property="og:type" content="article"><script type="application/ld+json">{"@type":"Article"}</script></head><body>ok</body>'
        self.assertEqual(mod.transform('recensione-example.html',source),source)

    def test_future_category_path_is_supported_without_body_changes(self):
        source='<head><link rel="canonical" href="https://zazoomtek.it/new-category/editorial.html"><meta property="og:type" content="article"><meta property="og:title" content="Nuova sezione"><meta name="description" content="Test"></head><body>Unchanged</body>'
        value=mod.transform('editorial.html',source,{'https://zazoomtek.it/new-category/editorial.html'})
        self.assertIn('max-image-preview:large',value)
        self.assertIn('"@type":"Article"',value)
        self.assertEqual(source.split('</head>')[1],value.split('</head>')[1])

    def test_never_change_noindex_or_mismatched_canonical(self):
        source = '<head><link rel="canonical" href="https://zazoomtek.it/ignored.html"><meta name="robots" content="noindex"></head><body>ok</body>'
        self.assertEqual(mod.transform('ignored.html',source),source)
        self.assertEqual(mod.transform('other.html',source),source)

if __name__ == '__main__':
    unittest.main()
