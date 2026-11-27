import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from scripts.orbiuno_publication_plan import due, stage, confirmed

class TestPublicationPlan(unittest.TestCase):
    def test_schedule(self):
        for hour, expected in ((7, []), (8, ["0800"]), (17, ["0800"]), (18, ["0800", "1800"])):
            self.assertEqual(due(datetime(2027, 1, 1, hour)), expected)
    def test_evidence(self):
        self.assertTrue(confirmed({"id":"123","url":"https://www.instagram.com/reel/abc/"}))
        self.assertFalse(confirmed({"id":"123","url":"https://instagram.com.evil/reel/abc/"}))
    def test_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            day = "2027-01-01"
            self.assertEqual(stage(root,day,"1800"),"editorial_missing")
            editor = root/"editions/daily"/f"{day}-1800.json"
            editor.parent.mkdir(parents=True)
            editor.write_text("{}")
            self.assertEqual(stage(root,day,"1800"),"editorial_ready")
            manifest = root/"media"/day/"edicion-1800-orbiuno"/"orbiuno_manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("{}")
            self.assertEqual(stage(root,day,"1800"),"ready")
            ledger = root/"editions/publication-ledger"/f"{day}-1800.json"
            ledger.parent.mkdir(parents=True)
            ledger.write_text(json.dumps({"orbiuno":{"state":"publishing"}}))
            self.assertEqual(stage(root,day,"1800"),"reconcile")
            ledger.write_text(json.dumps({"orbiuno":{"state":"published","id":"123","url":"https://www.instagram.com/reel/abc/"}}))
            self.assertEqual(stage(root,day,"1800"),"published")
            self.assertEqual(stage(root,day,"0800"),"editorial_missing")
    def test_invalid_published(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = root/"editions/publication-ledger/2027-01-01-0800.json"
            ledger.parent.mkdir(parents=True)
            ledger.write_text('{"orbiuno":{"state":"published"}}')
            with self.assertRaises(RuntimeError):
                stage(root,"2027-01-01","0800")

if __name__ == "__main__":
    unittest.main()
