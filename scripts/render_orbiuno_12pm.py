#!/usr/bin/env python3
"""ORBIUNO: edición de seguimiento sin repetir titulares, máx. 5 noticias por lámina.

El Reel utiliza la misma composición compacta de las 08:00 y voz oficial ef_dora.
No programa ni publica posts. Solo usa noticias verificadas con hechos nuevos.
"""
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit

import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-11-06"
OUT = ROOT / "media" / DATE
VIDEO = OUT / "reel_12pm.mp4"
MANIFEST = OUT / "reel_12pm.json"
FONT = Path("/usr/share/fonts/truetype/dejavu")
W, H = 1080, 1920
BG, WHITE, TEAL, CORAL, GOLD = "#0B252C", "#FFFFFF", "#5FE4CE", "#FF7161", "#FFD06A"
PALETTE = [CORAL, GOLD, TEAL, "#BB9CFF", "#FF91C1"]
VOICE = "ef_dora"
SPEED = 1.25
MAX_PER_SLIDE = 5
MAX_NEWS = 10
INTRO = ("ORBIUNO. Actualización del mediodía. "
         "Presentamos solamente las novedades verificadas desde el boletín de la mañana.")
END = ("Para conocer el desarrollo completo de cada noticia y consultar sus fuentes originales, "
       "entra a colombia guion al guion día punto pages punto dev, desde el enlace de arroba resumen punto noticias.")
BRIEFS = {
 "orbiuno-20261106-12m-maluma":
   "Caracol Radio informa que Maluma anunció una gira por más de sesenta ciudades, con inicio previsto en Bogotá en febrero de dos mil veintisiete.",
 "orbiuno-20261106-12m-bella-bonita":
   "Caracol Radio informa que Luis Alfonso y Los Dotores de la Carranga presentan una nueva versión de Bella y Bonita, conocida en redes sociales."
}

def face(size, bold=True):
    return ImageFont.truetype(str(FONT / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)

def wrap(draw, value, size, width, limit=2):
    f = face(size)
    rows, line = [], ""
    for word in str(value).split():
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=f)[2] <= width:
            line = trial
        else:
            if line:
                rows.append(line)
            line = word
    if line:
        rows.append(line)
    if len(rows) > limit:
        rows = rows[:limit]
        while rows[-1] and draw.textbbox((0, 0), rows[-1] + "…", font=f)[2] > width:
            rows[-1] = rows[-1][:-1]
        rows[-1] += "…"
    return rows

def label(draw, value, x, y, size, width, color=WHITE, limit=2, gap=9):
    rows = wrap(draw, value, size, width, limit)
    for line in rows:
        draw.text((x, y), line, font=face(size), fill=color)
        y += size + gap
    return y

def base():
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 16), fill=CORAL)
    d.text((56, 67), "ORBIUNO", font=face(73), fill=WHITE)
    d.text((59, 163), "COLOMBIA AL DÍA  ·  ACTUALIZACIÓN", font=face(25), fill=TEAL)
    d.rounded_rectangle((745, 96, 1026, 167), radius=14, fill=GOLD)
    d.text((765, 112), "06 NOV · 12:00", font=face(27), fill=BG)
    return im, d

def splash(news, target):
    im, d = base()
    d.text((74, 450), "SOLO", font=face(96), fill=WHITE)
    d.text((73, 578), "NOVEDADES", font=face(98), fill=GOLD)
    d.text((75, 755), f"{len(news)} NOTICIAS NUEVAS", font=face(52), fill=TEAL)
    label(d, "Sin repetir titulares del boletín de las 8:00 a. m.", 78, 856, 36, 905, WHITE, 3)
    d.rounded_rectangle((66, 1272, 1012, 1544), radius=28, fill="#183B43")
    label(d, "LAS FUENTES ORIGINALES Y EL DESARROLLO COMPLETO ESTÁN EN LA WEB", 104, 1330, 33, 855, WHITE, 4)
    d.text((77, 1774), "@resumen.noticias · enlace del perfil", font=face(27), fill=TEAL)
    im.save(target)

