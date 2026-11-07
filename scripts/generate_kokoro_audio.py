#!/usr/bin/env python3
"""Genera cuatro audios con Kokoro ONNX, sin reemplazar silenciosamente la voz."""
import argparse, json, pathlib, wave
from kokoro_onnx import Kokoro

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--script",required=True,help="JSON con lista de cuatro textos")
    p.add_argument("--model",required=True)
    p.add_argument("--voices",required=True)
    p.add_argument("--output",default="audio_orbiuno")
    p.add_argument("--voice",default="ef_dora")
    p.add_argument("--speed",type=float,default=1.25)
    a=p.parse_args()
    texts=json.loads(pathlib.Path(a.script).read_text(encoding="utf-8"))
    if not isinstance(texts,list) or len(texts)!=4 or not all(isinstance(t,str) and t.strip() for t in texts):
        raise SystemExit("Se requieren exactamente cuatro narraciones no vacías")
    engine=Kokoro(a.model,a.voices)
    available=engine.get_voices()
    if a.voice not in available:
        raise SystemExit(f"Voz solicitada {a.voice} no disponible; se bloquea la generación")
    folder=pathlib.Path(a.output);folder.mkdir(parents=True,exist_ok=True)
    durations=[]
    for i,txt in enumerate(texts,1):
        samples,rate=engine.create(txt,voice=a.voice,speed=a.speed,lang="es")
        import numpy as np
        pcm=(np.clip(samples,-1,1)*32767).astype("<i2")
        target=folder/f"noticia_{i:02}.wav"
        with wave.open(str(target),"wb") as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm.tobytes())
        durations.append(round(len(samples)/rate,2))
    (folder/"manifest.json").write_text(json.dumps({"voice":a.voice,"speed":a.speed,"durations_seconds":durations},ensure_ascii=False,indent=2),encoding="utf-8")
    print("Audio generado; REQUIERE validación auditiva del español antes de publicar",durations)
if __name__=="__main__":main()
