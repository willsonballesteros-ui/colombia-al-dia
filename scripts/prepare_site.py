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
VALID_IMAGE_TYPES = {"official_photo", "licensed_press_photo", "official_document", "commons_licensed_photo"}


def image_verified(news):
    return (
        news.get("imageType") in VALID_IMAGE_TYPES
        and news.get("imageRightsVerified") is True
        and bool(news.get("imageLicense"))
        and bool(news.get("imageCredit"))
        and (str(news.get("imageSourceUrl", "")).startswith("https://")
             or str(news.get("imageSourceUrl", "")).startswith("./media/"))
        and (
            str(news.get("imageUrl", "")).startswith("https://")
            or str(news.get("imageUrl", "")).startswith("./media/")
        )
        and not str(news.get("imageUrl", "")).endswith(".svg")
    )


def esc(s):
    return html.escape(str(s or ""), quote=True)


def image_markup(n):
    """La imagen es un botón de visor; el crédito nunca navega a Drive."""
    if not image_verified(n):
        return ""
    return (
        '<figure class="news-photo"><button type="button" class="photo-open" '
        'data-photo-id="{id}" aria-label="Ampliar fotografía: {alt}">'
        '<img src="{url}" loading="lazy" decoding="async" alt="{alt}" width="320" height="180">'
        '<span class="photo-expand" aria-hidden="true">⤢</span></button>'
        '<figcaption>{caption}<br>{credit} · {license} · '
        '<a href="{source}" target="_blank" rel="noopener noreferrer">Origen de la fotografía</a>'
        '</figcaption></figure>'
    ).format(id=esc(n['id']), url=esc(n['imageUrl']),
             alt=esc(n.get('imageAlt') or n['title']),
             caption=esc(n.get('imageCaption') or 'Fotografía'),
             credit=esc(n['imageCredit']), license=esc(n['imageLicense']),
             source=esc(n['imageSourceUrl']))

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
        and (len(n["originalArticleTextEs"].strip()) >= 1000
             or (len(n["originalArticleTextEs"].strip()) >= 640
                 and len(n["originalArticleTextEs"].strip().split("\n\n")) >= 3))
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
        'data-tts-id="{id}" aria-label="Cambiar velocidad. Actual: 1x" '
        'title="Velocidad de lectura">1x</button>'
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
        + ''.join('<p>' + esc(p) + '</p>' for p in report.split('\n\n')) + '</details>'
        if n.get("verification") == "editorial_verified" and (authored or len(report.split()) >= 110) else ""
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



# Las páginas históricas permanecen accesibles por sus URL originales,
# pero la portada nunca debe anunciar como "de hoy" una edición anterior.
EDITION_TIMES = (
    ("21:00", "9:00 p. m."), ("20:00", "8:00 p. m."),
    ("19:00", "7:00 p. m."), ("18:00", "6:00 p. m."),
    ("17:00", "5:00 p. m."), ("12:00", "12:00 m."),
    ("10:00", "10:00 a. m."), ("09:30", "9:30 a. m."), ("08:00", "8:00 a. m."),
)


def bogota_today():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Bogota")).date().isoformat()


