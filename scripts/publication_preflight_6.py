#!/usr/bin/env python3
"""ORBIUNO: preflight de publicación, sin acceso a Meta ni efectos secundarios.

El guard exige las seis noticias de la franja elegida y que todo esté en la web
ANTES de publicar. Guarda una evidencia JSON; no promociona source_only.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BOGOTA=ZoneInfo("America/Bogota")
SLOTS={"8am":"08:00","12m":"12:00","6pm":"18:00","7pm":"19:00","9pm":"21:00","10pm":"22:00"}
ROOT=Path(__file__).resolve().parents[1]


def preflight(data, *, slot, now=None, web_ids=None, reel_ids=None, allow_archive=False):
    now=now or datetime.now(BOGOTA)
    errors=[]
    day=str(data.get("editionDate") or "")
    try:
        age=(now.date()-date.fromisoformat(day)).days
        if age < 0 or (age > 0 and (not allow_archive or age > 7)):
            errors.append("edicion_caducada_o_futura")
    except ValueError:
        errors.append("fecha_edicion_invalida")
    slot_time=SLOTS.get(slot)
    if not slot_time:
        errors.append("franja_no_admitida")
    matches=sorted(
        (n for n in data.get("news", []) if n.get("date")==day
         and n.get("editionSlot")==slot_time and n.get("verification")=="editorial_verified"),
        key=lambda n:n.get("priority",999)
    )
    ids=[n.get("id") for n in matches]
    if len(matches)!=6 or len(set(ids))!=6 or not all(ids):
        errors.append("se_requieren_seis_noticias_distintas")
    national=0
    for index,n in enumerate(matches,1):
        first=(n.get("sources") or [{}])[0]
        url=str(first.get("url") or "")
        if urlsplit(url).scheme!="https" or not urlsplit(url).netloc:
            errors.append(f"noticia_{index}_fuente_no_verificada")
        if n.get("originalArticleReviewed") is not True:
            errors.append(f"noticia_{index}_articulo_propio_sin_revision")
        article=str(n.get("originalArticleTextEs") or "")
        if not article.strip():
            errors.append(f"noticia_{index}_sin_texto_integro")
        if n.get("originalArticleByline")!="Redacción ORBIUNO":
            errors.append(f"noticia_{index}_autor_propiedad_no_acreditado")
        if not n.get("audioFullTextEs"):
            errors.append(f"noticia_{index}_audio_sin_texto")
        # Ausencia de imágenes es permitida; imágenes presentes exigen
        # origen, crédito y derechos demostrados.
        if n.get("imageUrl") and not all((n.get("imageRightsVerified") is True,
                                          n.get("imageCredit"),n.get("imageLicense"),
                                          n.get("imageSourceUrl"))):
            errors.append(f"noticia_{index}_foto_sin_derechos")
        if str(n.get("category","")).lower() in ("colombia","nacional","bogotá"):
            national+=1
    if national<2:
        errors.append("revisar_distribucion_colombia_mundo")
    if web_ids is None:
        errors.append("sitio_publico_no_verificado")
    elif ids != list(web_ids):
        errors.append("orden_o_ids_web_diferentes")
    if reel_ids is None:
        errors.append("video_mp4_no_verificado")
    elif ids != list(reel_ids):
        errors.append("orden_o_ids_reel_diferentes")
    return {"editionDate":day,"slot":slot,"news_ids":ids,
            "news_count":len(matches),"colombia_count":national,
            "ready":not errors,"blockers":errors,
            "evaluated_at":now.isoformat(),"published":False}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--data",default=str(ROOT/"noticias.json"))
    parser.add_argument("--slot",choices=tuple(SLOTS),required=True)
    parser.add_argument("--allow-archive",action="store_true",help="Solo ediciones anteriores autorizadas, maximo 7 dias")
    parser.add_argument("--web-ids-json",help="Seis IDs verificados en la URL pública")
    parser.add_argument("--reel-ids-json",help="Seis IDs que aparecen realmente en el video")
    parser.add_argument("--output",default="dist/orbiuno-preflight.json")
    args=parser.parse_args(argv)
    db=json.loads(Path(args.data).read_text(encoding="utf-8"))
    web=json.loads(Path(args.web_ids_json).read_text(encoding="utf-8")) if args.web_ids_json else None
    reel=json.loads(Path(args.reel_ids_json).read_text(encoding="utf-8")) if args.reel_ids_json else None
    result=preflight(db,slot=args.slot,web_ids=web,reel_ids=reel,allow_archive=args.allow_archive)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("ORBIUNO",result["editionDate"],args.slot,
          "APTO PARA REVISIÓN FINAL" if result["ready"] else "BLOQUEADO",result["blockers"])
    return 0 if result["ready"] else 2


if __name__=="__main__":
    raise SystemExit(main())
