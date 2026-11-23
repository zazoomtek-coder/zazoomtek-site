import unittest

from emergency_sync import _community_is_near_duplicate


class CommunityDuplicateDetectionTests(unittest.TestCase):
    def test_rewritten_pubg_bentley_post_matches_existing_studio_article(self):
        candidate = {
            "title": (
                "PUBG MOBILE e Bentley, arriva una nuova collaborazione dedicata "
                "alle auto di lusso con tre modelli esclusivi"
            ),
            "text": (
                "PUBG MOBILE e Bentley portano tre automobili di lusso nel battle royale: "
                "Continental GTC Mulliner, Flying Spur Mulliner e Bentayga Azure. "
                "La partnership introduce vetture esclusive e personalizzazioni dedicate "
                "per i giocatori."
            ),
        }
        published = {
            "title": "PUBG MOBILE e Bentley: tre auto di lusso arrivano nel gioco",
            "body": [
                {
                    "type": "paragraph",
                    "text": (
                        "PUBG MOBILE annuncia una collaborazione con Bentley: Continental "
                        "GTC Mulliner, Flying Spur Mulliner e Bentayga Azure saranno "
                        "disponibili fino al 12 gennaio 2027."
                    ),
                },
                {
                    "type": "paragraph",
                    "text": (
                        "PUBG MOBILE amplia le proprie collaborazioni con il mondo "
                        "automobilistico annunciando una nuova partnership con Bentley."
                    ),
                },
            ],
        }
        duplicate, matched = _community_is_near_duplicate(candidate, [published])
        self.assertTrue(duplicate)
        self.assertEqual(matched, published["title"])

    def test_shared_brand_alone_does_not_block_different_products(self):
        candidate = {
            "title": "Samsung Galaxy S26 Ultra presenta una nuova fotocamera",
            "text": "Samsung Galaxy S26 Ultra integra un sensore fotografico aggiornato e nuove funzioni.",
        }
        published = {
            "title": "Samsung Galaxy Z Fold 8 cambia design e display",
            "body": [
                {"type": "paragraph", "text": "Samsung Galaxy Z Fold 8 adotta un display pieghevole e un nuovo design."}
            ],
        }
        duplicate, _ = _community_is_near_duplicate(candidate, [published])
        self.assertFalse(duplicate)


    def test_unrelated_samsung_monitor_and_trenord_updates_are_not_duplicates(self):
        candidate = {
            "title": "Samsung Odyssey G6, il primo monitor gaming al mondo con refresh rate fino a 1.100 Hz",
            "text": (
                "NEWS TECH: Samsung Odyssey G6, il primo monitor gaming al mondo con refresh rate fino a 1.100 Hz. "
                "Il nuovo display è progettato per il gaming competitivo e offre un'elevata frequenza di aggiornamento, "
                "tempi di risposta rapidi e immagini fluide durante le sessioni di gioco."
            ),
        }
        published = {
            "title": "Google Maps integra gli aggiornamenti Trenord in tempo reale, arrivano orari e ritardi live per i treni in Lombardia",
            "body": [
                {"type": "paragraph", "text": (
                    "Google Maps introduce una nuova funzionalità dedicata al trasporto ferroviario regionale: "
                    "il monitoraggio in tempo reale dei treni Trenord. Grazie a questa integrazione, i passeggeri "
                    "possono consultare direttamente dall'applicazione gli aggiornamenti sulla circolazione ferroviaria, "
                    "controllare eventuali ritardi e organizzare meglio i propri spostamenti."
                )},
                {"type": "paragraph", "text": (
                    "Le informazioni sulla circolazione sono consultabili da smartphone e computer, con orari, "
                    "ritardi e aggiornamenti live sui treni in Lombardia."
                )},
            ],
        }
        duplicate, _ = _community_is_near_duplicate(candidate, [published])
        self.assertFalse(duplicate)


if __name__ == "__main__":
    unittest.main()
