#!/usr/bin/env python3
import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_whole_site_audit import audit,target
class Audit(unittest.TestCase):
    def test_nested_future_category(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            page=root/'new-section'/'story.html'
            page.parent.mkdir()
            page.write_text('<head><title>A detailed original article heading</title><meta name="description" content="A complete descriptive summary about this original article with enough detail."><link rel="canonical" href="https://zazoomtek.it/new-section/story.html"></head><body><h1>Original title</h1><a href="/news.html">News</a></body>')
            r=audit(root)
            self.assertEqual(r['canonical_pages'],1)
            self.assertEqual(r['by_page']['new-section/story.html']['h1'],1)
            self.assertEqual(r['missing_targets'][0][0],'news.html')
    def test_external_and_fragment_links(self):
        self.assertEqual(target('/watch/abc123.html#intro'),'watch/abc123.html')
        self.assertIsNone(target('https://youtube.com/@ZazoomTek'))
        self.assertIsNone(target('#internal'))
if __name__=='__main__':unittest.main()
