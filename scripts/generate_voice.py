#!/usr/bin/env python3
"""ORBIUNO / MyCar - generación de voz con es-CO-SalomeNeural (v2, revisada).

Motor principal: Azure Speech (plan gratuito F0), vía REST.
Respaldo: edge-tts (no oficial, puede fallar sin aviso).

Cada segmento se valida con ffprobe. Si algún segmento queda sin audio
válido, el script termina con código 1 y el pipeline NO debe renderizar.

Entrada (JSON):
{
  "segments": [
    {"id": "saludo",    "text": "Buenos días, esto es ORBIUNO Noticias."},
    {"id": "n01",       "text": "ICETEX abre cincuenta becas ..."},
    {"id": "despedida", "text": "Gracias por acompañarnos."}
  ]
}

Uso:
  python generate_voice.py --input editions/audio_input.json --out build/audio
  python generate_voice.py ... --strict     # error si el total no está en 50-60 s

Secretos (GitHub Actions): AZURE_SPEECH_KEY, AZURE_SPEECH_REGION (p. ej. eastus)
Requisitos: Python 3.8+, ffmpeg y ffprobe en el PATH, `pip install edge-tts`
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

VOICE = "es-CO-SalomeNeural"
TEMPO = 1.25                 # velocidad final, aplicada con FFmpeg
MIN_BYTES = 3000             # un MP3 válido pesa más que esto
MIN_SEC_PER_CHAR = 1 / 30    # cota inferior a 1x: >= 1 s por cada 30 caracteres
TARGET_MIN, TARGET_MAX = 50, 60
AZURE_RETRIES = 2            # reintentos ante 429/5xx/errores de red

# Pronunciación: solo se aplica al texto que se envía a la voz.
# Confirmar escuchando; ajustar o ampliar según haga falta.
PRONUNCIATION = {
    "ICETEX": "Icétex",
    "Pääbo": "Pébo",
    "DANE": "Dáne",
    "PIB": "P I B",
    "ORBIUNO": "Orbiuno",
}


def prepare_text(text: str) -> str:
    for src, dst in PRONUNCIATION.items():
        text = re.sub(rf"\b{re.escape(src)}\b", dst, text)
    return re.sub(r"\s+", " ", text).strip()


def azure_tts(text: str, out_path: Path) -> None:
    key = os.environ.get("AZURE_SPEECH_KEY")
    region = os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise RuntimeError("faltan AZURE_SPEECH_KEY / AZURE_SPEECH_REGION")
    ssml = (
        "<speak version='1.0' xml:lang='es-CO'>"
        f"<voice name='{VOICE}'>{escape(text)}</voice></speak>"
    )
    last = None
    for attempt in range(AZURE_RETRIES + 1):
        req = urllib.request.Request(
            f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
            data=ssml.encode("utf-8"),
            method="POST",
            headers={
                "Ocp-Apim-Subscription-Key": key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
                "User-Agent": "orbiuno-voice",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                out_path.write_bytes(resp.read())
            return
        except urllib.error.HTTPError as e:
            last = RuntimeError(f"Azure HTTP {e.code}: {e.read()[:200]!r}")
            if e.code not in (429, 500, 502, 503, 504):
                raise last from e          # error de clave/región/texto: no reintentar
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = RuntimeError(f"Azure red: {e}")
        time.sleep(2 * (attempt + 1))
    raise last


def edge_tts_fallback(text: str, out_path: Path) -> None:
    import edge_tts  # pip install edge-tts

    async def run():
        await edge_tts.Communicate(text, VOICE).save(str(out_path))

    asyncio.run(run())


def duration_sec(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def validate(path: Path, text: str, tempo: float = 1.0) -> float:
    """Devuelve la duración si el audio es válido; si no, lanza error."""
    if not path.exists() or path.stat().st_size < MIN_BYTES:
        raise RuntimeError("archivo vacío o demasiado pequeño")
    dur = duration_sec(path)
    min_dur = max(1.0, len(text) * MIN_SEC_PER_CHAR / tempo)
    if dur < min_dur:
        raise RuntimeError(f"duración {dur:.1f}s menor a la esperada ({min_dur:.1f}s)")
    return dur


def speed_up(src: Path, dst: Path) -> None:
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-filter:a", f"atempo={TEMPO}", "-ar", "44100", "-b:a", "128k", str(dst)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg: {r.stderr.strip()[:200]}")


def synthesize(seg_id: str, text: str, out_dir: Path) -> dict:
    spoken = prepare_text(text)
    raw = out_dir / f"{seg_id}_raw.mp3"
    final = out_dir / f"{seg_id}.mp3"
    errors = []
    for engine, fn in (("azure", azure_tts), ("edge-tts", edge_tts_fallback)):
        try:
            fn(spoken, raw)
            validate(raw, spoken)
            speed_up(raw, final)
            dur = validate(final, spoken, TEMPO)
            raw.unlink(missing_ok=True)
            return {"id": seg_id, "file": final.name, "engine": engine,
                    "seconds": round(dur, 2), "chars": len(spoken)}
        except Exception as e:  # noqa: BLE001
            errors.append(f"{engine}: {e}")
            raw.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
    raise RuntimeError("sin audio válido -> " + " | ".join(errors))


def concat_full(files, out_path: Path) -> None:
    """Une los MP3 en orden en un solo archivo (audio completo para la web)."""
    list_file = out_path.with_suffix(".txt")
    list_file.write_text(
        "".join(f"file '{f.resolve().as_posix()}'\n" for f in files), encoding="utf-8")
    r = subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-ar", "44100", "-b:a", "128k", str(out_path)],
        capture_output=True, text=True,
    )
    list_file.unlink(missing_ok=True)
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg concat: {r.stderr.strip()[:200]}")


def load_segments(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    segs = data.get("segments") if isinstance(data, dict) else None
    if not segs:
        raise SystemExit("ERROR: el JSON no trae 'segments' o está vacío")
    seen = set()
    for s in segs:
        sid, text = s.get("id", ""), (s.get("text") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", sid):
            raise SystemExit(f"ERROR: id inválido '{sid}' (solo letras, números, _ y -)")
        if sid in seen:
            raise SystemExit(f"ERROR: id repetido '{sid}'")
        if not text:
            raise SystemExit(f"ERROR: el segmento '{sid}' no tiene texto")
        seen.add(sid)
    return segs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strict", action="store_true",
                    help=f"falla si el total no está entre {TARGET_MIN} y {TARGET_MAX} s")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            print(f"ERROR: {tool} no está instalado o no está en el PATH", file=sys.stderr)
            return 1

    segments = load_segments(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    results, failed, errors = [], False, []
    for seg in segments:
        try:
            info = synthesize(seg["id"], seg["text"], out_dir)
            print(f"OK   {info['id']:<12} {info['engine']:<9} {info['seconds']}s")
            results.append(info)
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {seg['id']}: {e}", file=sys.stderr)
            failed = True
            errors.append({"id": seg["id"], "error": str(e)})

    total = round(sum(r["seconds"] for r in results), 2)
    status = "blocked" if failed else "ok"
    in_range = TARGET_MIN <= total <= TARGET_MAX
    full_name = None

    if not failed:
        try:
            concat_full([out_dir / r["file"] for r in results], out_dir / "full.mp3")
            full_name = "full.mp3"
        except Exception as e:  # noqa: BLE001
            print(f"FAIL audio completo: {e}", file=sys.stderr)
            status = "blocked"
            failed = True
            errors.append({"id": "full", "error": str(e)})

    if args.strict and not in_range:
        failed = True
        status = "blocked"
        errors.append({"id": "duration", "error": f"fuera de rango: {total}s; objetivo {TARGET_MIN}-{TARGET_MAX}s"})

    report = {"voice": VOICE, "tempo": TEMPO, "total_seconds": total,
              "duration_in_target": in_range, "full_audio": full_name,
              "segments": results, "errors": errors, "status": status}
    (out_dir / "audio_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Duración total: {total}s (objetivo {TARGET_MIN}-{TARGET_MAX} s)")

    if failed:
        print("BLOQUEADO: no renderizar el Reel.", file=sys.stderr)
        return 1
    if not in_range:
        print("AVISO: duración fuera de rango; ajustar los textos.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
