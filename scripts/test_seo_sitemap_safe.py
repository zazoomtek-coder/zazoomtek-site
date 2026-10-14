#!/usr/bin/env python3
"""Isolated SEO sitemap tests: never alter the live site."""
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).with_name('seo_sitemap_safe.py')
spec = importlib.util.spec_from_file_location('seo_sitemap_safe', SCRIPT)
seo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seo)

class SitemapSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.write('index.html', '<head><link rel="canonical" href="https://zazoomtek.it/"></head>')
        self.write('news.html', '<head><meta property="article:published_time" content="2026-10-13T12:00:00+02:00"><link rel="canonical" href="https://zazoomtek.it/news.html"></head>')
        self.write('excluded.html', '<head><link rel="canonical" href="https://zazoomtek.it/excluded.html"><meta name="robots" content="NOINDEX, follow"></head>')
        self.write('preview-test.html', '<head><link rel="canonical" href="https://zazoomtek.it/preview-test.html"></head>')
        self.write('foreign.html', '<head><link rel="canonical" href="https://wrong.example/foreign.html"></head>')
        self.write('dup.html', '<head><link rel="canonical" href="https://zazoomtek.it/dup.html"><link rel="canonical" href="https://zazoomtek.it/dup.html"></head>')

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        (self.root / name).write_text(data, encoding='utf-8')

    def test_index_only_canonical_and_valid_date(self):
        result, count = seo.build(self.root)
        self.assertEqual(count, 2)
        sitemap = result['sitemap.xml']
        root = ET.fromstring(sitemap)
        ns = {'s': seo.SITEMAP_NS}
        self.assertEqual(len(root.findall('s:url', ns)), 2)
        self.assertIn(b'<lastmod>2026-10-13</lastmod>', sitemap)
        self.assertNotIn(b'excluded.html', sitemap)
        self.assertNotIn(b'preview-test.html', sitemap)
        self.assertNotIn(b'foreign.html', sitemap)
        self.assertNotIn(b'dup.html', sitemap)

    def test_new_nested_sections_are_discovered_without_duplicate_urls(self):
        folder=self.root / 'future' / 'editorial'
        folder.mkdir(parents=True)
        (folder/'index.html').write_text(
            '<head><link rel="canonical" href="https://zazoomtek.it/future/editorial/"></head>',
            encoding='utf-8')
        (folder/'article.html').write_text(
            '<head><link rel="canonical" href="https://zazoomtek.it/future/editorial/article.html"></head>',
            encoding='utf-8')
        forbidden=self.root / 'scripts'
        forbidden.mkdir()
        (forbidden/'internal.html').write_text(
            '<head><link rel="canonical" href="https://zazoomtek.it/scripts/internal.html"></head>',
            encoding='utf-8')
        output,count=seo.build(self.root)
        self.assertEqual(count,4)
        self.assertIn(b'https://zazoomtek.it/future/editorial/',output['sitemap.xml'])
        self.assertIn(b'https://zazoomtek.it/future/editorial/article.html',output['sitemap.xml'])
        self.assertNotIn(b'/scripts/internal.html',output['sitemap.xml'])

    def test_same_canonical_newsarticle_date_modified_is_used(self):
        self.write('tech-impact-example.html',
                   '<head><link rel="canonical" href="https://zazoomtek.it/tech-impact-example.html">'
                   '<script type="application/ld+json">'
                   '{"@context":"https://schema.org","@graph":['
                   '{"@type":"NewsArticle","mainEntityOfPage":"https://zazoomtek.it/tech-impact-example.html",'
                   '"datePublished":"2026-10-04","dateModified":"2026-10-12"},'
                   '{"@type":"NewsArticle","mainEntityOfPage":"https://zazoomtek.it/not-this-page.html",'
                   '"dateModified":"2026-10-14"}]}'
                   '</script></head><body>Article unchanged</body>')
        xml,_=seo.build(self.root)
        root=ET.fromstring(xml['sitemap.xml'])
        ns={'s':seo.SITEMAP_NS}
        matches=[node for node in root.findall('s:url',ns)
                 if node.find('s:loc',ns).text=='https://zazoomtek.it/tech-impact-example.html']
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0].find('s:lastmod',ns).text,'2026-10-12')
        self.assertNotIn(b'not-this-page.html',xml['sitemap.xml'])
    def test_unverified_dates_cannot_change_sitemap(self):
        self.write('news-future.html',
                   '<head><link rel="canonical" href="https://zazoomtek.it/news-future.html">'
                   '<script type="application/ld+json">'
                   '{"@type":"NewsArticle","mainEntityOfPage":"https://zazoomtek.it/news-future.html",'
                   '"dateModified":"2099-01-01"}'
                   '</script></head>')
        rows=seo.entries(self.root)
        item=next((x for x in rows if x[0].endswith('news-future.html')),None)
        self.assertIsNotNone(item)
        self.assertIsNone(item[1])
    def test_dry_run_and_repeat_are_safe(self):
        result, _ = seo.build(self.root)
        self.assertEqual(len(seo.publish(self.root, result, check=True)), 3)
        self.assertFalse((self.root / 'sitemap.xml').exists())
        self.assertEqual(len(seo.publish(self.root, result)), 3)
        self.assertEqual(seo.publish(self.root, result), [])

    def test_refuse_missing_home_canonical(self):
        self.write('index.html', '<head><meta name="robots" content="noindex"></head>')
        with self.assertRaises(ValueError):
            seo.build(self.root)

if __name__ == '__main__':
    unittest.main()
