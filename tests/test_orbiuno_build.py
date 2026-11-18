import functools, http.server, json, re, shutil, socketserver, sys, tempfile, threading, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image
import orbiuno_carousel as carousel
import orbiuno_media_manager as mm
import orbiuno_media_registry as reg
import orbiuno_voice as voice
import orbiuno_web as web
from test_orbiuno_gate import GUION, build_edition, make_audio


def fresh():
    tmp = tempfile.mkdtemp()
    ed, registry = build_edition(tmp)
    return tmp, ed, registry


class CarouselTests(unittest.TestCase):
    def test_seis_png_independientes_1080x1350(self):
        _, ed, _ = fresh()
        paths = carousel.build(ed)
        self.assertEqual([p.name for p in paths], ["portada.png"] + [f"noticia_0{i}.png" for i in range(1, 6)])
        hashes = set()
        for p in paths:
            with Image.open(p) as im:
                self.assertEqual((im.format, im.size), ("PNG", (1080, 1350)))
            hashes.add(reg.sha256_file(p))
        self.assertEqual(len(hashes), 6)

    def test_titular_que_no_cabe_bloquea_en_vez_de_recortar(self):
        _, ed, _ = fresh()
        m = json.loads((ed / "manifest.json").read_text())
        m["noticias"][2]["titular"] = "palabra " * 80
        (ed / "manifest.json").write_text(json.dumps(m))
        with self.assertRaises(carousel.TextOverflow):
            carousel.build(ed)

    def test_exige_cinco_noticias(self):
        _, ed, _ = fresh()
        m = json.loads((ed / "manifest.json").read_text()); m["noticias"].pop()
        (ed / "manifest.json").write_text(json.dumps(m))
        with self.assertRaises(ValueError):
            carousel.build(ed)

    def test_formato_de_fecha_y_hora(self):
        self.assertEqual(carousel.fmt_fecha("2026-11-12"), "12 NOV 2026")
        self.assertEqual((carousel.fmt_hora("08:00"), carousel.fmt_hora("18:00")), ("8:00 a. m.", "6:00 p. m."))


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.ed, _ = fresh()
        cls.out = Path(cls.tmp) / "site"
        web.build_site(cls.ed, cls.out)
        cls.manifest = json.loads((cls.ed / "manifest.json").read_text())

    def test_manifiesto_web_identico_byte_a_byte(self):
        self.assertEqual((self.out / "web-manifest.json").read_bytes(), (self.ed / "manifest.json").read_bytes())

    def test_portada_tiene_las_cinco_noticias_en_orden_con_audio_y_velocidades(self):
        h = (self.out / "index.html").read_text()
        ids = re.findall(r'data-story="([^"]+)"', h)
        self.assertEqual(ids, [n["id"] for n in self.manifest["noticias"]])
        self.assertEqual(h.count('class="speed"'), 20)
        self.assertEqual(h.count('class="listen"'), 5)
        for r in ("1", "1.25", "1.5", "2"):
            self.assertIn(f'data-rate="{r}"', h)

    def test_todos_los_enlaces_locales_existen(self):
        for page in [self.out / "index.html"] + list((self.out / "noticia").glob("*/index.html")):
            h = page.read_text()
            for ref in re.findall(r'(?:src|href)="([^"#]+)"', h):
                if ref.startswith("http"):
                    continue
                target = (page.parent / ref).resolve()
                self.assertTrue(target.exists(), f"{page}: {ref}")

    def test_cada_noticia_tiene_pagina_individual_estable(self):
        for n in self.manifest["noticias"]:
            self.assertTrue((self.out / "noticia" / n["id"] / "index.html").is_file())

    def test_fuente_original_abre_en_pestana_segura(self):
        h = (self.out / "index.html").read_text()
        self.assertEqual(h.count('rel="noopener noreferrer"'), 5)


