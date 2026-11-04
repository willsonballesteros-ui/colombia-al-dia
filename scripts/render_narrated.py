#!/usr/bin/env python3
"""Video ORBIUNO con voz femenina local (Kokoro) y 10 láminas, SIN avatar ni lip-sync.

No se afirma que una imagen hable. Requiere diez noticias editorial_verified
de la fecha ACTUAL de Bogotá, imágenes generadas, modelos Kokoro Apache 2.0
y ffmpeg. Nunca publica en Instagram ni toca una API de pago.
"""
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import soundfile as sf
from kokoro_onnx import Kokoro
from misaki.espeak import EspeakG2P


ROOT = Path(__file__).resolve().parents[1]
VOICE = "ef_dora"  # voz femenina española, no afirmar acento colombiano
MODEL = Path(os.environ.get("KOKORO_MODEL", "/tmp/kokoro-v1.0.onnx"))
VOICES = Path(os.environ.get("KOKORO_VOICES", "/tmp/voices-v1.0.bin"))


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL)


def first_words(text: str, limit: int) -> str:
    words = text.replace("\n", " ").strip().split()
    return " ".join(words[:limit]) + ("." if len(words) > limit else "")


def narration(news):
    headlines = ". ".join(first_words(n["title"], 12) for n in news)
    intro = (
        "ORBIUNO. Boletín narrado del día. Estas son las diez noticias más importantes "
        "de Colombia y el mundo. " + headlines + ". "
        "Ahora el detalle de cada noticia."
    )
    details = [
        "Noticia número {}. {}. {}".format(i, n["title"], first_words(n["summary"], 25))
        for i, n in enumerate(news, 1)
    ]
    return [intro, *details]


def make_segment(image_path: Path, audio_path: Path, output_path: Path):
    # 720x1280 es 9:16. El fondo acolcha láminas 1080x1350 sin recortar texto.
    vf = "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=0x071b46,setsar=1,fps=24"
    run(
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", "1", "-i", str(image_path),
        "-i", str(audio_path), "-vf", vf, "-shortest",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-c:a", "aac", "-b:a", "96k", "-pix_fmt", "yuv420p",
        str(output_path),
    )


def main():
    db = json.loads((ROOT / "noticias.json").read_text(encoding="utf-8"))
    day = db["editionDate"]
    actual = datetime.now(ZoneInfo("America/Bogota")).date().isoformat()
    if day != actual:
        raise RuntimeError(f"No crear video con noticias antiguas: {day} != {actual}")
    news = sorted(
        (x for x in db["news"] if x.get("date") == day and x.get("verification") == "editorial_verified"),
        key=lambda x: x.get("priority", 999),
    )
    if len(news) != 10 or len({n["id"] for n in news}) != 10:
        raise RuntimeError("Se requieren EXACTAMENTE diez noticias verificadas distintas")
    day_dir = ROOT / "media" / day
    images = [day_dir / "historia-orbiuno.png"] + [
        day_dir / f"top10-{i:02d}.png" for i in range(1, 11)
    ]
    if any(not x.is_file() for x in images):
        raise RuntimeError("Faltan archivos de imagen de la edición actual")
    if not MODEL.is_file() or not VOICES.is_file():
        raise RuntimeError("Faltan los pesos locales de Kokoro; no generar audio falso")
    script = narration(news)
    fingerprint = hashlib.sha256(json.dumps(news, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    output = day_dir / "boletin-narrado.mp4"
    manifest = day_dir / "boletin-narrado.json"
    if output.exists() and manifest.exists():
        prior = json.loads(manifest.read_text(encoding="utf-8"))
        if prior.get("fingerprint") == fingerprint:
            print("No duplicar video ya generado de esta edición")
            return

    g2p = EspeakG2P(language="es")
    kokoro = Kokoro(str(MODEL), str(VOICES))
    with tempfile.TemporaryDirectory(prefix="orbiuno-") as directory:
        tmp = Path(directory)
        pieces = []
        for i, (text, image) in enumerate(zip(script, images)):
            phonemes, _ = g2p(text)
            if not phonemes:
                raise RuntimeError(f"Sin fonemas en escena {i}")
            audio, sample_rate = kokoro.create(phonemes, VOICE, speed=1.07, is_phonemes=True)
            wav_path = tmp / f"scene-{i:02d}.wav"
            sf.write(str(wav_path), audio, sample_rate, subtype="PCM_16")
            clip = tmp / f"scene-{i:02d}.mp4"
            make_segment(image, wav_path, clip)
            pieces.append(clip)
            print("Escena renderizada:", i, flush=True)
        concat_file = tmp / "concat.txt"
        concat_file.write_text(
            "".join("file '{}'\n".format(p.as_posix()) for p in pieces),
            encoding="utf-8",
        )
        temporary_output = tmp / "out.mp4"
        run("ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy", "-movflags", "+faststart", str(temporary_output))
        if temporary_output.stat().st_size < 10000:
            raise RuntimeError("MP4 inválido, archivo demasiado pequeño")
        output.write_bytes(temporary_output.read_bytes())
    manifest.write_text(json.dumps({
        "editionDate": day,
        "fingerprint": fingerprint,
        "voice": VOICE,
        "narrationMode": "static_visuals_with_synthetic_narration",
        "hasTalkingAvatar": False,
        "hasRealLipSync": False,
        "scenes": 11,
        "video": output.name,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("GENERADO", output, output.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
