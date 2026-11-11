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


    def release_case(self, *, missing=False, bad_title=False, source_status=200,
                     audio_status=200, approved=False):
        story = {
            "id":"n1","title":"Titular contrastado","date":"2026-11-10",
            "verification":"editorial_verified","source":"Medio",
            "sourceUrl":"https://medio.test/articles/1",
            "audioUrl":"/media/n1.mp3",
            "image":{"url":"https://medio.test/photo.jpg","credit":"Autor",
                     "license":"licencia-autorizada","source":"Medio",
                     "rightsVerified":True,"kind":"photo"}
        }
        live = dict(story)
        if bad_title:
            live["title"] = "Otro titular"
        online = [] if missing else [live]
        def fetcher(url):
            if url.endswith("/noticias.json"):
                return 200, url, json.dumps({"news":online}).encode(), "application/json"
            if url.endswith("/articles/1"):
                return source_status, url, b"article", "text/html"
            if url.endswith("/media/n1.mp3"):
                return audio_status, url, b"audio bytes" if audio_status==200 else b"", "audio/mpeg"
            raise AssertionError("Unexpected request: "+url)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"manifest.json"
            path.write_text(json.dumps({"news":[story]}),encoding="utf-8")
            return preflight.check_release(str(path), "https://site.test/", fetcher,
                                           {"n1":"source_reviewed"} if approved else {})

    def test_release_matching_online_news(self):
        self.assertEqual(self.release_case()["story_count"],1)

    def test_release_missing_online_news_blocks(self):
        with self.assertRaisesRegex(ValueError,"G1 BLOCKED"):
            self.release_case(missing=True)

    def test_release_changed_headline_blocks(self):
        with self.assertRaisesRegex(ValueError,"G1 BLOCKED"):
            self.release_case(bad_title=True)

    def test_release_source_403_requires_human(self):
        with self.assertRaisesRegex(ValueError,"G2 REVIEW REQUIRED"):
            self.release_case(source_status=403)
        self.assertEqual(self.release_case(source_status=403,approved=True)["story_count"],1)

    def test_release_source_404_blocks(self):
        with self.assertRaisesRegex(ValueError,"G2 BLOCKED"):
            self.release_case(source_status=404)

    def test_release_audio_missing_blocks(self):
        with self.assertRaisesRegex(ValueError,"G3 BLOCKED"):
            self.release_case(audio_status=404)

if __name__ == "__main__":
    unittest.main()
