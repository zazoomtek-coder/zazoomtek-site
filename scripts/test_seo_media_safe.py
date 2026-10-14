#!/usr/bin/env python3
"""Safety tests for conservative per-page video metadata."""
import unittest
from seo_media_safe import verified_video

VIDEO={'aBcD0123_-Z':{'name':'Gameplay verificato','uploadDate':'2026-10-13T08:15:04Z'}}
FRAME='<iframe src="https://www.youtube.com/embed/aBcD0123_-Z"></iframe>'

class VideoSchemaSafety(unittest.TestCase):
    def test_real_embedded_video_inside_main(self):
        video=verified_video('<html><main>'+FRAME+'</main></html>',VIDEO)
        self.assertEqual(video['@type'],'VideoObject')
        self.assertEqual(video['name'],'Gameplay verificato')
        self.assertEqual(video['uploadDate'],'2026-10-13T08:15:04Z')
        self.assertEqual(video['embedUrl'],'https://www.youtube.com/embed/aBcD0123_-Z')

    def test_outside_main_or_script_generated_not_eligible(self):
        self.assertIsNone(verified_video('<aside>'+FRAME+'</aside>',VIDEO))
        self.assertIsNone(verified_video('<main><script>let s="'+FRAME+'";</script></main>',VIDEO))

    def test_missing_metadata_or_multiple_players_not_eligible(self):
        self.assertIsNone(verified_video('<main>'+FRAME+'</main>',{}))
        self.assertIsNone(verified_video('<main>'+FRAME+FRAME+'</main>',VIDEO))

    def test_only_main_article_hero_can_fill_missing_og(self):
        from seo_head_safe import transform
        from seo_media_safe import primary_article_image
        article='<main><article class="article-main"><h1>Notizia</h1><img src="/assets/special/story.webp" alt="Copertina originale della notizia" loading="eager"></article></main>'
        self.assertEqual(primary_article_image(article),'https://zazoomtek.it/assets/special/story.webp')
        head='<head><link rel="canonical" href="https://zazoomtek.it/story.html"></head>'
        html=head+article
        out=transform('story.html',html)
        self.assertIn('property="og:image"',out.split('</head>')[0])
        self.assertIn('https://zazoomtek.it/assets/special/story.webp',out)
        self.assertEqual(article,out.split('</head>')[1])
        archives='<main><article class="news-row"><img src="/assets/special/story.webp" alt="Copertina originale della notizia"></article></main>'
        self.assertIsNone(primary_article_image(archives))
        self.assertNotIn('property="og:image"',transform('story.html',head+archives))
        self.assertEqual(out,transform('story.html',out))

    def test_head_enrichment_stays_out_of_body(self):
        from seo_head_safe import transform
        head='<html><head><link rel="canonical" href="https://zazoomtek.it/play.html"><meta name="description" content="Videogioco"></head>'
        body='<body><main>'+FRAME+'</main></body></html>'
        out=transform('play.html',head+body,None,VIDEO)
        self.assertIn('"@type":"VideoObject"',out.split('</head>')[0])
        self.assertEqual(body,out.split('</head>')[1])
        self.assertEqual(out,transform('play.html',out,None,VIDEO))
        out2=transform('play.html',head+'<body><main><script>const a="'+FRAME+'"</script></main></body>',None,VIDEO)
        self.assertNotIn('"@type":"VideoObject"',out2)
if __name__=='__main__':
    unittest.main()
