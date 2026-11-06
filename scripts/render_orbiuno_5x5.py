#!/usr/bin/env python3
"""ORBIUNO: Reel 5+5 narrado, sin avatar ni fotos de licencia incierta.

Genera un MP4 vertical 1080x1920 con voz ef_dora nativa speed=1.25;
mide los tiempos de la sintesis, sincroniza resaltados y subtitulos por
frase y produce un manifiesto de trazabilidad. NO publica en Instagram.
"""
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import numpy as np
import soundfile as sf
import onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1080, 1920
DATE = "2026-11-06"
BKG = "#0B252C"
TEAL = "#5FE4CE"
CORAL = "#FF6F61"
AMBER = "#FFB300"
VIOLET = "#A87AED"
INK = "#0B252C"
WHITE = "#FFFFFF"
PALE = "#E5F6F3"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
SOURCE_EXPECTED = [
    "Reuters", "Caracol Radio", "La República", "Caracol Radio",
    "Reuters", "Reuters", "Reuters", "Reuters", "Caracol Radio", "Caracol Radio",
]
# Dos frases por tema; texto ORIGINAL, sin reproducir articulos de terceros.
VOICE = [
    ("Reuters investiga el entrenamiento de piratas informáticos norcoreanos.",
     "El reportaje examina su relación con ataques financieros y el uso de inteligencia artificial."),
    ("Caracol Radio informa que la Armada decomisó ciento cuatro armas de guerra en el Caribe.",
     "Cinco personas fueron capturadas durante el procedimiento marítimo."),
    ("La República informa que el Banco de la República elevó a siete coma uno por ciento su previsión de inflación para dos mil veintiséis.",
     "Se trata de una proyección, no de la inflación definitiva."),
    ("Caracol Radio cuenta que Jhon Arias anotó dos goles en el triunfo seis a uno de Palmeiras frente a Remo.",
     "El futbolista colombiano marcó durante los primeros catorce minutos."),
    ("Según Reuters, el papa León catorce inició una gira por Uruguay, Argentina y Perú.",
     "El recorrido por Suramérica sigue a una intervención médica reciente."),
    ("Reuters informa sobre nuevos incidentes con petroleros en el estrecho de Ormuz.",
     "Las autoridades marítimas advierten de riesgos para la navegación."),
    ("Reuters reporta dudas de inversionistas sobre una posible salida a bolsa de Anthropic.",
     "La valoración y el calendario de la oferta siguen bajo discusión."),
    ("También Reuters señala que la caída de las acciones tecnológicas afectó fondos de inversión.",
     "Varios gestores redujeron posiciones y equipos después de las pérdidas."),
    ("Caracol Radio informa que un tribunal ordenó la libertad del exministro Luis Fernando Velasco.",
     "El proceso judicial continúa y la decisión no significa absolución."),
    ("Caracol Radio reporta que el Ministerio de Minas pidió ahorrar electricidad entre seis y nueve de la noche.",
     "El objetivo es elevar las reservas de los embalses antes del verano."),
]
CTA = [
    "¡La noticia no termina aquí!",
    "Escucha cada noticia completa, una por una, en voz alta en nuestra web.",
    "Toca arroba resumen punto noticias y abre el enlace del perfil.",
]


def font(size, bold=True):
    f = FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")
    return ImageFont.truetype(str(f), size)


