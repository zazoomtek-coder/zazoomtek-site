#!/usr/bin/env python3
import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_public_health_readonly import check
class Health(unittest.TestCase):
    def test_valid_future_growing_site(self):
        prefix='https://zazoomtek.it'
        sitemap='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{prefix}/page{i}.html</loc></url>' for i in range(510))+'</urlset>'
        videos='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"><url><loc>'+prefix+'/watch/tEkXOj7XOwA.html</loc><video:video><video:title>Title</video:title></video:video></url></urlset>'
        news='<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"><url><loc>'+prefix+'/news.html</loc><news:news/></url></urlset>'
        documents={
          '/robots.txt':'User-agent: *\n'+''.join('Sitemap: '+prefix+p+'\n' for p in ['/sitemap.xml','/news-sitemap.xml','/video-sitemap.xml']),
          '/sitemap.xml':sitemap,'/news-sitemap.xml':news,'/video-sitemap.xml':videos,
          '/':'<head><link rel="canonical" href="'+prefix+'/"></head><main><h1>Home</h1></main>',
          '/watch/tEkXOj7XOwA.html':'<head><link rel="canonical" href="'+prefix+'/watch/tEkXOj7XOwA.html"><script>VideoObject</script></head><h1>Watch</h1>'
        }
        report=check(lambda x: documents[x])
        self.assertEqual(report['canonical'],510)
        self.assertEqual(report['videos'],1)
        self.assertEqual(report['findings'],[])
    def test_missing_video_is_reported(self):
        docs={'/robots.txt':'','/sitemap.xml':'<urlset/>','/news-sitemap.xml':'<urlset/>','/video-sitemap.xml':'<urlset/>','/':'<head></head>','/watch/tEkXOj7XOwA.html':'<head></head>'}
        report=check(lambda x:docs[x])
        self.assertTrue(report['findings'])
if __name__=='__main__':unittest.main()
