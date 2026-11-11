import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from orbiuno_editorial import build, choose, canonical_url


def candidates():
    items = []
    for i in range(5):
        items.append({
            "title": f"Noticia comprobable de prueba numero {i + 1}",
            "narration": f"Texto de narracion para la noticia numero {i + 1}.",
            "publishedAt": "2026-11-10T10:00:00Z",
            "source": {"name": "Fuente de prueba", "url": f"https://noticias.test/articulo/{i + 1}"},
            "editorialEvidence": "verified",
            "category": "Mundo",
            "tone": "positive" if i == 4 else "news",
        })
    return items


class EditorialAdapterTests(unittest.TestCase):
    def test_schema_and_gates(self):
        manifest = build(candidates(), "2026-11-10", "08:00")
        self.assertEqual(manifest["brand"], "ORBIUNO")
        self.assertEqual(manifest["editionDate"], "2026-11-10")
        self.assertEqual(manifest["slot"], "08:00")
        self.assertEqual(len(manifest["news"]), 5)
        self.assertEqual(manifest["voice"]["speed"], 1.25)
        self.assertTrue(all(x["verification"] == "pending" for x in manifest["news"]))
        self.assertTrue(all(not x["image"]["rightsVerified"] for x in manifest["news"]))
        self.assertTrue(all(value is False for value in manifest["approval"].values()))
        self.assertEqual(manifest["news"][-1]["category"], "Mundo")

    def test_duplicate_source_blocks(self):
        items = candidates()
        items[2]["source"]["url"] = items[0]["source"]["url"]
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            choose(items, "2026-11-10")

    def test_does_not_accept_future_publication(self):
        items = candidates()
        items[0]["publishedAt"] = "2026-11-12T09:00:00Z"
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            choose(items, "2026-11-10")

    def test_requires_verified_input(self):
        items = candidates()
        items[4]["editorialEvidence"] = "pending"
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            choose(items, "2026-11-10")

    def test_invalid_source(self):
        with self.assertRaises(ValueError):
            canonical_url("https://example.org/articulo/1")

    def test_missing_positive(self):
        items = candidates()
        items[4]["tone"] = "news"
        with self.assertRaisesRegex(ValueError, "BLOCKED"):
            choose(items, "2026-11-10")


if __name__ == "__main__":
    unittest.main()
