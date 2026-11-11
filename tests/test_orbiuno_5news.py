"""Five-news render safety tests; no publication or provider calls."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("render5",ROOT/"scripts/render_orbiuno_5news_animated.py")
render5=importlib.util.module_from_spec(spec)
spec.loader.exec_module(render5)

class FiveNewsTests(unittest.TestCase):
    def fake(self):
        return {"brand":"ORBIUNO","editionDate":"2026-11-11","slot":"08:00",
                "voice":{"name":"Camila Vega","id":render5.VOICE_ID,"speed":1.25,"recordedAtSpeed":1.0},
                "news":[{"id":str(i),"title":"Noticia "+str(i),"category":"Mundo"} for i in range(5)],
                "intro":{"leadAudioFile":"audio/lead.wav","headlineAudioFiles":["audio/h"+str(i)+".wav" for i in range(5)]}}
    def test_five_required(self):
        m=self.fake();m["news"].pop()
        with self.assertRaisesRegex(ValueError,"five"):
            render5.check_manifest(m,Path("."),False)
    def test_source_voice_required(self):
        m=self.fake();m["voice"]["id"]="other"
        with self.assertRaisesRegex(ValueError,"Camila"):
            render5.check_manifest(m,Path("."),False)
    def test_all_headline_clips_required(self):
        m=self.fake();m["intro"]["headlineAudioFiles"]=["audio/only-one.wav"]
        with self.assertRaisesRegex(ValueError,"five separate"):
            render5.check_manifest(m,Path("."),False)
    def test_no_silent_fallback(self):
        m=self.fake()
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaisesRegex(ValueError,"Missing/unapproved asset"):
                render5.check_manifest(m,Path(p),False)
    def test_release_never_bypasses_audio(self):
        m=self.fake();m["approval"]={g:True for g in render5.GATES}
        with tempfile.TemporaryDirectory() as p:
            with self.assertRaises(ValueError):
                render5.check_manifest(m,Path(p),True)

if __name__=="__main__":
    unittest.main()
