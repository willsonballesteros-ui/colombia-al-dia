#!/usr/bin/env python3
"""Preparar una narración ampliada ORIGINAL en español, no un artículo pirateado.

Conserva el campo de audio escrito por un editor. En las entradas
editorial_verified sin audio, elabora una versión española a partir de los
campos originales ya contrastados: summary/why/next. Nunca copia el cuerpo
íntegro del artículo del proveedor ni narra un RSS source_only como verificado.
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


ENGLISH_DOMAINS = {"reuters.com", "ft.com", "apnews.com", "bbc.com", "wsj.com",
                   "theguardian.com", "nytimes.com"}
VALID_LANGUAGES = {"es", "en"}


def identify_source_language(item):
    if item.get("sourceLanguage") in VALID_LANGUAGES:
        return item["sourceLanguage"]
    sources = item.get("sources") or []
    host = (urlsplit(sources[0].get("url", "")).hostname or "").lower() if sources else ""
    if any(host == domain or host.endswith("." + domain) for domain in ENGLISH_DOMAINS):
        return "en"
    return "es"


def normalize(text):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text.rstrip(" .\n\t") + "." if text else ""


def editorial_audio(item):
    """Síntesis propia, sin extractos extensos ni texto íntegro de terceros."""
    intro = normalize(item.get("summary"))
    context = normalize(item.get("why"))
    next_steps = normalize(item.get("next"))
    if not intro:
        return ""
    parts = [intro]
    if context and context.casefold() != intro.casefold():
        parts.append(context)
    if next_steps:
        # Introduce cautela: los próximos pasos son seguimiento, no hechos.
        parts.append("Los siguientes aspectos requieren seguimiento. " + next_steps)
    return " ".join(parts)


def enrich(db):
    count = 0
    for item in db.get("news", []):
        if item.get("verification") != "editorial_verified":
            continue
        language = identify_source_language(item)
        if item.get("sourceLanguage") != language:
            item["sourceLanguage"] = language
            count += 1
        if not item.get("audioFullTextEs"):
            full_text = editorial_audio(item)
            if full_text and len(full_text) > len(str(item.get("executiveSummary") or "")):
                item["audioFullTextEs"] = full_text
                item["audioEditorialSource"] = "ORBIUNO: narración editorial propia en español basada en fuentes atribuidas."
                item["audioIsFullPublisherArticle"] = False
                count += 1
    return count


def main():
    filename = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("noticias.json")
    db = json.loads(filename.read_text(encoding="utf-8"))
    changed = enrich(db)
    if changed:
        filename.write_text(json.dumps(db, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Audio editorial: {changed} nuevos campos / textos, sin reproducción íntegra de medios.")


if __name__ == "__main__":
    main()
