#!/usr/bin/env python3
"""Crea un RSS propio a partir de las 10 notas editoriales del día.

No replica artículos originales de terceros ni incluye titulares source_only.
"""
import json
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, ElementTree
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
BASE = "https://colombia-al-dia.pages.dev/"


def main():
    db = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    day = db["editionDate"]
    news = sorted((
        x for x in db["news"]
        if x.get("date") == day and x.get("verification") == "editorial_verified"
    ), key=lambda x: x.get("priority", 999))
    if len(news) != 10:
        raise RuntimeError(f"RSS de edición verificada requiere 10 noticias, hay {len(news)}")
    root = Element("rss", {"version": "2.0"})
    channel = SubElement(root, "channel")
    for tag, value in (
        ("title", "Colombia al Día | Noticias verificadas"),
        ("link", BASE),
        ("description", "Diez noticias contrastadas con sus fuentes originales y fecha de edición."),
        ("language", "es-CO"),
    ):
        SubElement(channel, tag).text = value
    published = datetime.fromisoformat(day + "T06:00:00").replace(tzinfo=ZoneInfo("America/Bogota"))
    for n in news:
        item = SubElement(channel, "item")
        link = BASE + "#noticia-" + n["id"]
        for tag, value in (
            ("title", n["title"]),
            ("link", link),
            ("guid", link),
            ("description", n["summary"] + " | Fuente: " + ", ".join(s["name"] for s in n["sources"])),
            ("pubDate", format_datetime(published)),
            ("category", n["category"]),
        ):
            SubElement(item, tag).text = value
    ElementTree(root).write(ROOT / "feed.xml", encoding="utf-8", xml_declaration=True)
    print("RSS generado:", len(news), "noticias de", day)


if __name__ == "__main__":
    main()
