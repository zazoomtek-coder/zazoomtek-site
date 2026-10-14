#!/usr/bin/env python3
import tempfile,unittest,json,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_watch_pages_safe import build,make_video,make_directory,feed_items,MAX_ITEMS
from seo_media_safe import verified_video,feed_videos
from seo_video_sitemap_safe import watch_candidate

class VideoWatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        header='<header class="zt-header"><nav class="zt-nav"><a href="/">Home</a></nav></header>'
        footer='<footer><p>ZazoomTek</p></footer>'
        (self.root/'news.html').write_text('<head></head><body>'+header+footer+'</body>')
        self.header,self.footer=header,footer
        self.items=[]
        for i in range(12):
            ident='abcdEFGh'+str(i).zfill(3)
            self.items.append({'id':ident,'title':f'Video originale ZazoomTek numero {i} su piattaforma PC',
                               'publishedAt':'2026-10-13T09:00:00Z','category':'recensioni','short':i%2==0,'live':False})
        (self.root/'home-video-feed.json').write_text(json.dumps(self.items))
    def tearDown(self):self.tmp.cleanup()
    def test_generated_watch_pages_have_video_main_schema_and_canonical(self):
        pages,n=build(self.root)
        self.assertEqual(n,12)
        self.assertEqual(len(pages),13)
        for name,source in pages.items():
            self.assertEqual(source.count('<h1'),1)
            if name.endswith('/index.html'):continue
            path=self.root/name
            self.assertIsNone(watch_candidate(path,self.root,feed_videos(self.root)) if path.exists() else None)
            self.assertEqual(source.count('<iframe'),1)
            self.assertIn('application/ld+json',source)
            self.assertIn('mainEntityOfPage',source)
            self.assertIn('loading="eager"',source)
        self.assertEqual(len(re.findall(r'href="/watch/abcdEFGh\d{3}\.html"',pages['watch/index.html'])),12)
    def test_no_duplicate_or_unverified_ids(self):
        self.items.append(self.items[0])
        self.items.append({'id':'not-id','title':'Bad','publishedAt':'2026-10-14T00:00:00Z'})
        self.items.append({'id':'abcdefgH999','title':'Sconosciuto','publishedAt':'future'})
        (self.root/'home-video-feed.json').write_text(json.dumps(self.items))
        out=feed_items(self.root)
        self.assertEqual(len(out),12)
    def test_future_live_not_started_excluded(self):
        self.items[0]['live']=True
        self.items[0]['completedLive']=False
        (self.root/'home-video-feed.json').write_text(json.dumps(self.items))
        self.assertEqual(len(feed_items(self.root)),11)
if __name__=='__main__': unittest.main()
