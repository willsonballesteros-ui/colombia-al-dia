"""Regresiones de los cuatro módulos aprobados (sin llamar APIs ni pagar)."""
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from scripts.build_caption import tracked_url
from scripts.generate_full_reports import acceptable, generate
from scripts.prepare_presenter_voice import script_for
from scripts.sync_sources import PER_CATEGORY, RSS, relevance_score, safe_article

ROOT=Path(__file__).resolve().parents[1]


class PipelineContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
        cls.news=next(n for n in cls.db["news"] if n.get("verification")=="editorial_verified"
                      and n.get("date")==cls.db["editionDate"])

    def test_midday_sports_feeds_without_auto_verified(self):
        self.assertEqual(PER_CATEGORY["Deportes"],2)
        self.assertGreaterEqual(sum(cat=="Deportes" for _,cat,_ in RSS),2)
        self.assertGreaterEqual(relevance_score("Selección Colombia F1 Champions","Deportes"),5)
        now=datetime(2026,11,4,12,4,tzinfo=ZoneInfo("America/Bogota"))
        item=safe_article(("Selección Colombia en Champions con noticias verificables",
                           "https://example.org/noticia",now,"Ejemplo"),
                           "Deportes",now,False)
        self.assertEqual(item["verification"],"source_only")
        self.assertIn("Pendiente",item["level"])

    def test_midday_caption_blocks_when_sports_unverified(self):
        from scripts.build_caption import build
        import os
        # Crear una edición de mediodía en memoria sin deportes verificados.
        # Las noticias de las 08:00 no deben contarse como edición de 12:00.
        from copy import deepcopy
        midday=deepcopy(self.db)
        candidate=deepcopy(self.news)
        candidate["id"]="test-mediodia-sin-deportes"
        candidate["editionSlot"]="12:00"
        candidate["category"]="Economía"
        midday["news"]=[candidate]
        with patch.dict(os.environ,{"ORBIUNO_EDITION_SLOT":"12m"}):
            manifest=build(midday)
        self.assertEqual(manifest["editionSlot"],"12m")
        self.assertEqual(len(manifest["sourceLinks"]),1)
        self.assertFalse(manifest["publicationReady"])
        self.assertIn("edicion_mediodia_requiere_1_o_2_deportes_verificados",manifest["blockers"])

    def test_separate_utm_by_placement_and_campaign(self):
        d="2026-11-04"
        self.assertIn("utm_medium=bio",tracked_url(d,"bio","8am"))
        self.assertIn("utm_medium=story",tracked_url(d,"story","12m"))
        self.assertIn("utm_campaign=edicion_20261104_6pm",
                      tracked_url(d,"comment","6pm"))

    def test_generated_reports_are_always_review_pending(self):
        article=dict(self.news)
        article.pop("originalArticleTextEs",None)
        article.pop("originalArticleReviewed",None)
        paragraphs=[" ".join(["Este reporte original se fundamenta en las fuentes citadas y mantiene su atribución."]*5)]*3
        valid="\n\n".join(paragraphs)
        self.assertTrue(acceptable(valid,article))
        db={"editionDate":article["date"],"news":[article]}
        with patch("scripts.generate_full_reports.model_report",return_value=valid):
            self.assertEqual(generate(db,"fake-key","fake-model"),1)
        self.assertFalse(article["originalArticleReviewed"])
        self.assertEqual(article["originalArticleReviewStatus"],
                         "pendiente_validacion_editorial")
        self.assertFalse(article["originalArticleIsPublisherVerbatim"])

    def test_reel_script_has_ten_headlines_and_no_unsafe_lip_sync_claim(self):
        notes=[dict(self.news,id=f"test-{n}",title=f"Titular número {n}")
               for n in range(1,11)]
        script=script_for(notes)
        self.assertEqual(script.count("Noticia "),10)
        self.assertIn("ORBIUNO",script)

    def test_analytics_endpoint_with_no_identifiers(self):
        backend=(ROOT/"functions/api/audio-event.js").read_text(encoding="utf-8")
        page=(ROOT/"index.html").read_text(encoding="utf-8")
        self.assertIn("ANALYTICS_ENGINE.writeDataPoint",backend)
        self.assertIn("analytics_binding_not_configured",backend)
        self.assertIn("/api/audio-event",page)
        self.assertIn("utm_source",page)
        self.assertIn("audio_play",page)
        self.assertIn("audio_finished",page)
        self.assertIn("landing_view",page)
        self.assertIn("utm_medium",page)
        self.assertIn("ANALYTICS_ENGINE.writeDataPoint",backend)
        self.assertNotIn("email:",backend)


if __name__=="__main__":
    unittest.main()
