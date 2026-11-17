import copy
import unittest

from scripts.orbiuno_import_daily import import_edition, validated


def example():
    day, slot = "2026-11-17", "08:00"
    news = []
    for i in range(1, 7):
        url = "https://example.org/news/article-" + str(i)
        article = ("Este es un párrafo original de prueba de la redacción de ORBIUNO, "
                   "que no reproduce el artículo del medio y tiene información contextual. ") * 4
        news.append({
            "id": f"orbiuno-20261117-0800-{i}",
            "date": day, "editionSlot": slot, "priority": i,
            "title": f"Titular de prueba sobre actualidad número {i}",
            "category": "Colombia" if i < 3 else "Internacional",
            "verification": "editorial_verified",
            "sources": [{"name": "Fuente", "url": url}],
            "originalArticleByline": "Redacción ORBIUNO",
            "originalArticleReviewed": True,
            "originalArticleTextEs": "\n\n".join([article] * 3),
            "originalArticleSourceUrls": [url],
            "originalArticleIsPublisherVerbatim": False,
            "reelLine": "Un ejemplo breve y verificable para la noticia uno.",
        })
    return {"editionDate": day, "editionSlot": slot,
            "editionKey": "ORBIUNO-2026-11-17-0800", "news": news}


class DailyEditionTests(unittest.TestCase):
    def setUp(self):
        self.d = example()
        self.old = {"editionDate": "2026-11-16",
                    "news": [{"id": "hist-20261116-1", "date": "2026-11-16",
                              "editionSlot": "19:00", "verification": "editorial_verified"}]}

    def test_validates_six_and_preserves_archive(self):
        new = import_edition(copy.deepcopy(self.old), self.d, today="2026-11-17")
        self.assertEqual(len(new["news"]), 7)
        self.assertEqual(new["news"][0]["id"], "hist-20261116-1")
        self.assertEqual(new["editionDate"], "2026-11-17")

    def test_idempotent_same_edition(self):
        new = import_edition(copy.deepcopy(self.old), self.d, today="2026-11-17")
        twice = import_edition(new, self.d, today="2026-11-17")
        self.assertEqual(len(twice["news"]), 7)

    def test_rejects_old_date(self):
        with self.assertRaisesRegex(ValueError, "otra fecha"):
            validated(self.d, today="2026-11-18")

    def test_rejects_five_news(self):
        self.d["news"].pop()
        with self.assertRaisesRegex(ValueError, "seis noticias"):
            validated(self.d, today="2026-11-17")

    def test_rejects_fake_homepage_source(self):
        self.d["news"][0]["sources"][0]["url"] = "https://example.org/"
        with self.assertRaisesRegex(ValueError, "artículo exacto"):
            validated(self.d, today="2026-11-17")

    def test_rejects_unlicensed_photo(self):
        self.d["news"][0]["imageUrl"] = "https://example.org/image.jpg"
        with self.assertRaisesRegex(ValueError, "Fotografía sin licencia"):
            validated(self.d, today="2026-11-17")

    def test_rejects_replaced_edition(self):
        old = import_edition(copy.deepcopy(self.old), self.d, today="2026-11-17")
        changed = example()
        changed["news"][0]["id"] = "orbiuno-20261117-0800-different"
        with self.assertRaisesRegex(ValueError, "sobrescribir"):
            import_edition(old, changed, today="2026-11-17")

    def test_rejects_duplicate_id(self):
        self.d["news"][1]["id"] = self.d["news"][0]["id"]
        with self.assertRaisesRegex(ValueError, "duplicados"):
            validated(self.d, today="2026-11-17")


if __name__ == "__main__":
    unittest.main()
