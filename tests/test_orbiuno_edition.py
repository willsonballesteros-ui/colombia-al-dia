import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import orbiuno_edition as oe  # noqa: E402
import publish_meta as pm  # noqa: E402
import merge_edition as me  # noqa: E402

EID = "2026-11-07-0800"


def make_news(i, role):
    n = 40 if role == "principal" else 24
    return {"id": f"t{i}", "date": "2026-11-07", "title": f"Titular de ensayo número {i} para pruebas",
            "category": "Ensayo", "verification": "editorial_verified", "reelShort": f"Ensayo {i}",
            "reelNarrationEs": "Según Medio, " + " ".join(["texto de ensayo"] * (n // 3)),
            "sources": [{"name": "Medio", "url": f"https://example.com/noticias/2026/11/07/articulo-{i}"}],
            "originalArticleTextEs": "Primer párrafo propio.\n\nSegundo párrafo propio.\n\nTercer párrafo propio.",
            "originalArticleByline": "Redacción ORBIUNO", "originalArticleReviewed": True}


def make_data(approved=True):
    ed = {"editionId": EID, "date": "2026-11-07", "slot": "08:00", "newsIds": ["t1", "t2", "t3", "t4"],
          "roles": list(oe.ROLES)}
    if approved:
        ed["review"] = {"status": "approved", "by": "Editor", "at": "2026-11-07T07:30:00-05:00"}
    return {"news": [make_news(i + 1, r) for i, r in enumerate(oe.ROLES)], "editions": [ed]}


class ValidacionEdicion(unittest.TestCase):
    def bad(self, mutate, needle, approved=True):
        d = make_data(approved)
        mutate(d)
        with self.assertRaises(oe.EditionError) as cm:
            oe.validate_edition(d, EID)
        self.assertIn(needle, str(cm.exception))

    def test_edicion_valida(self):
        ed, news = oe.validate_edition(make_data(), EID)
        self.assertEqual(len(news), 4)

    def test_tres_noticias_no_publica(self):
        self.bad(lambda d: d["editions"][0].update(newsIds=["t1", "t2", "t3"]), "exactamente 4")

    def test_roles_deben_ser_2_y_2(self):
        self.bad(lambda d: d["editions"][0].update(roles=["breve", "principal", "principal", "breve"]), "roles")

    def test_sin_verificar(self):
        self.bad(lambda d: d["news"][0].update(verification="source_only"), "editorial_verified")

    def test_portada_de_medio_no_es_articulo(self):
        self.bad(lambda d: d["news"][1]["sources"][0].update(url="https://www.reuters.com/"), "enlace directo")

    def test_agregador_no_es_articulo(self):
        self.bad(lambda d: d["news"][1]["sources"][0].update(url="https://news.google.com/rss/articles/CBMi123456789?oc=5"), "enlace directo")

    def test_sin_aprobacion_humana(self):
        self.bad(lambda d: None, "aprobación humana", approved=False)

    def test_preview_no_exige_aprobacion(self):
        oe.validate_edition(make_data(approved=False), EID, require_approved=False)

    def test_narracion_fuera_de_rango(self):
        self.bad(lambda d: d["news"][3].update(reelNarrationEs="muy corto"), "palabras")

    def test_fecha_distinta(self):
        self.bad(lambda d: d["news"][2].update(date="2026-11-06"), "fecha")

    def test_marcador_todo(self):
        self.bad(lambda d: d["news"][0].update(title="TODO titular real aquí"), "TODO")

    def test_fuente_debe_pronunciarse(self):
        self.bad(lambda d: d["news"][0].update(reelNarrationEs=" ".join(["texto de ensayo"] * 13)), "pronunciar la fuente")

    def test_guion_y_pie(self):
        ed, news = oe.validate_edition(make_data(), EID)
        segs = oe.narration_segments(ed, news)
        self.assertEqual(len(segs), 6)
        self.assertIn("sábado siete de noviembre", segs[0].lower())
        cap = oe.build_caption(ed, news)
        self.assertIn(f"[ORB-{EID}]", cap)
        self.assertLessEqual(len(cap), 2200)


class FakeGraph:
    def __init__(self, script):
        self.uid, self.script, self.calls = "123", script, []
        self.sleep = lambda s: None

    def call(self, method, path, params=None, retries=3):
        self.calls.append((method, path))
        r = self.script(method, path, params)
        if isinstance(r, Exception):
            raise r
        return r


class PublicacionMeta(unittest.TestCase):
    marker = f"[ORB-{EID}]"

    def test_idempotente_si_ya_existe(self):
        g = FakeGraph(lambda m, p, q: {"data": [{"id": "9", "caption": "x " + self.marker, "permalink": "https://i/p/9"}]})
        r = pm.publish_reel(g, "https://v", "c " + self.marker, self.marker, wait=lambda *a: None)
        self.assertEqual(r["status"], "already_published")
        self.assertFalse(any(m == "POST" for m, _ in g.calls))

    def test_flujo_reel_exitoso_exige_permalink(self):
        def s(m, p, q):
            if p.endswith("/media") and m == "GET":
                return {"data": []}
            if p.endswith("/media") and m == "POST":
                self.assertEqual(q["media_type"], "REELS")
                self.assertEqual(q["share_to_feed"], "true")
                return {"id": "c1"}
            if p.endswith("media_publish"):
                return {"id": "m1"}
            return {"id": "m1", "permalink": "https://i/reel/m1", "media_product_type": "REELS"}
        r = pm.publish_reel(FakeGraph(s), "https://v", "c", self.marker, wait=lambda *a: None)
        self.assertEqual((r["status"], r["id"]), ("published", "m1"))

    def test_sin_permalink_no_es_exito(self):
        def s(m, p, q):
            if p.endswith("/media") and m == "GET":
                return {"data": []}
            if p.endswith("/media"):
                return {"id": "c1"}
            if p.endswith("media_publish"):
                return {"id": "m1"}
            return {"id": "m1"}
        with self.assertRaises(pm.MetaError):
            pm.publish_reel(FakeGraph(s), "https://v", "c", self.marker, wait=lambda *a: None)

    def test_publish_ambiguo_se_recupera_por_marcador(self):
        state = {"n": 0}

        def s(m, p, q):
            if p.endswith("/media") and m == "GET":
                state["n"] += 1
                if state["n"] == 1:
                    return {"data": []}
                return {"data": [{"id": "m7", "caption": self.marker, "permalink": "https://i/r/7"}]}
            if p.endswith("/media"):
                return {"id": "c1"}
            if p.endswith("media_publish"):
                return pm.MetaError("timeout")
            return {"id": "m7", "permalink": "https://i/r/7"}
        r = pm.publish_reel(FakeGraph(s), "https://v", "c", self.marker, wait=lambda *a: None)
        self.assertEqual(r["id"], "m7")

    def test_contenedor_en_error_falla(self):
        g = FakeGraph(lambda m, p, q: {"status_code": "ERROR", "status": "2207026"})
        with self.assertRaises(pm.MetaError):
            pm.wait_ready(g, "c1")

    def test_token_se_redacta(self):
        self.assertNotIn("SECRETO", pm.redact("fallo con SECRETO en url", "SECRETO"))

    def test_main_sin_credenciales_no_es_exito(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / EID
            f.mkdir()
            (f / "reel-manifest.json").write_text(json.dumps({"publishable": True, "publicUrl": "https://x/v.mp4",
                                                              "bytes": 1, "caption": "c"}))
            with mock.patch.dict(os.environ, {}, clear=True):
                self.assertEqual(pm.main(["--edition", EID, "--media-root", d]), 2)

    def test_main_manifiesto_no_publicable(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / EID
            f.mkdir()
            (f / "reel-manifest.json").write_text(json.dumps({"publishable": False}))
            self.assertEqual(pm.main(["--edition", EID, "--media-root", d, "--dry-run"]), 2)


    def test_dry_run_no_llama_a_meta(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / EID
            f.mkdir()
            (f / "reel-manifest.json").write_text(json.dumps({
                "publishable": True, "publicUrl": "https://x/reel.mp4", "bytes": 1,
                "story": {"publicUrl": "https://x/story.mp4", "bytes": 1},
            }))
            with mock.patch.object(pm, "check_public_video") as video, \
                 mock.patch.object(pm, "check_web_first", return_value=[]), \
                 mock.patch.object(pm, "Graph") as graph:
                self.assertEqual(pm.main(["--edition", EID, "--media-root", d, "--dry-run"]), 0)
                self.assertEqual(video.call_count, 2)
                graph.assert_not_called()


class WebPrimero(unittest.TestCase):
    def fetcher(self, data, page=None):
        page = page if page is not None else " ".join(f'<h3>{n["title"]}</h3>' for n in data["news"])

        def f(url):
            return json.dumps(data) if url.endswith("noticias.json") else f"<html><body>{page}</body></html>"
        return f

    def test_todo_en_linea(self):
        self.assertEqual(pm.check_web_first(EID, self.fetcher(make_data()), base="https://x"), [])

    def test_titular_ausente_de_portada_bloquea(self):
        d = make_data()
        p = pm.check_web_first(EID, self.fetcher(d, page="otra cosa"), base="https://x")
        self.assertTrue(any("portada pública" in x for x in p))

    def test_titular_solo_en_json_embebido_bloquea(self):
        d = make_data()
        embedded = '<script type="application/json">' + json.dumps(d, ensure_ascii=False) + '</script>'
        self.assertTrue(pm.check_web_first(EID, self.fetcher(d, page=embedded), base="https://x"))

    def test_reportaje_corto_bloquea(self):
        d = make_data()
        d["news"][2]["originalArticleTextEs"] = "Solo un párrafo."
        p = pm.check_web_first(EID, self.fetcher(d), base="https://x")
        self.assertTrue(any("párrafos" in x for x in p))

    def test_sin_revision_bloquea(self):
        d = make_data()
        d["news"][0]["originalArticleReviewed"] = False
        self.assertTrue(pm.check_web_first(EID, self.fetcher(d), base="https://x"))

    def test_web_caida_bloquea(self):
        def boom(url):
            raise OSError("sin conexión")
        self.assertTrue(pm.check_web_first(EID, boom, base="https://x"))


class IntegracionJson(unittest.TestCase):
    def frag(self):
        d = make_data()
        return {"edition": d["editions"][0], "news": d["news"]}

    def test_merge_idempotente(self):
        base = {"news": [{"id": "otro"}]}
        once = me.merge(copy.deepcopy(base), self.frag())
        twice = me.merge(copy.deepcopy(once), self.frag())
        self.assertEqual(once, twice)
        self.assertEqual(len(once["news"]), 5)

    def test_merge_conflicto_aborta(self):
        base = make_data()
        base["news"][0]["title"] = "Otro titular distinto de ensayo para pruebas"
        with self.assertRaises(SystemExit):
            me.merge(base, self.frag())


@unittest.skipUnless(shutil.which("ffmpeg") and all(
    __import__("importlib").util.find_spec(m) for m in ("PIL", "numpy")), "requiere ffmpeg, Pillow y numpy")
class ReelCuatroNoticias(unittest.TestCase):
    def test_reel_1080x1920_con_escenas_sincronizadas(self):
        import numpy as np
        import render_orbiuno_edition as ar
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            data = make_data(approved=False)
            for i, n in enumerate(data["news"]):
                n["title"] = ["Ejemplo uno: el titular cambia por completo en esta tarjeta",
                              "Segundo caso técnico con palabras distintas para el contraste",
                              "Tercero breve: verificación del cambio de escena",
                              "Cuarto y último titular de ensayo, sin relación"][i]
            (d / "n.json").write_text(json.dumps(data, ensure_ascii=False))
            ed, news = oe.validate_edition(data, EID, require_approved=False)
            rng = np.random.default_rng(3)
            for i, t in enumerate(oe.narration_segments(ed, news)):
                sr, T = 24000, oe.words(t) / 3.6
                x = np.arange(int(sr * T)) / sr
                sp = np.fft.irfft(np.fft.rfft(rng.standard_normal(x.size)) / (1 + (np.fft.rfftfreq(x.size, 1 / sr) / 1500) ** 2), x.size)
                sp /= np.abs(sp).max()
                env = (np.abs(np.sin(2 * np.pi * 3.7 * x)) ** 1.5) * (0.5 + 0.5 * np.abs(np.sin(2 * np.pi * 0.45 * x + 1)))
                pcm = (np.clip(0.35 * sp * env, -1, 1) * 32767).astype("<i2")
                with wave.open(str(d / f"seg{i}.wav"), "wb") as w:
                    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())
            rc = ar.main(["--edition", EID, "--data", str(d / "n.json"), "--out-root", str(d / "media"),
                          "--preview", "--test-audio-dir", str(d)])
            m = json.loads((d / "media" / EID / "reel-manifest.json").read_text())
            self.assertEqual(rc, 0, m["checks"]["errors"])
            self.assertEqual((m["checks"]["width"], m["checks"]["height"]), (1080, 1920))
            self.assertEqual(len(m["scenes"]), 6)
            self.assertFalse(m["publishable"])  # prueba/preview jamás publicable
            self.assertEqual(m["voice"], "TEST-FIXTURE")
            self.assertEqual((m["story"]["checks"]["width"], m["story"]["checks"]["height"]), (1080, 1920))
            self.assertLess(m["story"]["checks"]["duration_s"], 60)
            self.assertLess(m["story"]["checks"]["duration_s"], m["checks"]["duration_s"] / 2)
            self.assertIsNone(m["music"])
            self.assertLessEqual(m["checks"]["true_peak_dbfs"], -0.5)
            # con música: ducking + sonoridad
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            "aevalsrc='0.5*sin(2*PI*220*t)*(0.6+0.4*sin(2*PI*2*t))':s=48000:d=5", str(d / "musica.m4a")], check=True)
            rc2 = ar.main(["--edition", EID, "--data", str(d / "n.json"), "--out-root", str(d / "media2"),
                           "--preview", "--test-audio-dir", str(d), "--music", str(d / "musica.m4a")])
            m2 = json.loads((d / "media2" / EID / "reel-manifest.json").read_text())
            self.assertEqual(rc2, 0, m2["checks"]["errors"])
            self.assertEqual(m2["music"]["file"], "musica.m4a")
            self.assertAlmostEqual(m2["checks"]["duration_s"], m["checks"]["duration_s"], delta=1.0)
            self.assertGreater(m2["checks"]["lufs_integrated"], -17.0)
            self.assertLess(m2["checks"]["lufs_integrated"], -11.0)

    def test_texto_dentro_de_zona_segura(self):
        import numpy as np
        import render_orbiuno_edition as ar
        data = make_data(approved=False)
        ed, news = oe.validate_edition(data, EID, require_approved=False)
        news[0]["reelShort"] = "Un titular bastante largo para comprobar que el ajuste de línea respeta la zona segura del formato vertical"
        cards = [ar.card_overview(ed, news), ar.card_outro(ed)] + [ar.card_overview(ed, news, i) for i in range(1, 5)]
        for c in cards:
            a = np.asarray(c).astype(int)
            bright = (a.max(axis=2) > 200) & (np.arange(a.shape[1])[None, :] >= 30)
            ys, xs = np.where(bright)
            self.assertGreaterEqual(xs.min(), 95)
            self.assertLessEqual(xs.max(), 945)
            self.assertGreaterEqual(ys.min(), 255)
            self.assertLessEqual(ys.max(), 1530)


if __name__ == "__main__":
    unittest.main()
