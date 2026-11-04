"""Regresión del diseño ultra-compacto y lectura por voz nativa."""
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
        self.assertNotIn('<details class="news-more">', first)
        self.assertNotIn("QUÉ PASÓ", first)
        self.assertNotIn("POR QUÉ IMPORTA", first)
        self.assertNotIn("QUÉ SIGUE", first)
        for item in expected:
            self.assertIn(item.get("executiveSummary") or item.get("summary"), first)

    def test_homepage_defaults_to_ten_verified_stories(self):
        self.assertIn("selectedDate='today'", self.page)
        self.assertIn("selectedDate==='today'?x.date===db.editionDate&&x.verification==='editorial_verified'",self.page)
        self.assertIn("Historial completo",self.page)

    def test_mobile_cards_are_horizontal_and_dense(self):
        self.assertIn("grid-template-columns:106px minmax(0,1fr)",self.page)
        self.assertIn("class=\"card compact-card\"",self.out)
        self.assertIn("class=\"visual-frame\"",self.out)
        self.assertIn("www.google.com/s2/favicons?domain=",self.out)
        self.assertIn("source-thumbnail-name",self.out)

    def test_source_urls_and_images_are_protected(self):
        rendered = self.out.split('<div class="cards" id="cards" aria-live="polite">', 1)[1].split('<div class="empty" id="empty"', 1)[0]
        for n in self.data["news"]:
            if n.get("verification") != "editorial_verified" or n.get("date") != self.data["editionDate"]:
                continue
            self.assertIn('id="noticia-{}"'.format(n["id"]), rendered)
            if n.get("imageRightsVerified") and n.get("imageUrl"):
                self.assertIn(n["imageUrl"], rendered)
            else:
                self.assertNotIn('src="./media/'+n["date"]+'/visual-', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)

    def test_full_narration_button_and_speed_control_are_compact(self):
        current = [x for x in self.data["news"] if x.get("date") == self.data["editionDate"]
                   and x.get("verification") == "editorial_verified"]
        rendered = self.out.split('<div class="cards" id="cards" aria-live="polite">', 1)[1].split('<div class="empty" id="empty"', 1)[0]
        self.assertEqual(rendered.count('data-tts-action="speed"'), 10)
        self.assertEqual(rendered.count('data-tts-full="true"'), 10)
        self.assertEqual(rendered.count("Escuchar toda la noticia"), 20)
        self.assertEqual(len(current), 10)
        self.assertTrue(all(len(x.get("audioFullTextEs", "")) > len(x["executiveSummary"]) for x in current))
        english = [x for x in current if x.get("sourceLanguage") == "en"]
        self.assertGreater(len(english), 0)
        self.assertEqual(rendered.count('class="tts-lang"'), len(english))
        self.assertNotIn('<details class="news-more">', rendered)

    def test_realtime_speed_switch_restarts_only_current_sentence(self):
        self.assertIn("speechRates=[1,1.25,1.5,2]", self.page)
        self.assertIn("utterance.rate=speechRates[speechRateIndex]", self.page)
        self.assertIn("const changeSpeechRate=()=>", self.page)
        self.assertIn("speechSession++", self.page)
        self.assertIn("speechSegmentIndex", self.page)
        self.assertIn("const buildSpeechSegments=news=>", self.page)
        self.assertIn("const readSpeechSegment=()=>", self.page)
        self.assertIn("utterance.lang='es-CO'", self.page)
        self.assertIn("sourceLanguage==='en'", self.page)

    def test_speech_api_is_user_initiated_and_free(self):
        self.assertIn("new window.SpeechSynthesisUtterance", self.page)
        self.assertIn("window.speechSynthesis", self.page)
        self.assertIn("window.speechSynthesis.speak(utterance)", self.page)
        self.assertIn("synth.pause()", self.page)
        self.assertIn("synth.resume()", self.page)
        self.assertIn("window.speechSynthesis.cancel()", self.page)
        self.assertIn("el('cards').addEventListener('click'", self.page)


if __name__ == "__main__":
    unittest.main()
