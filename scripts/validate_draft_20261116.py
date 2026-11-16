#!/usr/bin/env python3
"""Preflight del borrador ORBIUNO. No publica ni cambia la edición principal."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

def validate(edition):
    errors=[]
    news=edition.get("news",[])
    if edition.get("editionDate")!="2026-11-16" or edition.get("editionSlot")!="18:00":
        errors.append("fecha_u_hora_incorrecta")
    if len(news)!=6 or len({n.get("id") for n in news})!=6:
        errors.append("seis_noticias_distintas")
    if [n.get("priority") for n in news]!=list(range(1,7)):
        errors.append("orden_no_consecutivo")
    for i,n in enumerate(news,1):
        if n.get("date")!=edition.get("editionDate") or n.get("editionSlot")!=edition.get("editionSlot"):
            errors.append(f"{i}:fecha_franja")
        sources=n.get("sources") or []
        if not sources or not sources[0].get("name") or urlsplit(sources[0].get("url","")).scheme!="https":
            errors.append(f"{i}:fuente")
        if n.get("originalArticleReviewed") is not True:
            errors.append(f"{i}:revision_editorial")
        if not n.get("originalArticleTextEs","").strip() or n.get("audioFullTextEs","").strip()!=n.get("originalArticleTextEs","").strip():
            errors.append(f"{i}:integridad_audio_texto")
        if not (n.get("imageRightsVerified") is True and n.get("imageUrl") and n.get("imageCredit") and n.get("imageLicense") and n.get("imageSourceUrl")):
            errors.append(f"{i}:foto_real_derechos")
        if n.get("verification")!="editorial_verified":
            errors.append(f"{i}:verificacion_pendiente")
    for condition,tag in [
        (edition.get("webIdsVerified")==[n.get("id") for n in news],"sincronizacion_web"),
        (edition.get("reelIdsVerified")==[n.get("id") for n in news],"sincronizacion_reel"),
        (edition.get("coverIdsVerified")==[n.get("id") for n in news],"sincronizacion_portada"),
        (edition.get("mobileAudioEvidence",{}).get("iphone") is True,"audio_iphone"),
        (edition.get("mobileAudioEvidence",{}).get("android") is True,"audio_android"),
        (edition.get("videoAssetVerified") is True,"mp4_no_verificado")
    ]:
        if not condition:errors.append(tag)
    return {"ready":not errors,"news_count":len(news),"blockers":errors,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="drafts/orbiuno-2026-11-16-18h.json")
    a=p.parse_args()
    result=validate(json.loads(Path(a.data).read_text(encoding="utf-8")))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result["ready"] else 2

if __name__=="__main__":
    raise SystemExit(main())
