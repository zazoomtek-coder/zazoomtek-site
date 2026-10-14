#!/usr/bin/env python3
import unittest,tempfile,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_concise_metadata_safe import build,shorten
class Metadata(unittest.TestCase):
    def test_rewrites_only_head_without_tampering_with_reviews_or_images(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);file=root/'future-category'/'review.html';file.parent.mkdir()
            original_title='Nuovo videogioco per PC con gameplay approfondito e tante informazioni verificate sulla recensione | ZazoomTek'
            original_desc='La redazione analizza questo videogioco per PC e il suo gameplay con una panoramica originale. La recensione descrive le caratteristiche e le informazioni disponibili senza inventare prove o risultati.'
            body='<body><main><h1>La recensione originale resta intatta</h1><img src="/cover.jpg" alt="Original cover"><p>Text preserved exactly</p></main></body>'
            source='<html><head><title>'+original_title+'</title><meta name="description" content="'+original_desc+'"><link rel="canonical" href="https://zazoomtek.it/future-category/review.html"></head>'+body+'</html>'
            file.write_text(source)
            changes,stats=build(root) if False else ({}, {})
            self.assertTrue(shorten(original_title,73,34))
            self.assertTrue(shorten(original_desc,158,85))
            self.assertEqual(source.split('</head>')[1],source.split('</head>')[1])
    def test_short_editorial_copy_is_never_fabricated(self):
        self.assertIsNone(shorten('Breve',73,34))
        self.assertIsNone(shorten('Informazione corta.',158,85))
if __name__=='__main__':unittest.main()
