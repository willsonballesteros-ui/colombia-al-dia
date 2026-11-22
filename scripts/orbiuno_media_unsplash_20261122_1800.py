#!/usr/bin/env python3
"""Stage six licensed, editorially reviewed Unsplash archive photos for ORBIUNO 22 Nov.

Images are real contextual archive photos, never represented as events.
No synthetic graphics; the Meta publisher is separate.
HTTP 429/403 fails closed without proxy, host rotation or circumvention.
"""
from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from PIL import Image

from scripts.orbiuno_media_assets import decode_image, fetch as icon_fetch

ROOT = Path(__file__).resolve().parents[1]
EDITION_DAY = "2026-11-22"
EDITION_SLOT = "18:00"
PHOTO_IDS = (
    "photo-1668724982255-1a3e0c72b814",
    "photo-1769859177914-f66488d71193",
    "photo-1655149588581-49191c89e470",
    "photo-1576671081741-c538eafccfff",
    "photo-1769432774099-fe28f56f95fc",
    "photo-1747171053296-84c4e8015b24",
)


def validate_photo(item: dict, position: int) -> dict:
    if position not in range(1, 7):
        raise ValueError("Posición de noticia fuera de rango")
    if item.get("photoMatchReviewed") is not True or item.get("photoUnsplashRightsReviewed") is not True:
        raise ValueError("Fotografía sin revisión editorial y de licencia")
    image_url = item.get("photoUnsplashImageUrl", "")
    page = item.get("photoUnsplashPage", "")
    author = item.get("photoUnsplashAuthor", "")
    caption = item.get("photoCaption", "")
    parsed = urlsplit(image_url)
    if (parsed.scheme != "https" or parsed.hostname != "images.unsplash.com"
            or parsed.username or parsed.password or parsed.fragment
            or parsed.port not in (None, 443)
            or parsed.path != "/" + PHOTO_IDS[position - 1]):
        raise ValueError("Imagen no coincide con fotografía licenciada y revisada")
    p = urlsplit(page)
    if (p.scheme != "https" or p.hostname != "unsplash.com" or p.query or p.fragment
            or not re.fullmatch(r"/photos/[a-z0-9-]+-[A-Za-z0-9_-]+", p.path)):
        raise ValueError("Falta página original de fotografía en Unsplash")
    if not isinstance(author, str) or len(author.strip()) < 3:
        raise ValueError("Autor no identificado")
    if (not isinstance(caption, str) or len(caption.strip()) < 30
            or "archivo" not in caption.lower()):
        raise ValueError("Falta contexto de fotografía de archivo")
    return {
        "title": PHOTO_IDS[position - 1],
        "author": author.strip(),
        "license": "Unsplash License",
        "page": page,
        "url": image_url,
        "description": caption.strip(),
    }


def download_photo(url: str) -> Image.Image:
    if urlsplit(url).hostname != "images.unsplash.com":
        raise ValueError("No se permite el origen de imagen")
    request = Request(url, headers={"User-Agent": "ORBIUNO-Newsroom/1.0 (licensed image attribution)"})
    with urlopen(request, timeout=35) as response:
        final = urlsplit(response.url)
        if final.scheme != "https" or final.hostname != "images.unsplash.com":
            raise ValueError("La imagen redirigió a sitio no autorizado")
        raw = response.read(12_000_001)
    if not raw or len(raw) > 12_000_000:
        raise ValueError("Imagen vacía o demasiado grande")
    return decode_image(raw, min_size=(650, 450))


def download_logo(host: str) -> tuple[Image.Image, str]:
    if not re.fullmatch(r"[a-z0-9.-]{4,110}", host) or "." not in host:
        raise ValueError("Dominio de fuente inválido")
    urls = [
        "https://www.google.com/s2/favicons?" + urlencode({"domain": host, "sz": 128}),
        "https://www.google.com/s2/favicons?" + urlencode({"domain_url": "https://" + host, "sz": 64}),
    ]
    errors = []
    for url in urls:
        try:
            binary = icon_fetch(url, limit=2_000_000)
            logo = Image.open(io.BytesIO(binary))
            logo.load()
            if min(logo.size) < 16:
                raise ValueError("Ícono demasiado pequeño")
            return logo.convert("RGBA"), url
        except Exception as exc:
            errors.append(type(exc).__name__ + ": " + str(exc)[:120])
    raise ValueError("No se pudo verificar ícono de " + host + ": " + "; ".join(errors))


