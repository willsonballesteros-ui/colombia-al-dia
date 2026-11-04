"""Pruebas de precondiciones del Reel, sin generar personajes ni videos."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from scripts.assemble_reel import has_audio_video, make_slides


class ReelGuardrailsTests(unittest.TestCase):
    def test_both_video_and_audio_required(self):
        self.assertTrue(has_audio_video({"streams": [
            {"codec_type":"video"}, {"codec_type":"audio"}]}))
        self.assertFalse(has_audio_video({"streams":[{"codec_type":"video"}]}))
        self.assertFalse(has_audio_video({"streams":[{"codec_type":"audio"}]}))
        self.assertFalse(has_audio_video({"streams":[]}))

    def test_missing_news_slides_rejected(self):
        with TemporaryDirectory() as folder:
            with self.assertRaises(RuntimeError):
                make_slides(Path(folder))

    def test_reel_requires_exactly_ten_slide_files(self):
        with TemporaryDirectory() as folder:
            p=Path(folder)
            for i in range(1,11):
                (p/f"top10-{i:02d}.png").write_bytes(b"fixture")
            self.assertEqual(len(make_slides(p)),10)


if __name__=="__main__":
    unittest.main()
