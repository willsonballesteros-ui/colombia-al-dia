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
    """Photo-first safe-area cover: visible date/time and a single dominant headline."""
    with Image.open(principal_photo) as original:
        actual = original.convert("RGB")
        if actual.width < 650 or actual.height < 450:
            raise RuntimeError("Portada sin foto real de resolución suficiente")
        photo = ImageOps.fit(actual, (W, 1000), method=Image.Resampling.LANCZOS)
    img = Image.new("RGB", (W, H), INK)
    img.paste(photo, (0, 350))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 352), fill=INK)
    d.rectangle((0, 0, W, 17), fill=TEAL)
    d.text((64, 95), "ORBIUNO", font=font(83), fill=WHITE)
    d.text((65, 220), "EDICIÓN DE LA MAÑANA" if slot == "08:00" else "EDICIÓN INFORMATIVA",
           font=font(40), fill=GOLD)
    # The date/time block is within the Instagram grid crop's central 4:5 safe area.
    d.rounded_rectangle((52, 400, 1026, 553), radius=25, fill="#071C31")
    date_label = datetime.fromisoformat(day).strftime("%d / %m / %Y")
    d.text((77, 424), date_label, font=font(64), fill=WHITE)
    d.text((76, 498), f"{slot}  HORA COLOMBIA", font=font(37), fill=GOLD)
    d.rectangle((0, 1080, W, H), fill=INK)
    d.rectangle((51, 1115, 67, 1375), fill=TEAL)
    size = 61
    while size >= 40:
        try:
            principal_lines = wrapped(d, news[0]["title"], width=920, size=size, max_lines=3)
            break
        except ValueError:
            size -= 3
    else:
        raise RuntimeError("Titular de portada demasiado largo")
    for k, line in enumerate(principal_lines):
        d.text((95, 1133 + k * (size + 13)), line, font=font(size), fill=WHITE)
    d.text((64, 1405), "Y OTRAS 5 NOTICIAS", font=font(37), fill=GOLD)
    for k, n in enumerate(news[1:], 2):
        line = str(n["title"])
        small = 26
        while small >= 20:
            try:
                pieces = wrapped(d, line, width=865, size=small, max_lines=1)
                break
            except ValueError:
                small -= 1
        if small < 20:
            # Names remain complete in the individual story slides; no cropping here.
            pieces = wrapped(d, line, width=865, size=26, max_lines=2)
        y = 1473 + (k - 2) * 81
        d.text((64, y), f"{k:02}", font=font(28), fill=TEAL)
        for z, part in enumerate(pieces):
            d.text((135, y + z * 30), part, font=font(small), fill=WHITE)
    d.text((64, 1860), "colombia-al-dia.pages.dev", font=font(28), fill="#B9D2E4")
    img.save(path, quality=91)


def draw_story(news, ent, assets, day, slot, pos, path):
    photo_path = assets / ent["photoFile"]
    logo_path = assets / ent["logoFile"]
    if not photo_path.is_file() or not logo_path.is_file():
        raise RuntimeError("Falta fotografía o logo de una noticia")
    photo = Image.open(photo_path)
    photo.load()
    logo = Image.open(logo_path)
    logo.load()
    if photo.width < 650 or photo.height < 450 or logo.width < 32:
        raise RuntimeError("Imagen o logo ilegible")
    img = Image.new("RGB", (W, H), INK)
    cropped = ImageOps.fit(photo.convert("RGB"), (W, 985), method=Image.Resampling.LANCZOS)
    img.paste(cropped, (0, 208))
    d = ImageDraw.Draw(img)
    header(d, day, slot)
    d.rectangle((0, 1193, W, H), fill=INK)
    d.rounded_rectangle((55, 1232, 245, 1300), radius=13, fill=GOLD)
    d.text((78, 1244), f"{pos:02} / 06", font=font(32), fill=INK)
    title_size = 58
    while title_size >= 41:
        try:
            title_lines = wrapped(d, news["title"], width=950, size=title_size, max_lines=4)
            break
        except ValueError:
            title_size -= 3
    else:
        raise RuntimeError("Titular desborda incluso con fuente mínima")
    for j, line in enumerate(title_lines):
        d.text((62, 1330 + j * (title_size + 14)), line, font=font(title_size), fill=WHITE)
    # Actual favicon del dominio de la fuente, junto al nombre completo legible.
    small = ImageOps.contain(logo.convert("RGBA"), (136, 136))
    tile = Image.new("RGBA", (150, 150), "#FFFFFF")
    tile.alpha_composite(small, ((150-small.width)//2, (150-small.height)//2))
    img.paste(tile.convert("RGB"), (62, 1645))
    source = news["sources"][0]["name"].upper()
    fsize = 44 if len(source) <= 23 else 34
    for j, line in enumerate(wrapped(d, source, width=750, size=fsize, max_lines=2)):
        d.text((240, 1665 + j * 53), line, font=font(fsize), fill=GOLD)
    d.text((62, 1823), "colombia-al-dia.pages.dev", font=font(31), fill=WHITE)
    credit = ent["credit"]
    tail = "Foto: " + credit["author"] + " · " + credit["license"]
    if len(tail) > 85:
        tail = tail[:82] + "…"
    d.text((62, 1874), tail, font=font(20, bold=False), fill="#D5E2E7")
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
         "openingStyle": "saludo_corto_directo_a_noticias", "burnedSubtitles": False,\n         "sourceOnly": False, "publicationAuthorized": False,
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
