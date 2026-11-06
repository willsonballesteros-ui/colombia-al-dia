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
  "Caracol Radio",
  "The Guardian",
  "Primicias",
  "Reuters",
  "Reuters",
  "Reuters · Copernicus",
  "Associated Press",
  "Reuters",
  "Vanguardia",
  "Associated Press"
]
ITEMS_18 = [
  {
    "id": "18-1",
    "title": "Contraloría pide explicaciones por fallas en radares de El Dorado",
    "url": "https://caracol.com.co/2026/11/06/contraloria-pide-informacion-a-aerocivil-tras-fallas-en-radares-en-aeropuerto-el-dorado/",
    "source": "Caracol Radio",
    "category": "Actualidad",
    "socialHeadline": "Contraloría pide explicaciones por radares de El Dorado",
    "sources": [
      {
        "name": "Caracol Radio",
        "url": "https://caracol.com.co/2026/11/06/contraloria-pide-informacion-a-aerocivil-tras-fallas-en-radares-en-aeropuerto-el-dorado/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-2",
    "title": "Amenazas de bomba interrumpen vuelos en distintos puntos de Europa",
    "url": "https://www.theguardian.com/world/live/2026/nov/06/high-alert-hoax-bomb-threats-france-air-lingus-belgium-pope-leo-europe-live",
    "source": "The Guardian",
    "category": "Mundo",
    "socialHeadline": "Amenazas de bomba alteran vuelos en Europa",
    "sources": [
      {
        "name": "The Guardian",
        "url": "https://www.theguardian.com/world/live/2026/nov/06/high-alert-hoax-bomb-threats-france-air-lingus-belgium-pope-leo-europe-live"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-3",
    "title": "Colombia reanuda ventas de electricidad a Ecuador",
    "url": "https://www.primicias.ec/economia/colombia-reactiva-venta-energia-electrica-ecuador-noviembre-cortes-luz-estiaje-136588/",
    "source": "Primicias",
    "category": "Economía",
    "socialHeadline": "Colombia vuelve a vender electricidad a Ecuador",
    "sources": [
      {
        "name": "Primicias",
        "url": "https://www.primicias.ec/economia/colombia-reactiva-venta-energia-electrica-ecuador-noviembre-cortes-luz-estiaje-136588/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-4",
    "title": "Wall Street sigue pendiente de la caída de acciones ligadas a IA",
    "url": "https://www.reuters.com/business/ai-rout-sets-off-market-alarm-signals-traders-brace-whats-next-2026-11-06/",
    "source": "Reuters",
    "category": "Economía",
    "socialHeadline": "Mercados mundiales siguen atentos a la IA",
    "sources": [
      {
        "name": "Reuters",
        "url": "https://www.reuters.com/business/ai-rout-sets-off-market-alarm-signals-traders-brace-whats-next-2026-11-06/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-5",
    "title": "Estados Unidos incorpora IA para revisar estadísticas agrícolas",
    "url": "https://www.reuters.com/technology/usda-launch-ai-tool-check-crop-production-data-after-errors-2026-11-06/",
    "source": "Reuters",
    "category": "Tecnología e IA",
    "socialHeadline": "Estados Unidos usa IA para comprobar cifras agrícolas",
    "sources": [
      {
        "name": "Reuters",
        "url": "https://www.reuters.com/technology/usda-launch-ai-tool-check-crop-production-data-after-errors-2026-11-06/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-6",
    "title": "Copernicus reporta el octubre más cálido a escala mundial",
    "url": "https://www.reuters.com/sustainability/cop/after-warmest-october-record-2026-is-likely-exceed-15-c-above-pre-industrial-2026-11-06/",
    "source": "Reuters · Copernicus",
    "category": "Salud y Medioambiente",
    "socialHeadline": "Copernicus registra un octubre récord de calor",
    "sources": [
      {
        "name": "Reuters · Copernicus",
        "url": "https://www.reuters.com/sustainability/cop/after-warmest-october-record-2026-is-likely-exceed-15-c-above-pre-industrial-2026-11-06/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-7",
    "title": "U2 prepara «Carnaval de Luz» para el 13 de noviembre",
    "url": "https://apnews.com/article/e876604d953b05da81a3553d98361ad8",
    "source": "Associated Press",
    "category": "Entretenimiento y Farándula",
    "socialHeadline": "U2 anuncia nuevo álbum para el 13 de noviembre",
    "sources": [
      {
        "name": "Associated Press",
        "url": "https://apnews.com/article/e876604d953b05da81a3553d98361ad8"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-8",
    "title": "Manifestantes protestan contra un centro de datos en Ámsterdam",
    "url": "https://www.reuters.com/world/europe/activists-breach-microsoft-data-centre-construction-site-protests-spread-europe-2026-11-06/",
    "source": "Reuters",
    "category": "Tecnología e IA",
    "socialHeadline": "Protesta ante un centro de datos en Ámsterdam",
    "sources": [
      {
        "name": "Reuters",
        "url": "https://www.reuters.com/world/europe/activists-breach-microsoft-data-centre-construction-site-protests-spread-europe-2026-11-06/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-9",
    "title": "Alejandro Gutiérrez logra bronce juvenil en Dakar",
    "url": "https://www.vanguardia.com/deportes/2026/11/06/historico-bronce-para-colombia-alejandro-gutierrez-brillo-en-los-juegos-olimpicos-de-la-juventud-dakar-2026/",
    "source": "Vanguardia",
    "category": "Deportes",
    "socialHeadline": "Bronce para Colombia en salto ecuestre en Dakar",
    "sources": [
      {
        "name": "Vanguardia",
        "url": "https://www.vanguardia.com/deportes/2026/11/06/historico-bronce-para-colombia-alejandro-gutierrez-brillo-en-los-juegos-olimpicos-de-la-juventud-dakar-2026/"
      }
    ],
    "verification": "editorial_verified"
  },
  {
    "id": "18-10",
    "title": "Ucrania reclama garantías de seguridad antes de nuevas conversaciones",
    "url": "https://apnews.com/article/713268db3dac59bff6ad6c831c72cdb6",
    "source": "Associated Press",
    "category": "Política y Actualidad",
    "socialHeadline": "Ucrania reclama garantías para futuras negociaciones",
    "sources": [
      {
        "name": "Associated Press",
        "url": "https://apnews.com/article/713268db3dac59bff6ad6c831c72cdb6"
      }
    ],
    "verification": "editorial_verified"
  }
]
# Dos frases por tema; texto ORIGINAL, sin reproducir articulos de terceros.
VOICE = [
  [
    "Caracol Radio informa que la Contraloría solicitó explicaciones por las fallas de radar en El Dorado."
  ],
  [
    "The Guardian reporta amenazas de bomba que afectaron vuelos europeos; las autoridades investigan los casos."
  ],
  [
    "Primicias informa que Colombia reanudó la venta de energía a Ecuador."
  ],
  [
    "Reuters analiza la presión sobre las acciones tecnológicas y los mercados financieros."
  ],
  [
    "Reuters informa que Estados Unidos utilizará inteligencia artificial para verificar datos agrícolas."
  ],
  [
    "Según Copernicus y Reuters, octubre fue el mes de octubre más cálido registrado a escala mundial."
  ],
  [
    "Associated Press anuncia un nuevo disco de U dos, previsto para el trece de noviembre."
  ],
  [
    "Reuters reporta protestas ante un centro de datos de Microsoft en Ámsterdam."
  ],
  [
    "El Ministerio del Deporte confirma el bronce de Alejandro Gutiérrez en salto ecuestre de Dakar."
  ],
  [
    "Associated Press informa que Ucrania pide garantías de seguridad antes de nuevas negociaciones."
  ]
]
CTA = [
    "¡La noticia no termina aquí!",
    "Escucha cada noticia completa en nuestra web. Toca el enlace del perfil de arroba resumen punto noticias.",
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
    d.text((100, 268), "ORBIUNO", font=font(68), fill=WHITE)
    d.text((100, 338), "COLOMBIA AL DÍA  ·  NOTICIAS", font=font(25), fill=TEAL)
    d.rounded_rectangle((734, 274, 1004, 348), radius=16, fill=AMBER)
    d.text((754, 289), "06 NOV · 18:00", font=font(27), fill=INK)
    d.text((100, 370), "PANORAMA  /  10 NOTICIAS VERIFICADAS", font=font(27), fill=PALE)
    accents = [CORAL, AMBER, TEAL, VIOLET, CORAL]
    for j in range(5):
        i = block * 5 + j
        item = items[i]
        y = 410 + j * 205
        chosen = i == active
        accent = accents[j]
        bg = accent if chosen else ("#17373F" if block == 0 else "#213440")
        fg = INK if chosen else WHITE
        faint = INK if chosen else PALE
        d.rounded_rectangle((43, y, 1037, y + 193), radius=23, fill=bg)
        if not chosen:
            d.rounded_rectangle((43, y, 57, y + 216), radius=7, fill=accent)
        d.text((71, y + 16), f"{i+1:02d}", font=font(37), fill=fg if chosen else accent)
        category = str(item["category"]).upper()
        d.text((159, y + 19), category, font=font(19 if len(category) > 22 else 22), fill=fg if chosen else TEAL)
        source = item["sources"][0]["name"]
        d.text((160, y + 147), "FUENTE: " + source, font=font(24), fill=faint)
        pic = photo_cache.get(source)
        if pic is not None:
            icon = pic.copy().convert("RGBA")
            icon.thumbnail((48, 48), Image.Resampling.LANCZOS)
            d.rounded_rectangle((966, y + 137, 1022, y + 191), radius=8, fill=WHITE)
            im.paste(icon, (971 + (46-icon.width)//2, y + 139 + (46-icon.height)//2), icon)
            d = ImageDraw.Draw(im)
        title = str(item.get("socialHeadline") or item["title"]).strip()
        if i == -1:
            title = "NO APLICABLE"
        face = fit_font(d, title, 900, 2, high=40, low=28)
        yy = y + 58
        for line in lines(d, title, face, 900, 2):
            d.text((76, yy), line, font=face, fill=fg)
            yy += face.size + 7
        if chosen:
            d.rounded_rectangle((837, y + 12, 1020, y + 46), radius=12, fill=INK)
            d.text((866, y + 19), "EN FOCO", font=font(17), fill=WHITE)
    # Franja dedicada a subtitulos quemados; evita tapar los titulares.
    d.rounded_rectangle((100, 1450, 940, 1530), radius=24, fill="#07181E")
    d.text((120, 1460), "AUDIO · FUENTES ATRIBUIDAS", font=font(24), fill=AMBER)
    d.text((112, 1511), "ESCUCHA EN LA WEB · ENLACE DEL PERFIL", font=font(27), fill=WHITE)
    im.save(output, optimize=True)


def closing(output):
    im = Image.new("RGB", (W, H), BKG)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 17), fill=CORAL)
    d.text((100, 270), "ORBIUNO", font=font(87), fill=WHITE)
    d.text((100, 380), "COLOMBIA AL DÍA", font=font(36), fill=TEAL)
    d.rounded_rectangle((100, 525, 940, 1135), radius=43, fill="#173B42")
    d.text((98, 565), "¡LA NOTICIA", font=font(75), fill=AMBER)
    d.text((98, 668), "NO TERMINA AQUÍ!", font=font(60), fill=WHITE)
    d.text((97, 804), "ESCUCHA CADA NOTICIA", font=font(42), fill=TEAL)
    d.text((97, 873), "UNA POR UNA, EN LA WEB", font=font(37), fill=WHITE)
    d.rounded_rectangle((100, 1200, 940, 1340), radius=30, fill=CORAL)
    d.text((130, 1230), "ENLACE DEL PERFIL", font=font(50), fill=INK)
    d.text((110, 1440), "@resumen.noticias", font=font(43), fill=WHITE)
    d.text((110, 1490), "colombia-al-dia.pages.dev", font=font(33), fill=PALE)
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
    items = ITEMS_18
    if len(items) != 10: raise SystemExit("No hay diez reportajes")
    for item in items:
        if urlsplit(item["sources"][0]["url"]).scheme != "https": raise RuntimeError("Fuente inválida")
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
        curr = 3.18
        cues = []
        samples.append(np.zeros(int(24000*3.18),dtype=np.float32))
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
        captions = output_dir / "reel_18pm.srt"
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
        video = output_dir / "reel_18pm.mp4"
        # Regenerar composición original ORBIUNO PULSE aprobada a partir del sintetizador musical determinístico.
        pulse = output_dir / "ORBIUNO_Pulse.wav"
        run("python", "scripts/make_orbiuno_pulse.py", str(pulse))
        music_source, music_sr = sf.read(pulse)
        full = np.zeros(int(curr*music_sr) + 1000, dtype=np.float32)
        def lay(at,source_at,length,amp):
            j=int(at*music_sr); start=int(source_at*music_sr); n=min(int(length*music_sr),len(full)-j,len(music_source)-start)
            if n<=0:return
            wave=music_source[start:start+n].copy()*amp
            fade=min(int(.25*music_sr),n//3)
            if fade>0:
                wave[-fade:]*=np.linspace(1,0,fade,dtype=np.float32)
            full[j:j+n]+=wave
        lay(0,0,9.5,.75)
        lay(curr*.38,2.9,1.15,.28)
        lay(curr*.70,2.9,1.15,.28)
        lay(max(curr-2.6,0),20.4,2.5,.62)
        music = work / "musica.wav"
        sf.write(music,full,music_sr)

        # Ejecutar un solo encode. Duraciones graficas basadas en audio generado.
        force = "FontName=DejaVu Sans,FontSize=27,PrimaryColour=&H00FFFFFF,OutlineColour=&H000A131A,Outline=3,Shadow=0,Alignment=2,MarginV=395"
        vf = "fps=24,subtitles=" + str(captions) + ":force_style='" + force + "'"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "concat", "-safe", "0", "-i", str(listing),
            "-i", str(wav), "-i", str(music),
            "-filter_complex", "[2:a][1:a]sidechaincompress=threshold=0.025:ratio=6:attack=12:release=280[duck];[1:a][duck]amix=inputs=2:weights=1 0.7,alimiter=limit=0.88[out]",
            "-map", "0:v", "-map", "[out]", "-vf", vf, "-r", "24",
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
        if duration < 35 or duration > 90 or int(info["format"]["size"]) < 100000:
            raise RuntimeError("MP4 con duracion o tamaño invalido")
        manifest = {
            "editionDate": DATE, "slot": "18:00 America/Bogota",
            "format": "9:16", "resolution": [W, H],
            "display": "2 grupos de cinco; realce en funcion del audio",
            "newsCount": len(items), "sourceNames": SOURCE_EXPECTED,
            "voice": "kokoro-onnx/ef_dora", "nativeSpeed": 1.25,
            "postTimeStretch": False, "subtitles": "reel_18pm.srt",
            "durationSeconds": round(duration, 2), "output": "reel_18pm.mp4",
            "audioStreamVerified": True, "publicationVerified": False,
            "photoRightsMode": "solo fondos tipograficos; favicon real de fuente si disponible",
        }
        (output_dir / "reel_18pm.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("REEL_VALIDADO", json.dumps(manifest, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
