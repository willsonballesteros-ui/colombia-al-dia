"""Regresiones offline del publicador seis noticias, sin Meta ni llamadas de red."""
import unittest
from scripts.orbiuno_publish_6 import caption_for, SLOT

class OrbiunoPublishSixTests(unittest.TestCase):
    def test_caption_six_sources_and_web_link(self):
        manifest={"edition":"2026-11-15","news":[
            {"title":f"Titular verificado {i}",
             "sourceUrl":f"https://example.org/nota/{i}"}
            for i in range(1,7)
        ]}
        caption=caption_for(manifest)
        self.assertEqual(caption.count("Fuente:"),6)
        self.assertIn("https://colombia-al-dia.pages.dev/",caption)
        self.assertLess(len(caption),2000)

    def test_edition_key_slots(self):
        self.assertEqual(SLOT,{"08:00":"0800","12:00":"1200","18:00":"1800"})

if __name__=="__main__":
    unittest.main()
