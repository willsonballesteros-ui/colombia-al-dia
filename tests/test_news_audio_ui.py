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
        self.assertEqual(rendered.count('data-tts-full="editorial"'), 10)
        self.assertEqual(rendered.count('data-tts-full="true"'), 0)
        self.assertEqual(rendered.count("Escuchar versión ampliada"), 20)
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
        self.assertIn("hasAuthorizedFullArticle",self.page)

    def test_voice_selector_offers_real_spanish_device_voices(self):
        self.assertIn('id="voice-select"',self.page)
        self.assertIn('Voz en español',self.page)
        self.assertIn("const spanishVoices=()",self.page)
        self.assertIn("const selectSpanishVoice=()=>",self.page)
        self.assertIn("voiceschanged",self.page)
        self.assertIn("utterance.voice=voice",self.page)
        self.assertIn("restartCurrentSentence()",self.page)

    def test_full_article_requires_source_rights_and_translation(self):
        from copy import deepcopy
        from scripts.prepare_site import article_original_authorized
        first = next(n for n in self.data["news"] if n.get("sourceLanguage")=="en" and n.get("verification")=="editorial_verified")
        candidate = deepcopy(first)
        candidate["fullArticleTextEs"]="Texto íntegro permitido por la fuente. "*25
        candidate["fullArticleIsVerbatimSource"]=True
        candidate["fullArticleRightsVerified"]=True
        candidate["fullArticleLicense"]="Licencia de reproducción y traducción documentada"
        candidate["fullArticleSourceUrl"]=candidate["sources"][0]["url"]
        self.assertFalse(article_original_authorized(candidate))
        candidate["fullArticleTranslationAuthorized"]=True
        self.assertTrue(article_original_authorized(candidate))
        page = __import__("scripts.prepare_site",fromlist=["article_html"]).article_html(candidate)
        self.assertIn('data-tts-full="true"',page)
        self.assertIn("Escuchar toda la noticia",page)
        candidate["fullArticleRightsVerified"]=False
        self.assertFalse(article_original_authorized(candidate))
        page = __import__("scripts.prepare_site",fromlist=["article_html"]).article_html(candidate)
        self.assertNotIn('data-tts-full="true"',page)

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
