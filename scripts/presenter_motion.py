#!/usr/bin/env python3
"""Animación de presentadora original controlada por envolvente de audio.

Ruta gratuita C: ilustración editorial animada (NO lip-sync fonético ni
fotografía real). Sólo genera la escena de apertura; no publica ni cobra.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

SIZE = (360, 640)
FPS = 24
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def mouth_envelope(audio: np.ndarray, sample_rate: int, fps: int = FPS) -> list[float]:
    """Envolvente amortiguada que refleja la energía real de la narración."""
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    count = max(1, math.ceil(len(audio) / sample_rate * fps))
    samples_per_frame = max(1, int(sample_rate / fps))
    rms = []
    for i in range(count):
        seg = audio[i * samples_per_frame: (i + 1) * samples_per_frame]
        rms.append(float(np.sqrt(np.mean(seg * seg))) if len(seg) else 0.0)
    scale = max(0.01, float(np.percentile(rms, 89)))
    output = []
    smooth = 0.0
    for r in rms:
        target = min(1.0, max(0.0, (r / scale - 0.16) * 1.2))
        smooth = smooth * 0.52 + target * 0.48
        output.append(smooth)
    return output


def frame_image(index: int, energy: float, label: str) -> Image.Image:
    """Presentadora ilustrada con parpadeo, movimiento facial y boca expresiva."""
    w, h = SIZE
    im = Image.new("RGB", SIZE, (9, 32, 70))
    d = ImageDraw.Draw(im)
    d.ellipse((162, -145, 555, 280), outline=(38, 83, 147), width=12)
    d.ellipse((-180, 355, 200, 755), outline=(36, 104, 171), width=10)
    # Cabecera y escritorio del noticiero.
    d.rounded_rectangle((21, 19, 339, 72), radius=13, fill=(15, 60, 127))
    d.text((36, 29), "ORBIUNO  |  EN VIVO", font=ImageFont.truetype(FONT, 21), fill=(255, 217, 92))
    d.rounded_rectangle((22, 538, 338, 619), radius=16, fill=(8, 22, 51))
    d.text((38, 550), "10 NOTICIAS · COLOMBIA Y MUNDO", font=ImageFont.truetype(FONT, 13), fill="white")
    d.text((38, 579), label[:44], font=ImageFont.truetype(FONT, 11), fill=(210, 225, 245))
    bob = round(2.2 * math.sin(index / 17))
    # Cabello y silueta de la presentadora (diseño propio).
    d.ellipse((76, 118+bob, 280, 377+bob), fill=(41, 25, 36))
    d.polygon([(73, 493), (94, 365+bob), (142, 343+bob), (211, 345+bob),
               (267, 369+bob), (292, 493)], fill=(234, 225, 221))
    d.polygon([(50, 534), (78, 403+bob), (139, 368+bob), (181, 454+bob),
               (212, 371+bob), (290, 410+bob), (314, 534)], fill=(36, 87, 165))
    d.polygon([(140, 370+bob), (178, 454+bob), (215, 370+bob),
               (203, 492), (154, 491)], fill=(245, 245, 244))
    d.ellipse((113, 168+bob, 249, 370+bob), fill=(225, 169, 137))
    d.ellipse((106, 247+bob, 123, 276+bob), fill=(217, 151, 125))
    d.ellipse((245, 247+bob, 260, 276+bob), fill=(217, 151, 125))
    # Peinado con mechones sobre la frente.
    d.pieslice((92, 112+bob, 270, 283+bob), 180, 350, fill=(49, 31, 39))
    d.polygon([(124, 173+bob), (134, 206+bob), (220, 166+bob),
               (246, 185+bob), (251, 131+bob), (177, 121+bob)], fill=(44, 29, 38))
    d.arc((115, 125+bob, 246, 310+bob), 325, 65, fill=(78, 44, 46), width=10)
    # Mirada frontal, parpadeo aproximadamente cada 3.7 s.
    blink = (index % 89 in (0, 1, 2))
    for x in (148, 210):
        d.arc((x-21, 248+bob, x+21, 265+bob), 185, 354,
              fill=(66, 42, 48), width=3)
        if not blink:
            d.ellipse((x-5, 253+bob, x+5, 266+bob), fill=(39, 45, 58))
            d.ellipse((x-2, 254+bob, x, 256+bob), fill="white")
        else:
            d.line((x-11, 261+bob, x+11, 261+bob), fill=(74, 45, 47), width=2)
    d.arc((161, 281+bob, 195, 315+bob), 18, 100, fill=(159, 94, 84), width=2)
    # Apertura de boca sincronizada únicamente con volumen, no con fonemas.
    mouth_open = round(2 + 13 * energy)
    d.ellipse((164, 328+bob-mouth_open//3, 199, 337+bob+mouth_open),
              fill=(116, 43, 64))
    if mouth_open >= 6:
        d.arc((169, 327+bob-mouth_open//3, 193, 336+bob+mouth_open//2),
              0, 180, fill=(246, 219, 217), width=2)
    # Etiqueta visible que evita presentar la ilustración como una persona filmada.
    d.text((48, 621), "PRESENTADORA ILUSTRADA · VOZ SINTÉTICA",
           font=ImageFont.truetype(FONT, 9), fill=(187, 205, 228))
    return im


def make_presenter_clip(audio_path: Path, output_path: Path, label: str = "BOLETÍN DEL DÍA"):
    samples, rate = sf.read(str(audio_path), dtype="float32")
    energies = mouth_envelope(samples, rate)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "360x640",
        "-r", str(FPS), "-i", "pipe:0",
        "-i", str(audio_path),
        "-vf", "scale=720:1280:flags=lanczos,setsar=1",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "29",
        "-c:a", "aac", "-b:a", "96k", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-shortest", str(output_path),
    ]
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i, energy in enumerate(energies):
            process.stdin.write(frame_image(i, energy, label).tobytes())
    except (BrokenPipeError, OSError):
        process.kill()
        raise RuntimeError("FFmpeg interrumpió el render de la presentadora")
    finally:
        if process.stdin:
            process.stdin.close()
    if process.wait() != 0 or not output_path.is_file() or output_path.stat().st_size < 15_000:
        raise RuntimeError("La animación local no produjo un MP4 válido")
    return {
        "engine": "local_audio_envelope_illustration",
        "realLipSync": False,
        "talkingPresenter": True,
        "presenterType": "illustrated",
        "durationSec": round(len(samples) / rate, 2),
    }


if __name__ == "__main__":
    raise SystemExit("Uso: importar make_presenter_clip desde render_narrated.py")
