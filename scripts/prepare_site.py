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
        '<figure class="news-photo"><button type="button" class="photo-open" '
        'data-photo-id="{id}" aria-label="Ampliar fotografía: {alt}">'
        '<img src="{url}" loading="lazy" decoding="async" alt="{alt}" width="320" height="180">'
        '<span class="photo-expand" aria-hidden="true">⤢</span></button>'
        '<figcaption>{caption}<br><a href="{origin}" target="_blank" rel="noopener noreferrer">'
        '{credit}</a> · {license}</figcaption></figure>'
    ).format(id=esc(n['id']),url=esc(n['imageUrl']),alt=esc(n.get('imageAlt') or n['title']),
             caption=esc(n.get('imageCaption') or 'Fotografía'),origin=esc(n['imageSourceUrl']),
             credit=esc(n['imageCredit']),license=esc(n['imageLicense']))


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
        '<span class="source-thumbnail-name">{label}</span>'
        '<a class="source" target="_blank" rel="noopener noreferrer" href="{url}" title="Abrir fuente original: {label}">Fuente ↗</a></div>'
    ).format(icon=esc(icon_url), label=esc(label), url=esc(sources[0]["url"]))


def article_original_authorized(n):
    """El texto ÍNTEGRO del proveedor requiere permiso explícito y trazable."""
    sources = [s.get("url") for s in n.get("sources", [])]
    article_url = n.get("fullArticleSourceUrl")
    lang = n.get("sourceLanguage", "es")
    return (
        bool(n.get("fullArticleTextEs"))
        and n.get("fullArticleRightsVerified") is True
        and n.get("fullArticleIsVerbatimSource") is True
        and bool(n.get("fullArticleLicense"))
        and article_url in sources
        and (lang != "en" or n.get("fullArticleTranslationAuthorized") is True)
    )


def original_article_ready(n):
    """Un reportaje íntegro de ORBIUNO: texto propio, fuente y revisión."""
    sources = {s.get("url") for s in n.get("sources", [])}
    return (
        n.get("verification") == "editorial_verified"
        and n.get("originalArticleByline") == "Redacción ORBIUNO"
        and n.get("originalArticleReviewed") is True
        and isinstance(n.get("originalArticleTextEs"), str)
        and len(n["originalArticleTextEs"].strip()) >= 1000
        and isinstance(n.get("originalArticleSourceUrls"), list)
        and bool(n["originalArticleSourceUrls"])
        and all(url in sources for url in n["originalArticleSourceUrls"])
    )


def has_complete_audio(n):
    return article_original_authorized(n) or original_article_ready(n)


def article_html(n):
    sources = [s for s in n.get("sources", []) if str(s.get("url", "")).startswith("https://")]
    if not sources:
        return ""
    source = sources[0]
    complete = has_complete_audio(n)
    authored = original_article_ready(n)
    thumbnail = (image_markup(n) + source_thumbnail(n)) if image_verified(n) else source_thumbnail(n)
    # El audio SIEMPRE se queda en ORBIUNO: íntegro licenciado o resumen.
    label = ("Escuchar completo" if complete else
             "Escuchar noticia" if len(str(n.get("audioFullTextEs") or "").split()) >= 110
             else "Escuchar resumen")
    player_controls = (
        '<button type="button" class="listen-btn" data-tts-action="toggle" '
        'data-tts-id="{id}" data-tts-full="{authorized}" aria-pressed="false" '
        'aria-label="{label}" title="{tip}">▶ {label}</button>'
        '<button type="button" class="speed-btn" data-tts-action="speed" '
        'data-tts-id="{id}" aria-label="Cambiar velocidad. Actual: 1.25x" '
        'title="Velocidad de lectura">1.25x</button>'
        '<button type="button" class="stop-btn" data-tts-action="stop" '
        'data-tts-id="{id}" aria-label="Detener lectura" hidden>■</button>'
    ).format(
        id=esc(n["id"]), authorized="true" if complete else "false",
        label=label,
        tip=("Escuchar artículo íntegro de la redacción ORBIUNO" if authored
             else "Reproducir artículo íntegro de la fuente con licencia" if complete
             else "Escuchar narración original de ORBIUNO sin salir de la página"),
    )
    report = str(n.get("audioFullTextEs") or "").strip()
    transcript = (
        '<details class="news-transcript"><summary>Leer noticia desarrollada</summary>'
        '<p>' + esc(report) + '</p></details>'
        if n.get("verification") == "editorial_verified" and len(report.split()) >= 110 else ""
    )
    return (
        '<article id="noticia-{id}" class="card compact-card">'
        '<div class="visual-frame{photo_class}">{thumbnail}</div>'
        '<div class="news-body"><div class="news-meta">'
        '<span class="news-chip">{cat}</span><time datetime="{date}">{date}</time>'
        '</div><h3>{title}</h3><p class="news-preview">{summary}</p>'
        '<div class="news-actions">{controls}{article_tag}'
        '</div>{transcript}</div></article>'
    ).format(
        transcript=transcript,
        id=esc(n["id"]), thumbnail=thumbnail, photo_class=" has-photo" if image_verified(n) else "", controls=player_controls,
        article_tag='<span class="original-full-tag" title="Artículo completo redactado por ORBIUNO; fuente enlazada aparte">ORBIUNO</span>' if authored else "",
        cat=esc(n.get("category", "")), date=esc(n["date"]), title=esc(n["title"]),
        url=esc(source["url"]), label=esc(source["name"]),
        summary=esc(n.get("executiveSummary") or n.get("summary", "")),
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
