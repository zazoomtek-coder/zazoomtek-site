#!/usr/bin/env python3
import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_generic_article_headline_safe import transform,build
class Repair(unittest.TestCase):
    def test_generic_article_is_repaired_without_changing_rest_of_article(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'news-test.html'
            title='EA SPORTS presenta nuovi campioni e dettagli del gioco per la stagione'
            body='<body><main><article class="article-main"><h1>News</h1><div class="article-body"><p>'+title+'</p><p>Il testo originale resta intatto.</p></div></article></main></body>'
            source='<html><head><title>News | ZazoomTek</title><meta name="description" content="News"><link rel="canonical" href="https://zazoomtek.it/news-test.html"></head>'+body+'</html>'
            fixed=transform(p,root,source)
            self.assertNotEqual(fixed,source)
            self.assertIn('<h1>'+title+'</h1>',fixed)
            self.assertIn('Il testo originale resta intatto.',fixed)
            self.assertEqual(transform(p,root,fixed),fixed)
            self.assertEqual(source.count('<p>'),fixed.count('<p>'))
    def test_non_generic_review_and_existing_schema_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'news-test.html'
            src='<head><title>Review | ZazoomTek</title><link rel="canonical" href="https://zazoomtek.it/news-test.html"></head><h1>News</h1>'
            self.assertEqual(transform(p,root,src),src)
if __name__=='__main__':unittest.main()
