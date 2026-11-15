#!/usr/bin/env python3
"""Renderiza ORBIUNO 19:00 con voz femenina colombiana Azure Salome.
Requiere AZURE_SPEECH_KEY y AZURE_SPEECH_REGION en secretos del ejecutor.
No publica en Meta. No imprime secretos. Usa las seis noticias verificadas del JSON.
"""
import json, os, subprocess, tempfile, wave, io, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
DATE="2026-11-15"
SLOT="19:00"
VOICE="es-CO-SalomeNeural"
RATE="+25%"
W,H=1080,1920

def speech(text):
    from xml.sax.saxutils import escape
    key=os.environ.get("AZURE_SPEECH_KEY")
    region=os.environ.get("AZURE_SPEECH_REGION")
    if not key or not region:
        raise RuntimeError("Faltan secretos AZURE_SPEECH_KEY / AZURE_SPEECH_REGION. No se genera voz falsa.")
    ssml=f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="es-CO"><voice name="{VOICE}"><prosody rate="{RATE}">{escape(text)}</prosody></voice></speak>"""
    req=urllib.request.Request(f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1",
        data=ssml.encode("utf-8"),method="POST",headers={
        "Ocp-Apim-Subscription-Key":key,"Content-Type":"application/ssml+xml",
        "X-Microsoft-OutputFormat":"riff-24khz-16bit-mono-pcm",
        "User-Agent":"ORBIUNO"})
    with urllib.request.urlopen(req,timeout=50) as r: return r.read()

def main():
    db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    news=sorted([n for n in db["news"] if n.get("date")==DATE and n.get("editionSlot")==SLOT and n.get("verification")=="editorial_verified"],key=lambda n:n["priority"])
    if len(news)!=6:raise RuntimeError("Se requieren seis noticias verificadas")
    with tempfile.TemporaryDirectory() as tmp:
        td=Path(tmp);frames=[];segments=[]
        texts=["Seis noticias de Colombia y el mundo. Edición de las siete de la noche."]+[n["reelLine"] for n in news]
        texts[-1]+=" Escucha las noticias completas en colombia al día punto pages punto dev."
        for i,txt in enumerate(texts):
            audio=speech(txt);wav=td/f"{i:02d}.wav";wav.write_bytes(audio)
            with wave.open(io.BytesIO(audio),"rb") as w:duration=w.getnframes()/w.getframerate()
            if duration<=0:raise RuntimeError("Azure devolvió audio vacío")
            segments.append((wav,duration+.45))
            im=Image.new("RGB",(W,H),"#091D36");d=ImageDraw.Draw(im)
            font="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            d.text((95,220),"ORBIUNO",font=ImageFont.truetype(font,82),fill="white")
            d.rounded_rectangle((95,400,985,520),radius=20,fill="#FFCD63")
            d.text((120,434),"15 NOV 2026 · 7:00 P. M.",font=ImageFont.truetype(font,44),fill="#091D36")
            if i==0:
                d.text((95,610),"SEIS NOTICIAS DE LA NOCHE",font=ImageFont.truetype(font,44),fill="white")
                for j,n in enumerate(news):
                    import textwrap
                    title=textwrap.shorten(n["title"],width=46,placeholder="…")
                    d.text((95,710+j*120),f"{j+1}. {title}",font=ImageFont.truetype(font,28),fill="white")
                source=" · ".join(dict.fromkeys(n["sources"][0]["name"].upper() for n in news))
                d.rounded_rectangle((95,1510,985,1610),radius=16,fill="#FFCD63")
                d.text((120,1540),source,font=ImageFont.truetype(font,27),fill="#091D36")
            else:
                import textwrap
                d.text((95,620),f"NOTICIA {i} DE 6",font=ImageFont.truetype(font,44),fill="#FFCD63")
                for j,line in enumerate(textwrap.wrap(news[i-1]["title"],width=30)):
                    d.text((95,760+j*80),line,font=ImageFont.truetype(font,45),fill="white")
                d.rounded_rectangle((95,1330,985,1510),radius=18,fill="#FFCD63")
                d.text((120,1360),"FUENTE VERIFICADA",font=ImageFont.truetype(font,28),fill="#091D36")
                d.text((120,1410),news[i-1]["sources"][0]["name"].upper(),font=ImageFont.truetype(font,45),fill="#091D36")
            d.text((95,1770),"colombia-al-dia.pages.dev",font=ImageFont.truetype(font,35),fill="white")
            png=td/f"{i:02d}.png";im.save(png);frames.append(png)
        concat=td/"scenes.txt"
        concat.write_text("".join(f"file '{p}'\\nduration {dur:.4f}\\n" for p,(_,dur) in zip(frames,segments))+f"file '{frames[-1]}'\\n")
        audio_concat=td/"audios.txt";audio_concat.write_text("".join(f"file '{p}'\\n" for p,_ in segments))
        joined=td/"audio.wav"
        subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(audio_concat),"-c:a","pcm_s16le",str(joined)],check=True)
        output=ROOT/"dist"/"orbiuno-2026-11-15-1900";output.mkdir(parents=True,exist_ok=True)
        mp4=output/"ORBIUNO_2026-11-15_1900_SALOME.mp4"
        subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(concat),"-i",str(joined),"-vf","fps=24,format=yuv420p","-c:v","libx264","-preset","veryfast","-c:a","aac","-shortest","-movflags","+faststart",str(mp4)],check=True)
        print("SALOME_ES_CO_GENERATED",mp4)
if __name__=="__main__":main()
