#!/usr/bin/env python3
"""Construye entrada Salomé solo de una edición con seis noticias revisadas."""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
day=os.environ.get("ORBIUNO_EDITION_DATE") or datetime.now(ZoneInfo("America/Bogota")).date().isoformat()
slot=os.environ.get("ORBIUNO_EDITION_SLOT","08:00")
if slot not in {"08:00","12:00","18:00","19:00"}:
    raise SystemExit("BLOCKED: franja inválida")
data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
if data.get("editionDate")!=day:
    raise SystemExit("BLOCKED: edición de otra fecha")
news=sorted([n for n in data["news"] if n.get("date")==day and n.get("editionSlot")==slot and n.get("verification")=="editorial_verified"],key=lambda x:x["priority"])
if len(news)!=6 or len({n["id"] for n in news})!=6:
    raise SystemExit("BLOCKED: se requieren seis noticias distintas")
name={"08:00":"ocho de la mañana","12:00":"doce del mediodía","18:00":"seis de la tarde","19:00":"siete de la noche"}[slot]
segments=[{"id":"saludo","text":"Saludos. Estas son seis noticias de Colombia y el mundo. Edición de las "+name+"."}]
for i,n in enumerate(news,1):
    if n.get("originalArticleReviewed") is not True or not n.get("sources"):
        raise SystemExit("BLOCKED: noticia sin revisión o fuente")
    line=str(n.get("reelLine") or "").strip()
    if not line or len(line.split())>27:raise SystemExit("BLOCKED: falta frase breve para "+n["id"])
    segments.append({"id":f"n{i:02d}","text":line})
segments.append({"id":"despedida","text":"Escucha las noticias completas y consulta las fuentes originales en colombia al día punto pages punto dev. Gracias por seguir ORBIUNO."})
out=ROOT/"editions"/"audio_input.json"
out.write_text(json.dumps({"segments":segments,"metadata":{"type":"derived_from_verified_edition","date":day,"slot":slot,"publication_allowed":False}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("SALOME_INPUT",len(segments),out)
