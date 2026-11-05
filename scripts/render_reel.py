"""Render a vertical news bulletin with neural narration, without paid video APIs.

Usage: python scripts/render_reel.py noticias.json
Dependencies: edge-tts, pillow, ffmpeg executable.
Only editorially verified news are eligible.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "media"
VOICE = os.environ.get("ORBIUNO_TTS_VOICE", "es-CO-SalomeNeural")

def font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def wrap(draw, value, f, width):
    lines, line = [], ""
    for word in value.split():
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=f)[2] > width and line:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])

def eligible(news):
    return [n for n in news if str(n.get("verification", "")).lower() in
            ("verified", "editorial_verified") and n.get("title") and n.get("summary")]

async def main():
    data = json.loads(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "noticias.json").read_text(encoding="utf-8"))
    items = eligible(data.get("news", []))[:10]
    if not items:
        raise SystemExit("No hay noticias verificadas editorialmente; se cancela publicación.")
    OUT.mkdir(exist_ok=True)
    now = datetime.now(ZoneInfo("America/Bogota"))
    intro = "Estas son las principales noticias de Colombia y el mundo en nuestra edición de la mañana. "
    narration = intro + " ".join(
        f"Noticia {i}. {n['title']}. {n['summary']}" for i, n in enumerate(items, 1)
    ) + " Para ampliar la información y consultar las fuentes, visita colombia al dia punto pages punto dev. ORBIUNO, noticias que también se escuchan."
    audio = OUT / "reel_voice.mp3"
    await edge_tts.Communicate(narration, VOICE).save(str(audio))
    im = Image.new("RGB", (1080, 1920), "#101827")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 1080, 190), fill="#edb342")
    d.text((55, 45), "ORBIUNO | COLOMBIA AL DÍA", font=font(52), fill="#101827")
    d.text((55, 230), now.strftime("%d/%m/%Y %H:%M · Bogotá"), font=font(34), fill="white")
    d.text((55, 320), "LAS NOTICIAS SE ESCUCHAN", font=font(47), fill="#edb342")
    y = 420
    for i, n in enumerate(items, 1):
        lines = wrap(d, f"{i}. {n['title']}", font(36), 960)
        for line in lines[:2]:
            if y > 1640:
                break
            d.text((55, y), line, font=font(36), fill="white")
            y += 50
        y += 20
        if y > 1640:
            break
    d.text((55, 1760), "Más información: colombia-al-dia.pages.dev", font=font(31), fill="#edb342")
    cover = OUT / "reel_cover.png"
    im.save(cover)
    video = OUT / "reel_edicion.mp4"
    subprocess.run(["ffmpeg", "-y", "-loop", "1", "-framerate", "1", "-i", str(cover),
                    "-i", str(audio), "-c:v", "libx264", "-tune", "stillimage",
                    "-pix_fmt", "yuv420p", "-r", "24", "-c:a", "aac", "-b:a", "128k",
                    "-shortest", "-movflags", "+faststart", str(video)], check=True)
    print(json.dumps({"video": str(video), "news_count": len(items), "voice": VOICE}, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
