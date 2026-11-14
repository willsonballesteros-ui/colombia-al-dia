#!/usr/bin/env python3
"""Integrate the approved six-story Reel artifact on latest main without overwriting content.
Run only after the generation workflow confirms the MP4's audio/video and photo rights.
"""
import hashlib,io,json,re,shutil,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"media/2026-11-13"
OUT.mkdir(parents=True,exist_ok=True)
CACHE=Path(sys.argv[1]) if len(sys.argv)>1 else Path("/tmp/orbiuno-six-final")
MP4_NAME="ORBIUNO_2026-11-13_18H_6_NOTICIAS.mp4"
source_mp4=CACHE/MP4_NAME
source_meta=CACHE/"orbiuno-credits.json"
if not source_mp4.is_file() or not source_meta.is_file():raise RuntimeError("Artifact missing")
manifest=json.loads(source_meta.read_text(encoding="utf8"))
assert manifest.get("news_count")==6 and len(manifest.get("license_photos",[]))==6
assert len(manifest.get("story_ids",[]))==6
assert hashlib.sha256(source_mp4.read_bytes()).hexdigest()==manifest["sha256"]
sixth=manifest["license_photos"][5]
photo=sixth["photo"]
assert "balvin" in photo["file"].lower()
assert any(x in photo["license"].lower() for x in ("cc by","cc0","public domain"))
assert photo["commons"].startswith("https://commons.wikimedia.org/wiki/File")
assert photo["photo_url"].startswith("https://upload.wikimedia.org/")
from PIL import Image
req=urllib.request.Request(photo["photo_url"],headers={"User-Agent":"ORBIUNO-Noticias/1.0 (licensed commons archival image)"})
with urllib.request.urlopen(req,timeout=40) as r:raw=r.read()
im=Image.open(io.BytesIO(raw));im.load();assert im.width>=700 and im.height>=500
im.convert("RGB").save(OUT/"foto-6.jpg",quality=88)
dbpath=ROOT/"noticias.json"
db=json.loads(dbpath.read_text(encoding="utf8"))
ids={x["id"] for x in db["news"]}
# Reuse editorial text from the existing six-news production script; never scrape third party verbatim.
from scripts.produce_orbiuno_6_20261113 import SIXTH, SIXTH_ID
if SIXTH_ID not in ids:
 base=[x for x in db["news"] if x.get("date")=="2026-11-13" and x.get("editionSlot")=="18:00" and x.get("verification")=="editorial_verified"]
 assert len(base)==5,"Base edition changed; publication blocked"
 sixth=dict(SIXTH)
 sixth.update({"imageUrl":"./media/2026-11-13/foto-6.jpg",
   "imageAlt":"J Balvin, fotografía de archivo; no corresponde a los Latin Grammy de 2026",
   "imageCaption":"J Balvin, fotografía de archivo",
   "imageSourceUrl":photo["commons"],"imageCredit":photo["artist"],
   "imageLicense":photo["license"]})
 db["news"].append(sixth)
 dbpath.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
else:
 existing=next(x for x in db["news"] if x["id"]==SIXTH_ID)
 assert existing.get("imageRightsVerified") and existing.get("sources",[])[0].get("url")==SIXTH["sources"][0]["url"],"Conflict with existing sixth story"
shutil.copyfile(source_mp4,OUT/MP4_NAME)
shutil.copyfile(source_meta,OUT/"orbiuno-credits.json")
print("RESTORED SIX STORIES ON LATEST MAIN",len(db["news"]),source_mp4.stat().st_size,flush=True)
