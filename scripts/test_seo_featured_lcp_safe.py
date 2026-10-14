#!/usr/bin/env python3
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_featured_lcp_safe import transform, START,END

URL='https://yt3.ggpht.com/9FRlJEWGi_Ss_pNt5ErSXTgKUzZ6x2PMYLIJg4zlLdIsxufuePBUH5MLbbYpyhdos48YhYtk7c9d=s1600-rw-nd-v1'
class SafeFeaturedLcp(unittest.TestCase):
    def sample(self):
        return '<head><meta property="og:image" content="'+URL+'"></head><main>'+START+'<a class="zt-feature-card zt-feature-small" href="/news.html"><img src="'+URL+'" alt="NVIDIA notizia" loading="eager" decoding="async"></a><a class="zt-feature-card" href="/other"><img src="'+URL+'" loading="lazy"></a>'+END+'<section>Never edit</section></main>'
    def test_only_first_image_touched(self):
        src=self.sample()
        out=transform(src)
        self.assertNotEqual(out,src)
        self.assertEqual(out.count('fetchpriority="high"'),1)
        self.assertIn('loading="eager" decoding="async" fetchpriority="high"',out)
        self.assertIn('=s1200-rw-nd-v1',out)
        self.assertEqual(out[:out.index(START)],src[:src.index(START)])
        self.assertEqual(out[out.index(END):],src[src.index(END):])
        self.assertIn('<a class="zt-feature-card" href="/other"><img src="'+URL+'" loading="lazy"></a>',out)
        self.assertEqual(transform(out),out)
    def test_no_modification_without_explicit_eager_featured_card(self):
        old=self.sample().replace('loading="eager"','loading="lazy"')
        self.assertEqual(transform(old),old)
        self.assertEqual(transform('<main><img src="'+URL+'"></main>'),'<main><img src="'+URL+'"></main>')
    def test_preserve_author_provided_priority_or_srcset(self):
        old=self.sample().replace('loading="eager" decoding="async"','loading="eager" decoding="async" srcset="a.jpg 500w"')
        self.assertEqual(transform(old),old)
if __name__=='__main__':unittest.main()