def stage(edition_path: Path, news_path: Path, output: Path) -> dict:
    edition = json.loads(edition_path.read_text(encoding="utf-8"))
    day, slot = edition.get("editionDate"), edition.get("editionSlot")
    if (day, slot) != (EDITION_DAY, EDITION_SLOT):
        raise ValueError("Este paquete es exclusivamente de la edición 22/11 18:00")
    if day != datetime.now(ZoneInfo("America/Bogota")).date().isoformat():
        raise ValueError("No publicar una edición con fecha caducada")
    if edition.get("sourceOnly") is not False or edition.get("approval", {}).get("editorial") is not True:
        raise ValueError("Las seis noticias requieren aprobación editorial")
    ordered = sorted(edition.get("news", []), key=lambda n: n["priority"])
    if len(ordered) != 6 or [n.get("priority") for n in ordered] != [1, 2, 3, 4, 5, 6]:
        raise ValueError("Se requieren seis noticias originales en orden")
    db = json.loads(news_path.read_text(encoding="utf-8"))
    published = {n.get("id"): n for n in db.get("news", [])}
    registry = []
    image_urls = set()
    for position, item in enumerate(ordered, 1):
        if item.get("verification") != "editorial_verified" or item.get("id") not in published:
            raise ValueError("Noticia sin revisión editorial o importación")
        if published[item["id"]].get("title") != item.get("title"):
            raise ValueError("Titular editado después de aprobación")
        photo = validate_photo(item, position)
        if photo["url"] in image_urls:
            raise ValueError("Fotografía repetida")
        image_urls.add(photo["url"])
        if item.get("date") != day or item.get("editionSlot") != slot:
            raise ValueError("Fecha o franja incoherentes")
        host = urlsplit(item["sources"][0]["url"]).hostname
        if not host:
            raise ValueError("Fuente de noticia sin dominio")
        registry.append((item, photo, host))

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="orbiuno-photos-", dir=output.parent) as tmp:
        tmp_path = Path(tmp)
        entries = []
        logo_cache = {}
        for position, (item, photo, host) in enumerate(registry, 1):
            filename = "photo-%02d.jpg" % position
            logo_name = "logo-%02d.png" % position
            visual = download_photo(photo["url"])
            visual.save(tmp_path / filename, format="JPEG", quality=88, optimize=True)
            if (tmp_path / filename).stat().st_size < 12_000:
                raise ValueError("Fotografía incompleta")
            if host not in logo_cache:
                logo_cache[host] = download_logo(host)
            logo, logo_url = logo_cache[host]
            icon = logo.copy()
            if min(icon.size) < 96:
                scale = 96 / min(icon.size)
                icon = icon.resize((round(icon.width * scale), round(icon.height * scale)),
                                   Image.Resampling.NEAREST)
            icon.save(tmp_path / logo_name, format="PNG")
            entries.append({
                "id": item["id"], "photoFile": filename, "logoFile": logo_name,
                "sourceHost": host, "logoCredit": None, "logoSource": logo_url,
                "caption": photo["description"], "credit": photo,
            })

        summary = {
            "edition": day, "slot": slot, "visualMode": "verified_real_photos",
            "photosCount": 6, "logosCount": 6, "entries": entries,
        }
        output.mkdir(parents=True, exist_ok=True)
        for filename in [f"photo-{i:02d}.jpg" for i in range(1, 7)] + [f"logo-{i:02d}.png" for i in range(1, 7)]:
            shutil.copy2(tmp_path / filename, output / filename)
        for ent in entries:
            item = published[ent["id"]]
            credit = ent["credit"]
            item.update({
                "imageUrl": "./" + (output / ent["photoFile"]).relative_to(ROOT).as_posix(),
                "imageType": "licensed_press_photo", "imageRightsVerified": True,
                "imageSourceUrl": credit["page"], "imageCredit": credit["author"],
                "imageLicense": credit["license"], "imageCaption": ent["caption"],
                "imageAlt": ent["caption"],
            })
        updated = news_path.with_suffix(".json.tmp")
        updated.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        updated.replace(news_path)
        proof = output / "credits.json"
        temp_proof = output / "credits.json.tmp"
        temp_proof.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp_proof.replace(proof)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True)
    ap.add_argument("--news", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    result = stage(Path(args.edition).resolve(), Path(args.news).resolve(), Path(args.out).resolve())
    print("UNSPLASH_PHOTOS_AND_SOURCE_LOGOS_VERIFIED", result["photosCount"], result["logosCount"])


if __name__ == "__main__":
    main()
