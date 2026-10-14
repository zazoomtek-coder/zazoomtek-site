#!/usr/bin/env python3
import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_thumbnail_payload_safe import transform,inspect
BASE='https://yt3.ggpht.com/9FRlJEWGi_Ss_pNt5ErSXTgKUzZ6x2PMYLIJg4zlLdIsxufuePBUH5MLbbYpyhdos48YhYtk7c9d='
class SafeThumbs(unittest.TestCase):
    def test_only_lazy_cards_and_only_the_src(self):
        tag='<img class="article-image" src="'+BASE+'s1600-rw-nd-v1" alt="Review cover with text" loading="lazy" decoding="async">'
        result=transform(tag)
        self.assertIn('s1200-rw-nd-v1',result)
        self.assertEqual(result.replace('s1200-rw-nd-v1','s1600-rw-nd-v1'),tag)
        self.assertEqual(transform(result),result)
        self.assertEqual(transform(tag.replace('lazy','eager')),tag.replace('lazy','eager'))
    def test_hero_and_real_article_and_non_yt_untouched(self):
        src='<img class="hero" loading="lazy" src="'+BASE+'s1600-rw-nd-v1">'
        self.assertEqual(transform(src),src)
        self.assertEqual(transform('<meta property="og:image" content="'+BASE+'s1600-rw-nd-v1">'),'<meta property="og:image" content="'+BASE+'s1600-rw-nd-v1">')
        steam='<img loading="lazy" src="https://shared.fastly.steamstatic.com/store.jpg">'
        self.assertEqual(transform(steam),steam)
        self.assertEqual(transform('<img loading="lazy" src="'+BASE+'s1600-rw-nd-v1" srcset="x 500w">'),'<img loading="lazy" src="'+BASE+'s1600-rw-nd-v1" srcset="x 500w">')
    def test_nested_future_sections_and_no_body_effect_other_than_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            section=root/'new-future-category'
            section.mkdir()
            html='<head><title>Future article</title></head><main><a href="/article">Article</a><img loading="lazy" src="'+BASE+'s1600-rw-nd-v1"></main>'
            path=section/'article.html'
            path.write_text(html)
            changes,pages,images=inspect(root,minimum=1,scope='all')
            self.assertEqual((pages,images),(1,1))
            self.assertIn(path,changes)
            self.assertEqual(changes[path].replace('s1200-rw-nd-v1','s1600-rw-nd-v1'),html)
            self.assertEqual(path.read_text(),html) # read-only until explicit run
if __name__=='__main__':unittest.main()