class BrowserTests(unittest.TestCase):
    """Navegador real (Chromium headless). NO sustituye la prueba en iPhone/Safari."""

    @classmethod
    def setUpClass(cls):
        try:
            from playwright.sync_api import sync_playwright
            cls.pw = sync_playwright().start()
            cls.browser = cls.pw.chromium.launch(args=["--autoplay-policy=document-user-activation-required"])
        except Exception as exc:
            raise unittest.SkipTest("Chromium no disponible: " + str(exc))
        cls.tmp, ed, _ = fresh()
        for i in range(1, 6):
            make_audio(ed / f"audio{i}.mp3", dur=8)
        cls.out = Path(cls.tmp) / "site"
        web.build_site(ed, cls.out)
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a, **k):
                pass
        handler = functools.partial(Quiet, directory=str(cls.out))
        socketserver.TCPServer.allow_reuse_address = True
        cls.srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}/"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "srv"):
            cls.srv.shutdown(); cls.srv.server_close()
        if hasattr(cls, "browser"):
            cls.browser.close(); cls.pw.stop()

    def page(self, path=""):
        ctx = self.browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        pg = ctx.new_page(); errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("requestfailed", lambda r: errs.append("fallo " + r.url))
        pg.goto(self.base + path)
        return pg, errs

    def test_no_reproduce_sin_toque_y_reproduce_con_toque(self):
        pg, errs = self.page()
        a = pg.locator("[data-story] audio").first
        self.assertTrue(a.evaluate("e => e.paused"))
        pg.locator(".listen").first.click()
        pg.wait_for_function("document.querySelector('audio').currentTime > 0.5", timeout=8000)
        self.assertFalse(a.evaluate("e => e.paused"))
        self.assertEqual(a.evaluate("e => e.playbackRate"), 1.25)  # velocidad inicial
        self.assertEqual(errs, [])

    def test_cuatro_velocidades_pausa_y_reanudacion(self):
        pg, _ = self.page()
        box = pg.locator("[data-story]").first
        a = box.locator("audio")
        box.locator(".listen").click()
        pg.wait_for_function("document.querySelector('audio').currentTime > 0.3", timeout=8000)
        for rate in (1, 1.25, 1.5, 2):
            box.locator(f'.speed[data-rate="{rate}"]').click()
            self.assertEqual(a.evaluate("e => e.playbackRate"), rate)
        box.locator(".listen").click()
        self.assertTrue(a.evaluate("e => e.paused"))
        self.assertEqual(box.locator(".listen").inner_text(), "Reanudar")
        box.locator(".listen").click()
        self.assertFalse(a.evaluate("e => e.paused"))

    def test_solo_suena_una_noticia_a_la_vez(self):
        pg, _ = self.page()
        pg.locator(".listen").nth(0).click()
        pg.wait_for_function("document.querySelectorAll('audio')[0].currentTime > 0.3", timeout=8000)
        pg.locator(".listen").nth(1).click()
        pg.wait_for_function("document.querySelectorAll('audio')[1].currentTime > 0.3", timeout=8000)
        self.assertTrue(pg.locator("audio").nth(0).evaluate("e => e.paused"))

    def test_abrir_noticia_y_reproducir_su_audio(self):
        pg, errs = self.page()
        pg.locator("a.btn", has_text="Abrir noticia").first.click()
        pg.wait_for_url("**/noticia/n1/")
        self.assertIn("Titular 1", pg.locator("h1").inner_text())
        pg.locator(".listen").click()
        pg.wait_for_function("document.querySelector('audio').currentTime > 0.5", timeout=8000)
        self.assertEqual(errs, [])

    def test_sin_desborde_horizontal_en_movil(self):
        pg, _ = self.page()
        self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)


