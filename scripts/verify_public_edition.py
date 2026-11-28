#!/usr/bin/env python3
"""Verify a dated, approved ORBIUNO edition before any social publication."""
import argparse
import hashlib
import json
import re
import time
import unittest
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://colombia-al-dia.pages.dev/"

def require(condition, message):
    if not condition:
        raise ValueError(message)

def plan(day, slot, root=ROOT):
    require(re.fullmatch(r"\d{4}-\d{2}-\d{2}", day), "Invalid date")
    require(slot in ("0800", "1200", "1800"), "Invalid slot")
    folder = Path("media") / day / ("edicion-" + slot + "-orbiuno")
    local = root / folder
    m = json.loads((local / "orbiuno_manifest.json").read_text(encoding="utf-8"))
    require(m["edition"] == day and m["slot"] == slot[:2] + ":" + slot[2:], "Wrong edition")
    require(m["brand"] == "orbiuno" and m["newsCount"] == m["imagesCount"] == m["logosCount"] == m["fullNewsAudioFiles"] == 6, "Incomplete media")
    require(m["voice"] == "es-CO-SalomeNeural" and m["voiceSpeed"] == 1.25, "Wrong voice")
    require(len(m["photoCredits"]) == 6 and all(c.get("rightsVerified") and c.get("license") and c.get("author") and c.get("source") for c in m["photoCredits"]), "Missing rights")
    require(len(set(m["sourceUrls"])) == 6 and all(u.startswith("https://") for u in m["sourceUrls"]), "Missing sources")
    require(re.fullmatch(r"[A-Za-z0-9_-]+\.mp4", m["video"]), "Invalid video filename")
    require(hashlib.sha256((local / m["video"]).read_bytes()).hexdigest() == m["sha256"], "Local SHA mismatch")
    page = "orbiuno-" + day + "-" + slot + ".html"
    resources = [(page, "text/html", None), ((folder / m["video"]).as_posix(), "video/", m["sha256"])]
    for i in range(1, 7):
        for name, mime in ((f"orbiuno-noticia-{i:02d}.mp3","audio/"),(f"foto-orbiuno-{i:02d}.jpg","image/"),(f"orbiuno-logo-{i:02d}.png","image/")):
            f = local / name
            require(f.is_file() and f.stat().st_size > 100, "Missing " + name)
            resources.append(((folder / name).as_posix(), mime, hashlib.sha256(f.read_bytes()).hexdigest()))
    return m, resources

def fetch(path, mime, digest):
    req = Request(SITE + path, headers={"User-Agent":"ORBIUNO-Newsroom/1.0","Cache-Control":"no-cache","Accept":"*/*"})
    with urlopen(req, timeout=35) as response:
        require(response.status == 200, "HTTP not 200: " + path)
        require(response.url.startswith(SITE), "Unexpected redirect")
        require(response.headers.get("Content-Type","").lower().startswith(mime), "Unexpected MIME: " + path)
        body = response.read(30_000_001)
    require(100 < len(body) <= 30_000_000, "Invalid response length")
    if digest:
        require(hashlib.sha256(body).hexdigest() == digest, "Public SHA mismatch: " + path)
    return body

def verify(day, slot, getter=fetch):
    manifest, resources = plan(day, slot)
    for path, mime, digest in resources:
        body = getter(path, mime, digest)
        if mime == "text/html":
            html = body.decode("utf-8")
            require(all(u in html for u in manifest["sourceUrls"]), "Page sources mismatch")
            require(all(f"orbiuno-noticia-{i:02d}.mp3" in html for i in range(1,7)), "Page audio links mismatch")
        print("VERIFIED", path, flush=True)
    return {"state":"WEB_VERIFIED","edition":"ORBIUNO-"+day+"-"+slot,"resources":len(resources),"sha256":manifest["sha256"],"video_url":SITE+resources[1][0]}

class Tests(unittest.TestCase):
    def test_bad_slot(self):
        with self.assertRaises(ValueError):
            plan("2026-11-24","../../")
    def test_bad_day(self):
        with self.assertRaises(ValueError):
            plan("../x","1200")
    def test_local_edition(self):
        m, resources = plan("2026-11-24","1200")
        self.assertEqual(len(resources),20)
        self.assertEqual(m["sha256"],resources[1][2])

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--day")
    p.add_argument("--slot",default="1200")
    p.add_argument("--test",action="store_true")
    p.add_argument("--report",type=Path,default=Path("/tmp/orbiuno-preflight.json"))
    args=p.parse_args()
    if args.test:
        return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests)).wasSuccessful() else 1
    require(args.day == datetime.now(ZoneInfo("America/Bogota")).date().isoformat(), "Edition expired")
    # Pages may still serve the previous site while a new deployment propagates.
    attempts = 8
    for attempt in range(attempts):
        try:
            result=verify(args.day,args.slot)
            break
        except HTTPError as e:
            print("HTTP",e.code,e.url,flush=True)
            if e.code in (401,403,429) or attempt == attempts - 1:
                raise
            time.sleep(min(10 * (attempt + 1), 40))
        except (ValueError,OSError) as e:
            print(type(e).__name__,str(e),flush=True)
            if attempt == attempts - 1:
                raise
            time.sleep(min(10 * (attempt + 1), 40))
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
