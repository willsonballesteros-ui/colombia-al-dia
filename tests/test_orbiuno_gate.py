import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from PIL import Image
import orbiuno_approval as approval
import orbiuno_audio_check as audio
import orbiuno_gate as gate
import orbiuno_media_registry as media
from orbiuno_idempotency import DuplicateBlocked, Ledger, make_key
from orbiuno_meta_publish import MetaPublisher, PublishBlocked, PublishFailed, to_jpeg

KEY = "clave-de-prueba"
GUION = " ".join(["palabra"] * 14)  # ~14 palabras => 4.1-7 s


def ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def make_audio(path, kind="tone", dur=5):
    src = {"tone": f"sine=frequency=440:duration={dur}",
           "silence": f"anullsrc=r=44100:cl=mono"}[kind]
    extra = ["-t", str(dur)] if kind == "silence" else []
    ffmpeg("-f", "lavfi", "-i", src, *extra, "-c:a", "libmp3lame", str(path))


def png(path, size, color):
    Image.new("RGB", size, color).save(path, "PNG")


def sha(p):
    return media.sha256_file(p)


def build_edition(root):
    root = Path(root)
    ed, reg = root / "editions" / "2026-11-12-am", root / "branding" / "logos"
    ed.mkdir(parents=True); reg.mkdir(parents=True)
    fuentes, noticias, ev = {}, [], {}
    for i in range(1, 6):
        fid = f"medio{i}"
        logo = reg / f"{fid}.png"; png(logo, (600, 200), (i * 30, 10, 10))
        fuentes[fid] = {"nombre_oficial": f"Medio {i}", "dominios": [f"medio{i}.com"],
                        "archivo": f"{fid}.png", "url_origen": f"https://medio{i}.com/brand",
                        "sha256": sha(logo), "condiciones_uso": "autorización escrita"}
        shutil.copy(logo, ed / f"logo{i}.png")
        ph = ed / f"foto{i}.png"; png(ph, (1600, 1000), (20, i * 40, 90))
        evid = ed / f"licencia{i}.txt"; evid.write_text(f"captura licencia {i}")
        a = ed / f"audio{i}.mp3"; make_audio(a)
        nid = f"n{i}"
        noticias.append({"id": nid, "titular": f"Titular {i}", "resumen": "r" * 40, "fecha": "2026-11-12",
                         "fuente": f"Medio {i}", "url_fuente": f"https://www.medio{i}.com/nota-{i}",
                         "logo_fuente": f"logo{i}.png",
                         "foto": {"archivo": f"foto{i}.png", "sha256": sha(ph), "url_origen": "https://x.org",
                                  "autor": "A", "licencia": "CC", "credito": "A", "revision_humana": True},
                         "audio": {"archivo": f"audio{i}.mp3", "duracion_s": 5, "voz_colombiana_validada": True}})
        ev[nid] = {"fuente_id": fid, "guion": GUION, "foto": {
            "licencia_codigo": "CC-BY-4.0", "licencia_url": "https://creativecommons.org/licenses/by/4.0/",
            "sha256_foto": sha(ph), "evidencia": {"archivo": f"licencia{i}.txt", "sha256": sha(evid)}}}
    for j, name in enumerate(gate.PNG_NAMES):
        png(ed / name, (1080, 1350), (j * 20, 40, 80))
    (reg / "registry.json").write_text(json.dumps({"fuentes": fuentes}))
    (ed / "manifest.json").write_text(json.dumps(
        {"edition_id": "2026-11-12-am", "fecha": "2026-11-12", "hora": "08:00",
         "status": "approved", "noticias": noticias}))
    (ed / "evidence.json").write_text(json.dumps({"noticias": ev}))
    sign_approval(ed)
    return ed, reg / "registry.json"


def sign_approval(ed, by="editora"):
    d = approval.manifest_digest(ed / "manifest.json")
    at = "2026-11-12T12:00:00Z"
    (ed / "approval.json").write_text(json.dumps({
        "edition_id": "2026-11-12-am", "manifest_sha256": d, "approved_by": by, "approved_at": at,
        "signature": approval.sign(KEY, "2026-11-12-am", d, by, at)}))