def replace_old_home_banners(page, data, day):
    """Reemplazar promociones estáticas y caducadas sin borrar el archivo."""
    # Estas tres bandas fueron codificadas a mano (17 y 18 de noviembre).
    page = re.sub(
        r'<div\s+role="region"\s+aria-label="Edición de hoy"[^>]*>.*?</div>',
        "", page, flags=re.S | re.I,
    )
    page = re.sub(
        r'<div\s+role="navigation"\s+aria-label="Ediciones de hoy"[^>]*>.*?</div>',
        "", page, flags=re.S | re.I,
    )
    # La siguiente ejecución es idempotente, no crea dos menús nuevos.
    page = re.sub(
        r'<section\s+id="orbiuno-current-editions"[^>]*>.*?</section>',
        "", page, flags=re.S | re.I,
    )
    rows = [
        n for n in data.get("news", [])
        if n.get("date") == day
        and n.get("verification") == "editorial_verified"
        and n.get("editionSlot") in dict(EDITION_TIMES)
    ]
    slots = [
        (slot, label, sum(n["editionSlot"] == slot for n in rows))
        for slot, label in EDITION_TIMES
        if any(n["editionSlot"] == slot for n in rows)
    ]
    badges = "".join(
        '<a href="#edicion-{slot}" style="display:inline-block;margin:5px;'
        'padding:10px 14px;background:#1b5675;color:#fff;border-radius:8px;'
        'text-decoration:none;font-size:16px;font-weight:700">'
        '{label} · {count} noticias</a>'.format(
            slot=esc(slot.replace(":", "")), label=esc(label), count=count)
        for slot, label, count in slots
    )
    if day == "2026-11-22" and (ROOT / "media/2026-11-22/correcciones-v2/ORBIUNO_2026-11-22_1800_6_NOTICIAS_CORREGIDA_V2.mp4").is_file():
        badges += ('<p style="margin:9px 0 0;font-size:14px">'
                   '<a style="color:#a3f7ed" href="./media/2026-11-22/correcciones-v2/ORBIUNO_2026-11-22_1800_6_NOTICIAS_CORREGIDA_V2.mp4">'
                   '▶ Ver video ORBIUNO corregido de las 6:00 p. m.</a></p>')
    if not badges:
        badges = ('<span style="display:block;margin:8px 0;color:#e8f5fa">'
                  'Todavía no hay ediciones verificadas para hoy.</span>')
    new = (
        '<section id="orbiuno-current-editions" aria-label="Ediciones verificadas de hoy" '
        'data-day="{day}" style="background:#103449;color:#fff;text-align:center;'
        'padding:14px 12px 16px;border-bottom:3px solid #55e3cf;'
        'font:16px/1.5 system-ui,sans-serif">'
        '<strong style="display:block;font-size:19px;margin-bottom:5px">'
        'Noticias de hoy · {day_label} · Colombia</strong>{badges}'
        '</section>'
    ).format(
        day=esc(day),
        day_label=esc(__import__("datetime").date.fromisoformat(day).strftime("%d/%m/%Y")),
        badges=badges,
    )
    if "<body>" not in page:
        raise ValueError("La portada no contiene la etiqueta <body>")
    return page.replace("<body>", "<body>" + new, 1)


def fix_today_frontend(page):
    """La vista en el navegador también debe calcular HOY, no la última fecha del JSON."""
    # Las noticias se mantienen en el JSON para auditoría/historial, nunca
    # como si fueran publicadas hoy al cambiar de día en Bogotá.
    page = page.replace(
        "selectedDate==='today'?x.date===db.editionDate&&x.verification==='editorial_verified'",
        "selectedDate==='today'?x.date===today()&&x.verification==='editorial_verified'",
    )
    page = page.replace(
        "el('foot-date').textContent='Fuentes y edición: '+fmt(db.editionDate)+'.';",
        "el('foot-date').textContent='Fuentes y fecha: '+fmt(today())+'.';",
    )
    old_slots = (
        "const slots=[['08:00','8:00 a. m.'],['12:00','12:00 m.'],"
        "['18:00','6:00 p. m.']];\n"
        "  if(matching.some(x=>x.editionSlot==='20:00')) slots.unshift(['20:00','8:00 p. m.']);\n"
        "  if(matching.some(x=>x.editionSlot==='21:00')) slots.unshift(['21:00','9:00 p. m.']);"
    )
    all_slots = (
        "const slots=[['21:00','9:00 p. m.'],['20:00','8:00 p. m.'],"
        "['19:00','7:00 p. m.'],['18:00','6:00 p. m.'],"
        "['17:00','5:00 p. m.'],['12:00','12:00 m.'],"
        "['10:00','10:00 a. m.'],['09:30','9:30 a. m.'],['08:00','8:00 a. m.']];"
    )
    page = page.replace(old_slots, all_slots)
    page = page.replace(
        "(visible.length?visible:slots.slice(0,1))",
        "visible",  # No inventar una franja 8:00 si hoy todavía no hay noticias.
    )
    page = page.replace("const maxReel=4;", "const maxReel=6;")
    page = page.replace(
        "esc(fmt(db.editionDate))+'</small>",
        "esc(fmt(today()))+'</small>",
    )
    old_edition_items = (
        "n.date===db.editionDate&&n.verification==='editorial_verified'&&"
        "['21:00','20:00','08:00','12:00','18:00'].includes(n.editionSlot)"
    )
    page = page.replace(
        old_edition_items,
        "n.date===today()&&n.verification==='editorial_verified'&&"
        "['21:00','20:00','19:00','18:00','17:00','12:00','10:00','09:30','08:00'].includes(n.editionSlot)",
    )
    page = page.replace(
        "['21:00','20:00','08:00','12:00','18:00'].indexOf(a.editionSlot)-"
        "['21:00','20:00','08:00','12:00','18:00'].indexOf(b.editionSlot)",
        "['21:00','20:00','19:00','18:00','17:00','12:00','09:30','08:00'].indexOf(a.editionSlot)-"
        "['21:00','20:00','19:00','18:00','17:00','12:00','09:30','08:00'].indexOf(b.editionSlot)",
    )
    page = page.replace(
        "setInterval(loadFeed,300000);",
        "setInterval(()=>{loadFeed();if(selectedDate==='today')render();},300000);",
    )
    # Si la pestaña permanece abierta durante la medianoche, renovar también
    # los enlaces de edición del encabezado sin mostrar enlaces de ayer.
    if "const refreshEditionNav=()=>{" not in page and "const render=()=>{" in page:
        dynamic_nav = (
            "const refreshEditionNav=()=>{"
            "const nav=el('orbiuno-current-editions');if(!nav)return;"
            "const day=today();"
            "const times=[['21:00','9:00 p. m.'],['20:00','8:00 p. m.'],"
            "['19:00','7:00 p. m.'],['18:00','6:00 p. m.'],"
            "['17:00','5:00 p. m.'],['12:00','12:00 m.'],"
            "['09:30','9:30 a. m.'],['08:00','8:00 a. m.']];"
            "const verified=db.news.filter(x=>x.date===day&&x.verification==='editorial_verified');"
            "const links=times.map(([slot,label])=>{const count=verified.filter(x=>x.editionSlot===slot).length;"
            "return count?'<a href=\"\\u0023edicion-'+slot.replace(':','')+'\" "
            "style=\"display:inline-block;margin:5px;padding:10px 14px;background:#1b5675;"
            "color:#fff;border-radius:8px;text-decoration:none;font-size:16px;font-weight:700\">'"
            "+label+' · '+count+' noticias</a>':'';}).filter(Boolean).join('');"
            "nav.dataset.day=day;"
            "nav.innerHTML='<strong style=\"display:block;font-size:19px;margin-bottom:5px\">'"
            "+'Noticias de hoy · '+fmt(day)+' · Colombia</strong>'+"
            "(links||'<span>Hoy todavía no hay ediciones verificadas.</span>');"
            "};\n"
        )
        page = page.replace("const render=()=>{",
                            dynamic_nav + "const render=()=>{refreshEditionNav();", 1)
    if "['10:00','10:00 a. m.']" not in page:
        page = page.replace("['09:30','9:30 a. m.']", "['10:00','10:00 a. m.'],['09:30','9:30 a. m.']")
    if "['10:00','09:30'" not in page:
        page = page.replace("['09:30','08:00']", "['10:00','09:30','08:00']")
    # Texto honesto cuando la nueva edición aún no ha sido importada.
    page = page.replace(
        '<option value="today">Últimas noticias publicadas</option>',
        '<option value="today">Noticias de hoy</option>',
    )
    return page


