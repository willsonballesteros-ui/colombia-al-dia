import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import importlib.util

SPEC = importlib.util.spec_from_file_location("pub", str(Path(__file__).resolve().parents[1] / "scripts" / "publish_orbiuno_binary.py"))
pub = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pub)


def fixture():
    return {
        "edition_key": "ORBIUNO-2026-11-11-1200",
        "sha256": "a" * 64,
        "approved_for_production": True,
        "editorial_approved": True,
        "rights_verified": True,
        "audio_verified": True,
        "web_sync_verified": True,
        "final_review_approved": True,
        "caption": "ORBIUNO | Edición comprobada",
        "news": [
            {"id": str(i), "source_url": "https://www.example.com/article-" + str(i),
             "web_url": "https://colombia-al-dia.pages.dev/noticia-" + str(i)}
            for i in range(4)
        ]
    }


class Tests(unittest.TestCase):
    def test_approved_metadata(self):
        self.assertIn("ORBIUNO", pub.validate_manifest(fixture(), "ORBIUNO-2026-11-11-1200", "a" * 64))

    def test_unapproved_metadata_blocks(self):
        for field in ("approved_for_production", "editorial_approved", "rights_verified",
                      "audio_verified", "web_sync_verified", "final_review_approved"):
            m = fixture()
            m[field] = False
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                pub.validate_manifest(m, m["edition_key"], m["sha256"])

    def test_wrong_news_count_blocks(self):
        m = fixture()
        m["news"] = m["news"][:3]
        with self.assertRaises(RuntimeError):
            pub.validate_manifest(m, m["edition_key"], m["sha256"])

    def test_wrong_hash_blocks(self):
        with self.assertRaises(RuntimeError):
            pub.validate_manifest(fixture(), "ORBIUNO-2026-11-11-1200", "b" * 64)

    def test_duplicate_ids_block(self):
        m = fixture()
        m["news"][1]["id"] = m["news"][0]["id"]
        with self.assertRaises(RuntimeError):
            pub.validate_manifest(m, m["edition_key"], m["sha256"])

    def test_unauthorized_web_block(self):
        m = fixture()
        m["news"][2]["web_url"] = "https://example.com/noticia"
        with self.assertRaises(RuntimeError):
            pub.validate_manifest(m, m["edition_key"], m["sha256"])


if __name__ == "__main__":
    unittest.main()
