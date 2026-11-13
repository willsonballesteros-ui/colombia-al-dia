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
        self.assertGreaterEqual(len(expected), 1)
        self.assertLessEqual(len(expected), 18)
        self.assertTrue(all(sum(n.get('editionSlot')==slot for n in expected)<=5 for slot in ('08:00','12:00','18:00')))
        first = self.out.split('<div id="ediciones-hoy"', 1)[1].split('<div class="cards" id="cards" aria-live="polite">', 1)[0]
        self.assertEqual(first.count('data-tts-action="toggle"'), len(expected))
        self.assertEqual(first.count('data-tts-action="speed"'), len(expected))
        self.assertEqual(first.count('data-tts-action="stop"'), len(expected))
        self.assertEqual(first.count('class="news-preview"'), len(expected))
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
        rendered = self.out.split('<div id="ediciones-hoy"', 1)[1].split('<div class="cards" id="cards" aria-live="polite">', 1)[0]
        for n in self.data["news"]:
            if n.get("verification") != "editorial_verified" or n.get("date") != self.data["editionDate"]:
                continue
            self.assertIn('id="noticia-{}"'.format(n["id"]), rendered)
            if n.get("imageRightsVerified") and n.get("imageUrl"):
                self.assertIn(n["imageUrl"], rendered)
            else:
                self.assertNotIn('src="./media/'+n["date"]+'/visual-', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)

    def test_audio_is_inline_full_if_licensed_else_summary(self):
        current = [x for x in self.data["news"] if x.get("date") == self.data["editionDate"]
                   and x.get("verification") == "editorial_verified"]
        rendered = self.out.split('<div id="ediciones-hoy"', 1)[1].split('<div class="cards" id="cards" aria-live="polite">', 1)[0]
        self.assertGreaterEqual(len(current), 1)
        self.assertLessEqual(len(current), 18)
        self.assertTrue(all(not x.get("fullArticleRightsVerified") for x in current))
        self.assertEqual(rendered.count('data-tts-action="toggle"'), len(current))
        self.assertEqual(rendered.count('data-tts-action="speed"'), len(current))
        from scripts.prepare_site import has_complete_audio
        full_count=sum(has_complete_audio(item) for item in current)
        self.assertEqual(rendered.count('data-tts-full="true"'), full_count)
        self.assertEqual(rendered.count('data-tts-full="false"'), len(current)-full_count)
        for item in current:
            self.assertGreaterEqual(len(item["audioFullTextEs"].split()), 110)
            self.assertLessEqual(len(item["audioFullTextEs"].split()), 250)
            self.assertIn('data-tts-id="'+item["id"]+'" data-tts-full="'+
                          ('true' if has_complete_audio(item) else 'false')+'"', rendered)
        self.assertEqual(rendered.count('class="source"'), len(current))
        self.assertNotIn("Abrir para escuchar completo", rendered)
        self.assertNotIn("Escuchar versión ampliada", rendered)
        self.assertIn("Fuente ↗", rendered)
        self.assertNotIn('<details class="news-more">', rendered)

    def test_normal_speed_and_fallback_playback(self):
        self.assertIn('speechRates=[1,1.25,1.5,2]', self.page)
        self.assertIn('let speechRateIndex=0',self.page)
        self.assertIn('const player=new Audio()', self.page)
        self.assertIn('player.preservesPitch=true', self.page)
        self.assertIn('speechRates[speechRateIndex]/(audioManifest.baseRate||1.25)', self.page)
        self.assertIn('a.text===narrationText(n)', self.page)
        self.assertNotIn('id="voice-select"', self.page)
        self.assertNotIn('id="tone-select"', self.page)
        self.assertIn('SpeechSynthesisUtterance', self.page)
        self.assertIn('const startNative=', self.page)
        self.assertNotIn('Leyendo con la voz en español de tu dispositivo · ', self.page)

    def test_full_article_requires_source_rights_and_translation(self):
        from copy import deepcopy
        from scripts.prepare_site import article_original_authorized
        first = next(n for n in self.data["news"] if n.get("sourceLanguage")=="en" and n.get("verification")=="editorial_verified")
        candidate = deepcopy(first)
        # Aislar la licencia de reproducción de terceros: esta prueba no usa
        # el reportaje íntegro propio, que es una vía independiente y legítima.
        for key in ("originalArticleTextEs","originalArticleByline",
                    "originalArticleReviewed","originalArticleSourceUrls",
                    "originalArticleIsPublisherVerbatim","originalArticleReviewStatus"):
            candidate.pop(key, None)
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
        self.assertIn("Escuchar completo",page)
        candidate["fullArticleRightsVerified"]=False
        self.assertFalse(article_original_authorized(candidate))
        page = __import__("scripts.prepare_site",fromlist=["article_html"]).article_html(candidate)
        self.assertNotIn('data-tts-full="true"',page)
        self.assertIn('data-tts-full="false"', page)
        self.assertIn('Escuchar noticia', page)
        self.assertIn('Fuente ↗', page)

    def test_full_orbiuno_article_is_the_entire_spoken_transcript(self):
        from copy import deepcopy
        from scripts.prepare_site import original_article_ready
        originals = [n for n in self.data["news"] if original_article_ready(n)]
        self.assertGreater(len(originals), 0)
        for article in originals:
            actual = self.out.split('<script type="application/json" id="initial-news">', 1)[1].split('</script>', 1)[0]
            payload = json.loads(actual)
            generated = next(n for n in payload["news"] if n["id"] == article["id"])
            self.assertEqual(generated["audioFullTextEs"], article["originalArticleTextEs"].strip())

    def test_mobile_audio_repair_is_injected_without_redirect(self):
        from pathlib import Path
        self.assertIn('<script defer src="./audio-fix.js?v=20261113b"></script>', self.out)
        script = (ROOT / "audio-fix.js").read_text(encoding="utf-8")
        self.assertIn("player.play()", script)
        self.assertIn("SpeechSynthesisUtterance", script)
        self.assertIn("manifest.json", script)
        self.assertIn("stopImmediatePropagation()", script)
        self.assertNotIn("window.location.href", script)

    def test_recorded_audio_keeps_controls_and_edition_queue(self):
        # La edición de hoy vive en #ediciones-hoy, no en #cards.
        # Los clics se delegan en document para cubrir ambos contenedores.
        self.assertIn("document.addEventListener('click',event=>{\n const btn=event.target.closest('button[data-tts-action]')", self.page)
        self.assertIn('player.pause()', self.page)
        self.assertIn('await player.play()', self.page)
        self.assertIn("player.addEventListener('ended'", self.page)
        self.assertIn('queueIndex+1<editionQueue.length', self.page)
        self.assertIn('mediaSession', self.page)



if __name__ == "__main__":
    unittest.main()
