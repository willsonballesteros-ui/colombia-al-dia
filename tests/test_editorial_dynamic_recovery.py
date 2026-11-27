import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.update(NEWS_BRAND="orbiuno", EDITION_DAY="2026-11-26", EDITION_SLOT="18:00")
m=importlib.import_module("tools.editorial.produce_20261126_0800")

def story(i):
    return {"title":f"Noticia {i}","source":"Fuente","url":f"https://example.org/{i}",
            "originalArticleReviewed":True,"originalArticleTextEs":"texto "*130,
            "originalArticleSourceUrls":[f"https://example.org/{i}"],"spoken":f"Noticia {i}"}

class StopRender(Exception): pass

class Tests(unittest.TestCase):
    def test_dynamic_paths(self):
        self.assertEqual(m.STAMP,"1800")
        self.assertEqual(m.OUT.name,"edicion-1800-orbiuno")
        self.assertIn("1800-ready.json",m.RESEARCH.name)

    def test_reserve_before_render(self):
        def photo(brand,i,folder,n):
            if n["url"].endswith("/0"): raise ValueError("foto fallida")
            return {"license":"CC BY","author":"Autor"}
        with tempfile.TemporaryDirectory() as tmp, patch.object(m,"WORK",Path(tmp)), patch.object(m,"photo_and_credit",side_effect=photo), patch.object(m,"source_logo",return_value="logo.png"), patch.object(m,"run",side_effect=StopRender):
            with self.assertRaises(StopRender):
                m.compile_brand("orbiuno",[story(i) for i in range(6)],[story(6)])
            voice=json.loads((Path(tmp)/"orbiuno/voice_input.json").read_text())
            texts=[s["text"] for s in voice["segments"]]
            self.assertNotIn("Noticia 0",texts)
            self.assertIn("Noticia 6",texts)
            self.assertEqual(len(texts),7)

    def test_exhaustion_blocks(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(m,"WORK",Path(tmp)), patch.object(m,"photo_and_credit",side_effect=ValueError("foto fallida")), patch.object(m,"run") as render:
            with self.assertRaisesRegex(RuntimeError,"Reservas"):
                m.compile_brand("orbiuno",[story(i) for i in range(6)])
            render.assert_not_called()

if __name__=="__main__":
    unittest.main()
