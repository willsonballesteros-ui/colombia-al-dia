#!/usr/bin/env python3
"""Genera contenido HTML inicial legible, usando noticias verificadas y el JSON existente.

No valida hechos ni publica en redes: solo sincroniza el HTML de respaldo con
la edición contrastada. El JavaScript del portal mantiene búsqueda y filtros.
"""
import html
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build(data: dict, page: str) -> str:
    news = [
        n for n in data["news"]
        if n.get("date") == data.get("editionDate")
        and n.get("verification") == "editorial_verified"
    ]
    news.sort(key=lambda x: x.get("priority", 999))
    # Precarga SEO sin JS: sólo la edición verificada.
    articles = []
    for n in news[:10]:
        sid = html.escape(n["id"], quote=True)
        title = html.escape(n["title"])
        cat = html.escape(n["category"])
        day = html.escape(n["date"])
        image = html.escape(n.get("imageUrl", "./branding/orbiuno-icono.svg"), quote=True)
        source = n["sources"][0]
        href = html.escape(source["url"], quote=True)
        label = html.escape(source["name"])
        extra = "".join(
            '<a class="source" href="{}" target="_blank" rel="noopener noreferrer">Otra fuente: {}</a>'.format(
                html.escape(s["url"], quote=True), html.escape(s["name"])
            ) for s in n["sources"][1:]
        )
        articles.append(
            '<article id="noticia-{id}" class="card">'
            '<img class="news-image" src="{image}" loading="lazy" width="1080" height="600" '
            'alt="Ilustración editorial de {cat}; no es una fotografía del hecho">'
            '<div class="news-body">'
            '<div class="news-meta"><span class="news-chip">Top 10 · {cat}</span><time datetime="{day}">{day}</time></div>'
            '<h3>{title}</h3>'
            '<p class="news-preview">{summary}</p>'
            '<div class="news-actions">'
            '<button type="button" class="listen-btn" data-tts-action="toggle" data-tts-id="{id}" '
            'aria-pressed="false" aria-label="Escuchar resumen de esta noticia">▶ Escuchar resumen</button>'
            '<button type="button" class="stop-btn" data-tts-action="stop" data-tts-id="{id}" '
            'aria-label="Detener la lectura de esta noticia" hidden>■ Detener</button>'
            '<a class="source" href="{href}" target="_blank" rel="noopener noreferrer">Ver fuente: {label}</a>'
            '</div><details class="news-more"><summary>Leer resumen completo</summary>'
            '<div class="explain"><strong>QUÉ PASÓ</strong><p>{summary}</p></div>'
            '<div class="explain"><strong>POR QUÉ IMPORTA</strong><p>{why}</p></div>'
            '<div class="explain"><strong>QUÉ SIGUE</strong><p>{next}</p></div>{extra}'
            '</details></div></article>'.format(
                id=sid, image=image, cat=cat, day=day, title=title,
                href=href, label=label, summary=html.escape(n.get("summary", "")),
                why=html.escape(n.get("why", "")), next=html.escape(n.get("next", "")),
                extra=extra
            )
        )
    rendered = '<div class="cards" id="cards" aria-live="polite">' + "".join(articles) + '</div>'
    start = page.index('<div class="cards" id="cards" aria-live="polite">')
    finish = page.index('<div class="empty" id="empty"', start)
    page = page[:start] + rendered + page[finish:]

    # Escapar < para impedir cierre de script en contenido de terceros.
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", r"\u003c")
    marker = r'(<script type="application/json" id="initial-news">).*?(</script>)'
    page, count = re.subn(marker, lambda m: m.group(1) + encoded + m.group(2), page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("No se localizó #initial-news")
    # Mostrar el video como HTML inicial cuando el MP4 ya existe.
    # No depender del JavaScript para que el lector vea el reproductor.
    day = data["editionDate"]
    video = ROOT / "media" / day / "boletin-narrado.mp4"
    if 'id="boletin-video"' in page:
        if video.is_file():
            page = page.replace('id="boletin-video" hidden', 'id="boletin-video"')
        else:
            page = page.replace('id="boletin-video" style', 'id="boletin-video" hidden style')
        page = re.sub(
            r'<span id="boletin-date">[^<]*</span>',
            '<span id="boletin-date">' + day + '</span>', page, count=1
        )
        def set_video(m):
            source = re.sub(r'\s(?:src|poster)="[^"]*"', '', m.group(0))
            if video.is_file():
                source = source.replace(
                    '<video ', f'<video src="./media/{day}/boletin-narrado.mp4" poster="./media/{day}/historia-orbiuno.png" ', 1
                )
            return source
        page = re.sub(r'<video[^>]*id="boletin-player"[^>]*></video>', set_video, page, count=1)
    return page


def main():
    data = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    changed = False
    for item in data.get("news", []):
        pr = item.get("priority")
        if (item.get("date") == data.get("editionDate")
            and item.get("verification") == "editorial_verified"
            and isinstance(pr, int) and 1 <= pr <= 10):
            image_path = "./media/{}/visual-{:02d}.png".format(item["date"], pr)
            if item.get("imageUrl") != image_path:
                item["imageUrl"] = image_path
                changed = True
            if item.get("imageType") != "ilustracion_editorial":
                item["imageType"] = "ilustracion_editorial"
                changed = True
    if changed:
        (ROOT / "noticias.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    path = ROOT / "index.html"
    current = path.read_text(encoding="utf-8")
    rendered = build(data, current)
    if rendered != current:
        path.write_text(rendered, encoding="utf-8")
        print("Portada inicial y edición sincronizadas.")
    else:
        print("Portada ya sincronizada.")


if __name__ == "__main__":
    main()
