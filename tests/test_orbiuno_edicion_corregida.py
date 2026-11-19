"""Pruebas aisladas de la edición extraordinaria correctiva del 19/11.
No publica ni modifica archivos ni llama la red.
"""
import json
import unittest
from pathlib import Path
from scripts.orbiuno_import_daily import validated

ROOT = Path(__file__).resolve().parents[1]
EDITION = ROOT / "editions/daily/2026-11-19-0930.json"

class CorrectiveEdition(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(EDITION.read_text(encoding="utf-8"))

    def test_slot_and_schema(self):
        day, slot, news = validated(self.doc, today="2026-11-19")
        self.assertEqual((day, slot, len(news)), ("2026-11-19", "09:30", 6))
        self.assertEqual(self.doc["editionKey"], "ORBIUNO-2026-11-19-0930")
        self.assertFalse(self.doc["sourceOnly"])
        self.assertEqual(self.doc["correctionOf"], "ORBIUNO-2026-11-19-0800")

    def test_real_photo_selection_and_captions(self):
        self.assertEqual(len({n["photoCommonsTitle"] for n in self.doc["news"]}), 6)
        for n in self.doc["news"]:
            self.assertTrue(n["photoMatchReviewed"])
            self.assertTrue(n["photoCommonsTitle"].startswith("File:"))
            self.assertGreater(len(n["photoCaption"]), 20)
            self.assertIsNone(n["imageUrl"])
            self.assertFalse(n["imageRightsVerified"])

    def test_sources_and_own_articles(self):
        for n in self.doc["news"]:
            self.assertEqual(n["verification"], "editorial_verified")
            self.assertEqual(n["originalArticleByline"], "Redacción ORBIUNO")
            self.assertTrue(n["originalArticleReviewed"])
            self.assertFalse(n["originalArticleIsPublisherVerbatim"])
            self.assertTrue(n["sources"][0]["url"].startswith("https://"))
            self.assertGreater(len(n["originalArticleTextEs"].strip()), 640)

if __name__ == "__main__":
    unittest.main()
