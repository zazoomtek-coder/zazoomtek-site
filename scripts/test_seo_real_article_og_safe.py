#!/usr/bin/env python3
import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_real_article_og_safe import transform
class SafeOG(unittest.TestCase):
    def test_real_article_image_only_head_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'future-category'/'article.html';p.parent.mkdir()
            canon='https://zazoomtek.it/future-category/article.html'
            src='<html><head><title>Articolo</title><link rel="canonical" href="'+canon+'"></head><body><main><article class="article-main"><h1>News</h1><figure class="hero"><img src="/assets/test.webp" alt="Copertina originale di questo articolo"></figure><p>Body immutato</p></article></main></body></html>'
            out=transform(p,root,src)
            self.assertEqual(out.count('property="og:image"'),1)
            self.assertIn('https://zazoomtek.it/assets/test.webp',out)
            self.assertEqual(src.split('</head>')[1],out.split('</head>')[1])
            self.assertEqual(transform(p,root,out),out)
    def test_do_not_replace_existing_or_modify_listings(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'news.html'
            src='<head><link rel="canonical" href="https://zazoomtek.it/news.html"></head><body><main><img src="/assets/cover.webp" alt="News standard molto importante"></main></body>'
            self.assertEqual(transform(p,root,src),src)
            src2=src.replace('</head>','<meta property="og:image" content="https://example.org/existing.png"></head>')
            self.assertEqual(transform(p,root,src2),src2)
    def test_noindex_and_wrong_canonical_are_skipped(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'article.html'
            src='<head><link rel="canonical" href="https://zazoomtek.it/wrong.html"><meta name="robots" content="noindex"></head><article class="article-main"><img src="/image.webp" alt="Cover articolo originale qui"></article>'
            self.assertEqual(transform(p,root,src),src)
if __name__=='__main__':unittest.main()
