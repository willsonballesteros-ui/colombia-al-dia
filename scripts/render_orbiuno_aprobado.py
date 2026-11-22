#!/usr/bin/env python3
"""Render seguro de seis noticias, con fotos Commons, logos y voz colombiana.

Se niega a sustituir fotos por tarjetas o voz por Kokoro. No publica en Meta.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
W, H = 1080, 1920
INK = "#091D36"
GOLD = "#FFCE63"
WHITE = "#FFFFFF"
TEAL = "#55E3CF"
FONT = Path("/usr/share/fonts/truetype/dejavu")
VOICE = "es-CO-SalomeNeural"
TEMPO = 1.25


def font(size, bold=True):
    return ImageFont.truetype(str(FONT / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)


def wrapped(draw, value, *, width, size, max_lines):
    f = font(size)
    lines = []
    line = ""
    for word in str(value).split():
        proposed = (line + " " + word).strip()
        if draw.textbbox((0, 0), proposed, font=f)[2] > width and line:
            lines.append(line)
            line = word
        else:
            line = proposed
    if line:
        lines.append(line)
    if len(lines) > max_lines:
        raise ValueError("El titular desborda la lámina; no truncar: " + str(value)[:65])
    return lines


def header(d, day, slot):
    d.rectangle((0, 0, W, 208), fill=INK)
    d.rectangle((0, 0, W, 15), fill=TEAL)
    d.text((55, 35), "ORBIUNO", font=font(70), fill=WHITE)
    date_label = datetime.fromisoformat(day).strftime("%d/%m/%Y")
    d.text((60, 128), date_label + "  ·  " + slot + " HORA COLOMBIA",
           font=font(34), fill=GOLD)


def draw_cover(news, day, slot, path, principal_photo):
    """Foto protagonista: la portada conserva >65 % de altura fotográfica."""
    with Image.open(principal_photo) as original:
        actual = original.convert("RGB")
        if actual.width < 650 or actual.height < 450:
            raise RuntimeError("Portada sin foto real de resolución suficiente")
        # Imagen de fondo a pantalla completa para evitar bandas gigantes.
        photo = ImageOps.fit(actual, (W, H), method=Image.Resampling.LANCZOS)
    img = photo.copy()
    d = ImageDraw.Draw(img)
    # Marca estrecha y fecha legible sin tapar el motivo fotográfico.
    d.rectangle((0, 0, W, 148), fill=INK)
    d.rectangle((0, 0, W, 11), fill=TEAL)
    d.text((50, 35), "ORBIUNO", font=font(59), fill=WHITE)
    date_label = datetime.fromisoformat(day).strftime("%d/%m/%Y")
    d.rounded_rectangle((54, 187, 715, 296), radius=17, fill=INK)
    d.text((75, 204), f"{date_label} · {slot} CO", font=font(42), fill=GOLD)
    # Solo un titular principal: los otros cinco se presentan en sus láminas.
    # Panel de 400 px frente a los 840 px del diseño anterior.
    d.rectangle((0, 1470, W, H), fill=INK)
    d.rectangle((0, 1470, W, 1483), fill=TEAL)
    d.text((58, 1505), "EDICIÓN INFORMATIVA · 6 NOTICIAS", font=font(30), fill=GOLD)
    for size in (58, 54, 50, 46, 42, 38):
        try:
            lines = wrapped(d, news[0]["title"], width=965, size=size, max_lines=3)
            break
        except ValueError:
            continue
    else:
        raise RuntimeError("Titular de portada demasiado largo")
    for k, line in enumerate(lines):
        d.text((58, 1570 + k * (size + 11)), line, font=font(size), fill=WHITE)
    d.text((58, 1820), "Y OTRAS CINCO NOTICIAS", font=font(29), fill=GOLD)
    d.text((58, 1870), "colombia-al-dia.pages.dev", font=font(24), fill="#B9D2E4")
    img.save(path, quality=91)


def draw_story(news, ent, assets, day, slot, pos, path):
    photo_path = assets / ent["photoFile"]
    logo_path = assets / ent["logoFile"]
    if not photo_path.is_file() or not logo_path.is_file():
        raise RuntimeError("Falta fotografía o logo de una noticia")
    with Image.open(photo_path) as original:
        original.load()
        if original.width < 650 or original.height < 450:
            raise RuntimeError("Foto de noticia de resolución insuficiente")
        img = ImageOps.fit(original.convert("RGB"), (W, H), method=Image.Resampling.LANCZOS)
    with Image.open(logo_path) as original_logo:
        original_logo.load()
        if original_logo.width < 32:
            raise RuntimeError("Logo ilegible")
        logo = original_logo.convert("RGBA")
    d = ImageDraw.Draw(img)
    # La imagen permanece visible desde 145 hasta 1430 (>66 % de la altura).
    d.rectangle((0, 0, W, 145), fill=INK)
    d.rectangle((0, 0, W, 10), fill=TEAL)
    d.text((45, 33), "ORBIUNO", font=font(54), fill=WHITE)
    date_label = datetime.fromisoformat(day).strftime("%d/%m/%Y")
    d.text((550, 48), f"{date_label}  {slot} CO", font=font(28), fill=GOLD)
    # Se reserva exclusivamente el último cuarto para el texto.
    d.rectangle((0, 1430, W, H), fill=INK)
    d.rectangle((0, 1430, W, 1442), fill=TEAL)
    d.text((58, 1457), f"NOTICIA {pos:02} DE 06", font=font(30), fill=GOLD)
    for title_size in (57, 53, 49, 45, 41, 37):
        try:
            title_lines = wrapped(d, news["title"], width=960, size=title_size, max_lines=3)
            break
        except ValueError:
            continue
    else:
        raise RuntimeError("Titular demasiado largo para el panel compacto")
    for j, line in enumerate(title_lines):
        d.text((60, 1512 + j * (title_size + 10)), line, font=font(title_size), fill=WHITE)
    # Identidad de la fuente sin cubrir fotografía ni titulares.
    small = ImageOps.contain(logo, (80, 80))
    tile = Image.new("RGBA", (88, 88), "#FFFFFF")
    tile.alpha_composite(small, ((88-small.width)//2, (88-small.height)//2))
    img.paste(tile.convert("RGB"), (60, 1738))
    source = news["sources"][0]["name"].upper()
    fsize = 34 if len(source) <= 23 else 28
    for j, line in enumerate(wrapped(d, source, width=840, size=fsize, max_lines=2)):
        d.text((169, 1750 + j * 37), line, font=font(fsize), fill=GOLD)
    d.text((60, 1851), "colombia-al-dia.pages.dev", font=font(24), fill=WHITE)
    credit = ent["credit"]
    tail = "Foto: " + credit["author"] + " · " + credit["license"]
    if len(tail) > 85:
        tail = tail[:82] + "…"
    d.text((60, 1891), tail, font=font(18, bold=False), fill="#D5E2E7")
    img.save(path, quality=90)


def draw_outro(day, slot, path):
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    header(d, day, slot)
    d.text((76, 695), "ESCUCHA CADA NOTICIA", font=font(54), fill=GOLD)
    d.text((76, 784), "COMPLETA EN NUESTRA WEB", font=font(42), fill=WHITE)
    d.text((76, 975), "colombia-al-dia.pages.dev", font=font(43), fill=TEAL)
    d.text((76, 1090), "@resumen.noticias", font=font(45), fill=WHITE)
    img.save(path, quality=90)


def cmd(*parts):
    return subprocess.run([str(x) for x in parts], check=True, capture_output=True, text=True)


def seconds(path):
    return float(cmd("ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", path).stdout.strip())


def encode(image, audio, target, *, silent_duration=None):
    ff = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
          "-loop", "1", "-framerate", "30", "-i", image]
    if silent_duration is not None:
        ff += ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(silent_duration)]
    else:
        ff += ["-i", audio, "-t", str(seconds(audio) + .18)]
    ff += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "25", "-r", "30", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100",
           "-ac", "1", "-b:a", "128k", "-movflags", "+faststart", "-shortest", target]
    cmd(*ff)
    if not target.is_file() or target.stat().st_size < 5000:
        raise RuntimeError("Segmento de video vacío")


def render(*, news_file: Path, day: str, slot: str, assets: Path, output: Path):
    doc = json.loads(news_file.read_text(encoding="utf-8"))
    rows = sorted((n for n in doc["news"] if n.get("date") == day and n.get("editionSlot") == slot
                   and n.get("verification") == "editorial_verified"), key=lambda n: n["priority"])
    if len(rows) != 6 or len({n["id"] for n in rows}) != 6:
        raise ValueError("No hay seis noticias editoriales del día")
    proof = json.loads((assets / "credits.json").read_text(encoding="utf-8"))
    entries = proof.get("entries", [])
    if proof.get("photosCount") != 6 or proof.get("logosCount") != 6 or len(entries) != 6:
        raise ValueError("Sin seis fotografías reales y logos confirmados")
    if [n["id"] for n in rows] != [x["id"] for x in entries]:
        raise ValueError("El orden de las fotografías no coincide con las noticias")
    for n, ent in zip(rows, entries):
        if (n.get("imageRightsVerified") is not True or n.get("imageCredit") != ent["credit"]["author"]
                or n.get("imageUrl", "").split("/")[-1] != ent["photoFile"]):
            raise ValueError("La fotografía no coincide con su autorización")
    output.mkdir(parents=True, exist_ok=True)
    frames = output / "frames"
    audio_folder = output / "reel_audio"
    frames.mkdir(exist_ok=True)
    audio_folder.mkdir(exist_ok=True)
    draw_cover(rows, day, slot, frames / "portada.jpg", assets / entries[0]["photoFile"])
    for i, (n, ent) in enumerate(zip(rows, entries), 1):
        draw_story(n, ent, assets, day, slot, i, frames / f"noticia-{i:02d}.jpg")
    draw_outro(day, slot, frames / "cierre.jpg")
    # Apertura directa: un saludo muy breve en la primera noticia, sin resumen de titulares.
    # No se crean subtítulos de locución ni se añaden textos ajenos a la noticia.
    inputs = {"segments": [{"id": f"n{i:02}",
                             "text": ("Buenos días, bienvenidos a ORBIUNO Noticias. " if i == 1 and slot == "08:00"
                                      else "Bienvenidos a ORBIUNO Noticias. " if i == 1 else "") + n["reelLine"]}
                            for i, n in enumerate(rows, 1)]}
    (output / "voice_input.json").write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
    cmd(sys.executable, str(ROOT / "scripts/generate_voice.py"), "--input",
        output / "voice_input.json", "--out", audio_folder)
    audio_report = json.loads((audio_folder / "audio_report.json").read_text(encoding="utf-8"))
    if (audio_report.get("status") != "ok" or audio_report.get("voice") != VOICE
        or audio_report.get("tempo") != TEMPO or len(audio_report.get("segments", [])) != 6
        or any(s["seconds"] <= 1 for s in audio_report["segments"])):
        raise RuntimeError("Voz colombiana aprobada ausente o incompleta")
    parts = []
    first = output / "part-00.mp4"
    encode(frames / "portada.jpg", None, first, silent_duration=1.4)
    parts.append(first)
    for i, seg in enumerate(audio_report["segments"], 1):
        part = output / f"part-{i:02d}.mp4"
        encode(frames / f"noticia-{i:02d}.jpg", audio_folder / seg["file"], part)
        parts.append(part)
    last = output / "part-07.mp4"
    encode(frames / "cierre.jpg", None, last, silent_duration=3.0)
    parts.append(last)
    concat = output / "parts.txt"
    concat.write_text("".join("file '" + p.resolve().as_posix() + "'\n" for p in parts), encoding="utf-8")
    video_name = "ORBIUNO_" + day + "_" + slot.replace(":", "") + "_6_NOTICIAS.mp4"
    video = output / video_name
    # Re-encode the final join to constant 30fps: stream-copy of 24fps segments
    # may declare a misleading 120fps timebase and fail Meta's 24-60fps Reel gate.
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "concat",
        "-safe", "0", "-i", concat, "-map", "0:v:0", "-map", "0:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24",
        "-r", "30", "-vsync", "cfr", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", video)
    duration = seconds(video)
    if duration < 10 or video.stat().st_size < 300_000:
        raise RuntimeError("Video demasiado corto o vacío")
    streams = json.loads(cmd("ffprobe", "-v", "error", "-show_entries",
                             "stream=codec_type,codec_name,width,height", "-of", "json", video).stdout)["streams"]
    if (not any(s.get("codec_type") == "video" and s.get("codec_name") == "h264"
                and s.get("width") == W and s.get("height") == H for s in streams)
        or not any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac" for s in streams)):
        raise RuntimeError("MP4 no es 1080x1920 H264/AAC")
    m = {"edition": day, "slot": slot, "newsCount": 6, "newsIds": [n["id"] for n in rows],
         "voice": VOICE, "voiceSpeed": TEMPO, "voiceEngines": [x["engine"] for x in audio_report["segments"]],
         "language": "es-CO", "voiceAccentAudited": False, "width": W, "height": H,
         "duration": round(duration, 2), "fps": 30, "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
         "video": video_name, "visualMode": "verified_real_photos", "imagesCount": 6,
         "logosCount": 6, "photoCredits": [x["credit"] for x in entries],
         "openingStyle": "saludo_corto_directo_a_noticias", "burnedSubtitles": False,
         "sourceOnly": False, "publicationAuthorized": False,
         "news": [{"id": n["id"], "title": n["title"], "sourceUrl": n["sources"][0]["url"]}
                  for n in rows], "published": False, "instagramId": None, "instagramPermalink": None}
    (output / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return m


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", required=True)
    p.add_argument("--slot", required=True)
    p.add_argument("--assets", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    m = render(news_file=ROOT / "noticias.json", day=a.day, slot=a.slot,
               assets=Path(a.assets), output=Path(a.out))
    print("REEL_SALOME_6_PHOTOS_QA_READY", m["duration"], m["sha256"])


if __name__ == "__main__":
    main()
