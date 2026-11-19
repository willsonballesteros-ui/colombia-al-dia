"""Pruebas adversariales sin red ni Meta para el flujo visual/voz aprobado."""
import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from scripts.orbiuno_media_assets import commons_info, validate_editorial_photo, decode_image, stage
from scripts.orbiuno_qa_aprobado import validate


def commons_fixture(lic="CC BY 4.0", author="Autor comprobado", width=1200, mime="image/jpeg", description="Bosque natural"):
    return json.dumps({"query": {"pages": {"22": {
        "title": "File:Bosque de Colombia.jpg", "imageinfo": [{"mime": mime, "width": width,
        "height": 900, "thumburl": "https://upload.wikimedia.org/example.jpg",
        "extmetadata": {"LicenseShortName": {"value": lic}, "Artist": {"value": author},
                        "ImageDescription": {"value": description}}}]}}}}).encode()


class PhotoEvidenceTests(unittest.TestCase):
    def test_commons_metadata_is_required(self):
        data = commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture())
        self.assertEqual(data["license"], "CC BY 4.0")
        self.assertIn("commons.wikimedia.org/wiki/File:", data["page"])

    def test_rejects_reserved_rights(self):
        with self.assertRaises(ValueError):
            commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture(lic="All rights reserved"))

    def test_rejects_missing_author(self):
        with self.assertRaises(ValueError):
            commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture(author=""))

    def test_rejects_low_resolution(self):
        with self.assertRaises(ValueError):
            commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture(width=200))

    def test_rejects_svg(self):
        with self.assertRaises(ValueError):
            commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture(mime="image/svg+xml"))

    def test_rejects_ai(self):
        with self.assertRaises(ValueError):
            commons_info("File:Bosque de Colombia.jpg", getter=lambda _: commons_fixture(description="AI-generated illustration"))

    def test_rejects_unreviewed_photo_subject(self):
        with self.assertRaises(ValueError):
            validate_editorial_photo({"photoCommonsTitle": "File:Bosque de Colombia.jpg", "photoCaption": "Bosque amazónico"})

    def test_rejects_source_only_edition_before_media(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            edition = root / "edition.json"
            edition.write_text(json.dumps({"editionDate": "2026-11-19", "editionSlot": "18:00", "sourceOnly": True, "news": []}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source_only"):
                stage(edition, root / "missing.json", root / "images")

    def test_rejects_bytes_which_are_not_real_jpeg(self):
        with self.assertRaises(Exception):
            decode_image(b"FAKE JPEG" * 1000)


def build_fixture(tmp):
    news, credits, web = [], [], {"items": {}}
    for i in range(1, 7):
        id_ = "n" + str(i)
        text = ("Artículo propio completo " * 100).strip()
        Image.new("RGB", (1000, 800), (100+i, 110, 130)).save(tmp / f"photo-{i:02}.jpg")
        logo = Image.new("RGB", (100, 100), (255, 255, 255))
        for xx in range(100):
            for yy in range(100):
                logo.putpixel((xx, yy), ((xx*17+yy*19)%256, (xx*3+yy*9)%256, (xx*5+yy*7)%256))
        logo.save(tmp / f"logo-{i:02}.png")
        (tmp / "frames").mkdir(exist_ok=True)
        Image.new("RGB", (1080, 1920), (10, 28, 60)).save(tmp / "frames" / f"noticia-{i:02}.jpg")
        news.append({"id": id_, "date": "2026-11-19", "editionSlot": "18:00", "verification": "editorial_verified",
                     "priority": i, "originalArticleTextEs": text, "imageRightsVerified": True,
                     "imageLicense": "CC BY 4.0", "imageCredit": "Autora",
                     "sources": [{"url": f"https://original.com/news/{i}"}],
                     "imageUrl": f"./media/2026-11-19/1800_assets/photo-{i:02}.jpg",
                     "imageSourceUrl": "https://commons.wikimedia.org/wiki/File:Foto.jpg"})
        credits.append({"author": "Autora", "license": "CC BY 4.0"})
        web["items"][id_] = {"voice": "es-CO-SalomeNeural", "speed": 1.25, "text": text}
    video = tmp / "sample.mp4"
    video.write_bytes(b"0" * 400000)
    import hashlib
    m = {"edition": "2026-11-19", "slot": "18:00", "newsIds": [n["id"] for n in news],
         "voice": "es-CO-SalomeNeural", "voiceSpeed": 1.25, "language": "es-CO",
         "visualMode": "verified_real_photos", "imagesCount": 6, "logosCount": 6,
         "sourceOnly": False, "publicationAuthorized": False, "photoCredits": credits,
         "news": [{"sourceUrl": n["sources"][0]["url"]} for n in news],
         "video": "sample.mp4", "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
         "duration": 87.4}
    return m, {"news": news}, web


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.m, self.news, self.web = build_fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def run_gate(self):
        return validate(self.m, folder=self.root, assets=self.root, news=self.news, webvoice=self.web)

    def test_duration_above_60_is_allowed(self):
        self.assertEqual(self.run_gate(), [])

    def test_no_photo_rejected(self):
        self.m["imagesCount"] = 0
        self.assertIn("real_photos_or_logos_missing", self.run_gate())

    def test_no_logo_rejected(self):
        (self.root / "logo-03.png").unlink()
        self.assertIn("missing_visual_asset_3", self.run_gate())

    def test_dora_rejected(self):
        self.m["voice"] = "ef_dora"
        self.assertIn("wrong_voice_or_speed", self.run_gate())

    def test_source_only_rejected(self):
        self.m["sourceOnly"] = True
        self.assertIn("source_only_or_false_approval", self.run_gate())

    def test_truncated_web_audio_rejected(self):
        self.web["items"]["n2"]["text"] = "resumen"
        self.assertIn("web_full_audio_mismatch_2", self.run_gate())

    def test_wrong_original_link_rejected(self):
        self.m["news"][0]["sourceUrl"] = "https://example.com/"
        self.assertIn("source_url_mismatch_1", self.run_gate())

    def test_photo_credit_disagreement_rejected(self):
        self.news["news"][0]["imageCredit"] = "Autor diferente"
        self.assertIn("image_credit_mismatch_1", self.run_gate())

    def test_video_hash_rejected(self):
        self.m["sha256"] = "0" * 64
        self.assertIn("mp4_sha_mismatch", self.run_gate())

    def test_qa_cannot_self_authorize(self):
        self.assertFalse(self.m["publicationAuthorized"])


if __name__ == "__main__":
    unittest.main()
