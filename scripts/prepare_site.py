#!/usr/bin/env python3
"""Portada accesible de Colombia al Día, sin dibujos ni avatares.

La imagen se muestra SÓLO cuando una edición verificó su autoría,
procedencia y derechos de uso. En caso contrario, usar sólo tipografía.
"""
import html
import json
import re
from pathlib import Path


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


def article_html(n):
    sources = [s for s in n.get("sources", []) if str(s.get("url", "")).startswith("https://")]
    if not sources:
        return ""
    source = sources[0]
    extra = "".join(
        '<a class="source" target="_blank" rel="noopener noreferrer" href="{}">Otra fuente: {}</a>'.format(
            esc(s["url"]), esc(s["name"])
        ) for s in sources[1:]
    )
    return (
        '<article id="noticia-{id}" class="card">{photo}'
        '<div class="news-body"><div class="news-meta">'
        '<span class="news-chip">Top 10 · {cat}</span><time datetime="{date}">{date}</time>'
        '</div><h3>{title}</h3><p class="news-preview">{summary}</p>'
        '<div class="news-actions">'
        '<button type="button" class="listen-btn" data-tts-action="toggle" '
        'data-tts-id="{id}" aria-pressed="false" aria-label="Escuchar resumen de esta noticia">'
        '▶ Escuchar resumen</button>'
        '<button type="button" class="stop-btn" data-tts-action="stop" '
        'data-tts-id="{id}" aria-label="Detener la lectura de esta noticia" hidden>■ Detener</button>'
        '<a class="source" target="_blank" rel="noopener noreferrer" href="{url}">'
        'Ver fuente: {label}</a></div>'
        '<details class="news-more"><summary>Leer resumen completo</summary>'
        '<div class="explain"><strong>QUÉ PASÓ</strong><p>{summary}</p></div>'
        '<div class="explain"><strong>POR QUÉ IMPORTA</strong><p>{why}</p></div>'
        '<div class="explain"><strong>QUÉ SIGUE</strong><p>{next}</p></div>'
        '{extra}</details></div></article>'
    ).format(
        id=esc(n["id"]), photo=image_markup(n),
        cat=esc(n["category"]), date=esc(n["date"]), title=esc(n["title"]),
        url=esc(source["url"]), label=esc(source["name"]),
        summary=esc(n.get("summary", "")), why=esc(n.get("why", "")),
        next=esc(n.get("next", "")), extra=extra,
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
