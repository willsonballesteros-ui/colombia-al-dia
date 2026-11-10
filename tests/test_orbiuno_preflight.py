"""Regression tests: preflight validation without publishing."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("preflight", Path(__file__).resolve().parents[1] / "scripts/preflight_edition.py")
preflight = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(preflight)

class PreflightTests(unittest.TestCase):
    def check(self, story):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "edition.json"
            p.write_text(json.dumps({"news": [story]}), encoding="utf-8")
            return preflight.check_manifest(str(p))

    def test_valid_real_schema(self):
        self.assertEqual(self.check({"title":"Noticia real", "sources":[{"name":"Medio","url":"https://example.org/noticia/1"}],"verification":"editorial_verified"}), 1)

    def test_missing_verification_fails(self):
        with self.assertRaises(ValueError):
            self.check({"title":"Sin revision","fuente":"Medio","url":"https://example.org/noticia"})

    def test_homepage_fails(self):
        with self.assertRaises(ValueError):
            self.check({"title":"Solo portada","fuente":"Medio","url":"https://example.org/","verification":"editorial_verified"})

    def test_source_only_fails(self):
        with self.assertRaises(ValueError):
            self.check({"title":"Pendiente","fuente":"Medio","url":"https://example.org/noticia","verification":"source_only"})

    def test_720p_vertical_with_audio(self):
        payload = {"streams":[{"codec_type":"video","width":720,"height":1280},{"codec_type":"audio"}],"format":{"duration":"55"}}
        with patch.object(preflight.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(payload)
            self.assertEqual(preflight.check_video("fake.mp4"), 55)

    def test_video_without_audio_fails(self):
        payload = {"streams":[{"codec_type":"video","width":1080,"height":1920}],"format":{"duration":"55"}}
        with patch.object(preflight.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(payload)
            with self.assertRaises(ValueError):
                preflight.check_video("fake.mp4")

if __name__ == "__main__":
    unittest.main()