def ok_preflight(m, w):
    return []


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ed, self.reg = build_edition(self.tmp)
        self.ledger = Path(self.tmp) / "ledger.json"

    def run_gate(self, **kw):
        args = dict(ledger_path=self.ledger, approvers=["editora"], logo_registry=self.reg,
                    key=KEY, generator_id="bot", preflight_runner=ok_preflight)
        args.update(kw)
        return gate.evaluate(self.ed, None, **args)

    def has(self, errs, text):
        self.assertTrue(any(text in e for e in errs), f"{text!r} no está en {errs}")

    def edit(self, fn, name="manifest.json", resign=True):
        p = self.ed / name
        d = json.loads(p.read_text()); fn(d); p.write_text(json.dumps(d))
        if resign and name == "manifest.json":
            sign_approval(self.ed)

    def test_edition_valida_abre_la_compuerta(self):
        self.assertEqual(self.run_gate(), [])

    def test_foto_sin_licencia_permitida(self):
        self.edit(lambda d: d["noticias"]["n1"]["foto"].update(licencia_codigo="TODOS-LOS-DERECHOS"),
                  "evidence.json")
        self.has(self.run_gate(), "licencia no permitida")

    def test_evidencia_alterada(self):
        (self.ed / "licencia1.txt").write_text("otra cosa")
        self.has(self.run_gate(), "documento de evidencia no coincide")

    def test_foto_con_hash_modificado_rompe_vinculo(self):
        png(self.ed / "foto2.png", (1600, 1000), (1, 1, 1))
        self.has(self.run_gate(), "no coincide con el hash del manifiesto")

    def test_logo_no_registrado(self):
        png(self.ed / "logo1.png", (600, 200), (250, 250, 250))
        self.has(self.run_gate(), "no es el registrado")

    def test_logo_dominio_de_otra_fuente(self):
        self.edit(lambda d: d["noticias"][0].update(url_fuente="https://www.otro.com/nota"))
        self.has(self.run_gate(), "no pertenece a 'medio1'")

    def test_logo_pequeno(self):
        reg_root = Path(self.reg).parent
        png(reg_root / "medio3.png", (200, 80), (9, 9, 9)); shutil.copy(reg_root / "medio3.png", self.ed / "logo3.png")
        r = json.loads(Path(self.reg).read_text()); r["fuentes"]["medio3"]["sha256"] = sha(reg_root / "medio3.png")
        Path(self.reg).write_text(json.dumps(r))
        self.has(self.run_gate(), "demasiado pequeño")

    def test_audio_silencioso(self):
        make_audio(self.ed / "audio1.mp3", "silence")
        self.has(self.run_gate(), "silencioso")

    def test_audio_truncado(self):
        data = (self.ed / "audio2.mp3").read_bytes()
        (self.ed / "audio2.mp3").write_bytes(data[: len(data) // 5])
        self.has(self.run_gate(), "truncado")

    def test_audio_que_no_corresponde_al_guion(self):
        self.edit(lambda d: d["noticias"]["n3"].update(guion=" ".join(["x"] * 200)), "evidence.json")
        self.has(self.run_gate(), "fuera del rango esperado")

    def test_audio_sin_pista(self):
        ffmpeg("-f", "lavfi", "-i", "color=c=black:s=64x64:d=5", "-c:v", "libx264", str(self.ed / "v.mp4"))
        self.assertEqual(audio.check_audio(self.ed / "v.mp4", GUION), ["sin pista de audio legible"])

    def test_png_dimensiones_equivocadas_o_faltante(self):
        png(self.ed / "noticia_02.png", (1080, 1080), (5, 5, 5))
        (self.ed / "noticia_05.png").unlink()
        errs = self.run_gate()
        self.has(errs, "noticia_02.png"); self.has(errs, "noticia_05.png")

    def test_laminas_identicas(self):
        shutil.copy(self.ed / "noticia_01.png", self.ed / "noticia_02.png")
        self.has(self.run_gate(), "idénticas")

    def test_sin_aprobacion(self):
        (self.ed / "approval.json").unlink()
        self.has(self.run_gate(), "aprobación editorial ausente")

    def test_manifiesto_cambia_tras_aprobar(self):
        self.edit(lambda d: d["noticias"][0].update(titular="Titular cambiado"), resign=False)
        self.has(self.run_gate(), "cambió después de la aprobación")

    def test_firma_invalida_y_aprobador_no_autorizado(self):
        self.has(self.run_gate(key="otra-clave"), "firma de aprobación inválida")
        self.has(self.run_gate(approvers=["otra"]), "no está autorizado")

    def test_el_generador_no_puede_aprobar(self):
        sign_approval(self.ed, by="bot")
        self.has(self.run_gate(approvers=["bot"]), "no puede aprobarla")

    def test_sin_clave_bloquea(self):
        self.has(self.run_gate(key=None), "clave de aprobación no disponible")

    def test_preflight_fallido_bloquea(self):
        self.has(self.run_gate(preflight_runner=lambda m, w: ["preflight: web distinta"]), "web distinta")

    def test_edicion_ya_publicada(self):
        key = make_key("2026-11-12-am", approval.manifest_digest(self.ed / "manifest.json"))
        Ledger(self.ledger).update(key, status="published", media_id="123")
        self.has(self.run_gate(), "ya publicada")

    def test_ruta_insegura(self):
        with self.assertRaises(ValueError):
            media.safe_path(self.ed, "../manifest.json")


class PublisherTests(unittest.TestCase):
    URLS = [f"https://colombia-al-dia.pages.dev/e/{i}.jpg" for i in range(6)]

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.ledger = Ledger(Path(self.tmp) / "l.json")
        self.calls = []
        os.environ["ORBIUNO_ALLOW_LIVE"] = "1"

    def tearDown(self):
        os.environ.pop("ORBIUNO_ALLOW_LIVE", None)

    def http(self, fail_child=None, fail_publish=False):
        n = {"c": 0}
        def f(method, url, params):
            self.calls.append((method, url.split("/")[-1], dict(params)))
            if url.endswith("/media") and params.get("is_carousel_item"):
                n["c"] += 1
                if fail_child == n["c"]:
                    raise RuntimeError("red caída")
                return {"id": f"child{n['c']}"}
            if url.endswith("/media"):
                return {"id": "carrusel1"}
            if url.endswith("carrusel1"):
                return {"status_code": "FINISHED"}
            if url.endswith("media_publish"):
                if fail_publish:
                    raise RuntimeError("timeout")
                return {"id": "post1"}
        return f

    def pub(self, http, **kw):
        a = dict(ig_user_id="17", token="tok", graph_version="vX", dry_run=False, sleep=lambda s: None)
        a.update(kw)
        return MetaPublisher(http, self.ledger, **a)

    def test_dry_run_no_llama_a_la_red(self):
        r = MetaPublisher(self.http(), self.ledger).publish("k", self.URLS, "txt")
        self.assertTrue(r["dry_run"]); self.assertEqual(self.calls, [])

    def test_token_invalido_o_ausente_bloquea(self):
        with self.assertRaises(PublishBlocked):
            self.pub(self.http(), token=None).publish("k", self.URLS, "txt")
        self.assertEqual(self.calls, [])

    def test_sin_autorizacion_live_bloquea(self):
        os.environ.pop("ORBIUNO_ALLOW_LIVE")
        with self.assertRaises(PublishBlocked):
            self.pub(self.http()).publish("k", self.URLS, "txt")

    def test_publicacion_completa_y_reintento_bloqueado(self):
        r = self.pub(self.http()).publish("k", self.URLS, "txt")
        self.assertEqual(r["media_id"], "post1")
        n = len(self.calls)
        with self.assertRaises(DuplicateBlocked):
            self.pub(self.http()).publish("k", self.URLS, "txt")
        self.assertEqual(len(self.calls), n)

    def test_fallo_parcial_no_publica_y_reintento_reutiliza_hijos(self):
        with self.assertRaises(PublishFailed):
            self.pub(self.http(fail_child=4)).publish("k", self.URLS, "txt")
        self.assertFalse(any(c[1] == "media_publish" for c in self.calls))
        self.calls.clear()
        r = self.pub(self.http()).publish("k", self.URLS, "txt")
        created = [c for c in self.calls if c[2].get("is_carousel_item")]
        self.assertEqual(len(created), 3)  # solo las 3 imágenes que faltaban
        self.assertEqual(r["media_id"], "post1")

    def test_publicar_sin_confirmacion_exige_revision_manual(self):
        with self.assertRaises(PublishFailed):
            self.pub(self.http(fail_publish=True)).publish("k", self.URLS, "txt")
        with self.assertRaises(DuplicateBlocked):
            self.pub(self.http()).publish("k", self.URLS, "txt")

    def test_exige_seis_imagenes_https(self):
        with self.assertRaises(PublishBlocked):
            self.pub(self.http()).publish("k", self.URLS[:5], "txt")
        with self.assertRaises(PublishBlocked):
            self.pub(self.http()).publish("k", ["http://x/a.jpg"] * 6, "txt")

    def test_conversion_a_jpeg_y_tamano(self):
        p = Path(self.tmp) / "a.png"; png(p, (1080, 1350), (3, 3, 3))
        out = to_jpeg(p, Path(self.tmp) / "a.jpg")
        with Image.open(out) as im:
            self.assertEqual((im.format, im.size), ("JPEG", (1080, 1350)))
        png(p, (1000, 1000), (3, 3, 3))
        with self.assertRaises(PublishBlocked):
            to_jpeg(p, Path(self.tmp) / "b.jpg")


if __name__ == "__main__":
    unittest.main(verbosity=2)
