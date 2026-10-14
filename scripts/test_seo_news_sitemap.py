#!/usr/bin/env python3
import sys,tempfile,unittest,json
from datetime import datetime,timezone
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).parent))
from seo_news_sitemap import entries, make_xml, NEWS_NS, SITEMAP_NS, run

class NewsSitemapSafety(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.now=datetime(2026,10,14,10,0,tzinfo=timezone.utc)
        self.published='2026-10-13T13:03:00Z'
        self.article=self.root/'future-section'/'fresh.html'
        self.article.parent.mkdir()
        self.url='https://zazoomtek.it/future-section/fresh.html'
        self.headline='Nuova notizia su tecnologia & videogiochi'
        self.article.write_text(self.content())
    def tearDown(self):self.temp.cleanup()
    def content(self,published=None,kind='NewsArticle',robots='index,follow'):
        data={'@context':'https://schema.org','@graph':[{'@type':kind,'headline':self.headline,'datePublished':published or self.published,'mainEntityOfPage':{'@id':self.url}}]}
        return '<head><link rel="canonical" href="'+self.url+'"><meta name="robots" content="'+robots+'"><script type="application/ld+json">'+json.dumps(data)+'</script></head><body>Never change</body>'
    def test_recent_nested_url_xml_escape_and_no_write(self):
        e=entries(self.root,self.now)
        self.assertEqual(len(e),1)
        xml=make_xml(e)
        tree=ET.fromstring(xml)
        self.assertEqual(len(tree.findall('{'+SITEMAP_NS+'}url')),1)
        self.assertIn(b'&amp;',xml)
        self.assertIn(b'publication_date',xml)
        self.assertEqual(len(list(self.root.rglob('*.html'))),1)
    def test_old_or_future_or_review_are_excluded(self):
        for date in ('2026-10-11T10:00:00Z','2026-10-16T13:00:00Z'):
            self.article.write_text(self.content(published=date))
            self.assertEqual(entries(self.root,self.now),[])
        self.article.write_text(self.content(kind='Review'))
        self.assertEqual(entries(self.root,self.now),[])
        self.article.write_text(self.content(robots='noindex'))
        self.assertEqual(entries(self.root,self.now),[])
    def test_recent_standard_editorial_news_requires_registry_and_matching_page(self):
        page=self.root/'news-standard-test.html'
        title='Titolo approvato nella redazione'
        meta='<head><link rel="canonical" href="https://zazoomtek.it/news-standard-test.html"><meta property="og:type" content="article"><meta property="og:title" content="'+title+'"><meta name="robots" content="index,follow"></head><body>Testo integrale</body>'
        page.write_text(meta)
        registry={'items':[{'slug':page.name,'title':title,'published_at':'2026-10-14T09:50:00Z','kind':'standard'}]}
        (self.root/'manual-news.json').write_text(json.dumps(registry))
        urls=[r[0] for r in entries(self.root,self.now)]
        self.assertIn('https://zazoomtek.it/news-standard-test.html',urls)
        page.write_text(meta.replace(title,'Titolo diverso'))
        self.assertNotIn('https://zazoomtek.it/news-standard-test.html',[r[0] for r in entries(self.root,self.now)])
        page.write_text(meta)
        registry['items'][0]['published_at']='2026-10-10T09:50:00Z'
        (self.root/'manual-news.json').write_text(json.dumps(registry))
        self.assertNotIn('https://zazoomtek.it/news-standard-test.html',[r[0] for r in entries(self.root,self.now)])

    def test_empty_news_sitemap_is_valid(self):
        self.article.unlink()
        xml=make_xml(entries(self.root,self.now))
        self.assertEqual(len(ET.fromstring(xml)),0)
if __name__=='__main__':unittest.main()
