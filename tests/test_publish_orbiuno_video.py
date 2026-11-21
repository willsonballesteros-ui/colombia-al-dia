"""Pruebas de publicación idempotente, sin llamadas reales a Meta."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.publish_orbiuno_video import (
    PublishError, build_caption, find_duplicate, https_url,
    load_manifest, publish_ig,
)


def manifest():
    return {
        "edition": "2026-11-21", "slot": "08:00",
        "newsCount": 6, "newsIds": [f"news-{n}" for n in range(6)],
        "news": [{"id": f"news-{n}", "title": f"Noticia {n}",
                  "sourceUrl": f"https://fuente.org/noticia/{n}"} for n in range(6)],
        "voice": "es-CO-SalomeNeural", "voiceSpeed": 1.25,
        "imagesCount": 6, "logosCount": 6,
        "visualMode": "verified_real_photos",
        "photoCredits": [{"author": "Autor", "license": "CC BY-SA 4.0",
                          "page": f"https://commons.wikimedia.org/wiki/File:photo{n}.jpg"}
                         for n in range(6)],
        "video": "ORBIUNO_2026-11-21_0800_6_NOTICIAS.mp4",
    }


class PublishGateTests(unittest.TestCase):
    def test_manifest_and_sources(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "manifest.json"
            p.write_text(json.dumps(manifest()), encoding="utf-8")
            data, prefix, video = load_manifest(p)
            self.assertEqual(data["newsCount"], 6)
            self.assertIn("2026-11-21", prefix)
            self.assertIn("0800_6_NOTICIAS.mp4", video)
            self.assertEqual(build_caption(data, prefix).count("https://fuente.org/noticia/"), 6)

    def test_duplicate_news_rejected(self):
        import json
        bad = manifest()
        bad["newsIds"][1] = bad["newsIds"][0]
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "manifest.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(PublishError, "únicas"):
                load_manifest(p)

    def test_non_https_rejected(self):
        for u in ("http://example.com", "https://me:pass@example.com", ""):
            with self.assertRaises(PublishError):
                https_url(u)

    def test_duplicate_prevents_another_ig_post(self):
        data = {"data": [{"id": "123456", "caption": "ORBIUNO | 2026-11-21 | 08:00 CO\n..."
                          , "permalink": "https://www.instagram.com/reel/existing/"}]}
        with patch("scripts.publish_orbiuno_video.graph", return_value=data):
            result = find_duplicate("token", "123/media", "ORBIUNO | 2026-11-21 | 08:00 CO", "caption")
            self.assertEqual(result["id"], "123456")

    def test_publication_skips_when_duplicate(self):
        with patch("scripts.publish_orbiuno_video.check_identity"), \
             patch("scripts.publish_orbiuno_video.find_duplicate",
                   return_value={"id": "123456", "permalink": "https://www.instagram.com/reel/existing/"}), \
             patch("scripts.publish_orbiuno_video.graph") as graph:
            result = publish_ig("token", "17841438062554418", "ORBIUNO | 2026-11-21 | 08:00 CO",
                                "https://cdn.example.org/news.mp4", "Caption")
            self.assertTrue(result["duplicate"])
            graph.assert_not_called()


if __name__ == "__main__":
    unittest.main()
