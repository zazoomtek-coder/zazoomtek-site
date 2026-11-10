import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import seo_editorial_optimizer as optimizer
import seo

POST = {
    "id": "UgABCDEFGHIJKLMN", "text_complete": True,
    "title": "Nuovo router Wi-Fi 7 per la rete domestica",
    "text": "Il nuovo router Wi-Fi 7 introduce una rete domestica più veloce. Il dispositivo supporta la nuova connettività e migliora la copertura wireless.",
    "image": "https://example.test/router.jpg",
}
VALID = {
    "seo_title": "Router Wi-Fi 7: novità per la rete domestica",
    "meta_description": "Scopri le novità del router Wi-Fi 7 e le caratteristiche della nuova rete domestica, con un'analisi delle funzioni principali.",
    "primary_keyword": "router Wi-Fi 7",
    "related_keywords": ["rete domestica", "connettività wireless"],
    "image_alt": "Router Wi-Fi 7 per la rete domestica",
}

class Response:
    def __init__(self, payload): self.payload = payload
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, limit): return json.dumps(self.payload).encode("utf-8")

def api_response(content):
    return {"choices": [{"message": {"content": json.dumps(content, ensure_ascii=False)}}]}

class SEOOptimizerTests(unittest.TestCase):
    def test_missing_key_marks_new_post_pending_without_touching_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            original = {"posts": [dict(POST)]}
            path.write_text(json.dumps(original), encoding="utf-8")
            result = optimizer.optimize_new_community_posts(set(), path, {})
            self.assertEqual(result["reason"], "missing_api_key")
            saved = json.loads(path.read_text(encoding="utf-8"))["posts"][0]
            self.assertTrue(saved["seo_pending"])
            self.assertEqual(saved["text"], POST["text"])

    @patch("seo_editorial_optimizer.urlopen")
    def test_valid_metadata_saved_without_touching_source(self, mocked):
        mocked.return_value = Response(api_response(VALID))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            path.write_text(json.dumps({"posts": [dict(POST)]}), encoding="utf-8")
            result = optimizer.optimize_new_community_posts(set(), path, {"OPENAI_API_KEY": "test"})
            saved = json.loads(path.read_text(encoding="utf-8"))["posts"][0]
            self.assertEqual(result["optimized"], 1)
            self.assertEqual(saved["text"], POST["text"])
            self.assertEqual(saved["title"], POST["title"])
            self.assertEqual(saved["seo"]["seo_title"], VALID["seo_title"])
            self.assertIn("seo_optimized_at", saved)

    def test_invalid_metadata_is_rejected(self):
        invalid = dict(VALID, seo_title="Titolo troppo lungo " * 5)
        with self.assertRaises(ValueError):
            optimizer.validate_result(invalid, POST)

    def test_seo_metadata_is_used_without_replacing_editorial_headline(self):
        row = dict(POST, source="youtube-community", body=[POST["text"]], seo=VALID)
        self.assertEqual(seo.title_tag(row), VALID["seo_title"])
        self.assertEqual(seo.description(row), VALID["meta_description"])
        self.assertIn(VALID["primary_keyword"], seo.keywords(row))
        schema = seo.article_schema(row, "https://zazoomtek.it/test", seo.description(row), "")
        self.assertEqual(schema["headline"], POST["title"])
        self.assertEqual(schema["description"], VALID["meta_description"])

    @patch("seo_editorial_optimizer.urlopen", side_effect=TimeoutError("timeout"))
    def test_timeout_is_fail_open(self, mocked):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            original = {"posts": [dict(POST)]}
            path.write_text(json.dumps(original), encoding="utf-8")
            result = optimizer.optimize_new_community_posts(set(), path, {"OPENAI_API_KEY": "test"})
            self.assertEqual(result["failed"], 1)
            saved = json.loads(path.read_text(encoding="utf-8"))["posts"][0]
            self.assertTrue(saved["seo_pending"])
            self.assertEqual(saved["text"], POST["text"])

    @patch("seo_editorial_optimizer.urlopen", return_value=Response({"choices": []}))
    def test_malformed_response_is_fail_open(self, mocked):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            original = {"posts": [dict(POST)]}
            path.write_text(json.dumps(original), encoding="utf-8")
            result = optimizer.optimize_new_community_posts(set(), path, {"OPENAI_API_KEY": "test"})
            self.assertEqual(result["failed"], 1)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    @patch("seo_editorial_optimizer.urlopen")
    def test_pending_posts_are_retried_even_when_not_new(self, mocked):
        mocked.return_value = Response(api_response(VALID))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            pending = dict(POST, seo_pending=True)
            path.write_text(json.dumps({"posts": [pending]}), encoding="utf-8")
            result = optimizer.optimize_new_community_posts({POST["id"]}, path, {"OPENAI_API_KEY": "test"})
            saved = json.loads(path.read_text(encoding="utf-8"))["posts"][0]
            self.assertEqual(result["optimized"], 1)
            self.assertNotIn("seo_pending", saved)
            self.assertIn("seo", saved)

    @patch("seo_editorial_optimizer.urlopen")
    def test_old_posts_are_not_sent_to_ai(self, mocked):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "community.json"
            path.write_text(json.dumps({"posts": [dict(POST)]}), encoding="utf-8")
            result = optimizer.optimize_new_community_posts({POST["id"]}, path, {"OPENAI_API_KEY": "test"})
            self.assertEqual(result["optimized"], 0)
            mocked.assert_not_called()

if __name__ == "__main__":
    unittest.main()
