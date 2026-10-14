#!/usr/bin/env python3
"""Prove existing Article JSON-LD can gain the real hero without changing page body."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from seo_schema_image_safe import transform, build, LD_SCRIPT

class ArticleImageSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.article=self.root/'new-section'/'article.html'
        self.article.parent.mkdir()
        self.canon='https://zazoomtek.it/new-section/article.html'
        self.body='<body><main><article class="article-main"><h1>Articolo</h1><figure class="hero"><img src="/assets/special/cover.webp" alt="Immagine editoriale originale articolo"></figure><p>Non modificare mai il contenuto</p></article></main></body>'
        self.payload={'@context':'https://schema.org','@type':'NewsArticle','headline':'Una notizia','mainEntityOfPage':self.canon,'datePublished':'2026-10-14','publisher':{'@type':'Organization','name':'ZazoomTek'}}
    def tearDown(self):
        self.temp.cleanup()
    def source(self,payload=None,robots='index,follow'):
        schema=json.dumps(payload or self.payload, ensure_ascii=False)
        return f'<html><head><link rel="canonical" href="{self.canon}"><meta name="robots" content="{robots}"><script type="application/ld+json">{schema}</script></head>'+self.body+'</html>'
    def test_add_only_true_image_keep_dates_and_body(self):
        source=self.source()
        new=transform(self.article,self.root,source)
        obj=json.loads(LD_SCRIPT.search(new).group('json'))
        self.assertEqual(obj['image'],['https://zazoomtek.it/assets/special/cover.webp'])
        self.assertEqual(obj['datePublished'],'2026-10-14')
        self.assertEqual(source[source.index('</head>'):],new[new.index('</head>'):])
        self.assertEqual(new,transform(self.article,self.root,new))
    def test_do_not_replace_image_or_touch_noindex(self):
        known=dict(self.payload,image=['https://example.com/original.jpg'])
        old=self.source(known)
        self.assertEqual(old,transform(self.article,self.root,old))
        old=self.source(robots='noindex,follow')
        self.assertEqual(old,transform(self.article,self.root,old))
    def test_skip_different_canonical_invalid_schema_and_missing_real_image(self):
        old=self.source().replace(self.canon,'https://zazoomtek.it/wrong.html')
        self.assertEqual(old,transform(self.article,self.root,old))
        old=self.source().replace('"NewsArticle"','"FAQPage"')
        self.assertEqual(old,transform(self.article,self.root,old))
        old=self.source().replace('article-main','news-row')
        self.assertEqual(old,transform(self.article,self.root,old))
    def test_new_future_category_is_supported(self):
        (self.root/'index.html').write_text('<head><link rel="canonical" href="https://zazoomtek.it/"></head></html>')
        self.article.write_text(self.source())
        # Only test single-page transformation; full-build guard applies to real site.
        out=transform(self.article,self.root,self.article.read_text())
        self.assertIn('assets/special/cover.webp',out)
if __name__=='__main__': unittest.main()
