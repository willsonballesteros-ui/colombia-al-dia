#!/usr/bin/env python3
"""ORBIUNO: import one reviewed six-news edition without replacing historical news.

The editorial JSON belongs in editions/daily/YYYY-MM-DD-HHMM.json.
This command only prepares local publication artifacts. It never calls Meta.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")
SLOTS = {"08:00", "09:30", "12:00", "17:00", "18:00", "19:00"}
ROOT = Path(__file__).resolve().parents[1]


def validated(doc: dict, today: str | None = None, *, expected_count: int = 6) -> tuple[str, str, list[dict]]:
    day = doc.get("editionDate")
    slot = doc.get("editionSlot")
    if not isinstance(day, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
        raise ValueError("Fecha editorial inválida")
    if slot not in SLOTS:
        raise ValueError("Franja inválida: usar 08:00, 09:30, 12:00, 17:00, 18:00 o 19:00")
    if today is not None and day != today:
        raise ValueError("Edición de otra fecha: no se puede publicar como hoy")
    news = doc.get("news")
    if not isinstance(news, list) or len(news) != expected_count:
        raise ValueError("Se requieren exactamente seis noticias")
    if doc.get("editionKey") != "ORBIUNO-" + day + "-" + slot.replace(":", ""):
        raise ValueError("editionKey no coincide con fecha y franja")
    ids = [n.get("id") for n in news]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != expected_count:
        raise ValueError("IDs faltantes o duplicados")
    priorities = [n.get("priority") for n in news]
    if sorted(priorities) != list(range(1, expected_count + 1)):
        raise ValueError("Prioridades deben ser 1..6, sin repetir")
    for item in news:
        if item.get("date") != day or item.get("editionSlot") != slot:
            raise ValueError("Fecha o franja de noticia distinta al manifiesto")
        if item.get("verification") != "editorial_verified":
            raise ValueError("Noticia sin revisión editorial")
        if item.get("originalArticleReviewed") is not True:
            raise ValueError("Artículo propio aún sin revisión")
        if item.get("originalArticleByline") != "Redacción ORBIUNO":
            raise ValueError("Falta firma editorial ORBIUNO")
        body = item.get("originalArticleTextEs", "")
        if not isinstance(body, str) or not (
            len(body.strip()) >= 1000 or (len(body.strip()) >= 640 and len(body.strip().split("\n\n")) >= 3)
        ):
            raise ValueError("Redacción completa insuficiente")
        if item.get("originalArticleIsPublisherVerbatim") is not False:
            raise ValueError("No reproducir el artículo del proveedor")
        if not isinstance(item.get("title"), str) or len(item["title"].strip()) < 10:
            raise ValueError("Titular inválido")
        if len(str(item.get("reelLine", "")).split()) > 27 or not item.get("reelLine"):
            raise ValueError("Línea del Reel debe tener de 1 a 27 palabras")
        sources = item.get("sources", [])
        urls = [s.get("url", "") for s in sources if isinstance(s, dict)]
        if not urls:
            raise ValueError("Sin fuente original")
        for url in urls:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.path in ("", "/"):
                raise ValueError("La fuente debe enlazar al artículo exacto por HTTPS")
        originals = item.get("originalArticleSourceUrls")
        if not isinstance(originals, list) or not originals or not all(url in urls for url in originals):
            raise ValueError("Fuentes no coinciden con texto original")
        if item.get("imageUrl"):
            if item.get("imageRightsVerified") is not True or not item.get("imageCredit") or not item.get("imageLicense") or not item.get("imageSourceUrl"):
                raise ValueError("Fotografía sin licencia, autor o procedencia")
    return day, slot, sorted(news, key=lambda n: n["priority"])


def import_edition(base: dict, edition: dict, today: str | None = None) -> dict:
    day, slot, incoming = validated(edition, today=today)
    if not isinstance(base.get("news"), list):
        raise ValueError("noticias.json no contiene listado histórico")
    old = list(base["news"])
    same_slot = [n for n in old if n.get("date") == day and
                 n.get("editionSlot") == slot and n.get("verification") == "editorial_verified"]
    if same_slot:
        if [n.get("id") for n in sorted(same_slot, key=lambda n: n.get("priority", 999))] != [n["id"] for n in incoming]:
            raise ValueError("Ya existe otra edición verificable en esa fecha/franja; evitar sobrescribir")
        for n in incoming:
            existing = next(x for x in same_slot if x["id"] == n["id"])
            # Identical editorial fields are allowed; previously published metadata is preserved.
            if any(existing.get(k) != v for k, v in n.items()):
                raise ValueError("La edición anterior difiere; no sobreescribir contenido publicado")
        base["editionDate"] = day
        return base
    seen = {n.get("id") for n in old}
    if any(n["id"] in seen for n in incoming):
        raise ValueError("ID ya utilizado en el histórico")
    result = dict(base)
    result["news"] = old + incoming
    result["editionDate"] = day
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--edition", required=True)
    parser.add_argument("--news", default="noticias.json")
    parser.add_argument("--today", default=datetime.now(BOGOTA).date().isoformat())
    args = parser.parse_args()
    f = Path(args.edition).resolve()
    if ROOT not in f.parents or not re.fullmatch(r"\d{4}-\d{2}-\d{2}-(0800|0930|1200|1700|1800|1900)\.json", f.name):
        raise SystemExit("Se requiere un fichero editions/daily/YYYY-MM-DD-HHMM.json del repositorio")
    if f.parent != ROOT / "editions" / "daily":
        raise SystemExit("Carpeta inesperada para edición")
    doc = json.loads(f.read_text(encoding="utf-8"))
    day, slot, news = validated(doc, today=args.today)
    if f.name != day + "-" + slot.replace(":", "") + ".json":
        raise SystemExit("Nombre del JSON no coincide con fecha y franja")
    dst = Path(args.news)
    db = json.loads(dst.read_text(encoding="utf-8"))
    combined = import_edition(db, doc, today=args.today)
    dst.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"state": "EDITION_IMPORTED", "date": day, "slot": slot,
                      "count": len(news), "ids": [n["id"] for n in news]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
