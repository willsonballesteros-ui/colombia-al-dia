#!/usr/bin/env python3
"""Verificación objetiva de una locución ORBIUNO.

Rechaza silencio, tonos puros y audios con ritmo imposible. Con --asr transcribe
con Whisper y compara con el guion (única forma automática de medir inteligibilidad).
Un resultado OK NO sustituye una escucha humana de la primera muestra.
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import numpy as np

SR = 16000
SAMPLE = ("Esta es una prueba de voz de Orbiuno. Las noticias más importantes de "
          "Colombia y el mundo, en un solo lugar. Hoy es sábado siete de noviembre "
          "de dos mil veintiséis.")


def run(*args, **kw):
    return subprocess.run(args, check=True, capture_output=True, **kw)


def probe_duration(path):
    out = run("ffprobe", "-v", "error", "-show_entries", "format=duration",
              "-of", "json", str(path)).stdout
    return float(json.loads(out)["format"]["duration"])


def decode(path):
    raw = run("ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
              "-af", "pan=mono|c0=c0", "-f", "f32le", "-ar", str(SR), "pipe:1").stdout  # canal izquierdo: sin +3 dB de downmix
    return np.frombuffer(raw, dtype=np.float32)


def db(x):
    return 20 * math.log10(max(float(x), 1e-9))


def tone_concentration(samples):
    """Fracción de energía en el pico espectral (±3 bins). Tono puro ~1; voz <0.3."""
    win, hop = 1024, 512
    if samples.size < win:
        return 1.0
    w = np.hanning(win)
    acc = np.zeros(win // 2 + 1)
    for i in range(0, min(samples.size - win, SR * 20), hop):
        acc += np.abs(np.fft.rfft(samples[i:i + win] * w)) ** 2
    k = int(np.argmax(acc))
    return float(acc[max(0, k - 3):k + 4].sum() / max(acc.sum(), 1e-12))


def analyze(samples, duration, text):
    r = {"duration_s": round(duration, 2), "errors": []}
    if samples.size < SR:
        r["errors"].append("audio demasiado corto (<1 s)")
        r["ok"] = False
        return r
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(samples ** 2)))
    frame = int(0.05 * SR)
    n = samples.size // frame
    frms = np.sqrt((samples[:n * frame].reshape(n, frame) ** 2).mean(axis=1))
    active = frms > 10 ** (-45 / 20)
    act = frms[active]
    cv = float(act.std() / act.mean()) if act.size > 5 else 0.0
    words = len(re.findall(r"\w+", text))
    wps = words / duration
    r.update(peak_dbfs=round(db(peak), 1), rms_dbfs=round(db(rms), 1),
             active_ratio=round(float(active.mean()), 2),
             amplitude_cv=round(cv, 2),
             tone_concentration=round(tone_concentration(samples), 2),
             words=words, words_per_s=round(wps, 2))
    if r["rms_dbfs"] < -40:
        r["errors"].append("nivel demasiado bajo: posible silencio")
    if r["active_ratio"] < 0.5:
        r["errors"].append("menos de la mitad del audio tiene señal")
    if r["tone_concentration"] > 0.35:
        r["errors"].append("energía concentrada en una frecuencia: tono de prueba, no voz")
    if cv < 0.25:
        r["errors"].append("amplitud casi constante: no parece voz")
    if not 1.8 <= wps <= 6.0:
        r["errors"].append(f"ritmo implausible ({wps:.1f} palabras/s) para el guion")
    if peak >= 0.999:
        r["errors"].append("recorte (clipping)")
    r["ok"] = not r["errors"]
    return r


def asr_overlap(path, text, model="base"):
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(decode(path), language="es", beam_size=1)
    heard = " ".join(s.text for s in segs)

    def norm(s):
        return set(re.findall(r"[a-záéíóúñü0-9]+",
                              unicodedata.normalize("NFC", s.lower())))
    want, got = norm(text), norm(heard)
    return len(want & got) / max(1, len(want)), heard


def synthesize(text, out_mp3):
    """Misma ruta de código que scripts/generate_web_voice.py."""
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    o = ort.SessionOptions()
    o.intra_op_num_threads = 2
    o.inter_op_num_threads = 1
    o.enable_cpu_mem_arena = False
    o.enable_mem_pattern = False
    o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(
        os.environ.get("ORBIUNO_VOICE_MODEL", "/tmp/kokoro-v1.0.onnx"),
        sess_options=o, providers=["CPUExecutionProvider"])
    k = Kokoro.from_session(session, os.environ.get("ORBIUNO_VOICE_BANK", "/tmp/voices-v1.0.bin"))
    audio, sr = k.create(text, "ef_dora", speed=1.25, lang="es")
    run("ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1",
        "-i", "pipe:0", "-c:a", "libmp3lame", "-b:a", "64k", str(out_mp3),
        input=np.asarray(audio, dtype=np.float32).tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", help="archivo existente a validar")
    ap.add_argument("--synthesize", action="store_true", help="generar con Kokoro ef_dora")
    ap.add_argument("--text", default=SAMPLE)
    ap.add_argument("--out", default="voz-prueba.mp3")
    ap.add_argument("--report", default="voz-reporte.json")
    ap.add_argument("--asr", action="store_true", help="comparar con transcripción Whisper")
    ap.add_argument("--asr-min", type=float, default=0.6)
    a = ap.parse_args()
    path = Path(a.out)
    if a.synthesize:
        synthesize(a.text, path)
    elif a.audio:
        path = Path(a.audio)
    else:
        ap.error("indique --synthesize o --audio")
    rep = analyze(decode(path), probe_duration(path), a.text)
    rep["file"] = str(path)
    if a.asr:
        score, heard = asr_overlap(path, a.text)
        rep.update(asr_overlap=round(score, 2), asr_text=heard)
        if score < a.asr_min:
            rep["errors"].append(f"transcripción coincide solo {score:.0%} con el guion")
            rep["ok"] = False
    Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()
