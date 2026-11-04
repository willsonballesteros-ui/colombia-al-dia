#!/usr/bin/env python3
"""Portada accesible de Colombia al Día, sin dibujos ni avatares.

La imagen se muestra SÓLO cuando una edición verificó su autoría,
procedencia y derechos de uso. En caso contrario, usar sólo tipografía.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse, quote


ROOT = Path(__file__).resolve().parents[1]
VALID_IMAGE_TYPES = {"official_photo", "licensed_press_photo", "official_document"}


def image_verified(news):
    return (
        news.get("imageType") in VALID_IMAGE_TYPES
        and news.get("imageRightsVerified") is True
        and bool(news.get("imageLicense"))
        and bool(news.get("imageCredit"))
        and str(news.get("imageSourceUrl", "")).startswith("https://")
        and (
            str(news.get("imageUrl", "")).startswith("https://")
            or str(news.get("imageUrl", "")).startswith("./media/")
        )
        and not str(news.get("imageUrl", "")).endswith(".svg")
    )


def esc(s):
    return html.escape(str(s or ""), quote=True)


def image_markup(n):
    if not image_verified(n):
        return ""
    return (
        '<figure class="news-photo"><img src="{url}" loading="lazy" '
        'alt="{alt}" width="1080" height="600">'
        '<figcaption>Imagen: <a href="{origin}" target="_blank" rel="noopener noreferrer">'
        '{credit}</a>. {license}</figcaption></figure>'
    ).format(
        url=esc(n["imageUrl"]), alt=esc(n.get("imageAlt") or n["title"]),
        origin=esc(n["imageSourceUrl"]), credit=esc(n["imageCredit"]),
        license=esc(n["imageLicense"]),
    )


def source_thumbnail(n):
    """Mostrar el favicon real del dominio citado; no es foto del hecho."""
    sources = [s for s in n.get("sources", []) if str(s.get("url", "")).startswith("https://")]
    if not sources:
        return ""
    host = (urlparse(sources[0]["url"]).hostname or "").lower()
    if not host or not re.fullmatch(r"[a-z0-9.-]+", host):
        return ""
    icon_url = "https://www.google.com/s2/favicons?domain=" + quote(host, safe="") + "&sz=128"
    label = sources[0].get("name", "Fuente")
    return (
        '<div class="source-thumbnail">'
        '<img src="{icon}" loading="lazy" width="64" height="64" '
        'alt="Icono del sitio de {label}; no es fotografía del hecho">'
        '<span class="source-thumbnail-name">{label}</span></div>'
    ).format(icon=esc(icon_url), label=esc(label))


def article_html(n):
    sources = [s for s in n.get("sources", []) if str(s.get("url", "")).startswith("https://")]
    if not sources:
        return ""
    source = sources[0]
    thumbnail = image_markup(n)
    if not thumbnail:
        thumbnail = source_thumbnail(n)
    return (
        '<article id="noticia-{id}" class="card compact-card">'
        '<div class="visual-frame">{thumbnail}</div>'
        '<div class="news-body"><div class="news-meta">'
        '<span class="news-chip">{cat}</span><time datetime="{date}">{date}</time>'
        '</div><h3>{title}</h3><p class="news-preview">{summary}</p>'
        '<div class="news-actions">'
        '<button type="button" class="listen-btn" data-tts-action="toggle" '
        'data-tts-id="{id}" data-tts-full="{full}" aria-pressed="false" '
        'aria-label="{listen}" title="{listen}">▶ {listen}</button>'
        '<button type="button" class="speed-btn" data-tts-action="speed" data-tts-id="{id}" '
        'aria-label="Cambiar velocidad de lectura. Actual: 1x" title="Cambiar velocidad">1x</button>'
        '<button type="button" class="stop-btn" data-tts-action="stop" '
        'data-tts-id="{id}" aria-label="Detener lectura" title="Detener lectura" hidden>■</button>'
        '{spanish}'
        '<a class="source" target="_blank" rel="noopener noreferrer" href="{url}" '
        'title="Abrir la fuente original {label}">Fuente ↗</a>'
        '</div></div></article>'
    ).format(
        id=esc(n["id"]), thumbnail=thumbnail,
        cat=esc(n.get("category", "")), date=esc(n["date"]), title=esc(n["title"]),
        url=esc(source["url"]), label=esc(source["name"]),
        summary=esc(n.get("executiveSummary") or n.get("summary", "")),
        full="true" if n.get("audioFullTextEs") else "false",
        listen="Escuchar toda la noticia" if n.get("audioFullTextEs") else "Escuchar resumen",
        spanish='<span class="tts-lang" title="Narración editorial en español de una fuente publicada en inglés" lang="es">ES</span>' if n.get("sourceLanguage") == "en" and n.get("audioFullTextEs") else "",
    )


def build(data, page):
    news = sorted(
        (n for n in data["news"]
         if n.get("date") == data.get("editionDate")
         and n.get("verification") == "editorial_verified"),
        key=lambda n: n.get("priority", 999),
    )[:10]
    rendered = '<div class="cards" id="cards" aria-live="polite">' + "".join(
        article_html(n) for n in news
    ) + '</div>'
    begin = page.index('<div class="cards" id="cards" aria-live="polite">')
    end = page.index('<div class="empty" id="empty"', begin)
    page = page[:begin] + rendered + page[end:]
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
    marker = r'(<script type="application/json" id="initial-news">).*?(</script>)'
    page, count = re.subn(marker, lambda m: m.group(1) + encoded + m.group(2),
                          page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("No se localizó #initial-news")
    return page


def main():
    data = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    path = ROOT / "index.html"
    old = path.read_text(encoding="utf-8")
    new = build(data, old)
    if old != new:
        path.write_text(new, encoding="utf-8")
        print("Portada sobria sincronizada.")
    else:
        print("Sin cambios en portada.")


if __name__ == "__main__":
    main()
