#!/usr/bin/env python3
import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_news_archive_descriptions import transform
class Archive(unittest.TestCase):
    def test_each_archive_gets_unique_copy_without_body_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'news-3.html'
            src='<head><title>News - Pagina 3 | ZazoomTek</title><meta name="description" content="Le ultime News pubblicate da ZazoomTek, in ordine cronologico."><link rel="canonical" href="https://zazoomtek.it/news-3.html"></head><body><h1>News</h1></body>'
            out=transform(p,root,src)
            self.assertIn('pagina 3',out)
            self.assertEqual(src.split('</head>')[1],out.split('</head>')[1])
            self.assertEqual(transform(p,root,out),out)
    def test_non_archive_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'news.html'
            src='<head><title>News | ZazoomTek</title></head>'
            self.assertEqual(transform(p,root,src),src)
if __name__=='__main__':unittest.main()
