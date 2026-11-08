"""Regression tests for multi-image YouTube Community review imports."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import community_youtube
from article_templates import interleave_review_images


def sample_post():
    return {
        "backstagePostRenderer": {
            "postId": "UgkTestCommunityPost123456",
            "contentText": "Review Tech: Sample product review with enough text to qualify.",
            "backstageAttachment": {
                "images": [
                    {"thumbnails": [
                        {"url": "https://yt3.ggpht.com/photo-one=s480"},
                        {"url": "https://yt3.ggpht.com/photo-one=s1200"},
                    ]},
                    {"thumbnails": [
                        {"url": "https://yt3.ggpht.com/photo-two=s480"},
                        {"url": "https://yt3.ggpht.com/photo-two=s1200"},
                    ]},
                    {"thumbnails": [
                        {"url": "https://yt3.ggpht.com/photo-three=s480"},
                        {"url": "https://yt3.ggpht.com/photo-three=s1200"},
                    ]},
                ]
            },
        }
    }


class CommunityMultiImageTests(unittest.TestCase):
    def test_collects_all_images_and_keeps_first_as_cover(self):
        old = community_youtube.MULTI_IMAGE_IMPORT_ENABLED
        try:
            community_youtube.MULTI_IMAGE_IMPORT_ENABLED = True
            row = community_youtube.post_records(sample_post())[0]
            self.assertEqual(row["image"], "https://yt3.ggpht.com/photo-one=s1200")
            self.assertEqual(
                [item["src"] for item in row["images"]],
                ["https://yt3.ggpht.com/photo-two=s1200",
                 "https://yt3.ggpht.com/photo-three=s1200"],
            )
        finally:
            community_youtube.MULTI_IMAGE_IMPORT_ENABLED = old

    def test_rollback_switch_restores_cover_only_collection(self):
        old = community_youtube.MULTI_IMAGE_IMPORT_ENABLED
        try:
            community_youtube.MULTI_IMAGE_IMPORT_ENABLED = False
            row = community_youtube.post_records(sample_post())[0]
            self.assertEqual(row["image"], "https://yt3.ggpht.com/photo-one=s1200")
            self.assertEqual(row["images"], [])
        finally:
            community_youtube.MULTI_IMAGE_IMPORT_ENABLED = old

    def test_review_images_are_interleaved_in_relevant_sections(self):
        review = {
            "category": "recensioni-tech",
            "title": "Sample Tech Review",
            "images": [
                {"src": "https://yt3.ggpht.com/photo-two=s1200"},
                {"src": "https://yt3.ggpht.com/photo-three=s1200"},
            ],
        }
        body = (
            "<h2>Materiali e Design</h2><p>Design paragraph.</p>"
            "<h2>Hardware e Prestazioni</h2><p>Hardware paragraph.</p>"
            "<h2>Uso Quotidiano</h2><p>Daily use paragraph.</p>"
        )
        rendered = interleave_review_images(body, review, lambda url: url)
        self.assertEqual(rendered.count("<figure class=\"story-figure\">"), 2)
        self.assertLess(rendered.index("Design paragraph."), rendered.index("photo-two"))
        self.assertLess(rendered.index("Hardware paragraph."), rendered.index("photo-three"))
        self.assertLess(rendered.index("photo-two"), rendered.index("<h2>Hardware e Prestazioni</h2>"))

    def test_gaming_review_images_follow_gaming_sections(self):
        review = {
            "category": "recensioni-gaming",
            "title": "Sample Gaming Review",
            "images": [
                {"src": "https://yt3.ggpht.com/game-two=s1200"},
                {"src": "https://yt3.ggpht.com/game-three=s1200"},
            ],
        }
        body = (
            "<h2>Storia</h2><p>Story paragraph.</p>"
            "<h2>Gameplay</h2><p>Gameplay paragraph.</p>"
            "<h2>Aspetto tecnico</h2><p>Technical paragraph.</p>"
        )
        rendered = interleave_review_images(body, review, lambda url: url)
        self.assertLess(rendered.index("Story paragraph."), rendered.index("game-two"))
        self.assertLess(rendered.index("Gameplay paragraph."), rendered.index("game-three"))
        self.assertLess(rendered.index("game-two"), rendered.index("<h2>Gameplay</h2>"))

    def test_rendering_rollback_hides_additional_images(self):
        import article_templates
        old = article_templates.MULTI_IMAGE_REVIEW_RENDERING_ENABLED
        try:
            article_templates.MULTI_IMAGE_REVIEW_RENDERING_ENABLED = False
            review = {"category": "recensioni-tech", "images": [
                {"src": "https://yt3.ggpht.com/rollback=s1200"}
            ]}
            body = "<h2>Materiali e Design</h2><p>Original paragraph.</p>"
            self.assertEqual(interleave_review_images(body, review, lambda url: url), body)
        finally:
            article_templates.MULTI_IMAGE_REVIEW_RENDERING_ENABLED = old

    def test_non_review_articles_are_unchanged(self):
        body = "<h2>News</h2><p>Original text.</p>"
        review = {"category": "news-tech", "images": [
            {"src": "https://yt3.ggpht.com/photo-two=s1200"}
        ]}
        self.assertEqual(interleave_review_images(body, review, lambda url: url), body)


if __name__ == "__main__":
    unittest.main()
