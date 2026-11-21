"""Adversarial tests for the 21 Nov 2026 Unsplash real-photo fallback."""
from __future__ import annotations

import unittest
from scripts.orbiuno_media_unsplash_20261121 import validate_photo, PHOTO_IDS


class UnsplashPhotoTests(unittest.TestCase):
    def valid(self):
        return {
            "photoMatchReviewed": True, "photoUnsplashRightsReviewed": True,
            "photoUnsplashImageUrl": "https://images.unsplash.com/" + PHOTO_IDS[0] + "?w=1600",
            "photoUnsplashPage": "https://unsplash.com/photos/real-airport-photo-i4cfTmz6jr8",
            "photoUnsplashAuthor": "Photographer", "photoCaption": "Aeropuerto real, fotografía de archivo ilustrativa.",
        }

    def test_six_whitelisted_photo_ids(self):
        self.assertEqual(len(PHOTO_IDS), 6)
        self.assertEqual(len(set(PHOTO_IDS)), 6)

    def test_verified_url_and_author(self):
        photo = validate_photo(self.valid(), 1)
        self.assertEqual(photo["license"], "Unsplash License")
        self.assertEqual(photo["author"], "Photographer")

    def test_rejects_unlicensed(self):
        item = self.valid()
        item["photoUnsplashRightsReviewed"] = False
        with self.assertRaises(ValueError):
            validate_photo(item, 1)

    def test_rejects_mismatched_image(self):
        item = self.valid()
        item["photoUnsplashImageUrl"] = "https://images.unsplash.com/" + PHOTO_IDS[1]
        with self.assertRaises(ValueError):
            validate_photo(item, 1)

    def test_rejects_external_or_redirected_origin(self):
        item = self.valid()
        item["photoUnsplashImageUrl"] = "https://untrusted.example/" + PHOTO_IDS[0]
        with self.assertRaises(ValueError):
            validate_photo(item, 1)

    def test_rejects_no_archive_disclosure(self):
        item = self.valid()
        item["photoCaption"] = "Este es el sismo del día 21 de noviembre."
        with self.assertRaises(ValueError):
            validate_photo(item, 1)


if __name__ == "__main__":
    unittest.main()