def lines(draw, text, face, max_width, max_lines=2):
    ans, buf = [], ""
    for word in str(text).split():
        candidate = (buf + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            buf = candidate
        else:
            if buf:
                ans.append(buf)
            buf = word
    if buf:
        ans.append(buf)
    if len(ans) > max_lines:
        ans = ans[:max_lines]
        while ans[-1] and draw.textbbox((0, 0), ans[-1] + "…", font=face)[2] > max_width:
            ans[-1] = ans[-1][:-1]
        ans[-1] += "…"
    return ans


def fit_font(draw, txt, width, max_lines, high=41, low=26):
    for size in range(high, low - 1, -1):
        ft = font(size)
        if len(lines(draw, txt, ft, width, 100)) <= max_lines:
            return ft
    return font(low)


def favicon(item):
    # Solo emblema iconico real del dominio citado, nunca logotipo imaginario.
    try:
        from build_carousel import favicon as real_favicon
        return real_favicon(item)
    except Exception as exc:
        print("Favicon opcional ausente:", type(exc).__name__, flush=True)
        return None


def panel(items, block, active, photo_cache, output):
    im = Image.new("RGB", (W, H), BKG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 15), fill=CORAL)
    d.text((54, 68), "ORBIUNO", font=font(68), fill=WHITE)
    d.text((55, 148), "COLOMBIA AL DÍA  ·  NOTICIAS", font=font(25), fill=TEAL)
    d.rounded_rectangle((734, 79, 1024, 153), radius=16, fill=AMBER)
    d.text((758, 92), "06 NOV · 08:00", font=font(27), fill=INK)
    d.text((55, 212), "PANORAMA  /  10 NOTICIAS VERIFICADAS", font=font(27), fill=PALE)
    accents = [CORAL, AMBER, TEAL, VIOLET, CORAL]
    for j in range(5):
        i = block * 5 + j
        item = items[i]
        y = 275 + j * 232
        chosen = i == active
        accent = accents[j]
        bg = accent if chosen else ("#17373F" if block == 0 else "#213440")
        fg = INK if chosen else WHITE
        faint = INK if chosen else PALE
        d.rounded_rectangle((43, y, 1037, y + 216), radius=23, fill=bg)
        if not chosen:
            d.rounded_rectangle((43, y, 57, y + 216), radius=7, fill=accent)
        d.text((71, y + 16), f"{i+1:02d}", font=font(37), fill=fg if chosen else accent)
        category = str(item["category"]).upper()[:22]
        d.text((159, y + 19), category, font=font(22), fill=fg if chosen else TEAL)
        source = item["sources"][0]["name"]
        d.text((160, y + 166), "FUENTE: " + source, font=font(24), fill=faint)
        pic = photo_cache.get(source)
        if pic is not None:
            icon = pic.copy().convert("RGBA")
            icon.thumbnail((48, 48), Image.Resampling.LANCZOS)
            d.rounded_rectangle((966, y + 151, 1022, y + 205), radius=8, fill=WHITE)
            im.paste(icon, (971 + (46-icon.width)//2, y + 155 + (46-icon.height)//2), icon)
            d = ImageDraw.Draw(im)
        title = str(item.get("socialHeadline") or item["title"]).strip()
        if i == 0:
            title = "REUTERS INVESTIGA A HACKERS NORCOREANOS"
        face = fit_font(d, title, 900, 2, high=40, low=28)
        yy = y + 62
        for line in lines(d, title, face, 900, 2):
            d.text((76, yy), line, font=face, fill=fg)
            yy += face.size + 7
        if chosen:
            d.rounded_rectangle((837, y + 12, 1020, y + 46), radius=12, fill=INK)
            d.text((866, y + 19), "EN FOCO", font=font(17), fill=WHITE)
    # Franja dedicada a subtitulos quemados; evita tapar los titulares.
    d.rounded_rectangle((47, 1489, 1033, 1750), radius=24, fill="#07181E")
    d.text((71, 1509), "AUDIO · FUENTES ATRIBUIDAS", font=font(24), fill=AMBER)
    d.text((64, 1809), "ESCUCHA EN LA WEB · ENLACE DEL PERFIL", font=font(27), fill=WHITE)
    im.save(output, optimize=True)


def closing(output):
    im = Image.new("RGB", (W, H), BKG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 17), fill=CORAL)
    d.text((72, 98), "ORBIUNO", font=font(87), fill=WHITE)
    d.text((75, 215), "COLOMBIA AL DÍA", font=font(36), fill=TEAL)
    d.rounded_rectangle((67, 465, 1010, 1125), radius=43, fill="#173B42")
    d.text((98, 565), "¡LA NOTICIA", font=font(75), fill=AMBER)
    d.text((98, 668), "NO TERMINA AQUÍ!", font=font(60), fill=WHITE)
    d.text((97, 804), "ESCUCHA CADA NOTICIA", font=font(42), fill=TEAL)
    d.text((97, 873), "UNA POR UNA, EN LA WEB", font=font(37), fill=WHITE)
    d.rounded_rectangle((86, 1210, 990, 1360), radius=30, fill=CORAL)
    d.text((130, 1243), "ENLACE DEL PERFIL", font=font(50), fill=INK)
    d.text((101, 1450), "@resumen.noticias", font=font(43), fill=WHITE)
    d.text((95, 1542), "colombia-al-dia.pages.dev", font=font(33), fill=PALE)
    im.save(output, optimize=True)


def srtstamp(t):
    ms = round(t * 1000)
    h, rest = divmod(ms, 3600000)
    m, rest = divmod(rest, 60000)
    s, milli = divmod(rest, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def run(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def main():
    today = datetime.now(ZoneInfo("America/Bogota")).date().isoformat()
    if today != DATE:
        raise SystemExit("Este trabajo solo genera la edicion del 06/11/2026; no publica atrasadas.")
    data = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    if data.get("editionDate") != DATE:
        raise SystemExit("No coincide la fecha del archivo editorial")
    items = sorted(
        [x for x in data["news"] if x.get("date") == DATE
         and x.get("verification") == "editorial_verified"],
        key=lambda x: x.get("priority", 999)
    )
    if len(items) != 10 or len({x["id"] for x in items}) != 10:
        raise SystemExit("No hay exactamente diez noticias editoriales distintas")
    for i, item in enumerate(items):
        sources = item.get("sources", [])
        if not sources or sources[0].get("name") != SOURCE_EXPECTED[i]:
            raise SystemExit("Cambió el orden o la fuente de la noticia " + str(i+1))
        if urlsplit(sources[0]["url"]).scheme != "https":
            raise SystemExit("Fuente sin enlace HTTPS")
    if not any("Deport" in x["category"] for x in items):
        raise SystemExit("Falta deporte")
    if not any("Inteligencia artificial" in x["category"] for x in items):
        raise SystemExit("Falta IA")
    output_dir = ROOT / "media" / DATE
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.inter_op_num_threads = 1
    opts.enable_cpu_mem_arena = False
    opts.enable_mem_pattern = False
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(os.environ.get("ORBIUNO_VOICE_MODEL", "/tmp/kokoro-v1.0.onnx"),
                                   sess_options=opts, providers=["CPUExecutionProvider"])
    speech = Kokoro.from_session(session, os.environ.get("ORBIUNO_VOICE_BANK", "/tmp/voices-v1.0.bin"))
    with tempfile.TemporaryDirectory(prefix="orbiuno-5x5-") as scratch:
        work = Path(scratch)
        icons = {}
        for item in items:
            src = item["sources"][0]["name"]
            if src not in icons:
                icons[src] = favicon(item)
        segments, samples, sr_current = [], [], None
        curr = 0.0
        cues = []
        for idx, phrases in enumerate(VOICE + [tuple(CTA)]):
            for phrase in phrases:
                audio, sr = speech.create(phrase, "ef_dora", speed=1.25, lang="es",
                                          sentence_pause=.15, clause_pause=.07)
                if sr_current is not None and sr != sr_current:
                    raise RuntimeError("Frecuencia de muestras variable")
                sr_current = sr
                a = np.asarray(audio, dtype=np.float32)
                if a.size == 0 or np.max(np.abs(a)) < .01:
                    raise RuntimeError("Sintesis de audio vacia o silenciosa")
                pad = np.zeros(int(sr * .08), dtype=np.float32)
                duration = (a.size + pad.size) / sr
                end = curr + duration
                segments.append((idx, phrase, curr, end, duration))
                samples.extend((a, pad))
                cues.append((curr, end, phrase))
                curr = end
                print("Segmento", len(segments), "voz", round(curr, 1), "s", flush=True)
        merged = np.concatenate(samples)
        wav = work / "voz.wav"
        sf.write(wav, merged, sr_current, subtype="PCM_16")
        captions = output_dir / "reel_08am.srt"
        with captions.open("w", encoding="utf-8") as stream:
            for num, (a, b, line) in enumerate(cues, 1):
                stream.write(f"{num}\n{srtstamp(a)} --> {srtstamp(b)}\n{line}\n\n")
        pic_frames = []
        for num, (idx, phrase, start, end, length) in enumerate(segments):
            path = work / f"frame_{num:03d}.png"
            if idx < 10:
                panel(items, 0 if idx < 5 else 1, idx, icons, path)
            else:
                closing(path)
            pic_frames.append((path, length))
        listing = work / "frames.txt"
        with listing.open("w", encoding="utf-8") as out:
            for path, length in pic_frames:
                out.write("file '" + str(path) + "'\n")
                out.write("duration " + str(round(length, 6)) + "\n")
            out.write("file '" + str(pic_frames[-1][0]) + "'\n")
        video = output_dir / "reel_08am.mp4"
        # Ejecutar un solo encode. Duraciones graficas basadas en audio generado.
        force = "FontName=DejaVu Sans,FontSize=27,PrimaryColour=&H00FFFFFF,OutlineColour=&H000A131A,Outline=3,Shadow=0,Alignment=2,MarginV=260"
        vf = "fps=24,subtitles=" + str(captions) + ":force_style='" + force + "'"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-i", str(wav), "-vf", vf, "-r", "24",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest", str(video))
        info = json.loads(run("ffprobe", "-v", "error", "-show_entries",
                              "format=duration,size:stream=codec_type,codec_name,width,height",
                              "-of", "json", str(video)).stdout)
        streams = info["streams"]
        if not any(x.get("codec_type") == "audio" for x in streams):
            raise RuntimeError("MP4 sin audio")
        if not any(x.get("codec_type") == "video" and x.get("width") == W and x.get("height") == H for x in streams):
            raise RuntimeError("MP4 sin video vertical 1080x1920")
        duration = float(info["format"]["duration"])
        if duration < 35 or int(info["format"]["size"]) < 100000:
            raise RuntimeError("MP4 con duracion o tamaño invalido")
        manifest = {
            "editionDate": DATE, "slot": "08:00 America/Bogota",
            "format": "9:16", "resolution": [W, H],
            "display": "2 grupos de cinco; realce en funcion del audio",
            "newsCount": len(items), "sourceNames": SOURCE_EXPECTED,
            "voice": "kokoro-onnx/ef_dora", "nativeSpeed": 1.25,
            "postTimeStretch": False, "subtitles": "reel_08am.srt",
            "durationSeconds": round(duration, 2), "output": "reel_08am.mp4",
            "audioStreamVerified": True, "publicationVerified": False,
            "photoRightsMode": "solo fondos tipograficos; favicon real de fuente si disponible",
        }
        (output_dir / "reel_08am.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("REEL_VALIDADO", json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
