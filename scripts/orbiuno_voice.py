#!/usr/bin/env python3
"""Voice Engine: genera un audio por noticia con un motor intercambiable.

Motores: EdgeTTS (voz candidata es-CO-SalomeNeural; requiere `pip install edge-tts`, red y
verificar términos de uso comercial) y Kokoro (opcional, voces sin acento colombiano garantizado).
La salida se verifica con orbiuno_audio_check. EL ACENTO COLOMBIANO NO SE VALIDA AQUÍ:
exige una prueba de escucha humana registrada en voz_validacion.json (revisor, fecha, muestra con hash).
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbiuno_audio_check as audio  # noqa: E402

CANDIDATE_VOICE = "es-CO-SalomeNeural"


class EdgeTTS:
    name = "edge-tts"

    def __init__(self, voice=CANDIDATE_VOICE, rate="+0%"):
        self.voice, self.rate = voice, rate

    def synthesize(self, text, out_path):
        subprocess.run([sys.executable, "-m", "edge_tts", "--voice", self.voice, "--rate", self.rate,
                        "--text", text, "--write-media", str(out_path)], check=True, timeout=180)


def synthesize_edition(engine, evidence, out_dir):
    """evidence = contenido de evidence.json. Devuelve {id: ruta}; lanza si algún audio falla."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for nid, ev in evidence["noticias"].items():
        path = out_dir / f"audio_{nid}.mp3"
        engine.synthesize(ev["guion"], path)
        errs = audio.check_audio(path, ev["guion"])
        if errs:
            raise RuntimeError(f"audio de {nid} rechazado: {errs}")
        result[nid] = path
    return result


def validation_record_errors(record, base_dir):
    """Comprueba que exista el registro humano de la prueba de escucha."""
    errs = []
    for campo in ("voz", "revisor", "fecha", "veredicto", "muestra"):
        if not record.get(campo):
            errs.append(f"voz_validacion: falta {campo}")
    if record.get("veredicto") != "acento_colombiano_aprobado":
        errs.append("la prueba de escucha no aprobó el acento colombiano")
    m = record.get("muestra") or {}
    try:
        p = Path(base_dir) / m["archivo"]
        if hashlib.sha256(p.read_bytes()).hexdigest() != m.get("sha256"):
            errs.append("la muestra de voz no coincide con su hash")
    except Exception as exc:
        errs.append("muestra de voz: " + str(exc))
    return errs
