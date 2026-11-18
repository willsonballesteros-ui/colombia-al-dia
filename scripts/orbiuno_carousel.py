#!/usr/bin/env python3
"""Generador de carrusel ORBIUNO: seis PNG de 1080x1350 desde el manifiesto.

Portada + cinco láminas. Usa SOLO la foto y el logotipo del manifiesto (nunca genera
imágenes de noticias). Si un texto no cabe, lanza TextOverflow (bloqueo): no recorta
ni abrevia en silencio. Sin etiquetas de categoría.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H = 1080, 1350
NAVY, NAVY2, ORANGE, WHITE = (9, 27, 71), (18, 52, 110), (255, 111, 15), (255, 255, 255)
MESES = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
FONT_BOLD = ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONT_REG = ["/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
SITE = "colombia-al-dia.pages.dev"


class TextOverflow(Exception):
    pass


def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    raise RuntimeError("no hay fuente TTF disponible (instalar fonts-dejavu-core)")


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if not cur:
                raise TextOverflow(f"palabra demasiado larga: {word!r}")
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit(draw, text, paths, max_w, max_lines, sizes):
    for s in sizes:
        f = _font(paths, s)
        lines = wrap(draw, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    raise TextOverflow(f"el texto no cabe en {max_lines} líneas: {text[:60]!r}")


def draw_block(d, xy, lines, font, fill, gap=1.18):
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=font, fill=fill)
        y += int(font.size * gap)
    return y


def gradient():
    img = Image.new("RGB", (W, H), NAVY)
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(NAVY[i] + (NAVY2[i] - NAVY[i]) * t) for i in range(3)))
    return img


def fmt_fecha(iso):
    y, m, d = iso.split("-")
    return f"{int(d)} {MESES[int(m) - 1]} {y}"


def fmt_hora(h):
    hh, mm = map(int, h.split(":"))
    return f"{hh % 12 or 12}:{mm:02d} {'a. m.' if hh < 12 else 'p. m.'}"


def wordmark(d, x, y, size=54, brand_logo=None, img=None):
    if brand_logo and Path(brand_logo).exists() and img is not None:
        lg = Image.open(brand_logo).convert("RGBA")
        lg.thumbnail((360, size + 20))
        img.paste(lg, (x, y), lg)
        return
    d.text((x, y), "ORBIUNO", font=_font(FONT_BOLD, size), fill=WHITE)


def pill(d, box, text, font, bg, fg):
    d.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=bg)
    tw = d.textlength(text, font=font)
    d.text(((box[0] + box[2] - tw) / 2, (box[1] + box[3]) / 2 - font.size * 0.62), text, font=font, fill=fg)


def cta(d, y):
    pill(d, (60, y, W - 60, y + 96), "", _font(FONT_BOLD, 10), WHITE, NAVY)
    f1, f2 = _font(FONT_REG, 28), _font(FONT_BOLD, 42)
    d.text((100, y + 8), "Escucha el desarrollo completo en voz alta en:", font=f1, fill=NAVY)
    d.text((100, y + 42), SITE, font=f2, fill=NAVY)


def cover(manifest, brand_logo):
    img = gradient()
    d = ImageDraw.Draw(img)
    wordmark(d, 60, 50, 70, brand_logo, img)
    pill(d, (700, 55, W - 60, 120), fmt_fecha(manifest["fecha"]), _font(FONT_BOLD, 36), WHITE, NAVY)
    pill(d, (740, 132, W - 60, 190), fmt_hora(manifest["hora"]), _font(FONT_BOLD, 34), ORANGE, WHITE)
    d.text((60, 230), "5", font=_font(FONT_BOLD, 250), fill=ORANGE)
    d.text((220, 250), "NOTICIAS", font=_font(FONT_BOLD, 110), fill=WHITE)
    d.text((220, 365), "DEL DÍA", font=_font(FONT_BOLD, 110), fill=WHITE)
    y = 520
    for n in manifest["noticias"]:
        f, lines = fit(d, n["titular"], FONT_BOLD, W - 230, 2, [42, 40, 38, 36])
        d.ellipse((60, y + 6, 112, y + 58), fill=ORANGE)
        d.text((72, y + 8), "✓", font=_font(FONT_BOLD, 40), fill=WHITE)
        y = max(draw_block(d, (140, y), lines, f, WHITE, 1.12), y + 62) + 26
    if y > 1180:
        raise TextOverflow("los cinco titulares no caben en la portada")
    d.text((60, 1195), "Desliza para ver cada noticia  →", font=_font(FONT_BOLD, 36), fill=ORANGE)
    cta(d, 1240)
    return img


def cover_crop(path, size):
    with Image.open(path) as im:
        return ImageOps.fit(im.convert("RGB"), size, Image.LANCZOS, centering=(0.5, 0.4))


def news_slide(manifest, idx, root, brand_logo):
    n = manifest["noticias"][idx]
    img = gradient()
    d = ImageDraw.Draw(img)
    wordmark(d, 40, 28, 44, brand_logo, img)
    d.text((W - 330, 40), fmt_fecha(manifest["fecha"]), font=_font(FONT_BOLD, 28), fill=WHITE)
    d.text((W - 110, 36), f"{idx + 1}/5", font=_font(FONT_BOLD, 38), fill=WHITE)
    ph_y, ph_h = 110, 690
    img.paste(cover_crop(Path(root) / n["foto"]["archivo"], (W - 40, ph_h)), (20, ph_y))
    fade = Image.new("RGBA", (W - 40, 260))
    fd = ImageDraw.Draw(fade)
    for yy in range(260):
        fd.line([(0, yy), (W, yy)], fill=NAVY + (int(235 * (yy / 260) ** 1.6),))
    img.paste(fade, (20, ph_y + ph_h - 260), fade)
    logo = Image.open(Path(root) / n["logo_fuente"]).convert("RGBA")
    logo.thumbnail((380, 130))
    tab = (20, ph_y, 20 + logo.size[0] + 70, ph_y + logo.size[1] + 40)
    d.rounded_rectangle(tab, radius=18, fill=WHITE)
    img.paste(logo, (tab[0] + 28, tab[1] + 20), logo)
    f, lines = fit(d, n["titular"], FONT_BOLD, W - 100, 3, [70, 64, 58, 52])
    ty = 790
    y = draw_block(d, (50, ty), lines, f, WHITE)
    d.rectangle((50, y + 14, 58, y + 14 + 150), fill=ORANGE)
    rf, rl = fit(d, n["resumen"], FONT_REG, W - 160, 4, [36, 34, 32, 30])
    y = draw_block(d, (84, y + 14), rl, rf, WHITE, 1.25)
    credit = f"Fuente: {n['fuente']}  ·  Foto: {n['foto']['credito']}"
    cf, cl = fit(d, credit, FONT_REG, W - 100, 1, [26, 24, 22, 20])
    cy = max(y + 14, 1180)
    if cy > 1210:
        raise TextOverflow("titular+resumen ocupan demasiado espacio en la lámina")
    d.text((50, cy), cl[0], font=cf, fill=(200, 212, 235))
    cta(d, 1240)
    return img


def build(edition, out=None, brand_logo=None):
    edition = Path(edition)
    manifest = json.loads((edition / "manifest.json").read_text(encoding="utf-8"))
    if len(manifest["noticias"]) != 5:
        raise ValueError("el carrusel exige cinco noticias")
    out = Path(out or edition)
    out.mkdir(parents=True, exist_ok=True)
    slides = [("portada.png", cover(manifest, brand_logo))]
    slides += [(f"noticia_{i + 1:02d}.png", news_slide(manifest, i, edition, brand_logo)) for i in range(5)]
    for name, im in slides:
        assert im.size == (W, H)
        im.save(out / name, "PNG", optimize=True)
    return [out / n for n, _ in slides]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--brand-logo", type=Path)
    a = ap.parse_args()
    try:
        for p in build(a.edition, a.out, a.brand_logo):
            print("OK", p)
    except Exception as exc:
        print("BLOQUEO:", exc, file=sys.stderr)
        sys.exit(1)
