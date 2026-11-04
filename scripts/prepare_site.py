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
    # El contenido estático NO incluye titulares RSS pendientes de verificación.
    articles = []
    for n in news[:10]:
        source_links = "".join(
            '<a class="source" target="_blank" rel="noopener noreferrer" href="{}">Ver fuente: {}</a> '.format(
                html.escape(s["url"], quote=True), html.escape(s["name"])
            )
            for s in n.get("sources", [])
            if s.get("url", "").startswith("https://")
        )
        articles.append(
            '<article id="noticia-{}" class="card"><h3>{}</h3><p>{}</p><p><strong>Por qué importa:</strong> {}</p><a class="source" href="#noticia-{}">Enlace directo a esta noticia</a> {}</article>'.format(
                html.escape(n["id"], quote=True), html.escape(n["title"]), html.escape(n["summary"]), html.escape(n["why"]), html.escape(n["id"], quote=True), source_links
            )
        )

    rendered = '<div class="cards" id="cards" aria-live="polite">' + "".join(articles) + "</div>"
    marker = r'<div class="cards" id="cards" aria-live="polite">.*?</div>'
    page, count = re.subn(marker, lambda _: rendered, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("No se localizó #cards para insertar noticias iniciales")

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
