"""Regression: oversized MyCar videos stay untouched while ORBIUNO deploys."""
import json
import tempfile
import unittest
from pathlib import Path
from scripts.stage_cloudflare_site import MAX_ASSET_BYTES, build


class PagesStageTests(unittest.TestCase):
    def test_excludes_only_big_asset(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"index.html").write_text("<h1>ORBIUNO</h1>")
            (root/"noticias.json").write_text(json.dumps({"editionDate":"2026-11-21","news":[]}))
            (root/"feed.xml").write_text("<rss/>")
            (root/"audio-fix.js").write_text("console.log('ok')")
            folder=root/"media"/"2026-11-21"
            folder.mkdir(parents=True)
            (folder/"ORBIUNO.mp4").write_bytes(b"video-valid")
            with (folder/"MYCAR.mp4").open("wb") as f:
                f.truncate(MAX_ASSET_BYTES+1)
            result=build(root,root/"site")
            self.assertIn("media/2026-11-21/MYCAR.mp4",result["excluded"])
            self.assertTrue((root/"site"/"media"/"2026-11-21"/"ORBIUNO.mp4").exists())
            self.assertFalse((root/"site"/"media"/"2026-11-21"/"MYCAR.mp4").exists())
            self.assertTrue((folder/"MYCAR.mp4").exists())


if __name__=="__main__":
    unittest.main()
