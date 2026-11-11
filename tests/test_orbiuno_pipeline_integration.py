"""Guardrail tests against the repository's real template and approved voice."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from orbiuno_pipeline import state, manifest_check, probe_check, web_sync, ig_gate, drive_upload


class OrbiunoPipelineIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.template = json.loads((ROOT / "editions/PLANTILLA_NO_APROBADA.json").read_text(encoding="utf-8"))

    def test_real_template_detected(self):
        self.assertEqual(self.template["brand"], "ORBIUNO")
        self.assertEqual(len(self.template["news"]), 5)
        self.assertEqual(manifest_check.validate(self.template, self.template, expected_items=5), [])
        altered = json.loads(json.dumps(self.template))
        altered["news"][0]["id"] = altered["news"][1]["id"]
        self.assertTrue(any("duplicate" in x for x in manifest_check.validate(altered, self.template, expected_items=5)))

    def test_real_template_rejects_wrong_fields(self):
        incompatible = {"edition_id": "x", "items": [], "date": "2026-11-11"}
        self.assertTrue(manifest_check.validate(incompatible, self.template))

    def test_bogota_slot_with_delayed_cron(self):
        self.assertEqual(state.edition_key(datetime(2026, 11, 11, 13, 40, tzinfo=timezone.utc)), "2026-11-11-0800")
        self.assertEqual(state.edition_key(datetime(2026, 11, 12, 0, 5, tzinfo=timezone.utc)), "2026-11-11-1800")
        with self.assertRaises(ValueError):
            state.edition_key(datetime(2026, 11, 11, 13, 0))

    def test_state_never_promotes_without_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            filename = os.path.join(tmp, "edition.json")
            edition = state.EditionState(filename, "2026-11-11-0800")
            with self.assertRaises(ValueError):
                edition.move("published")
            edition.move("verified")
            self.assertEqual(state.EditionState(filename, "2026-11-11-0800").state, "verified")

    def test_ffprobe_checks(self):
        sample = {"streams": [{"codec_type": "video", "codec_name": "h264", "width": 720, "height": 1280},
                              {"codec_type": "audio", "codec_name": "aac"}],
                  "format": {"duration": "55.2"}}
        self.assertEqual(probe_check.check_ffprobe(sample), [])
        sample["format"]["duration"] = "45.1"
        self.assertTrue(any("duración" in x for x in probe_check.check_ffprobe(sample)))

    def test_web_uses_nested_real_source(self):
        item = {"id": "abcd1234", "title": "Titular real", "source": {"name": "Fuente", "url": "https://example.net/historia"}}
        html = '<article id="noticia-abcd1234"><h2>Titular real</h2><a href="https://example.net/historia">Fuente</a></article>'
        self.assertEqual(web_sync.check_web([item], html), [])
        self.assertTrue(web_sync.check_web([item], "<html>vacío</html>"))

    def test_instagram_never_publishes_without_approval(self):
        calls = []
        def transport(*args, **kwargs):
            calls.append(args)
            return {"id": "bad"}
        env = {"IG_PUBLISH_AUTHORIZED": "yes", "META_ACCESS_TOKEN": "x", "IG_USER_ID": "1"}
        with self.assertRaises(PermissionError):
            ig_gate.publish_reel("https://example.net/reel.mp4", "caption", transport, env, state="draft")
        self.assertEqual(calls, [])

    def test_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.txt"
            p.write_bytes(b"hello")
            self.assertEqual(drive_upload.sha256(str(p)), "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")


if __name__ == "__main__":
    unittest.main()
