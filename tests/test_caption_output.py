"""Bloqueo de regresiones: copy breve y URL en una sola línea."""
import json
import unittest
from scripts.build_caption import ROOT, URL, build, tracked_url


class CaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
        cls.out=build(cls.db)

    def test_caption_short_and_url_isolated(self):
        text=self.out["caption"]
        self.assertLess(len(text),500)
        self.assertIn("\n🌐 "+self.out["links"]["caption"]+"\n",text)
        self.assertIn("utm_source=instagram",text)
        self.assertIn("utm_medium=caption",text)
        self.assertIn("utm_campaign=edicion_",text)
        self.assertTrue(self.out["links"]["bio"].startswith(URL+"?utm_source=instagram&utm_medium=bio"))
        self.assertIn("utm_medium=story",self.out["links"]["story"])
        self.assertIn("🎧 Las noticias también se escuchan en nuestra web.",text)
        self.assertIn("Elige voz en español, tono y velocidad",text)
        self.assertNotIn("1. ",text)
        self.assertNotIn("QUÉ PASÓ",text.upper())
        self.assertNotIn("POR QUÉ IMPORTA",text.upper())
        self.assertNotIn("QUÉ SIGUE",text.upper())

    def test_first_comment_clean(self):
        comment=self.out["firstComment"]
        self.assertEqual(comment.splitlines()[-1],"🌐 "+self.out["links"]["firstComment"])
        self.assertIn("utm_medium=comment",comment)
        self.assertIn("fuentes originales",comment)

    def test_no_personal_identifiers_in_utm(self):
        for url in self.out["links"].values():
            self.assertTrue(url.startswith(URL+"?"))
            self.assertNotIn("email=",url)
            self.assertNotIn("user_id=",url)
        self.assertEqual(self.out["links"]["bio"],tracked_url(self.db["editionDate"],"bio",self.out["editionSlot"]))

    def test_six_unique_slides_ten_original_sources(self):
        self.assertEqual(len(self.out["media"]),6)
        self.assertEqual(len(set(self.out["media"])),6)
        self.assertEqual(len(self.out["sourceLinks"]),10)
        self.assertTrue(all(s["url"].startswith("https://") for s in self.out["sourceLinks"]))


if __name__=="__main__":
    unittest.main()
