#!/usr/bin/env python3
"""ORBIUNO: portada para Reel + 10 láminas Instagram, lectura en ~3 segundos.

Nunca inventa imágenes de los hechos: foto con licencia y crédito o
sección visual tipográfica de la fuente claramente identificada.
Un Reel hablado debe generarse por el pipeline audiovisual independiente.
"""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from prepare_site import image_verified

W, H = 1080, 1350
NAVY, INK, PAPER, GOLD, MUTED = "#081D49", "#1E293C", "#FBFCFE", "#E3B45C", "#59677B"
ROOT = Path(__file__).resolve().parents[1]
FONTS = Path("/usr/share/fonts/truetype/dejavu")


def font(size, bold=False):
    return ImageFont.truetype(str(FONTS / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def fit_lines(d, text, face, width, limit):
    out, current = [], ""
    for word in str(text or "").split():
        trial = (current + " " + word).strip()
        if d.textbbox((0, 0), trial, font=face)[2] <= width:
            current = trial
        else:
            if current: out.append(current)
            current = word
    if current: out.append(current)
    if len(out) > limit:
        out = out[:limit]
        while out[-1] and d.textbbox((0, 0), out[-1]+"…", font=face)[2] > width:
            out[-1] = out[-1][:-1]
        out[-1] += "…"
    return out


def paragraph(d, text, x, y, face, color, width=930, max_lines=4, gap=9):
    for line in fit_lines(d, text, face, width, max_lines):
        d.text((x, y), line, font=face, fill=color)
        y += face.size + gap
    return y


def bg():
    im = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 180), fill=NAVY)
    d.rectangle((0, 0, W, 10), fill=GOLD)
    d.text((66, 30), "ORBIUNO", font=font(66, True), fill="white")
    d.text((70, 122), "COLOMBIA AL DÍA  ·  NOTICIAS", font=font(22, True), fill=GOLD)
    return im


def photo_path(note):
    if not image_verified(note): return None
    url = str(note["imageUrl"])
    if not url.startswith("./media/"): return None
    path = ROOT / url[2:]
    return path if path.is_file() and path.suffix.lower() in (".png",".jpg",".jpeg",".webp") else None


def news_card(note, i, day, output):
    im = bg()
    d = ImageDraw.Draw(im)
    d.text((70, 219), f"{i:02d} / 10     {note['category'].upper()}", font=font(24, True), fill=MUTED)
    picture = photo_path(note)
    if picture:
        with Image.open(picture) as src:
            im.paste(ImageOps.fit(src.convert("RGB"), (946, 340), method=Image.Resampling.LANCZOS), (66, 284))
        d = ImageDraw.Draw(im)
        paragraph(d, "FOTO: "+str(note["imageCredit"]), 70, 632, font(17), MUTED, 900, 1, 0)
    else:
        # Identificación tipográfica de procedencia, NO logotipo oficial ni
        # fotografía sintética; se deja claro qué medio reportó la noticia.
        d.rounded_rectangle((66, 282, 1014, 622), radius=18, fill="#E8EFF8")
        d.text((102, 333), "INFORMACIÓN REPORTADA POR", font=font(24, True), fill=MUTED)
        paragraph(d, note["sources"][0]["name"], 101, 411, font(54, True), NAVY, 866, 3, 16)
    end = paragraph(d, note["title"], 72, 704, font(50, True), INK, 925, 4, 13)
    d.line((74, 973, 1008, 973), fill="#DCE4EE", width=2)
    paragraph(d, note.get("executiveSummary") or note.get("summary") or "", 74, 1003,
              font(30), INK, 930, 3, 13)
    d.rectangle((0, 1244, W, H), fill=NAVY)
    paragraph(d, "FUENTE: "+str(note["sources"][0]["name"]), 65, 1261, font(21, True), "white", 950, 1, 0)
    d.text((65, 1303), "Fuente original: colombia-al-dia.pages.dev", font=font(18), fill=GOLD)
    im.save(output, optimize=True)


def cover(day, output):
    im = bg()
    d = ImageDraw.Draw(im)
    paragraph(d, "10 NOTICIAS", 69, 343, font(90, True), NAVY, 930, 2, 12)
    paragraph(d, "en menos tiempo.", 72, 492, font(50, True), INK, 920, 2, 12)
    d.line((73, 672, 1006, 672), fill=GOLD, width=5)
    paragraph(d, "Colombia, economía, inteligencia artificial y mundo.", 74, 727, font(35), INK, 915, 3, 16)
    paragraph(d, "Desliza y consulta las fuentes originales.", 74, 1084, font(30, True), NAVY, 920, 2, 14)
    d.text((74, 1249), day[8:10]+"/"+day[5:7]+"/"+day[:4]+"  ·  @resumen.noticias",
           font=font(24), fill=MUTED)
    im.save(output, optimize=True)


def main():
    db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=db["editionDate"]
    news=sorted((x for x in db["news"] if x.get("date")==day and
                 x.get("verification")=="editorial_verified"),key=lambda x:x.get("priority",999))
    if len(news)!=10 or len({x["id"] for x in news})!=10:
        raise RuntimeError("Se requieren diez hechos distintos contrastados")
    for x in news:
        if not x.get("sources") or not x["sources"][0]["url"].startswith("https://"):
            raise RuntimeError("Falta fuente original HTTPS")
    out=ROOT/"media"/day
    out.mkdir(parents=True,exist_ok=True)
    cover(day,out/"portada.png")
    for i,n in enumerate(news,1):
        news_card(n,i,day,out/f"top10-{i:02d}.png")
    # No se crea un video de una persona que no existe.
    # portada.png NO va en el carrusel: Instagram permite un máximo de 10 elementos.
    print("10 láminas para carrusel Instagram + portada visual para Reel. Sin imágenes ficticias.")


if __name__=="__main__":
    main()
