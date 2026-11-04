"""Pruebas sin red del filtro de prioridad para titulares automáticos."""
import unittest
from scripts.sync_sources import relevance_score, safe_article
from datetime import datetime
from zoneinfo import ZoneInfo


class RelevanceTests(unittest.TestCase):
    def test_important_national_economy(self):
        self.assertGreaterEqual(relevance_score("Inflación nacional y tasa de interés del Banco Central", "Economía"), 5)

    def test_important_global_technology(self):
        self.assertGreaterEqual(relevance_score("Nuevos avances en inteligencia artificial y ciberseguridad", "Tecnología e IA"), 5)

    def test_low_impact_excluded(self):
        self.assertLess(relevance_score("Horóscopo: los signos zodiacales del día", "Colombia"), 5)

    def test_feed_never_editorially_verified(self):
        now = datetime(2026, 11, 4, 9, 0, tzinfo=ZoneInfo("America/Bogota"))
        item = safe_article(("Cumbre mundial sobre inteligencia artificial", "https://example.com/articulo", now, "Agencia"), "Mundo", now, False)
        self.assertEqual(item["verification"], "source_only")


if __name__ == "__main__":
    unittest.main()
