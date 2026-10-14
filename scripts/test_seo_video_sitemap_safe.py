#!/usr/bin/env python3
import json,sys,tempfile,unittest
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path.insert(0,str(Path(__file__).parent))
from seo_video_sitemap_safe import entries,build,NS,VNS
class VerifiedWatch(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.folder=self.root/'future-video'
        self.folder.mkdir()
        self.page=self.folder/'watch.html'
        self.id='tEkXOj7XOwA'
        self.title='Sesame Street PS5 Gameplay Completo'
        self.url='https://zazoomtek.it/future-video/watch.html'
        (self.root/'home-video-feed.json').write_text(json.dumps([{'id':self.id,'title':self.title,'publishedAt':'2026-10-13T08:39:35Z'}]))
        self.set_page()
    def tearDown(self):self.temp.cleanup()
    def set_page(self, video=True, aside=False):
        head='<head><link rel="canonical" href="'+self.url+'"><meta name="robots" content="index,follow"></head>'
        iframe='<iframe src="https://www.youtube.com/embed/'+self.id+'" title="Video YouTube"></iframe>' if video else '<a href="https://youtube.com/watch?v='+self.id+'">Video</a>'
        self.page.write_text(head+'<body><main><h1>'+self.title+'</h1><p>Gameplay originale e commentato del videogioco, con immagini e descrizione delle missioni di questa sessione.</p>'+('<aside>'+iframe+'</aside>' if aside else iframe)+'</main></body>')
    def test_valid_watch_page_xml(self):
        found=entries(self.root)
        self.assertEqual(len(found),1)
        xml=build(found)
        document=ET.fromstring(xml)
        self.assertEqual(len(document.findall('{'+NS+'}url')),1)
        self.assertEqual(len(document.findall('.//{'+VNS+'}video')),1)
    def test_no_video_link_only(self):
        self.set_page(video=False)
        self.assertEqual(entries(self.root),[])
    def test_dont_list_unrelated_or_noindex(self):
        self.set_page()
        src=self.page.read_text()
        self.page.write_text(src.replace('Sesame Street PS5 Gameplay Completo','Notizia poco correlata',1))
        self.assertEqual(entries(self.root),[])
        self.page.write_text(src.replace('index,follow','noindex,follow'))
        self.assertEqual(entries(self.root),[])
    def test_no_feed_no_fabricated_video_dates(self):
        (self.root/'home-video-feed.json').write_text('[]')
        self.assertEqual(entries(self.root),[])
if __name__=='__main__':unittest.main()
