"""Portada: solo ediciones del día local de Colombia; archivo conservado."""
import unittest
from scripts.prepare_site import build, replace_old_home_banners, fix_today_frontend

PAGE = """<!doctype html><html lang="es"><head></head><body>
<div role="region" aria-label="Edición de hoy" style="padding:10px"><a href="/edicion-2026-11-18-0800.html">EDICIÓN DEL 18 NOV</a></div>
<div role="region" aria-label="Edición de hoy" style="padding:10px"><a href="/edicion-2026-11-17-1800.html">EDICIÓN DEL 17 NOV</a></div>
<div role="navigation" aria-label="Ediciones de hoy" style="padding:10px">TODAS LAS NOTICIAS</div>
<div id="ediciones-hoy"></div><div class="empty" id="empty"></div>
<script type="application/json" id="initial-news">{}</script></body></html>"""

def sample(date, slot, i):
    return {"id": f"n{i}", "date": date, "editionSlot": slot, "verification": "editorial_verified",
            "priority": i, "title": "Noticia original verificada de prueba", "summary": "Un ejemplo.",
            "category": "Colombia", "sources": [{"name": "Fuente oficial", "url": "https://example.com/noticia"}]}

class HomeEditionTodayTests(unittest.TestCase):
    def setUp(self):
        self.db = {"editionDate": "2026-11-22", "news": [
            sample("2026-11-22", "09:30", 1),
            sample("2026-11-22", "18:00", 2),
            sample("2026-11-21", "08:00", 3),
        ]}

    def test_old_banners_removed_and_current_slots_linked(self):
        page = build(self.db, PAGE, as_of="2026-11-22")
        self.assertNotIn("EDICIÓN DEL 18 NOV", page)
        self.assertNotIn("EDICIÓN DEL 17 NOV", page)
        self.assertIn('href="#edicion-0930"', page)
        self.assertIn('href="#edicion-1800"', page)
        self.assertNotIn('href="#edicion-0800"', page)
        self.assertIn('data-day="2026-11-22"', page)
        self.assertIn("colombia", page.lower())
        self.assertEqual(page.count('id="orbiuno-current-editions"'), 1)

    def test_no_yesterday_news_on_new_day(self):
        page = build(self.db, PAGE, as_of="2026-11-23")
        self.assertNotIn('href="#edicion-0930"', page)
        self.assertNotIn('href="#edicion-1800"', page)
        self.assertNotIn("EDICIÓN DEL 17 NOV", page)
        self.assertIn("Todavía no hay ediciones verificadas para hoy", page)
        self.assertNotIn('id="edicion-0930"', page)

    def test_repeated_update_is_idempotent(self):
        first = replace_old_home_banners(PAGE, self.db, "2026-11-22")
        second = replace_old_home_banners(first, self.db, "2026-11-22")
        self.assertEqual(first, second)

    def test_current_bogota_date_and_all_slots_in_browser(self):
        sample_js = ("const slots=[['08:00','8:00 a. m.'],['12:00','12:00 m.'],"
                     "['18:00','6:00 p. m.']];\n"
                     "  if(matching.some(x=>x.editionSlot==='20:00')) slots.unshift(['20:00','8:00 p. m.']);\n"
                     "  if(matching.some(x=>x.editionSlot==='21:00')) slots.unshift(['21:00','9:00 p. m.']);\n"
                     "const maxReel=4;\n"
                     "selectedDate==='today'?x.date===db.editionDate&&x.verification==='editorial_verified'\n"
                     "const editionItems=()=>db.news.filter(n=>n.date===db.editionDate&&n.verification==='editorial_verified'&&"
                     "['21:00','20:00','08:00','12:00','18:00'].includes(n.editionSlot));")
        output = fix_today_frontend(sample_js)
        self.assertIn("x.date===today()", output)
        self.assertIn("const maxReel=6", output)
        self.assertIn("['09:30','9:30 a. m.']", output)
        self.assertIn("n.date===today()", output)
        self.assertEqual(output, fix_today_frontend(output))

if __name__ == "__main__":
    unittest.main()
