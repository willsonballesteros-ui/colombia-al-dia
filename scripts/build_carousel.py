#!/usr/bin/env python3
"""Colombia al Día: carrusel sobrio, 12 láminas, SIN avatares ni dibujos.

1 portada + 10 noticias + 1 cierre. Usa fotos reales sólo si el registro
editorial demuestra crédito, fuente, licencia y derechos verificados.
En ausencia de estos requisitos, láminas 100% tipográficas.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from prepare_site import image_verified

W, H = 1080, 1350
NAVY = "#0C2966"
INK = "#1F2A40"
WHITE = "#FFFFFF"
CREAM = "#F8F9FC"
GOLD = "#E7BF65"
MUTED = "#546178"
FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(str(Path(FONT_DIR) / name), size)


def lines(draw, content, face, max_width, limit):
    words = str(content or "").split()
    result, current = [], ""
    for word in words:
        next_line = (current + " " + word).strip()
        if draw.textbbox((0, 0), next_line, font=face)[2] <= max_width:
            current = next_line
        else:
            if current:
                result.append(current)
            current = word
    if current:
        result.append(current)
    if len(result) > limit:
        result = result[:limit]
        while result[-1] and draw.textbbox((0, 0), result[-1] + "…", font=face)[2] > max_width:
            result[-1] = result[-1][:-1]
        result[-1] += "…"
    return result


def paragraph(d, text, x, y, face, color, width=940, max_lines=4, gap=10):
    for line in lines(d, text, face, width, max_lines):
        d.text((x, y), line, font=face, fill=color)
        y += face.size + gap
    return y


def base(day, n=None, category=None):
    im = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 218), fill=NAVY)
    d.rectangle((0, 0, W, 7), fill=GOLD)
    d.text((58, 43), "COLOMBIA AL DÍA", font=font(57, True), fill=WHITE)
    d.text((61, 136), "COLOMBIA  ·  MUNDO  ·  TECNOLOGÍA", font=font(22, True), fill=GOLD)
    d.text((800, 185), day[8:10]+"/"+day[5:7]+"/"+day[:4], font=font(19), fill=WHITE)
    if n is not None:
        d.text((62, 250), f"NOTICIA {n:02d} / 10", font=font(24, True), fill=NAVY)
        paragraph(d, category or "", 700, 250, font(22), MUTED, 330, 1)
    return im


def verified_photo(item, root):
    if not image_verified(item):
        return None
    # No descargar ni hotlinkear a la prensa sin comprobación documental.
    # Las fotos oficiales autorizadas deben existir ya en el repositorio.
    url = str(item["imageUrl"])
    if not url.startswith("./media/"):
        return None
    path = root / url[2:]
    if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        return path
    return None


def news_card(item, index, day, root, output):
    im = base(day, index, item["category"])
    d = ImageDraw.Draw(im)
    title_end = paragraph(d, item["title"], 63, 322, font(46, True), INK, 952, 4, 14)
    d.line((64, 580, 1015, 580), fill="#CFD8E4", width=3)
    picture = verified_photo(item, root)
    if picture:
        with Image.open(picture) as photo:
            fitted = ImageOps.fit(photo.convert("RGB"), (945, 243), method=Image.Resampling.LANCZOS)
            im.paste(fitted, (67, 606))
        d = ImageDraw.Draw(im)
        d.text((70, 862), "Foto: " + str(item["imageCredit"])[:55], font=font(17), fill=MUTED)
        sections = [
            (888, "QUÉ PASÓ", item.get("summary", ""), 2),
            (1011, "POR QUÉ IMPORTA", item.get("why", ""), 2),
            (1136, "QUÉ SIGUE", item.get("next", ""), 1),
        ]
        desc_size = 20
    else:
        sections = [
            (625, "QUÉ PASÓ", item.get("summary", ""), 4),
            (818, "POR QUÉ IMPORTA", item.get("why", ""), 4),
            (1008, "QUÉ SIGUE", item.get("next", ""), 3),
        ]
        desc_size = 26
    for start, heading, body, count in sections:
        d.text((67, start), heading, font=font(23, True), fill=NAVY)
        paragraph(d, body, 67, start+37, font(desc_size), INK, 943, count, 8)
    d.rectangle((0, 1268, W, H), fill=NAVY)
    main = item["sources"][0]
    source_name = str(main["name"])
    source_text = "FUENTE: " + source_name
    paragraph(d, source_text, 60, 1282, font(20, True), WHITE, 955, 1, 0)
    d.text((63, 1319), "Fuentes y enlaces completos en colombia-al-dia.pages.dev", font=font(16), fill=GOLD)
    im.save(output, optimize=True)


def cover(day, out):
    im = base(day)
    d = ImageDraw.Draw(im)
    d.text((66, 333), "10 NOTICIAS", font=font(84, True), fill=NAVY)
    d.text((69, 465), "EN UN SOLO LUGAR", font=font(44, True), fill=INK)
    paragraph(d, "Los hechos esenciales de Colombia y el mundo, explicados sin rodeos.",
              70, 605, font(38), INK, 910, 4, 16)
    d.line((70, 830, 1010, 830), fill=GOLD, width=5)
    paragraph(d, "¿Cuál de estas noticias te impacta más?",
              70, 886, font(39, True), NAVY, 930, 3, 18)
    d.text((73, 1138), "Desliza para conocer los hechos y sus fuentes.", font=font(24), fill=MUTED)
    im.save(out, optimize=True)


def closing(day, out):
    im = base(day)
    d = ImageDraw.Draw(im)
    d.text((70, 355), "INFORMACIÓN", font=font(66, True), fill=NAVY)
    d.text((70, 452), "CON FUENTES.", font=font(66, True), fill=NAVY)
    paragraph(d, "Consulta los enlaces originales y el detalle de cada noticia.",
              72, 640, font(35), INK, 915, 4, 15)
    d.line((71, 845, 1009, 845), fill=GOLD, width=5)
    d.text((74, 905), "ENLACE EN LA BIOGRAFÍA", font=font(35, True), fill=NAVY)
    d.text((74, 983), "colombia-al-dia.pages.dev", font=font(31), fill=INK)
    d.text((74, 1087), "@resumen.noticias", font=font(26), fill=MUTED)
    d.text((74, 1236), "¿Qué tema quieres que sigamos?", font=font(24, True), fill=NAVY)
    im.save(out, optimize=True)


def main():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root/"noticias.json").read_text(encoding="utf-8"))
    day = data["editionDate"]
    selected = sorted((n for n in data["news"]
                      if n.get("date") == day and n.get("verification") == "editorial_verified"),
                      key=lambda x: x.get("priority", 999))
    if len(selected) != 10 or len({n["id"] for n in selected}) != 10:
        raise RuntimeError("Se requieren diez noticias editoriales distintas")
    for n in selected:
        if not n.get("sources") or not n["sources"][0]["url"].startswith("https://"):
            raise RuntimeError("Cada noticia requiere una URL original real")
    out = root/"media"/day
    out.mkdir(parents=True, exist_ok=True)
    cover(day, out/"portada.png")
    for i, item in enumerate(selected, 1):
        news_card(item, i, day, root, out/f"top10-{i:02d}.png")
    closing(day, out/"cierre.png")
    # Historia informativa, sin iconografía inventada ni sticker falso.
    story = Image.new("RGB", (1080,1920), NAVY)
    d = ImageDraw.Draw(story)
    d.rectangle((0, 0, 1080, 14), fill=GOLD)
    d.text((76, 195), "COLOMBIA AL DÍA", font=font(70, True), fill=WHITE)
    d.text((78, 425), "10 NOTICIAS DEL DÍA", font=font(52, True), fill=GOLD)
    paragraph(d, "Datos, contexto y fuentes originales.",
              79, 625, font(45), WHITE, 925, 4, 18)
    d.text((80, 1280), "Consulta las fuentes en la web", font=font(36, True), fill=WHITE)
    d.text((80, 1370), "colombia-al-dia.pages.dev", font=font(34), fill=GOLD)
    d.text((81, 1530), "Sticker Enlace: añadir desde Instagram", font=font(20), fill="#CAD9F0")
    story.save(out/"historia.png", optimize=True)
    suggested = {
        "date": day, "publishedStickers": False,
        "note": "Sugerencias editoriales únicamente. Los stickers nativos deben añadirse y verificarse en la app de Instagram; Metricool no los inserta.",
        "stories": [
            {"sticker": "Enlace", "url": "https://colombia-al-dia.pages.dev/", "slide": "Portada"},
            {"sticker": "Encuesta", "question": "¿Qué noticia te impactó más?", "options": ["Colombia", "Mundo"]},
            {"sticker": "Cuestionario", "question": "¿Cuál tema seguimos?", "options": ["Economía", "IA", "Infraestructura"]},
        ],
    }
    (out/"sugerencias-stickers.json").write_text(
        json.dumps(suggested, ensure_ascii=False, indent=2)+"\n", encoding="utf-8"
    )
    print("Carrusel:", 12, "piezas (portada, 10 noticias, cierre); historia y guía de stickers.")


if __name__ == "__main__":
    main()
