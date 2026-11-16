import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from community_youtube import title_type


class YouTubeCommunityTitleTypeTests(unittest.TestCase):
    def test_all_six_editorial_families(self):
        cases = {
            "NEWS TECH: Smartphone": "news",
            "NEWS GAMING: Nuovo gioco": "news",
            "NEWS EXTRA: Speciale evento": "extra",
            "NEWS SPECIALI: Analisi": "speciali",
            "NEWS GUIDE: Configurazione": "guide",
            "NEWS GUIDES: Impostazioni": "guide",
            "RECENSIONE: Prodotto": "review",
            "RECENSIONE TECH: Prodotto": "review",
            "RECENSIONE GAMING: Gioco": "review",
            "REVIEW: Prodotto": "review",
            "REVIEW TECH: Prodotto": "review",
            "REVIEW GAMING: Gioco": "review",
            "RECENSIONE/REVIEW: Prodotto": "review",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                parsed_title, kind = title_type(title)
                self.assertEqual(parsed_title, title)
                self.assertEqual(kind, expected)

    def test_legacy_prefixes_remain_supported(self):
        cases = {
            "Guida: Wi-Fi": "guide",
            "Speciale: Gaming": "speciali",
            "Extra: Evento": "extra",
            "News: Aggiornamento": "news",
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(title_type(title)[1], expected)


if __name__ == "__main__":
    unittest.main()
