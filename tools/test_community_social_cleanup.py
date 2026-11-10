"""Regression tests for trailing YouTube Community social boilerplate."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from article_templates import clean_community_social_boilerplate


class CommunitySocialCleanupTests(unittest.TestCase):
    def test_removes_trailing_channel_promotion_and_hashtags(self):
        blocks = [
            "News Gaming: GTA 6\nRockstar annuncia nuovi dettagli.",
            "Subscribe 🌐 zazoomtek.it ▶️ YouTube: @ZazoomTek ❤️ Patreon: ZazoomTek 🎵 TikTok: @zazoomtek 💬 WhatsApp: ZazoomTek",
            "#GTA6 #GrandTheftAutoVI #RockstarGames #GTAVITheFestival #TravisScott #CardiB #GamingNews #ZazoomTek",
        ]
        self.assertEqual(
            clean_community_social_boilerplate(blocks),
            ["News Gaming: GTA 6\nRockstar annuncia nuovi dettagli."],
        )

    def test_preserves_editorial_hashtags_and_social_mentions(self):
        blocks = [
            "La community segue #GTA6 e Rockstar Games. Seguici su YouTube per gli aggiornamenti.",
            "Il dibattito continua.",
        ]
        self.assertEqual(clean_community_social_boilerplate(blocks), blocks)

    def test_removes_trailing_rows_inside_same_block(self):
        block = (
            "Testo editoriale completo.\n"
            "Subscribe 🌐 zazoomtek.it ▶️ YouTube: @ZazoomTek ❤️ Patreon: ZazoomTek 🎵 TikTok: @zazoomtek 💬 WhatsApp: ZazoomTek\n"
            "#GTA6 #GamingNews #ZazoomTek"
        )
        self.assertEqual(
            clean_community_social_boilerplate([block]),
            ["Testo editoriale completo."],
        )


if __name__ == "__main__":
    unittest.main()
