import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_continuous_audit import audit

class FutureSections(unittest.TestCase):
    def test_new_nested_section_is_discovered_and_bad_html_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            page=root/'new-category'/'future-article.html'
            page.parent.mkdir()
            page.write_text('<html><head><title>Test</title><link rel="canonical" href="https://zazoomtek.it/new-category/future-article.html"><meta name="description" content="A sample"></head><body>OK</body></html>',encoding='utf-8')
            count,problems=audit(root)
            self.assertEqual(count,1)
            self.assertEqual(problems,[])
            page.write_text('<head><title>Test</title><meta name="robots" content="noindex"></head>',encoding='utf-8')
            count,problems=audit(root)
            self.assertEqual(problems,[])  # intentional noindex is excluded
            page.write_text('<head><title>Test</title></head>',encoding='utf-8')
            _,problems=audit(root)
            self.assertTrue(any(k=='canonical' for _,k,_ in problems))

    def test_draft_folder_ignored(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'drafts').mkdir()
            (root/'drafts'/'hidden.html').write_text('<head></head>')
            count,problems=audit(root)
            self.assertEqual(count,0)
            self.assertEqual(problems,[])
if __name__=='__main__':unittest.main()
