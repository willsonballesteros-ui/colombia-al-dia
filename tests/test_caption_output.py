"""Bloqueo de regresiones: copy breve y URL en una sola línea."""
import json
import unittest
from scripts.build_caption import ROOT, URL, build


class CaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
        cls.out=build(cls.db)

    def test_caption_short_and_url_isolated(self):
        text=self.out["caption"]
        self.assertLess(len(text),500)
        self.assertIn("\n🌐 "+URL+"\n",text)
        self.assertNotIn("1. ",text)
        self.assertNotIn("QUÉ PASÓ",text.upper())
        self.assertNotIn("POR QUÉ IMPORTA",text.upper())
        self.assertNotIn("QUÉ SIGUE",text.upper())

    def test_first_comment_clean(self):
        comment=self.out["firstComment"]
        self.assertEqual(comment.splitlines()[-1],"🌐 "+URL)
        self.assertIn("fuentes originales",comment)

    def test_ten_unique_media_and_sources(self):
        self.assertEqual(len(self.out["media"]),10)
        self.assertEqual(len(set(self.out["media"])),10)
        self.assertEqual(len(self.out["sourceLinks"]),10)
        self.assertTrue(all(s["url"].startswith("https://") for s in self.out["sourceLinks"]))


if __name__=="__main__":
    unittest.main()
