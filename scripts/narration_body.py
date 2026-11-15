"""Narración de noticias: únicamente el cuerpo editorial, sin presentación de marca.

Mantiene los párrafos y elimina únicamente frases de autopromoción sobre ORBIUNO.
El mismo texto debe alimentar el reproductor y el contenido desarrollado visible.
"""
import re


def story_body(raw):
    paragraphs = []
    for paragraph in str(raw or "").strip().split("\n\n"):
        sentences = re.split(r"(?<=[.!?])\s+", paragraph.strip())
        kept = [s for s in sentences if s and not re.search(r"\bORBIUNO\b", s, flags=re.I)]
        if kept:
            paragraphs.append(" ".join(kept))
    return "\n\n".join(paragraphs).strip()


def narration_for(news, original_article_ready):
    raw = (news.get("originalArticleTextEs") if original_article_ready(news)
           else news.get("audioFullTextEs")) or ""
    return story_body(raw)
