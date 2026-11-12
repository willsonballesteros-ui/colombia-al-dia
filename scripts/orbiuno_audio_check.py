#!/usr/bin/env python3
"""Comprobación técnica de audio con ffprobe/ffmpeg reales.

Demuestra: pista de audio presente, decodificable, no silenciosa y duración
coherente con el guion. NO demuestra acento colombiano ni reproducción en iPhone.
"""
import json
import re
import subprocess

WORDS_PER_SECOND = (2.0, 3.4)  # rango razonable de locución informativa a 1×


def expected_duration_range(text):
    n = len(text.split())
    return n / WORDS_PER_SECOND[1], n / WORDS_PER_SECOND[0]


def check_audio(path, script_text, min_mean_db=-50.0, min_peak_db=-35.0):
    errs = []
    try:
        p = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
             "stream=codec_type:format=duration", "-of", "json", str(path)],
            capture_output=True, text=True, timeout=20)
        info = json.loads(p.stdout or "{}")
        if p.returncode != 0 or not info.get("streams"):
            return ["sin pista de audio legible"]
        duration = float(info["format"]["duration"])
        dec = subprocess.run(["ffmpeg", "-v", "error", "-stats", "-i", str(path), "-f", "null", "-"],
                             capture_output=True, text=True, timeout=120)
        times = re.findall(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)", dec.stderr)
        stderr_clean = re.sub(r"[^\n\r]*time=[^\n\r]*", "", dec.stderr).strip()
        if dec.returncode != 0 or stderr_clean:
            errs.append("el audio no se decodifica limpiamente: " + stderr_clean[:120])
        if not times:
            errs.append("no se pudo medir la duración realmente decodificada")
        else:
            h, m, sec = times[-1]
            decoded = int(h) * 3600 + int(m) * 60 + float(sec)
            # la cabecera puede mentir (archivo truncado): manda lo realmente decodificado
            if abs(decoded - duration) > max(0.5, duration * 0.05):
                errs.append(f"archivo truncado o inconsistente: cabecera {duration:.1f}s, "
                            f"decodificado {decoded:.1f}s")
            duration = min(duration, decoded)
        vol = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                             capture_output=True, text=True, timeout=120).stderr
        mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", vol)
        peak = re.search(r"max_volume:\s*(-?[\d.]+) dB", vol)
        if not mean or not peak:
            errs.append("no se pudo medir el volumen")
        elif float(mean.group(1)) < min_mean_db or float(peak.group(1)) < min_peak_db:
            errs.append("audio silencioso o con volumen demasiado bajo")
        lo, hi = expected_duration_range(script_text)
        if not (lo <= duration <= hi):
            errs.append(f"duración {duration:.1f}s fuera del rango esperado "
                        f"({lo:.1f}-{hi:.1f}s) para el guion")
    except Exception as exc:
        errs.append("audio: " + str(exc))
    return errs
