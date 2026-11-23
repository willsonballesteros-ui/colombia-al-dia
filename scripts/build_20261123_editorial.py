#!/usr/bin/env python3
"""Preparación verificable 23 NOV 2026. NO PUBLICA.
Produce guiones, entrada de voz corta para Reels, artículos largos
para web, captions y checklist de derechos. Todo a partir de la selección auditada.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"editions/research/2026-11-23-am-source-checked.json"
OUT=ROOT/"build/edicion-2026-11-23-am"
BOGOTA="America/Bogota"
DAY="2026-11-23"
SLOTS={"orbiuno":"08:30","mycar":"08:30"}
COUNTS={"orbiuno":6,"mycar":5}
WEBS={"orbiuno":"https://colombia-al-dia.pages.dev/","mycar":"https://busco-autos.pages.dev/"}
ACCOUNTS={"orbiuno":"@resumen.noticias","mycar":"@mycar.buscoautos"}

def compile_news(data):
    if data["editionDate"]!=DAY or data.get("publicationAuthorized") is not False:
        raise ValueError("No se acepta una edición de fecha ajena o con autorización ficticia")
    manifest={"editionDate":DAY,"editionSlot":"08:30","timezone":BOGOTA,
              "verifiedArticles":0,"unlicensedPhotos":0,"readyToPublish":False,
              "blockingReasons":[],"brands":{}}
    for brand,count in COUNTS.items():
        notes=data.get(brand,[])
        if len(notes)!=count or [n["order"] for n in notes]!=list(range(1,count+1)):
            raise ValueError(f"{brand}: número y orden de noticias incorrecto")
        bdir=OUT/brand
        bdir.mkdir(parents=True,exist_ok=True)
        voices=[{"id":"saludo","text":f"Buenos días. Bienvenidos a {'Orbiuno' if brand=='orbiuno' else 'MyCar'} Noticias. Hoy, lunes veintitrés de noviembre de dos mil veintiséis, estas son las noticias."}]
        articles=[]
        captions=[f"{brand.upper()} | Lunes 23 de noviembre de 2026 | 8:30 a. m. Colombia",
                  "Fuentes originales y cobertura completa:"]
        for n in notes:
            body=n["originalArticleTextEs"]
            if n.get("originalArticleReviewed") is not True or len(body)<640 or len(body.split("\n\n"))!=3:
                raise ValueError("Falta artículo propio revisado de "+n.get("title",""))
            if not n["url"].startswith("https://") or n.get("originalArticleSourceUrls")!=[n["url"]]:
                raise ValueError("Fuente original inválida")
            manifest["verifiedArticles"]+=1
            if n.get("photoStatus")!="VERIFIED_EXACT_EVENT_LICENSED_PHOTO":
                manifest["unlicensedPhotos"]+=1
                manifest["blockingReasons"].append("Falta fotografía pertinente/licenciada: "+brand+" "+str(n["order"]))
            if n.get("logoStatus")!="VERIFIED_SOURCE_LOGO":
                manifest["blockingReasons"].append("Falta logo de fuente comprobado: "+brand+" "+str(n["order"]))
            # Reel lee una frase por noticia. La web leerá el texto íntegro propio.
            voices.append({"id":f"n{n['order']:02d}","text":n.get("spoken") or n["reelLine"]})
            articles.append({"id":f"{brand}-20261123-0830-{n['order']}",
             "headline":n["title"],"source":{"name":n["source"],"url":n["url"]},
             "summary":n["summary"],"textForWebAudio":body,
             "photograph":None,"photoRightsVerified":False})
            captions.extend([f"{n['order']}. {n['title']}",n["url"]])
        voices.append({"id":"despedida",
            "text":f"Gracias por acompañarnos. Escucha la lectura completa de cada noticia en el enlace de nuestro perfil, {WEBS[brand].removeprefix('https://').replace('-', ' guion ').replace('.', ' punto ')}."})
        captions.extend(["",f"Escucha cada noticia desde el enlace del perfil {ACCOUNTS[brand]}.",WEBS[brand],
                         "Fotos reales y fuentes comprobadas antes de publicar.","#ORBIUNO #NoticiasColombia" if brand=="orbiuno" else "#MyCar #NoticiasMotor"])
        (bdir/"voice_input.json").write_text(json.dumps({"segments":voices},ensure_ascii=False,indent=2)+"\n")
        (bdir/"web_articles.json").write_text(json.dumps({"edition":DAY,"brand":brand,"news":articles},ensure_ascii=False,indent=2)+"\n")
        (bdir/"caption.txt").write_text("\n".join(captions)+"\n")
        manifest["brands"][brand]={"count":count,"voiceSegments":len(voices),"sourceURLs":[x["url"] for x in notes],
             "originalArticles":count,"publicationState":"BLOCKED_MEDIA"}
    # No se permite pasar a aprobación por mera generación de voz.
    if len(manifest["blockingReasons"])<11:
        raise ValueError("Error en comprobación de derechos")
    (OUT/"QA.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print("EDITORIAL_PREPARED_MEDIA_BLOCKED",manifest["verifiedArticles"],manifest["unlicensedPhotos"])
    return manifest

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=SOURCE)
    opts=parser.parse_args()
    data=json.loads(opts.source.read_text(encoding="utf-8"))
    compile_news(data)
if __name__=="__main__":
    main()
