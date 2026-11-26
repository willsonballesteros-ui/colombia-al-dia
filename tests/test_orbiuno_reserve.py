import unittest
from scripts.orbiuno_reserve import select

DAY="2026-11-26"
SLOT="08:00"

def candidate(i):
    url=f"https://example.org/news/{i}"
    return {"id":f"n{i}","priority":i,"date":DAY,"editionSlot":SLOT,
            "verification":"editorial_verified","originalArticleReviewed":True,
            "originalArticleByline":"Redacción ORBIUNO",
            "originalArticleTextEs":"A"+"x"*1100,
            "originalArticleIsPublisherVerbatim":False,"title":f"Noticia número {i}",
            "reelLine":"Una noticia verificada","sources":[{"url":url}],
            "originalArticleSourceUrls":[url]}

def edition():
    return {"editionDate":DAY,"editionSlot":SLOT,"editionKey":"ORBIUNO-"+DAY+"-0800",
            "sourceOnly":False,"news":[candidate(i) for i in range(1,7)],
            "reserveNews":[candidate(i) for i in range(7,10)]}

class ReserveTests(unittest.TestCase):
    def test_replaces_two_failures_and_preserves_six(self):
        def probe(doc,n):
            if n["id"] in {"n2","n4"}:
                raise OSError("logo or photo")
        out,errors=select(edition(),probe)
        self.assertEqual([n["id"] for n in out["news"]],["n1","n3","n5","n6","n7","n8"])
        self.assertEqual([n["priority"] for n in out["news"]],list(range(1,7)))
        self.assertEqual(len(errors),2)
    def test_no_unreviewed_replacement(self):
        doc=edition()
        doc["reserveNews"][0]["originalArticleReviewed"]=False
        out,errors=select(doc,lambda d,n: (_ for _ in ()).throw(OSError("failed")) if n["id"]=="n1" else None)
        self.assertEqual(out["news"][-1]["id"],"n8")
        self.assertEqual(len(errors),2)
    def test_duplicate_source_and_id(self):
        doc=edition()
        doc["news"][1]["sources"]=doc["news"][0]["sources"]
        doc["news"][1]["originalArticleSourceUrls"]=doc["news"][0]["originalArticleSourceUrls"]
        doc["reserveNews"][0]["id"]="n1"
        out,errors=select(doc,lambda d,n:None)
        self.assertEqual(out["news"][-1]["id"],"n8")
        self.assertEqual(len(errors),2)
    def test_exhaustion_fails_closed(self):
        doc=edition()
        doc["reserveNews"]=[]
        with self.assertRaises(RuntimeError):
            select(doc,lambda d,n: (_ for _ in ()).throw(OSError("failed")) if n["id"]=="n1" else None)
    def test_source_only_blocked(self):
        doc=edition()
        doc["sourceOnly"]=True
        with self.assertRaises(ValueError):
            select(doc,lambda d,n:None)

if __name__=="__main__":
    unittest.main()
