import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.publication_preflight_6 import preflight

NOW=datetime(2026,11,15,9,49,tzinfo=ZoneInfo("America/Bogota"))
def news(i):
    return {"id":f"n-{i}","date":"2026-11-15","editionSlot":"08:00",
            "verification":"editorial_verified","priority":i,
            "category":"Colombia" if i<3 else "Mundo",
            "sources":[{"url":f"https://example.org/story/{i}"}],
            "originalArticleReviewed":True,
            "originalArticleTextEs":"Un reportaje propio de prueba.",
            "originalArticleByline":"Redacción ORBIUNO",
            "audioFullTextEs":"Un reportaje propio de prueba."}

class PublishPreflightTests(unittest.TestCase):
    def test_missing_public_site_and_video_fail_closed(self):
        db={"editionDate":"2026-11-15","news":[news(i) for i in range(1,7)]}
        result=preflight(db,slot="8am",now=NOW)
        self.assertFalse(result["ready"])
        self.assertIn("sitio_publico_no_verificado",result["blockers"])
        self.assertIn("video_mp4_no_verificado",result["blockers"])

    def test_six_matching_ids_after_checks(self):
        db={"editionDate":"2026-11-15","news":[news(i) for i in range(1,7)]}
        ids=[f"n-{i}" for i in range(1,7)]
        result=preflight(db,slot="8am",now=NOW,web_ids=ids,reel_ids=ids)
        self.assertTrue(result["ready"])
        self.assertFalse(result["published"])
        wrong=list(reversed(ids))
        self.assertFalse(preflight(db,slot="8am",now=NOW,web_ids=wrong,reel_ids=ids)["ready"])

    def test_images_only_when_rights_are_proven(self):
        db={"editionDate":"2026-11-15","news":[news(i) for i in range(1,7)]}
        db["news"][0]["imageUrl"]="https://example.org/protected.jpg"
        ids=[f"n-{i}" for i in range(1,7)]
        result=preflight(db,slot="8am",now=NOW,web_ids=ids,reel_ids=ids)
        self.assertIn("noticia_1_foto_sin_derechos",result["blockers"])

    def test_stale_or_incomplete_never_publication_ready(self):
        db={"editionDate":"2026-11-09","news":[news(i) for i in range(1,6)]}
        self.assertFalse(preflight(db,slot="8am",now=NOW)["ready"])


if __name__=="__main__":
    unittest.main()
