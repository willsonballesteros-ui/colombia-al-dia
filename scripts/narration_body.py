"""Texto editorial narrado: mantiene párrafos completos y excluye autopromoción."""
import re


def story_body(raw):
    paragraphs = []
    for paragraph in str(raw or "").strip().split("\n\n"):
        sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
        kept = []
        for sentence in sentences:
            if not sentence:
                continue
            # Las promociones independientes NO son parte del reportaje.
            if re.match(r"(?i)^\s*(?:síguenos|sigue a orbiuno|visita nuestra web|escucha en nuestra página)", sentence):
                continue
            # Evita perder hechos porque una oración mencione la marca.
            sentence = re.sub(r"(?i)\b(?:redacción\s+)?ORBIUNO(?:\s+Noticias)?\b", "", sentence)
            sentence = re.sub(r"\s{2,}", " ", sentence).strip(" ·—:-,;")
            if sentence:
                kept.append(sentence)
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs).strip()


def narration_for(news, original_article_ready):
    raw = (news.get("originalArticleTextEs") if original_article_ready(news)
           else news.get("audioFullTextEs")) or ""
    return story_body(raw)
