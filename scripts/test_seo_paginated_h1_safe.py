#!/usr/bin/env python3
import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_paginated_h1_safe import build
class ArchiveH1(unittest.TestCase):
    def test_nonarchive_pages_unmodified(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'random.html';p.write_text('<h2>News in evidenza</h2>')
            self.assertEqual(build(tmp),{})
    def test_only_page_archives_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'pagina-3.html';p.write_text('<title>Wrong</title>')
            self.assertEqual(build(tmp),{})
if __name__=='__main__':unittest.main()
