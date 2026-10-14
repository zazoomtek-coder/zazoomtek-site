#!/usr/bin/env python3
import tempfile,unittest,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from seo_video_archive_safe import build
class Archive(unittest.TestCase):
    def test_preserves_old_and_includes_future_feed(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)
            def item(id,date='2026-10-01T12:00:00Z'):
                return {'id':id,'title':'La recensione originale su ZazoomTek','publishedAt':date,'category':'recensioni'}
            old=[item('aBCDEfgH012')]
            feed=[item('zBCDEfgH012') for _ in range(12)]
            (r/'video-watch-archive.json').write_text(json.dumps(old))
            (r/'home-video-feed.json').write_text(json.dumps(feed))
            data,n=build(r)
            self.assertEqual(len(data),2)
            self.assertEqual(n,1)
    def test_bad_ids_and_dates_do_not_get_in(self):
        with tempfile.TemporaryDirectory() as t:
            r=Path(t)
            good={'id':'aBCDEfgH012','title':'Video originale ZazoomTek','publishedAt':'2026-10-01T12:00:00Z'}
            src=[good for _ in range(10)]+[{**good,'id':'wrong'},{**good,'publishedAt':'2034-10-01T12:00:00Z','id':'aBCDEfgH013'}]
            (r/'home-video-feed.json').write_text(json.dumps(src))
            data,n=build(r)
            self.assertEqual(len(data),1)
if __name__=='__main__':unittest.main()