def panel(news, first, active, icons, target):
    chunk = news[first:first + MAX_PER_SLIDE]
    assert 1 <= len(chunk) <= MAX_PER_SLIDE
    im, d = base()
    d.text((66, 259), f"NOVEDADES {first + 1:02d}–{first + len(chunk):02d}", font=face(45), fill=GOLD)
    count = len(chunk)
    height = min(387, int((1160 - 20*(count - 1)) / count))
    top = 365 if count >= 4 else 420
    for idx, news_item in enumerate(chunk):
        global_index = first + idx
        y = top + idx * (height + 20)
        focused = global_index == active
        accent = PALETTE[idx % len(PALETTE)]
        color = accent if focused else "#1B3942"
        fg = BG if focused else WHITE
        muted = BG if focused else TEAL
        d.rounded_rectangle((50, y, 1029, y + height), radius=22, fill=color)
        if not focused:
            d.rounded_rectangle((50, y, 65, y + height), radius=8, fill=accent)
        d.text((81, y + 22), f"{global_index+1:02d}", font=face(45), fill=fg if focused else accent)
        d.text((170, y + 29), str(news_item["category"]).upper()[:24], font=face(26), fill=muted)
        headline = str(news_item.get("socialHeadline") or news_item["title"])
        fsize = 47 if count <= 2 else 38
        label(d, headline, 90, y + 99, fsize, 882, fg, 3 if count <= 2 else 2)
        source = news_item["sources"][0]["name"]
        d.text((92, y + height - 63), "FUENTE: " + source, font=face(26), fill=muted)
        icon = icons.get(source)
        if icon is not None:
            icon = icon.copy().convert("RGBA")
            icon.thumbnail((60, 60), Image.Resampling.LANCZOS)
            d.rounded_rectangle((942, y + height - 80, 1021, y + height - 8), radius=10, fill=WHITE)
            im.paste(icon, (952+(59-icon.width)//2, y+height-75+(59-icon.height)//2), icon)
            d = ImageDraw.Draw(im)
    d.rounded_rectangle((57, 1640, 1028, 1813), radius=22, fill="#092027")
    label(d, "ESCUCHA EL REPORTE COMPLETO", 93, 1667, 33, 895, GOLD, 1)
    d.text((96, 1725), "colombia-al-dia.pages.dev", font=face(29), fill=WHITE)
    im.save(target)

def closing(target):
    im, d = base()
    label(d, "¿QUIERES LA NOTICIA COMPLETA?", 77, 480, 66, 925, GOLD, 3)
    label(d, "Escoge el tema y escúchalo en nuestra web.", 80, 780, 41, 870, WHITE, 3)
    d.rounded_rectangle((69, 1210, 1010, 1430), radius=30, fill=CORAL)
    d.text((102, 1276), "ENLACE EN EL PERFIL  ↓", font=face(39), fill=BG)
    d.text((82, 1565), "@resumen.noticias", font=face(43), fill=WHITE)
    d.text((82, 1645), "colombia-al-dia.pages.dev", font=face(32), fill=TEAL)
    im.save(target)

def run(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout

def newly_reportable(item):
    if item.get("verification") != "editorial_verified":
        return False
    if item.get("date") != DATE or not item.get("audioFullTextEs"):
        return False
    original = str(item.get("id", ""))
    # En la edición de hoy, todos los id -am- ya fueron narrados a las 8:00.
    # Una actualización exige hechos adicionales documentados expresamente.
    if "-am-" in original:
        update = item.get("editorialUpdate") or {}
        return update.get("substantial") is True and bool(update.get("newFacts")) and bool(update.get("verifiedSource"))
    return True

def main():
    if datetime.now(ZoneInfo("America/Bogota")).date().isoformat() != DATE:
        raise SystemExit("Edición caducada: no regenerar ni republicar noticias atrasadas")
    db = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    candidates = sorted([x for x in db["news"] if newly_reportable(x)], key=lambda x:x.get("priority", 999))
    selected, urls, titles = [], set(), set()
    for item in candidates:
        sources = item.get("sources", [])
        if not sources:
            continue
        link = str(sources[0].get("url") or "").strip()
        if urlsplit(link).scheme != "https" or link in urls:
            continue
        t = item["title"].casefold().strip()
        if t in titles:
            continue
        selected.append(item)
        urls.add(link)
        titles.add(t)
        if len(selected) == MAX_NEWS:
            break
    if not selected:
        raise SystemExit("SIN NOVEDADES: se cancela la edición, no se repiten noticias")
    assert len(selected) <= MAX_NEWS
    OUT.mkdir(parents=True, exist_ok=True)
    speech_options = ort.SessionOptions()
    speech_options.intra_op_num_threads = 2
    speech_options.inter_op_num_threads = 1
    model = ort.InferenceSession("/tmp/kokoro-v1.0.onnx",
                                  sess_options=speech_options, providers=["CPUExecutionProvider"])
    tts = Kokoro.from_session(model, "/tmp/voices-v1.0.bin")
    with tempfile.TemporaryDirectory(prefix="orbiuno-compacto-") as folder:
        tmp = Path(folder)
        from build_carousel import favicon
        icons = {}
        for item in selected:
            source = item["sources"][0]["name"]
            if source not in icons:
                try:
                    icons[source] = favicon(item)
                except Exception:
                    icons[source] = None
        pieces = [INTRO] + [BRIEFS.get(n["id"]) or n.get("summary", "") for n in selected] + [END]
        if any(not phrase.strip() for phrase in pieces):
            raise RuntimeError("Noticia sin texto para narrar")
        frames, audio_chunks, sample_rate = [], [], 24000
        for i, words in enumerate(pieces):
            audio, sr = tts.create(words, VOICE, speed=SPEED, lang="es",
                                   sentence_pause=.1, clause_pause=.06)
            if sr != sample_rate or len(audio) == 0 or float(np.max(np.abs(audio))) < .01:
                raise RuntimeError("Error en voz oficial femenina ef_dora")
            a = np.asarray(audio, dtype="float32")
            pad = np.zeros(int(sr*.28), dtype="float32")
            audio_chunks.extend((a, pad))
            image_path = tmp / f"frame_{i:02d}.png"
            if i == 0:
                splash(selected, image_path)
            elif i == len(pieces) - 1:
                closing(image_path)
            else:
                active = i - 1
                panel(selected, (active // MAX_PER_SLIDE) * MAX_PER_SLIDE, active, icons, image_path)
            frames.append((image_path, (len(a)+len(pad))/sr))
        wav = tmp/"audio.wav"
        sf.write(wav, np.concatenate(audio_chunks), sample_rate, subtype="PCM_16")
        concat = tmp/"frames.txt"
        with concat.open("w", encoding="utf-8") as f:
            for path, seconds in frames:
                f.write(f"file '{path}'\n")
                f.write(f"duration {seconds:.6f}\n")
            f.write(f"file '{frames[-1][0]}'\n")
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","concat","-safe","0","-i",str(concat),"-i",str(wav),
            "-vf","fps=24","-c:v","libx264","-preset","veryfast","-crf","27",
            "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
            "-movflags","+faststart","-shortest",str(VIDEO))
        meta = json.loads(run("ffprobe","-v","error","-show_entries",
                              "format=duration,size:stream=codec_type,width,height",
                              "-of","json",str(VIDEO)))
        duration = float(meta["format"]["duration"])
        if not (15 <= duration <= 90):
            raise RuntimeError(f"Duración fuera del límite: {duration:.1f}s")
        if not any(s.get("codec_type")=="audio" for s in meta["streams"]):
            raise RuntimeError("MP4 sin audio")
        if not any(s.get("codec_type")=="video" and s.get("width")==W and s.get("height")==H for s in meta["streams"]):
            raise RuntimeError("Resolución incompatible")
        result = {
            "editionDate":DATE,"slot":"12:00 America/Bogota",
            "format":"compacto: portada + grupos de máximo 5 noticias + cierre",
            "newsCount":len(selected),"newsIds":[n["id"] for n in selected],
            "repeatedMorningNews":0,"slidesOfNews":(len(selected)+4)//5,
            "voice":VOICE,"voiceEngine":"kokoro-onnx","voiceRate":SPEED,
            "durationSeconds":round(duration,1),"publicationVerified":False,
            "sourceLinks":[n["sources"][0]["url"] for n in selected],
            "audioStreamVerified":True,"filename":VIDEO.name
        }
        MANIFEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("REEL_ACTUALIZACION_COMPACTA_OK",json.dumps(result,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
