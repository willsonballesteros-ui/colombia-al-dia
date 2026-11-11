"""Fail-closed HTML cross-check; separate from publishing or deployment."""
import html as html_lib
import re


def check_web(items, html_text: str):
    errors, offsets = [], []
    for entry in items:
        item_id = str(entry["id"])
        needle = re.compile(r'id=["\']noticia-' + re.escape(item_id) + r'["\']')
        match = needle.search(html_text)
        if not match:
            errors.append(f"ancla noticia-{item_id} ausente")
            continue
        offsets.append(match.start())
        segment = html_lib.unescape(html_text[match.start():match.start() + 8000])
        title = str(entry.get("title", ""))
        url = str(entry.get("source", {}).get("url", ""))
        if title and title not in segment:
            errors.append(f"título de {item_id} no coincide")
        if url and url not in segment:
            errors.append(f"fuente de {item_id} no coincide")
    if offsets != sorted(offsets):
        errors.append("orden de noticias distinto")
    return errors
