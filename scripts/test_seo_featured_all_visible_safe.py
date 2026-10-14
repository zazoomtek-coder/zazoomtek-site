#!/usr/bin/env python3
import re,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_featured_all_visible_safe import START,END,transform
BASE='https://yt3.ggpht.com/9FRlJEWGi_Ss_pNt5ErSXTgKUzZ6x2PMYLIJg4zlLdIsxufuePBUH5MLbbYpyhdos48YhYtk7c9d='
class NewsCovers(unittest.TestCase):
    def source(self):
        blocks=[]
        for i in range(6):
            b='<img src="'+BASE+('s1200' if i==0 else 's1600')+'-rw-nd-v1" alt="Notizia '+str(i)+'" loading="'+('eager' if i==0 else 'lazy')+'" decoding="async"'+(' fetchpriority="high"' if i==0 else '')+'>'
            blocks.append('<a class="zt-feature-card" href="/news'+str(i)+'.html">'+b+'</a>')
        return '<head><meta name="robots" content="index,follow"></head><main>'+START+''.join(blocks)+END+'<article>Never change text or content</article></main>'
    def test_six_visible_cards_no_layout_changes(self):
        src=self.source();out=transform(src)
        self.assertEqual(out.count('loading="eager"'),6)
        self.assertEqual(out.count('fetchpriority="high"'),1)
        self.assertEqual(out.count('=s1200-rw-nd-v1'),6)
        self.assertEqual(out[:out.index(START)],src[:src.index(START)])
        self.assertEqual(out[out.index(END):],src[src.index(END):])
        self.assertEqual(re.findall(r'<a\b[^>]+>',out),re.findall(r'<a\b[^>]+>',src))
        self.assertEqual(transform(out),out)
    def test_wrong_number_of_featured_cards_refused(self):
        src=self.source()
        with self.assertRaises(RuntimeError):transform(src.replace('<!-- FEATURED_NEWS_END -->','<img src="extra.jpg"><!-- FEATURED_NEWS_END -->'))
if __name__=='__main__':unittest.main()
