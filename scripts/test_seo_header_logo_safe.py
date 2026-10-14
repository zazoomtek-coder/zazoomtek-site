#!/usr/bin/env python3
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_header_logo_safe import rewrite_html,NEW
class HeaderLogo(unittest.TestCase):
    def test_only_logo_tag_within_header(self):
        source='<head><meta property="og:image" content="https://zazoomtek.it/ChatGPT.png"></head><header><a><img class="brand-logo-img" src="ChatGPT.png" alt="ZazoomTek" width="52" height="52"></a><img src="https://img.icons8.com/youtube.png" alt="YouTube"></header><main><img src="/ChatGPT.png" alt="Article logo"></main>'
        out=rewrite_html(source)
        self.assertIn('src="'+NEW+'" alt="ZazoomTek" width="52" height="52"',out)
        self.assertIn('<meta property="og:image" content="https://zazoomtek.it/ChatGPT.png">',out)
        self.assertIn('<main><img src="/ChatGPT.png" alt="Article logo"></main>',out)
        self.assertEqual(rewrite_html(out),out)
    def test_only_exact_source_and_alt(self):
        source='<header><img src="/ChatGPT.png" alt="ZazoomTek"><img src="/ChatGPT.png" alt="Elsewhere"><img src="elsewhere.png" alt="ZazoomTek"></header>'
        out=rewrite_html(source)
        self.assertEqual(out.count(NEW),1)
        self.assertIn('alt="Elsewhere"',out)
if __name__=='__main__':unittest.main()
