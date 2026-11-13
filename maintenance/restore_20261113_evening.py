#!/usr/bin/env python3
"""Recuperar cinco noticias editoriales del 13/11, 18 h, desde HTML preservado.

No se inventan noticias ni se reemplazan otras entradas. Se extraen
únicamente los textos, enlaces y derechos ya mostrados en la versión previa.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "backups/2026-11-13-index-corrupto.html"
DB = ROOT / "noticias.json"


def text(markup):
    return html.unescape(re.sub(r"<[^>]*>", "", markup)).strip()


def pick(regex, block, label):
    match = re.search(regex, block, flags=re.S)
    if not match:
        raise ValueError(f"Falta {label} en archivo de respaldo")
    return match


def build():
    # Solo la sección editorial HTML original, antes del JSON que se dañó.
    raw = BACKUP.read_bytes().split(b'<script type="application/json" id="initial-news">')[0].decode("utf-8")
    records = []
    for order in range(1, 6):
        news_id = f"orbiuno-20261113-18h-{order}"
        escaped = re.escape(news_id)
        card = pick(r'<article id="noticia-' + escaped + r'"[^>]*>(.*?)</article>', raw, news_id).group(1)
        title = text(pick(r'<div class="news-body">.*?<h3>(.*?)</h3>', card, 'titular').group(1))
        category = text(pick(r'<span class="news-chip">(.*?)</span>', card, 'categoría').group(1))
        summary = text(pick(r'<p class="news-preview">(.*?)</p>', card, 'resumen').group(1))
        original_text = text(pick(r'<details class="news-transcript">.*?<p>(.*?)</p>', card, 'texto original').group(1))
        source_name = text(pick(r'<span class="source-thumbnail-name">(.*?)</span>', card, 'nombre fuente').group(1))
        source_url = html.unescape(pick(r'<a class="source"[^>]*href="([^"]+)"', card, 'URL fuente').group(1))
        image = pick(r'<figure class="news-photo">.*?<img src="([^"]+)"[^>]*alt="([^"]+)"', card, 'foto')
        caption = pick(r'<figcaption>(.*?)<br><a href="([^"]+)"[^>]*>(.*?)</a>(.*?)</figcaption>', card, 'crédito de imagen')
        image_license = text(caption.group(4)).strip(' ·\u00a0')
        photo_url = html.unescape(image.group(1))
        entry = {
            "id": news_id, "date": "2026-11-13",
            "editionSlot": "18:00", "priority": order,
            "category": category, "title": title,
            "summary": summary, "executiveSummary": summary,
            "sources": [{"name": source_name, "url": source_url}],
            "sourceLanguage": "en" if "reuters.com" in source_url else "es",
            "verification": "editorial_verified",
            "audioFullTextEs": original_text,
            "audioIsFullPublisherArticle": False,
            "imageType": "official_photo" if "Dominio público" in image_license else "licensed_press_photo",
            "imageRightsVerified": True,
            "imageLicense": image_license,
            "imageCredit": text(caption.group(3)),
            "imageSourceUrl": html.unescape(caption.group(2)),
            "imageUrl": photo_url,
            "imageAlt": html.unescape(image.group(2)),
            "imageCaption": text(caption.group(1)),
        }
        if len(title) < 10 or len(original_text.split()) < 110 or not source_url.startswith("https://"):
            raise ValueError(f"Datos incompletos, no publicar {news_id}")
        records.append(entry)
    return records


def main():
    db = json.loads(DB.read_text(encoding="utf-8"))
    existing = {n["id"] for n in db["news"]}
    additions = [n for n in build() if n["id"] not in existing]
    # Restaurar como archivo histórico si la portada ya avanzó a una nueva fecha.
    # No retroceder editionDate ni sustituir las noticias actuales.
    if additions and len(additions) != 5:
        raise ValueError("Recuperación parcial: no incorporar noticias incompletas")
    db["news"].extend(additions)
    from datetime import datetime
    if db.get("editionDate") == "2026-11-13":
        db["editedAtBogota"] = "2026-11-13T18:00:00-05:00"
    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Noticias de las 18 h recuperadas:", len(additions))


if __name__ == "__main__":
    main()
