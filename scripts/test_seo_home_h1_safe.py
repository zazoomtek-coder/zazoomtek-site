#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_home_h1_safe import transform,BEFORE,AFTER

STYLE='<style>.module-head h2{font-weight:900;font-size:1rem}.module-head h2:after{content:"";height:48px}@media(max-width:720px){.module-head h2{font-size:.8rem}}</style>'
class HomeH1(unittest.TestCase):
    def sample(self):return '<head>'+STYLE+'</head><main><section>'+BEFORE+'<!-- FEATURED_NEWS_START -->PLACEHOLDER<!-- FEATURED_NEWS_END --></section></main>'
    def test_only_existing_visible_heading_and_css_selector_change(self):
        old=self.sample()
        new=transform(old)
        self.assertIn(AFTER,new)
        self.assertEqual(new.count('<h1 '),1)
        self.assertNotIn('.module-head h2',new)
        self.assertEqual(new.count('.module-head :is(h2,h1)'),3)
        self.assertEqual(new.split('<!-- FEATURED_NEWS_START -->')[1],old.split('<!-- FEATURED_NEWS_START -->')[1])
        self.assertEqual(new.split('</style>')[1].replace(AFTER,BEFORE),old.split('</style>')[1])
        self.assertEqual(transform(new),new)
    def test_dont_erase_an_existing_h1_or_change_other_sections(self):
        with self.assertRaises(RuntimeError):transform(self.sample().replace('<main>','<main><h1>Other heading</h1>'))
        with self.assertRaises(RuntimeError):transform(self.sample().replace('News in evidenza','Other'))
if __name__=='__main__':unittest.main()
