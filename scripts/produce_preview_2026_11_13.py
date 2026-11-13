#!/usr/bin/env python3
"""Build review-only MP4 Reels. Not connected to any Meta publish action."""
import json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import produce_night_reels as p

os.environ["PREVIEW_ONLY"]="1"
os.environ["EDITION_DATE_LABEL"]="13 NOV 2026 · BORRADOR"
p.OUT=ROOT/"media/2026-11-13-preview"
p.OUT.mkdir(parents=True,exist_ok=True)
db=json.loads((ROOT/"editorial/2026-11-13-preview.json").read_text(encoding="utf-8"))
assert db["publicationAuthorized"] is False and db["status"]=="BORRADOR_REQUIERE_APROBACION_USUARIO"
for brand in ("orbiuno","mycar"):
 items=db[brand]
 assert len(items)==4
 stories=[]
 for a in items:
  stories.append({"title":a["title"],"source":a["source"],"source_url":a["source_url"],"photo_query":a["photo_query"]})
 audios=p.dora([a["voice"] for a in items],brand+"-preview")
 p.render(brand.upper(),stories,audios,"")
 src=p.OUT/(brand+"-2026-11-12-noche.mp4")
 final=p.OUT/(brand+"-2026-11-13-BORRADOR.mp4")
 src.rename(final)
 manifest=p.OUT/(brand+"-credits.json")
 obj=json.loads(manifest.read_text())
 obj["output"]=str(final)
 obj["status"]="PREVIEW_ONLY_NOT_PUBLISHED"
 obj["editionDate"]="2026-11-13"
 obj["source_news"]=[{"title":a["title"],"url":a["source_url"]} for a in items]
 manifest.write_text(json.dumps(obj,ensure_ascii=False,indent=2))
 print("Preview created",final,final.stat().st_size,flush=True)