class MediaManagerTests(unittest.TestCase):
    def api(self, lic="CC BY 4.0", artist="<a href='x'>Ana Pérez</a>", width=2400, mime="image/jpeg"):
        return {"query": {"pages": {"1": {"title": "File:Foto.jpg", "imageinfo": [{
            "url": "https://upload.wikimedia.org/foto.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:Foto.jpg",
            "width": width, "height": 1600, "mime": mime,
            "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": artist},
                            "AttributionRequired": {"value": "true"}}}]}}}}

    def test_candidata_valida_pero_siempre_requiere_revision_humana(self):
        c = mm.parse_candidates(self.api())[0]
        self.assertFalse(c["bloqueada"]); self.assertEqual(c["licencia_codigo"], "CC-BY-4.0")
        self.assertEqual(c["autor"], "Ana Pérez"); self.assertTrue(c["requiere_revision_humana"])

    def test_licencias_no_abiertas_se_bloquean(self):
        for lic in ("CC BY-NC 4.0", "All rights reserved", "Fair use", ""):
            self.assertTrue(mm.parse_candidates(self.api(lic=lic))[0]["bloqueada"], lic)

    def test_sin_autor_resolucion_baja_o_formato_raro_se_bloquean(self):
        self.assertTrue(mm.parse_candidates(self.api(artist=""))[0]["bloqueada"])
        self.assertTrue(mm.parse_candidates(self.api(width=800))[0]["bloqueada"])
        self.assertTrue(mm.parse_candidates(self.api(mime="image/gif"))[0]["bloqueada"])

    def test_no_descarga_candidata_bloqueada(self):
        c = mm.parse_candidates(self.api(lic="CC BY-NC 4.0"))[0]
        with self.assertRaises(ValueError):
            mm.download_and_document(lambda u, p: b"x", c, {}, tempfile.mkdtemp(), "f")

    def test_evidencia_generada_pasa_la_validacion_de_licencias_de_la_compuerta(self):
        raw = self.api(); c = mm.parse_candidates(raw)[0]
        d = Path(tempfile.mkdtemp())
        buf = tempfile.mktemp(suffix=".jpg"); Image.new("RGB", (2400, 1600), (9, 9, 9)).save(buf, "JPEG")
        rec = mm.download_and_document(lambda u, p: Path(buf).read_bytes(), c, raw, d, "foto1")
        self.assertEqual(reg.check_photo_evidence(d, rec["foto_manifest"], rec["foto_evidence"]), [])
        self.assertFalse(rec["foto_manifest"]["revision_humana"])

    def test_busqueda_usa_la_api_de_commons(self):
        seen = {}
        def fake(url, params):
            seen["url"], seen["q"] = url, params["gsrsearch"]; return self.api()
        data, cands = mm.search(fake, "ANDI Colombia")
        self.assertIn("commons.wikimedia.org", seen["url"]); self.assertEqual(len(cands), 1)


class VoiceTests(unittest.TestCase):
    class Fake:
        name = "fake"
        def __init__(self, kind): self.kind = kind
        def synthesize(self, text, out): make_audio(out, self.kind, dur=5)

    def ev(self):
        return {"noticias": {"n1": {"guion": GUION}, "n2": {"guion": GUION}}}

    def test_genera_un_audio_por_noticia(self):
        r = voice.synthesize_edition(self.Fake("tone"), self.ev(), tempfile.mkdtemp())
        self.assertEqual(set(r), {"n1", "n2"})

    def test_audio_silencioso_se_rechaza(self):
        with self.assertRaises(RuntimeError):
            voice.synthesize_edition(self.Fake("silence"), self.ev(), tempfile.mkdtemp())

    def test_acento_no_se_da_por_validado_sin_prueba_de_escucha(self):
        d = Path(tempfile.mkdtemp()); (d / "m.mp3").write_bytes(b"muestra")
        ok = {"voz": "es-CO-SalomeNeural", "revisor": "editora", "fecha": "2026-11-12",
              "veredicto": "acento_colombiano_aprobado",
              "muestra": {"archivo": "m.mp3", "sha256": reg.sha256_file(d / "m.mp3")}}
        self.assertEqual(voice.validation_record_errors(ok, d), [])
        self.assertTrue(voice.validation_record_errors({}, d))
        self.assertTrue(voice.validation_record_errors({**ok, "veredicto": "pendiente"}, d))
        self.assertTrue(voice.validation_record_errors({**ok, "muestra": {"archivo": "m.mp3", "sha256": "0" * 64}}, d))


if __name__ == "__main__":
    unittest.main(verbosity=2)
