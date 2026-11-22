"""Pruebas de composición: fotografía protagonista y paneles inferiores compactos.

Sin red, sin Meta y sin alterar videos ya publicados.
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.render_orbiuno_aprobado import draw_cover, draw_story


class PhotoFirstRenderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.assets = self.root / "assets"
        self.assets.mkdir()
        self.color = (130, 155, 170)
        Image.new("RGB", (1080, 1920), self.color).save(
            self.assets / "photo-01.jpg", quality=100
        )
        Image.new("RGBA", (128, 128), (255, 255, 255, 255)).save(
            self.assets / "logo-01.png"
        )

    def tearDown(self):
        self.tmp.cleanup()

    def assert_photo_visible(self, path):
        with Image.open(path) as image:
            self.assertEqual(image.size, (1080, 1920))
            # Región central: ningún panel gigante debe tapar la fotografía.
            for y in (450, 700, 1050, 1330):
                sample = image.getpixel((540, y))
                self.assertTrue(
                    all(abs(actual - expected) < 12
                        for actual, expected in zip(sample, self.color)),
                    f"Foto tapada en y={y}: {sample}",
                )
            # Pie compacto oscuro (no más de 490 px).
            footer = image.getpixel((1000, 1910))
            self.assertLess(sum(footer), 150)

    def test_cover_shows_real_photo_through_center(self):
        target = self.root / "cover.jpg"
        draw_cover(
            [{"title": "Una noticia de Colombia para la portada"}],
            "2026-11-22", "09:30", target,
            self.assets / "photo-01.jpg",
        )
        self.assert_photo_visible(target)

    def test_story_shows_real_photo_through_center(self):
        target = self.root / "story.jpg"
        draw_story(
            {"title": "Seis noticias con fotografías protagonistas",
             "sources": [{"name": "ORGANISMO OFICIAL"}]},
            {"photoFile": "photo-01.jpg",
             "logoFile": "logo-01.png",
             "credit": {"author": "Archivo", "license": "CC BY 4.0"}},
            self.assets, "2026-11-22", "09:30", 1, target,
        )
        self.assert_photo_visible(target)


if __name__ == "__main__":
    unittest.main()
