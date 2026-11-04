#!/usr/bin/env python3
"""Generar voz femenina del Reel sin comprar créditos de avatar.

Usa edge-tts (servicio online externo; disponibilidad y derechos de uso
sujetos al proveedor). Es OPCIONAL, requiere aceptación explícita de las
condiciones comerciales del proveedor en la ficha de derechos; no garantiza
cero coste/continuidad ni hace lip-sync. Alternativa: WAV aportado por editor.
"""
import asyncio
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
VOICE="es-CO-SalomeNeural"


def script_for(notes):
    if len(notes)!=10 or len({x["id"] for x in notes})!=10:
        raise RuntimeError("La locución debe contener diez titulares únicos")
    return (
        "Bienvenidos a ORBIUNO, Colombia al Día. Estos son los diez titulares de hoy. "
        + " ".join(
            f"Noticia {i}. {n['title'].rstrip('.')}."
            for i,n in enumerate(notes,1)
        )
        + " Escucha las noticias en nuestra página web y consulta cada fuente original."
    )


def prepare(daydir,db):
    if os.getenv("ORBIUNO_EDGE_TTS_OPT_IN")!="1":
        print("TTS en línea desactivado: se requiere aprobación explícita")
        return False
    manifest=daydir/"presentadora-foto.json"
    image=daydir/"presentadora-foto.jpg"
    if not image.is_file() or not manifest.is_file():
        print("No hay fotografía/manifest de presentadora aprobados")
        return False
    m=json.loads(manifest.read_text(encoding="utf-8"))
    needed=["rightsVerified","consentVerified","voiceAuthorized",
            "scriptChecked","imageRightsVerified","ttsCommercialUseApproved"]
    if not all(m.get(k) is True for k in needed):
        raise RuntimeError("Faltan consentimientos y permisos comerciales de imagen o TTS")
    notes=sorted((x for x in db["news"] if x.get("date")==db["editionDate"]
                  and x.get("verification")=="editorial_verified"),
                 key=lambda x:x.get("priority",999))
    text=script_for(notes)
    import edge_tts
    with tempfile.TemporaryDirectory(prefix="orbiuno-voice-") as tmp:
        mp3=Path(tmp)/"speech.mp3"
        audio=daydir/"presentadora-voz.wav"
        asyncio.run(edge_tts.Communicate(
            text,voice=VOICE,rate="-3%",pitch="+3Hz").save(str(mp3)))
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                        "-i",str(mp3),"-ar","48000","-ac","2",str(audio)],check=True)
        if audio.stat().st_size < 90_000:
            audio.unlink(missing_ok=True)
            raise RuntimeError("El audio del presentador se generó incompleto")
    m["speaksAllTenHeadlines"]=True
    m["ttsVoice"]=VOICE
    m["ttsScript"]=text
    m["ttsType"]="generated_synthetic_voice"
    manifest.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Voz sintética generada para diez titulares; no existe lip-sync facial")
    return True


def main():
    db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    if db["editionDate"]!=datetime.now(ZoneInfo("America/Bogota")).date().isoformat():
        raise RuntimeError("La edición no corresponde a la fecha local actual")
    prepare(ROOT/"media"/db["editionDate"],db)


if __name__=="__main__":
    main()