def build(data, page, *, as_of=None):
    """Mantener las tres franjas verificadas, con fotos y lectura, en UNA portada."""
    # Evitar que el botón lea una sinopsis cuando existe la redacción integral
    # propia, revisada y autorizada de ORBIUNO. Compartir el MISMO texto entre
    # la vista desarrollada y el reproductor (incluido el fallback nativo).
    from copy import deepcopy
    try:
        from scripts.narration_body import narration_for
    except ModuleNotFoundError:
        from narration_body import narration_for
    data = deepcopy(data)
    for news in data.get("news", []):
        if news.get("verification") == "editorial_verified":
            body = narration_for(news, original_article_ready)
            if body:
                news["audioFullTextEs"] = body
                if original_article_ready(news):
                    news["originalArticleTextEs"] = body
    today = as_of or bogota_today()
    published=[
        n for n in data["news"]
        if n.get("date")==today
        and n.get("verification")=="editorial_verified"
        and n.get("editionSlot") in ("08:00","09:30","10:00","12:00","17:00","18:00","19:00","20:00","21:00")
    ]
    slots=(("08:00","8:00 a. m."),("12:00","12:00 m."),("18:00","6:00 p. m."))
    if any(n.get("editionSlot") == "10:00" for n in published):
        slots=(("10:00","10:00 a. m. · Edición del día"),)+slots
    if any(n.get("editionSlot") == "09:30" for n in published):
        slots=(("09:30","9:30 a. m. · Edición corregida"),)+slots
    if any(n.get("editionSlot") == "17:00" for n in published):
        slots=(("17:00","5:00 p. m. · Edición extraordinaria"),)+slots
    if any(n.get("editionSlot") == "19:00" for n in published):
        slots=(("19:00","7:00 p. m."),)+slots
    if any(n.get("editionSlot") == "21:00" for n in published):
        slots=(("21:00","9:00 p. m."),)+slots
    if any(n.get("editionSlot") == "20:00" for n in published):
        slots=(("20:00","8:00 p. m."),)+slots
    # Ocultar franjas vacías cuando existe una edición extraordinaria verificable.
    # Si no hay ninguna, conservar un único aviso honesto y no tres franjas antiguas.
    active_slots=[pair for pair in slots if any(n.get("editionSlot")==pair[0] for n in published)]
    slots=tuple(active_slots)
    sections=[]
    reel_limits={"08:00":6,"09:30":6,"10:00":6,"12:00":6,"17:00":6,"18:00":6,"19:00":6,"20:00":6,"21:00":6}
    for slot,label in slots:
        rows=sorted((n for n in published if n.get("editionSlot")==slot),
                    key=lambda n:n.get("priority",999))
        # Solo se etiqueta "del Reel" cuando los IDs y orden se consignaron
        # explícitamente al publicar Instagram. No deducirlo por prioridad.
        featured=sorted(
            (n for n in rows if isinstance(n.get("instagramReelOrder"),int)
             and not isinstance(n.get("instagramReelOrder"),bool)
             and n.get("instagramReelOrder")>0),
            key=lambda n:n["instagramReelOrder"]
        )[:reel_limits[slot]]
        featured_ids={n["id"] for n in featured}
        more=[n for n in rows if n["id"] not in featured_ids]
        content=""
        if featured:
            content+=(
                '<h4 class="edition-subheading">📌 Noticias del Reel · En el mismo orden de Instagram</h4>'
                '<div class="cards edition-cards">'+''.join(article_html(n) for n in featured)+'</div>'
            )
        if more:
            title=('🔎 Más noticias verificadas · Cobertura ampliada' if featured
                   else 'Noticias verificadas de esta edición')
            content+=(
                '<h4 class="edition-subheading">'+title+'</h4>'
                '<div class="cards edition-cards">'+''.join(article_html(n) for n in more)+'</div>'
            )
        if not rows:
            content='<p class="edition-empty">No hay noticias verificadas cargadas para esta franja.</p>'
        sections.append(
            '<section class="edition-section" id="edicion-'+slot.replace(":","")+'">'
            '<h3 class="edition-heading"><span>Edición de las '+label+'</span>'
            '<small>'+str(len(rows))+' noticias verificadas</small></h3>'
            +content+'</section>'
        )
    # El contenedor #cards se conserva para búsquedas y filtrado de histórico;
    # las tres ediciones son el contenido visible inicial de la portada.
    begin=page.index('<div id="ediciones-hoy"')
    finish=page.index('<div class="empty" id="empty"',begin)
    page=page[:begin]+(
       '<div id="ediciones-hoy" aria-label="Publicaciones del día">'
       +''.join(sections)+'</div>'
       '<div class="cards" id="cards" aria-live="polite"></div>'
    )+page[finish:]
    encoded=json.dumps(data,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")
    marker=r'(<script type="application/json" id="initial-news">).*?(</script>)'
    page,count=re.subn(marker,lambda m:m.group(1)+encoded+m.group(2),page,count=1,flags=re.S)
    if count!=1:
        raise ValueError("No se localizó #initial-news")
    # Quitar los enlaces históricos que aparecían arriba de la portada.
    page = replace_old_home_banners(page, data, today)
    page = fix_today_frontend(page)
    # El SEO debe describir seis noticias por edición, no el formato anterior.
    page=page.replace("Diez noticias verificadas con fuentes originales.",
                      "Seis noticias por edición, con fuentes originales.")
    # El botón de fotografía abre un visor local, separado de la fuente.
    # Nunca debe enviar al repositorio ni a un Drive del editor.
    photo_loader = '<script defer src="./photo-viewer.js?v=20261113c"></script>'
    if photo_loader not in page:
        if '</head>' not in page:
            raise ValueError("No se localizó cierre del encabezado HTML")
        page = page.replace('</head>', photo_loader + '\n</head>', 1)
    # Reparación de reproducción en Safari/iPhone: cargar el reproductor
    # local con MP3 y voz nativa de respaldo, sin abrir fuentes externas.
    # Se inserta una única vez para mantener idempotencia del generador.
    audio_loader = '<script defer src="./audio-fix.js?v=20261113b"></script>'
    if audio_loader not in page:
        if '</head>' not in page:
            raise ValueError("No se localizó cierre del encabezado HTML")
        page = page.replace('</head>', audio_loader + '\n</head>', 1)
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
