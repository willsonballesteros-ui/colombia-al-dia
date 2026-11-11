#!/usr/bin/env python3
"""Stage five verified stories in noticias.json and index.html, never post Instagram.
This explicitly requires existing, licensed assets. Commit/deploy is a separate step.
"""
from __future__ import annotations
import argparse
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def stage(manifest: Path, database: Path, root: Path, write: bool=False):
    manifest=manifest.resolve();base=manifest.parent
    m=json.loads(manifest.read_text(encoding="utf-8"))
    if len(m.get("news",[]))!=5 or len({x.get("id") for x in m["news"]})!=5:
        raise ValueError("Five distinct stories required")
    if any(x.get("verification")!="editorial_verified" for x in m["news"]):
        raise ValueError("Unverified editorial items cannot be mirrored to website")
    db=json.loads(database.read_text(encoding="utf-8"))
    existing=db.get("news")
    if not isinstance(existing,list):
        raise ValueError("noticias.json must contain a news array")
    ids={x["id"] for x in m["news"]}
    other=[n for n in existing if n.get("id") not in ids and
           not (n.get("date")==m["editionDate"] and n.get("editionSlot")==m["slot"] and
                isinstance(n.get("instagramReelOrder"),int) and n.get("instagramReelOrder")>0)]
    entries=[];assets=[]
    for i,x in enumerate(m["news"],1):
        img=x.get("image",{})
        if img.get("rightsVerified") is not True or not all(img.get(k) for k in ("credit","license","sourceUrl")):
            raise ValueError("Image rights incomplete for "+x["id"])
        rel=img.get("file")
        if not rel or Path(rel).is_absolute():
            raise ValueError("Local image path missing")
        photo=(base/rel).resolve()
        if not photo.is_relative_to(base) or not photo.is_file() or photo.suffix.lower() not in (".jpg",".jpeg",".png",".webp"):
            raise ValueError("Missing licensed local image for "+x["id"])
        dest_rel=Path("media")/"orbiuno"/m["editionDate"]/(x["id"]+photo.suffix.lower())
        assets.append((photo,root/dest_rel))
        entries.append({
            "id":x["id"],"date":m["editionDate"],"editionSlot":m["slot"],
            "title":x["title"],"category":x.get("category","Actualidad"),
            "summary":x["narration"],"executiveSummary":x["narration"],
            "audioFullTextEs":x["narration"],"verification":"editorial_verified",
            "instagramReelOrder":i,"priority":i,
            "sources":[{"name":x["source"]["name"],"url":x["source"]["url"]}],
            "imageType":"licensed_press_photo","imageUrl":"./"+dest_rel.as_posix(),
            "imageRightsVerified":True,"imageCredit":img["credit"],
            "imageLicense":img["license"],"imageSourceUrl":img["sourceUrl"],
            "imageAlt":x["title"],"originalArticleReviewed":False,
            "fullArticleRightsVerified":False
        })
    db["editionDate"]=m["editionDate"]
    db["news"]=entries+other
    if write:
        for src,dst in assets:
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        database.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("STAGED five stories. Run scripts/prepare_site.py, then verify_alignment.py.")
    else:
        print("DRY RUN: five stories match, licenses declared, source files present; no changes made.")
    return [x["id"] for x in entries]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("manifest",type=Path)
    p.add_argument("--newsdb",type=Path,default=ROOT/"noticias.json")
    p.add_argument("--write",action="store_true")
    a=p.parse_args()
    stage(a.manifest,a.newsdb,ROOT,a.write)

if __name__=="__main__":
    main()
