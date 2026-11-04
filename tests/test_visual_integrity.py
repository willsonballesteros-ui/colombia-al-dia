"""Pruebas editoriales: prohibición de avatares e imágenes ficticias."""
import copy
import json
import unittest
from pathlib import Path
from scripts.prepare_site import ROOT, build, image_verified
from scripts.validate_news import check


class VisualIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.db = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
        self.template = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_current_news_has_no_unlicensed_images(self):
        editorials = [n for n in self.db["news"]
                      if n["date"] == self.db["editionDate"]
                      and n.get("verification") == "editorial_verified"]
        self.assertEqual(len(editorials), 10)
        self.assertTrue(all(not n.get("imageUrl") for n in editorials))
        page = build(self.db, self.template)
        preloaded = page.split('id="cards" aria-live="polite">', 1)[1].split('<div class="empty"', 1)[0]
        self.assertNotIn('class="news-photo"', preloaded)
        self.assertNotIn('class="news-image"', preloaded)

    def test_drawing_is_rejected(self):
        record = copy.deepcopy(self.db["news"][0])
        record["imageType"] = "ilustracion_editorial"
        record["imageUrl"] = "./media/2026-11-04/visual-01.png"
        self.assertFalse(image_verified(record))
        copy_db = copy.deepcopy(self.db)
        copy_db["news"][0] = record
        with self.assertRaises(AssertionError):
            check(copy_db)

    def test_photo_requires_provenance_and_rights(self):
        note = copy.deepcopy(self.db["news"][0])
        note.update({
            "imageType": "official_photo",
            "imageUrl": "https://example.org/photo.jpg",
            "imageSourceUrl": "https://example.org/press-release",
            "imageCredit": "Organismo oficial",
            "imageLicense": "Licencia verificada",
        })
        self.assertFalse(image_verified(note))
        note["imageRightsVerified"] = True
        self.assertTrue(image_verified(note))

    def test_site_excludes_avatar(self):
        self.assertNotIn('id="boletin-video"', self.template)
        self.assertNotIn("presenter_motion.py", self.template)
        self.assertNotIn("presenter_engines.py", self.template)


if __name__ == "__main__":
    unittest.main()
