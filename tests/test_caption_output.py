"""Bloqueo de regresiones: copy breve y URL en una sola línea."""
import json
import os
import unittest
from scripts.build_caption import ROOT, URL, build, tracked_url


class CaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
        slots={n.get("editionSlot") for n in cls.db["news"] if n.get("date")==cls.db["editionDate"] and n.get("verification")=="editorial_verified"}
        candidate=next((k for k,v in (("9pm","21:00"),("8am","08:00"),("12m","12:00"),("6pm","18:00")) if v in slots),None)
        assert candidate, "No hay noticias verificadas para probar"
        original=os.environ.get("ORBIUNO_EDITION_SLOT")
        os.environ["ORBIUNO_EDITION_SLOT"]=candidate
        try:
            cls.out=build(cls.db)
        finally:
            if original is None: os.environ.pop("ORBIUNO_EDITION_SLOT",None)
            else: os.environ["ORBIUNO_EDITION_SLOT"]=original

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
        self.assertIn("Escucha nuestra voz en español y ajusta la velocidad",text)
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

    def test_three_unique_slides_ten_original_sources(self):
        self.assertEqual(len(self.out["media"]),1+len(self.out["newsPerSlide"]))
        self.assertEqual(len(set(self.out["media"])),len(self.out["media"]))
        self.assertEqual(self.out["newsPerSlide"],[2]* (sum(self.out["newsPerSlide"])//2) + ([1] if sum(self.out["newsPerSlide"])%2 else []))
        self.assertEqual(len(self.out["sourceLinks"]),sum(self.out["newsPerSlide"]))
        self.assertTrue(all(s["url"].startswith("https://") for s in self.out["sourceLinks"]))


if __name__=="__main__":
    unittest.main()
