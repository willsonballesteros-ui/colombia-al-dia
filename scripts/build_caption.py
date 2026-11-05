#!/usr/bin/env python3
"""Copies de Instagram cortos con URL sola en una línea y primer comentario.

Genera archivos para entregar a Metricool. NO afirma que un comentario esté
publicado ni coloca enlaces falsamente clicables sobre diapositivas.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
URL="https://colombia-al-dia.pages.dev/"
HANDLE="@resumen.noticias"


def edition_slot():
    requested=os.getenv("ORBIUNO_EDITION_SLOT","").lower()
    if requested in ("8am","12m","6pm"):
        return requested
    hour=datetime.now(ZoneInfo("America/Bogota")).hour
    return "8am" if hour<11 else "12m" if hour<17 else "6pm"


def tracked_url(day,medium,slot):
    assert medium in {"bio","caption","comment","story"}
    args={"utm_source":"instagram","utm_medium":medium,
          "utm_campaign":"edicion_"+day.replace("-","")+"_"+slot}
    return URL+"?"+urlencode(args)



def build(db):
    day=db["editionDate"]
    news=sorted((n for n in db["news"] if n.get("date")==day
                 and n.get("verification")=="editorial_verified"),
                key=lambda n:n.get("priority",999))
    if len(news)!=10 or len({n["id"] for n in news})!=10:
        raise RuntimeError("Se requieren diez noticias verificadas distintas")
    for n in news:
        assert n["sources"] and str(n["sources"][0]["url"]).startswith("https://")
    display=day[8:10]+"/"+day[5:7]+"/"+day[:4]
    slot=edition_slot()
    verified_sports=sum(n.get("category")=="Deportes" for n in news)
    sports_ready=slot!="12m" or 1<=verified_sports<=2
    blockers=[] if sports_ready else ["edicion_mediodia_requiere_1_o_2_deportes_verificados"]
    caption_link=tracked_url(day,"caption",slot)
    comment_link=tracked_url(day,"comment",slot)
    bio_link=tracked_url(day,"bio",slot)
    story_link=tracked_url(day,"story",slot)
    caption=(
        "ORBIUNO | "+display+"\n\n"
        "Edición "+{"8am":"de la mañana","12m":"del mediodía","6pm":"de la noche"}[slot]+" · diez noticias en seis láminas.\n\n"
        "🎧 Las noticias también se escuchan en nuestra web.\n"
        "Elige voz en español, tono y velocidad a tu gusto.\n\n"
        "👇 Escucha el audio y consulta las fuentes originales:\n"
        "🌐 "+caption_link+"\n\n"
        "¿Qué noticia te impactó más? Comenta su número.\n\n"
        + HANDLE+"  #ORBIUNO #NoticiasColombia #ResumenDelDia"
    )
    first_comment=(
        "🎧 Las noticias también se escuchan en ORBIUNO.\n"
        "Escoge la voz y la velocidad desde nuestra página.\n"
        "👇 Escucha y verifica las fuentes originales:\n"
        "🌐 "+comment_link
    )
    assert "\n🌐 "+caption_link in caption
    assert first_comment.endswith("\n🌐 "+comment_link)
    return {
        "editionDate":day,
        "brand":"ORBIUNO",
        "editionSlot":slot,
        "verifiedSports":verified_sports,
        "publicationReady":sports_ready,
        "blockers":blockers,
        "utmCampaign":"edicion_"+day.replace("-","")+"_"+slot,
        "links":{"bio":bio_link,"story":story_link,"caption":caption_link,"firstComment":comment_link},
        "caption":caption,
        "firstComment":first_comment,
        "publicationVerified":False,
        "media":[
            "https://raw.githubusercontent.com/willsonballesteros-ui/colombia-al-dia/main/media/"
            +day+"/portada.png"
        ]+[
            "https://raw.githubusercontent.com/willsonballesteros-ui/colombia-al-dia/main/media/"
            +day+"/grupo-"+str(i).zfill(2)+".png"
            for i in range(1,6)
        ],
        "sourceLinks":[{"title":n["title"],"url":n["sources"][0]["url"]} for n in news],
        "note":"La URL del caption en Instagram es texto, no enlace tocable: el enlace de la biografía o un sticker nativo sí puede serlo.",
    }


def main():
    data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    payload=build(data)
    out=ROOT/"media"/payload["editionDate"]
    out.mkdir(parents=True,exist_ok=True)
    (out/"instagram-caption.txt").write_text(payload["caption"]+"\n",encoding="utf-8")
    (out/"instagram-primer-comentario.txt").write_text(
        payload["firstComment"]+"\n",encoding="utf-8")
    (out/"instagram-enlaces-utm.txt").write_text(
        "BIO: "+payload["links"]["bio"]+"\n"
        "HISTORIA: "+payload["links"]["story"]+"\n"
        "DESCRIPCIÓN: "+payload["links"]["caption"]+"\n"
        "PRIMER COMENTARIO: "+payload["links"]["firstComment"]+"\n",
        encoding="utf-8")
    (out/"instagram-publicacion.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Copy",len(payload["caption"]),"caracteres; primer comentario preparado.")


if __name__=="__main__":
    main()
