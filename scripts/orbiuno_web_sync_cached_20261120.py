#!/usr/bin/env python3
"""Synchronize one previously QA-approved ORBIUNO preview into the public web.

Reuses only the real licensed photographs and editorial metadata already
reviewed in GitHub Actions artifact 44733147573. Does not call Meta or Commons.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = {"CC BY 4.0", "CC BY-SA 4.0", "CC BY 3.0", "CC BY-SA 3.0",
            "CC BY 2.0", "CC BY-SA 2.0", "CC BY-SA 3.0 igo",
            "CC0", "CC0 1.0", "Public domain", "PD"}
EXPECTED_DAY = "2026-11-20"
EXPECTED_SLOT = "08:00"
EXPECTED_COUNT = 6
EXPECTED_ID = "ORBIUNO-2026-11-20-0800"


def sync(edition_file: Path, cache: Path, news_file: Path, target: Path):
    edition = json.loads(edition_file.read_text(encoding="utf-8"))
    if (edition.get("editionDate"), edition.get("editionSlot"),
        edition.get("editionKey"), edition.get("sourceOnly")) != (
        EXPECTED_DAY, EXPECTED_SLOT, EXPECTED_ID, False):
        raise ValueError("No es la edición verificada de la mañana 20/11; no modificar web")
    selected = sorted(edition["news"], key=lambda n: n["priority"])
    if len(selected) != EXPECTED_COUNT or len({n["id"] for n in selected}) != EXPECTED_COUNT:
        raise ValueError("Faltan o sobran noticias")
    cached = json.loads((cache / "credits.json").read_text(encoding="utf-8"))
    reel_editorial = json.loads((cache / "editorial.json").read_text(encoding="utf-8"))
    if len(cached) != EXPECTED_COUNT or len(reel_editorial) != EXPECTED_COUNT:
        raise ValueError("El paquete previo no tiene las seis noticias")
    existing = json.loads(news_file.read_text(encoding="utf-8"))
    lookup = {n["id"]: n for n in existing["news"]}
    if any(n["id"] not in lookup for n in selected):
        raise ValueError("Falta importar la edición revisada; detener")
    if any(n.get("verification") != "editorial_verified" or
           n.get("originalArticleReviewed") is not True for n in selected):
        raise ValueError("Falta revisión editorial y artículo completo")
    verified = []
    for i, (item, credit, reel) in enumerate(zip(selected, cached, reel_editorial)):
        if (item["title"], item["sources"][0]["url"], item["photoCommonsTitle"]) != (
            credit.get("headline"), credit.get("source"), credit.get("image_title")):
            raise ValueError("Titular/fuente/foto discordante: " + str(i))
        if item["title"] != reel.get("title") or item["sources"][0]["url"] != reel.get("url"):
            raise ValueError("La edición de video difiere del artículo web: " + str(i))
        if item["photoMatchReviewed"] is not True or not item["photoCaption"].strip():
            raise ValueError("Falta revisar la pertinencia de la foto")
        if credit.get("license") not in ACCEPTED or not credit.get("author") or not credit.get("commons", "").startswith("https://commons.wikimedia.org/wiki/File:"):
            raise ValueError("Fotografía sin derechos o autor confirmados: " + str(i))
        src = cache / f"photo-{i:02d}.jpg"
        if not src.is_file() or src.stat().st_size < 12_000:
            raise ValueError("Foto ausente del paquete audiovisual: " + str(i))
        with Image.open(src) as photo:
            photo.load()
            if photo.format != "JPEG" or photo.width < 650 or photo.height < 450:
                raise ValueError("Foto corrupta o pequeña: " + str(i))
        verified.append((item, credit, src))
    # Never touch the older archive or the Reel: only date-scoped images and metadata.
    target.mkdir(parents=True, exist_ok=True)
    entries = []
    for i, (item, credit, src) in enumerate(verified, 1):
        filename = f"photo-{i:02d}.jpg"
        dst = target / filename
        if dst.exists() and hashlib.sha256(dst.read_bytes()).digest() != hashlib.sha256(src.read_bytes()).digest():
            # An earlier verified photo pack was already committed to the historical
            # path: preserve it only when its independent license ledger and hash
            # match this exact news item. Never overwrite it or accept an unknown JPG.
            ledger_path = target / "preverified_sources.json"
            if not ledger_path.is_file():
                raise ValueError("Hay foto distinta sin libro de procedencia, BLOQUEAR")
            previous = json.loads(ledger_path.read_text(encoding="utf-8"))
            rows = previous.get("photos", [])
            if len(rows) != EXPECTED_COUNT:
                raise ValueError("La procedencia de fotos anteriores está incompleta")
            old = rows[i - 1]
            if (old.get("filename"), old.get("title"), old.get("author"),
                old.get("license"), old.get("page")) != (
                filename, credit["image_title"], credit["author"],
                credit["license"], credit["commons"]):
                raise ValueError("La foto previa no coincide editorialmente: " + str(i))
            if hashlib.sha256(dst.read_bytes()).hexdigest() != old.get("sha256"):
                raise ValueError("La fotografía previa no coincide con su hash: " + str(i))
            with Image.open(dst) as prior_photo:
                prior_photo.load()
                if prior_photo.format != "JPEG" or prior_photo.width < 650 or prior_photo.height < 450:
                    raise ValueError("Foto anterior corrupta o ilegible")
        if not dst.exists():
            shutil.copyfile(src, dst)
        saved = lookup[item["id"]]
        base = "./" + target.resolve().relative_to(ROOT).as_posix() + "/"
        saved.update(
            imageUrl=base + filename,
            imageType="licensed_press_photo",
            imageRightsVerified=True,
            imageSourceUrl=credit["commons"],
            imageCredit=credit["author"],
            imageLicense=credit["license"],
            imageCaption=item["photoCaption"],
            imageAlt=item["photoCaption"])
        entries.append({"id": item["id"], "photoFile": filename,
                        "author": credit["author"], "license": credit["license"],
                        "source": credit["commons"], "sha256": hashlib.sha256(dst.read_bytes()).hexdigest()})
    news_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (target / "credits.json").write_text(json.dumps(
        {"edition": EXPECTED_ID, "originRun": 44733147573, "items": entries},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("ORBIUNO_CACHED_PHOTOS_VERIFIED", len(entries), "edition", EXPECTED_ID)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--news", default=str(ROOT / "noticias.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sync(Path(a.edition), Path(a.cache), Path(a.news), Path(a.out))


if __name__ == "__main__":
    main()
