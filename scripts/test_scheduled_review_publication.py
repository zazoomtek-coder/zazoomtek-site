#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

spec=importlib.util.spec_from_file_location("publish",Path(__file__).with_name("publish-approved-reviews.py"))
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/"editorial").mkdir()
        self.item=dict(id="test",status="approved",publish_at="2026-10-25T15:00:00+01:00",
                       source="anteprima-test.html",target="test-recensione-pc.html",
                       title="Test Recensione PC",platform="PC",date_label="25 ottobre 2026",
                       description="Una prova editoriale.",image="https://example.com/cover.jpg")
        self.save()
        (self.root/self.item["source"]).write_text('<html><head><title>Test</title><meta name="robots" content="noindex"></head>'
            '<body><div class="previewbar">NON PUBBLICATA</div><h1>Test</h1><article>testo</article></body></html>')
        (self.root/"index.html").write_text(p.HOME_A+
            '<article class="video-card zt-review-card">old</article>'*5+p.HOME_B)
        (self.root/"recensioni-scritte.html").write_text(p.ARCHIVE+"Other</div>")
        for f in ("sitemap.xml","google-sitemap.xml"):
            (self.root/f).write_text("<urlset></urlset>")

    def save(self):
        (self.root/p.QUEUE).write_text(json.dumps(dict(version=1,timezone="Europe/Rome",items=[self.item])))

    def run_at(self,date,dry=False):
        return p.publish(self.root,datetime.fromisoformat(date),dry)

    def test_not_early(self):
        self.assertEqual(self.run_at("2026-10-25T13:59:00+00:00"),[])
        self.assertFalse((self.root/self.item["target"]).exists())

    def test_due_and_idempotent(self):
        self.assertEqual(len(self.run_at("2026-10-25T14:00:00+00:00")),5)
        public=(self.root/self.item["target"]).read_text()
        self.assertIn('rel="canonical"',public)
        self.assertNotIn("NON PUBBLICATA",public)
        self.assertNotIn('name="robots" content="noindex"',public)
        self.assertEqual(self.run_at("2026-10-25T14:02:00+00:00"),[])

    def test_draft_never_publishes(self):
        self.item["status"]="draft"
        self.save()
        self.assertEqual(self.run_at("2026-10-26T10:00:00+00:00"),[])

    def test_wrong_dst_offset_fails(self):
        self.item["publish_at"]="2026-10-25T15:00:00+02:00"
        self.save()
        with self.assertRaises(ValueError):
            self.run_at("2026-10-25T15:00:00+00:00")

    def test_dry_run(self):
        self.assertEqual(len(self.run_at("2026-10-25T14:00:00+00:00",True)),5)
        self.assertFalse((self.root/self.item["target"]).exists())

    def test_missing_approved_source_fails(self):
        (self.root/self.item["source"]).unlink()
        with self.assertRaises(ValueError):
            self.run_at("2026-10-25T14:00:00+00:00")

    def test_old_review_is_not_reinserted_into_latest_five(self):
        self.run_at("2026-10-25T14:00:00+00:00")
        newer=p.HOME_A+(
            '<article class="video-card zt-review-card"><h3>NEWER</h3></article>'*5
            )+p.HOME_B
        (self.root/"index.html").write_text(newer)
        self.assertEqual(self.run_at("2026-10-27T14:00:00+00:00"),[])
        self.assertEqual((self.root/"index.html").read_text(),newer)


if __name__=="__main__":
    unittest.main(verbosity=2)
