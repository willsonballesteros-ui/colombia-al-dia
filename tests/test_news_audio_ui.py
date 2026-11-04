"""Pruebas de regresión del diseño compacto y el control accesible de lectura."""
import json
import re
import unittest
from pathlib import Path
from scripts.prepare_site import build, ROOT


class NewsAudioUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
        cls.page = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.out = build(cls.data, cls.page)

    def test_ten_editorial_cards_have_audio_controls(self):
        expected = [
            n for n in self.data["news"]
            if n.get("verification") == "editorial_verified"
            and n.get("date") == self.data["editionDate"]
        ]
        self.assertEqual(len(expected), 10)
        first = self.out.split('<div class="cards" id="cards" aria-live="polite">', 1)[1].split('<div class="empty" id="empty"', 1)[0]
        self.assertEqual(first.count('data-tts-action="toggle"'), 10)
        self.assertEqual(first.count('data-tts-action="stop"'), 10)
        self.assertEqual(first.count('class="news-preview"'), 10)
        self.assertEqual(first.count('<details class="news-more">'), 10)
        self.assertNotIn('<details class="news-more" open', first)

    def test_source_urls_and_images_are_protected(self):
        rendered = self.out.split('<div class="cards" id="cards" aria-live="polite">', 1)[1].split('<div class="empty" id="empty"', 1)[0]
        for n in self.data["news"]:
            if n.get("verification") != "editorial_verified" or n.get("date") != self.data["editionDate"]:
                continue
            self.assertIn('id="noticia-{}"'.format(n["id"]), rendered)
            self.assertIn(n["imageUrl"], rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)

    def test_speech_api_is_user_initiated_and_free(self):
        self.assertIn("new window.SpeechSynthesisUtterance", self.page)
        self.assertIn("window.speechSynthesis", self.page)
        self.assertIn("synth.speak(utterance)", self.page)
        self.assertIn("synth.pause()", self.page)
        self.assertIn("synth.resume()", self.page)
        self.assertIn("window.speechSynthesis.cancel()", self.page)
        self.assertIn("el('cards').addEventListener('click'", self.page)


if __name__ == "__main__":
    unittest.main()
