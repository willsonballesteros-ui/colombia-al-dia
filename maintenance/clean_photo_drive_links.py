#!/usr/bin/env python3
"""Elimina vínculos a Drive privado de cinco fotos del archivo de ORBIUNO.
Conserva fotografías, créditos, licencias y enlaces periodísticos originales.
Es idempotente y no toca publicaciones de Instagram.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
db_path=ROOT/"noticias.json"
db=json.loads(db_path.read_text(encoding="utf8"))
ids={f"orbiuno-20261113-18h-{i}" for i in range(1,6)}
seen=set()
updated=0
for item in db["news"]:
    if item.get("id") not in ids:
        continue
    seen.add(item["id"])
    old=str(item.get("imageSourceUrl") or "")
    if old.startswith("https://drive.google.com/"):
        photo=item.get("imageUrl","")
        if not photo.startswith("./media/2026-11-13/foto-"):
            raise RuntimeError("Fotografía local inesperada para "+item["id"])
        item["imageSourceUrl"]=photo
        updated+=1
    elif not old.startswith("./media/2026-11-13/foto-"):
        raise RuntimeError("Procedencia diferente; requiere revisión "+item["id"])
if seen!=ids:
    raise RuntimeError("Faltan noticias originales; no modificar versión "+repr(ids-seen))
for item in db["news"]:
    for src in item.get("sources", []):
        if "drive.google.com" in str(src.get("url", "")):
            raise RuntimeError("Fuente periodística en Drive: "+item["id"])
    if "drive.google.com" in str(item.get("imageSourceUrl","")):
        raise RuntimeError("Queda una atribución privada: "+item["id"])
if updated:
    db_path.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print("FOTOGRAFÍAS_LOCALES_SIN_DRIVE",updated,flush=True)
