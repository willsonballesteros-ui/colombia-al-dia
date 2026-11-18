#!/usr/bin/env python3
"""Puerta de seguridad obligatoria ANTES del render de Reels Salomé.

Sin aprobación auditiva explícita no se entrega un video.
No consulta Meta, ni lee secretos, ni modifica main.
"""
import json
import math
import os
import subprocess
from pathlib import Path

class VoiceBlocked(RuntimeError):
    pass

def approved_audio(directory="build/audio", *, approval_env="VOICE_SAMPLE_APPROVED", expected_ids=None):
    folder=Path(directory)
    report_file=folder/"audio_report.json"
    if os.environ.get(approval_env) != "true":
        raise VoiceBlocked("VOICE_SAMPLE_APPROVED no es true: falta aprobación de la muestra")
    if not report_file.is_file():
        raise VoiceBlocked("audio_report.json no existe; voz sin verificar")
    report=json.loads(report_file.read_text(encoding="utf-8"))
    if report.get("status") != "ok":
        raise VoiceBlocked("audio_report.json status=blocked; NO renderizar")
    if report.get("voice") != "es-CO-SalomeNeural" or report.get("tempo") != 1.25:
        raise VoiceBlocked("voz o velocidad diferentes de SalomeNeural 1.25x")
    segments=report.get("segments",[])
    ids=[x.get("id") for x in segments]
    if not segments or len(set(ids))!=len(ids) or (expected_ids and ids!=list(expected_ids)):
        raise VoiceBlocked("segmentos fuera de orden, repetidos o faltantes")
    total=report.get("total_seconds",0)
    # 50–60 s es un objetivo editorial, NO un límite de rechazo.
    # Proteger solo contra audio vacío, corrupto o duración no finita.
    if not isinstance(total,(int,float)) or not math.isfinite(total) or total<=0:
        raise VoiceBlocked("duración del audio ausente o inválida")
    # duration_in_target=False es una advertencia, no un fallo de voz.
    for item in segments:
        if item.get("engine") not in ("azure","edge-tts"):
            raise VoiceBlocked("motor no reconocido")
        f=folder/str(item.get("file",""))
        if f.parent != folder or not f.is_file() or f.stat().st_size<3000:
            raise VoiceBlocked("falta MP3 válido: "+str(item.get("id")))
        x=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","default=nw=1:nk=1",str(f)],capture_output=True,text=True)
        if x.returncode or not x.stdout.strip():
            raise VoiceBlocked("ffprobe falló para "+str(item["id"]))
        try:d=float(x.stdout.strip())
        except ValueError: raise VoiceBlocked("MP3 sin duración")
        if abs(d-item.get("seconds",0))>.25:
            raise VoiceBlocked("duración de MP3 difiere del reporte: "+item["id"])
    full=folder/"full.mp3"
    if not full.is_file() or full.stat().st_size<3000:
        raise VoiceBlocked("full.mp3 no existe")
    return report

if __name__ == "__main__":
    try:
        data=approved_audio(os.environ.get("VOICE_AUDIO_DIR","build/audio"))
        print("SALOME_AUDIO_APPROVED",data["total_seconds"])
    except (VoiceBlocked,OSError,ValueError) as e:
        raise SystemExit("BLOCKED: "+str(e))
