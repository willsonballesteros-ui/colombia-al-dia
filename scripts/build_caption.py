#!/usr/bin/env python3
"""Copies de Instagram cortos con URL sola en una línea y primer comentario.

Genera archivos para entregar a Metricool. NO afirma que un comentario esté
publicado ni coloca enlaces falsamente clicables sobre diapositivas.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
URL="https://colombia-al-dia.pages.dev/"
HANDLE="@resumen.noticias"


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
    caption=(
        "ORBIUNO | "+display+"\n\n"
        "Diez noticias de Colombia y el mundo, claras y directas.\n\n"
        "🎧 Las noticias también se escuchan en nuestra web.\n"
        "Elige voz en español, tono y velocidad a tu gusto.\n\n"
        "👇 Escucha el audio y consulta las fuentes originales:\n"
        "🌐 "+URL+"\n\n"
        "¿Qué noticia te impactó más? Comenta su número.\n\n"
        + HANDLE+"  #ORBIUNO #NoticiasColombia #ResumenDelDia"
    )
    first_comment=(
        "🎧 Las noticias también se escuchan en ORBIUNO.\n"
        "Escoge la voz y la velocidad desde nuestra página.\n"
        "👇 Escucha y verifica las fuentes originales:\n"
        "🌐 "+URL
    )
    assert "\n🌐 "+URL in caption
    assert first_comment.endswith("\n🌐 "+URL)
    return {
        "editionDate":day,
        "brand":"ORBIUNO",
        "caption":caption,
        "firstComment":first_comment,
        "publicationVerified":False,
        "media":[
            "https://raw.githubusercontent.com/willsonballesteros-ui/colombia-al-dia/main/media/"
            +day+"/top10-"+str(i).zfill(2)+".png"
            for i in range(1,11)
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
    (out/"instagram-publicacion.json").write_text(
        json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Copy",len(payload["caption"]),"caracteres; primer comentario preparado.")


if __name__=="__main__":
    main()
