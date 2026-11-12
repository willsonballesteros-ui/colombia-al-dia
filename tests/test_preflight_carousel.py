import hashlib, importlib.util, json, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("carousel_preflight", root/"scripts/preflight_carousel.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CarouselSafety(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        Image.new("RGB",(500,400),"navy").save(self.root/"photo.png")
        Image.new("RGB",(80,80),"white").save(self.root/"logo.png")
        (self.root/"voice.mp3").write_bytes(b"x"*15000)
        phash=hashlib.sha256((self.root/"photo.png").read_bytes()).hexdigest()
        self.manifest={"edition_id":"2026-11-12-am","fecha":"2026-11-12","hora":"08:00","status":"approved","noticias":[]}
        for i in range(5):
            self.manifest["noticias"].append({
              "id":f"item{i}","titular":f"Titular periodístico verificado {i}",
              "resumen":"Texto editorial suficientemente largo para la comprobación de datos.",
              "fecha":"2026-11-12","fuente":"Medio de prueba",
              "url_fuente":f"https://example.org/articulo/{i}","logo_fuente":"logo.png",
              "foto":{"archivo":"photo.png","url_origen":"https://example.org/photo.png",
                      "autor":"Autor", "licencia":"CC BY 4.0","credito":"Autor",
                      "sha256":phash,"revision_humana":True},
              "audio":{"archivo":"voice.mp3","duracion_s":12,"voz_colombiana_validada":True}})
        self.input=self.root/"manifest.json"
        self.web=self.root/"web.json"

    @staticmethod
    def fake(args, **kwargs):
        if args[0]=="ffprobe":
            return subprocess.CompletedProcess(args,0,json.dumps({"format":{"duration":"12"},"streams":[{"codec_type":"audio","codec_name":"mp3","sample_rate":"44100","channels":1}]}),"")
        return subprocess.CompletedProcess(args,0,"","mean_volume: -18.0 dB" if "volumedetect" in args else "")

    def check(self, other=None, web=True, fake=None):
        self.input.write_text(json.dumps(self.manifest),encoding="utf-8")
        self.web.write_text(json.dumps(other if other is not None else self.manifest),encoding="utf-8")
        with patch.object(mod.subprocess,"run",side_effect=fake or self.fake):
            return mod.validate(self.input,self.web if web else None)

    def test_valid_structure(self):
        self.assertEqual([],self.check())
    def test_missing_web_blocks(self):
        self.assertTrue(self.check(web=False))
    def test_mismatch_blocks(self):
        other=json.loads(json.dumps(self.manifest))
        other["noticias"][0]["resumen"]="El resumen de la web es distinto, lo que bloquea publicación."
        self.assertTrue(any("no coinciden" in e for e in self.check(other)))
    def test_bad_hash_blocks(self):
        self.manifest["noticias"][0]["foto"]["sha256"]="0"*64
        self.assertTrue(any("SHA-256" in e for e in self.check()))
    def test_silent_audio_blocks(self):
        def fake(args,**kwargs):
            if "volumedetect" in args:
                return subprocess.CompletedProcess(args,0,"","mean_volume: -inf dB")
            return self.fake(args,**kwargs)
        self.assertTrue(any("silencioso" in e for e in self.check(fake=fake)))
    def test_no_audio_track_blocks(self):
        def fake(args,**kwargs):
            if args[0]=="ffprobe":
                return subprocess.CompletedProcess(args,0,json.dumps({"format":{"duration":"12"},"streams":[]}),"")
            return self.fake(args,**kwargs)
        self.assertTrue(any("pista de audio" in e for e in self.check(fake=fake)))
    def test_duplicate_blocks(self):
        self.manifest["noticias"][1]["url_fuente"]=self.manifest["noticias"][0]["url_fuente"]
        self.assertTrue(any("duplicada" in e for e in self.check()))
    def test_path_traversal_blocks(self):
        self.manifest["noticias"][0]["foto"]["archivo"]="../not-allowed.png"
        self.assertTrue(any("fotografía" in e for e in self.check()))
    def test_unapproved_blocks(self):
        self.manifest["status"]="blocked"
        self.assertTrue(any("no aprobada" in e for e in self.check()))

    def real_audio_fixture(self, silent=False):
        source = "anullsrc=r=44100:cl=mono" if silent else "sine=frequency=440:sample_rate=44100:duration=3"
        cmd = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
               "-f", "lavfi", "-i", source]
        if silent:
            cmd += ["-t", "3"]
        cmd += ["-ac", "1", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k",
                str(self.root / "voice.mp3")]
        subprocess.run(cmd, check=True, timeout=30)
        for note in self.manifest["noticias"]:
            note["audio"]["duracion_s"] = 3.0
        self.input.write_text(json.dumps(self.manifest), encoding="utf-8")
        self.web.write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_real_ffmpeg_silence_blocks(self):
        self.real_audio_fixture(silent=True)
        problems = mod.validate(self.input, self.web)
        self.assertTrue(any("silencioso" in e for e in problems), problems)

    def test_real_ffmpeg_tone_passes_audio_preflight(self):
        self.real_audio_fixture(silent=False)
        problems = mod.validate(self.input, self.web)
        self.assertEqual([], problems)
