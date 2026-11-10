#!/usr/bin/env python3
"""Importar una edición humana revisada a un árbol de PR; nunca publicar."""
import argparse
import json
import re
from copy import deepcopy
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

def approved_article(source):
    u = urlsplit(source)
    return u.scheme == "https" and u.hostname is not None and (
        u.hostname == "unfccc.int" and u.path.rstrip("/") == "/cop31"
        or u.hostname == "www.senado.gov.co" and "/noticias/" in u.path
        or u.hostname == "www.elespectador.com" and "/economia/" in u.path
        or u.hostname == "www.dane.gov.co" and "/ipc/" in u.path
    )

def merge(db, edition):
    day, slot = edition["editionDate"], edition["editionSlot"]
    if slot not in ("08:00", "12:00", "18:00"):
        raise ValueError("Franja no permitida")
    if edition.get("editorialReviewed") is not True:
        raise ValueError("Falta revisión editorial expresa")
    stories=edition.get("stories")
    if not isinstance(stories,list) or len(stories)!=4:
        raise ValueError("La edición requiere exactamente cuatro notas revisadas")
    current_ids={n["id"] for n in db["news"]}
    existing={n["id"]: n for n in db["news"]}
    added=[]
    for i,n in enumerate(stories,1):
        if n.get("date")!=day or n.get("editionSlot")!=slot or n.get("priority")!=i:
            raise ValueError("Fecha, franja u orden inconsistente")
        if not re.fullmatch(r"orbiuno-\\d{8}-\\d{2}h-0[1-4]",n["id"]):
            raise ValueError("Identificador editorial no válido")
        src=n["source"]
        if not approved_article(src["url"]):
            raise ValueError("Fuente no directa o fuera de lista revisada: "+src["url"])
        paragraphs=n["body"]
        if not isinstance(paragraphs,list) or len(paragraphs)<3 or any(len(x)<130 for x in paragraphs):
            raise ValueError("Reportaje propio requiere tres párrafos sustanciales")
        report="\n\n".join(paragraphs)
        if len(report)<640 or not 110<=len(report.split())<=250:
            raise ValueError("Extensión editorial/audio fuera de los límites")
        item={
            "id":n["id"],"date":day,"editionSlot":slot,"priority":i,
            "category":n["category"],"level":"Noticia verificada por la redacción",
            "title":n["title"],"summary":n["summary"],
            "executiveSummary":n["summary"],"sources":[src],
            "verification":"editorial_verified","sourceLanguage":"en" if src["name"].startswith("ONU") else "es",
            "audioFullTextEs":report,"audioIsFullPublisherArticle":False,
            "originalArticleTextEs":report,"originalArticleByline":"Redacción ORBIUNO",
            "originalArticleReviewed":True,"originalArticleReviewStatus":"aprobado",
            "originalArticleSourceUrls":[src["url"]],
            "originalArticleIsPublisherVerbatim":False
        }
        if item["id"] in existing and existing[item["id"]]!=item:
            raise ValueError("Edición previamente aprobada difiere: "+item["id"])
        if item["id"] not in current_ids:
            added.append(item)
    revised=deepcopy(db)
    revised["news"]=added+revised["news"]
    revised["editionDate"]=day
    revised["editedAtBogota"]=day+" 18:15"
    return revised

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--edition",required=True)
    p.add_argument("--root",type=Path,default=ROOT)
    p.add_argument("--apply",action="store_true",help="Escribir SOLO en árbol de prueba, nunca publicar")
    args=p.parse_args()
    path=args.root/"noticias.json"
    db=json.loads(path.read_text(encoding="utf-8"))
    edition=json.loads(Path(args.edition).read_text(encoding="utf-8"))
    updated=merge(db,edition)
    from scripts.validate_news import check
    check(updated)
    count=sum(n.get("editionSlot")==edition["editionSlot"] and
              n.get("date")==edition["editionDate"] and
              n.get("verification")=="editorial_verified" for n in updated["news"])
    if count!=4:
        raise ValueError(f"La franja debe tener 4 notas únicas; hay {count}")
    if args.apply:
        path.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"EDICIÓN PREPARADA, NO PUBLICADA: {edition['editionDate']} {edition['editionSlot']}, {count} notas; apply={args.apply}")

if __name__=="__main__":
    main()
