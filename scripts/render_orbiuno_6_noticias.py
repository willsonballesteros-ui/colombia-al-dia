#!/usr/bin/env python3
"""ORBIUNO · Reel de seis noticias verificadas; no publica ni modifica noticias.

Diseño sin capturas ni fotografías de terceros. Fuente original en cada lámina.
Salida en dist/ con MP4, manifiesto y SHA para preflight web y Meta.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import soundfile as sf
import onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
BOGOTA=ZoneInfo("America/Bogota")
W,H=1080,1920
BG="#091D36"
PANEL="#163753"
WHITE="#FFFFFF"
TEAL="#55E3CF"
GOLD="#FFCD63"
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans"


def face(size,bold=True):
    return ImageFont.truetype(FONT+("-Bold" if bold else "")+".ttf",size)


def lines(draw,text,font,width,limit):
    out=[];line=""
    for word in str(text).split():
        trial=(line+" "+word).strip()
        if draw.textbbox((0,0),trial,font=font)[2]<=width:
            line=trial
        else:
            if line:out.append(line)
            line=word
    if line:out.append(line)
    if len(out)>limit:
        raise RuntimeError("Texto supera el espacio seguro: "+str(text)[:80])
    return out


def paragraph(draw,text,x,y,size,width,limit=4,ink=WHITE,leading=1.35):
    font=face(size)
    for line in lines(draw,text,font,width,limit):
        draw.text((x,y),line,font=font,fill=ink)
        y+=int(size*leading)
    return y


def base(day,stamp):
    image=Image.new("RGB",(W,H),BG)
    draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,W,16),fill=TEAL)
    draw.text((100,280),"ORBIUNO",font=face(76),fill=WHITE)
    draw.text((102,392),"COLOMBIA Y EL MUNDO",font=face(29),fill=TEAL)
    draw.rounded_rectangle((100,452,980,575),radius=22,fill=GOLD)
    draw.text((125,472),day+"  ·  "+stamp,font=face(34),fill=BG)
    draw.rectangle((0,1570,W,1582),fill=TEAL)
    draw.text((100,1623),"ESCUCHA LAS NOTICIAS COMPLETAS",font=face(32),fill=GOLD)
    draw.text((102,1692),"colombia-al-dia.pages.dev",font=face(33),fill=WHITE)
    draw.text((102,1760),"@resumen.noticias",font=face(27),fill=TEAL)
    return image,draw


def cover(day,stamp,notes,path):
    image,draw=base(day,stamp)
    draw.text((102,638),"6 NOTICIAS VERIFICADAS",font=face(42),fill=GOLD)
    for i,n in enumerate(notes):
        y=730+i*125
        draw.rounded_rectangle((100,y,980,y+112),radius=15,fill=PANEL)
        draw.text((122,y+18),f"{i+1:02d}",font=face(37),fill=GOLD)
        paragraph(draw,n["title"],210,y+18,27,720,2)
    # Franja de fuentes visible también en la portada, no solo en cada noticia.
    # Son nombres editoriales de las fuentes, no logotipos oficiales no verificados.
    names=list(dict.fromkeys(n["sources"][0]["name"].upper() for n in notes))
    draw.rounded_rectangle((100,1500,980,1555),radius=12,fill=GOLD)
    label="FUENTES: "+"  ·  ".join(names)
    font_size=25
    while draw.textbbox((0,0),label,font=face(font_size))[2]>830 and font_size>17:
        font_size-=1
    draw.text((125,1511),label,font=face(font_size),fill=BG)
    image.save(path)


def story(day,stamp,n,position,path):
    image,draw=base(day,stamp)
    draw.text((101,658),f"NOTICIA {position} DE 6",font=face(37),fill=GOLD)
    paragraph(draw,n["title"],101,740,54,878,5,leading=1.3)
    draw.rounded_rectangle((100,1100,980,1490),radius=24,fill=GOLD)
    draw.text((135,1130),"FUENTE VERIFICADA",font=face(31),fill=BG)
    # Nombre editorial de la fuente destacado, NO fingir logotipo oficial
    source=n["sources"][0]["name"].upper()
    source_size=76 if len(source)<16 else 59
    paragraph(draw,source,135,1210,source_size,790,2,ink=BG,leading=1.15)
    from urllib.parse import urlsplit
    domain=urlsplit(n["sources"][0]["url"]).hostname or ""
    paragraph(draw,domain.removeprefix("www."),135,1405,27,790,2,ink=BG)
    image.save(path)


def closing(day,stamp,path):
    image,draw=base(day,stamp)
    paragraph(draw,"Consulta nuestras seis noticias y sus fuentes originales en la web.",100,740,52,860,5)
    image.save(path)


def run(*args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)


def main():
    db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=os.getenv("ORBIUNO_EDITION_DATE") or datetime.now(BOGOTA).date().isoformat()
    slot=os.getenv("ORBIUNO_EDITION_SLOT","08:00")
    if slot not in ("08:00","12:00","18:00","19:00"):
        raise RuntimeError("Franja inválida")
    if db["editionDate"]!=day:
        raise RuntimeError("Edición caducada. No utilizar noticias del día anterior")
    notes=sorted((n for n in db["news"] if n.get("date")==day and
                  n.get("editionSlot")==slot and
                  n.get("verification")=="editorial_verified"),
                 key=lambda n:n.get("priority",999))
    if len(notes)!=6 or len({n["id"] for n in notes})!=6:
        raise RuntimeError("Se requieren exactamente seis noticias actuales y únicas")
    for n in notes:
        if not n.get("sources") or not n["sources"][0].get("url","").startswith("https://"):
            raise RuntimeError("Noticia sin fuente HTTPS")
        if n.get("originalArticleReviewed") is not True:
            raise RuntimeError("Texto propio no revisado")
        if n.get("imageUrl") and n.get("imageRightsVerified") is not True:
            raise RuntimeError("Fotografía sin permiso")
    out=ROOT/"dist"/("orbiuno-"+day+"-"+slot.replace(":",""))
    out.mkdir(parents=True,exist_ok=True)
    options=ort.SessionOptions()
    options.intra_op_num_threads=2
    options.inter_op_num_threads=1
    model=os.environ.get("ORBIUNO_VOICE_MODEL","/tmp/kokoro-v1.0.onnx")
    bank=os.environ.get("ORBIUNO_VOICE_BANK","/tmp/voices-v1.0.bin")
    session=ort.InferenceSession(model,sess_options=options,providers=["CPUExecutionProvider"])
    voice=Kokoro.from_session(session,bank)
    stamp=slot+" HORA COLOMBIA"
    slot_name={"08:00":"ocho de la mañana","12:00":"doce del mediodía","18:00":"seis de la tarde","19:00":"siete de la noche"}[slot]
    scene_text=["Saludos. Estas son seis noticias de Colombia y el mundo. Edición de las "+slot_name+"."]
    for n in notes:
        phrase=str(n.get("reelLine") or n["summary"]).strip()
        if len(phrase.split())>27:
            raise RuntimeError("Guion demasiado extenso; ajustar reelLine de "+n["id"])
        scene_text.append(phrase)
    scene_text.append("Escucha las noticias completas en nuestra página web: colombia al día punto pages punto dev. ¡Sigue a ORBIUNO Noticias!")
    audio_arrays=[];sr_ref=None
    for text in scene_text:
        audio,sr=voice.create(text,"ef_dora",speed=1.25,lang="es",
                              sentence_pause=.12,clause_pause=.06)
        arr=np.asarray(audio,dtype=np.float32)
        if not arr.size or np.max(np.abs(arr))<.01:
            raise RuntimeError("Audio ausente en segmento")
        if sr_ref is not None and sr_ref!=sr:
            raise RuntimeError("Frecuencia de audio inconsistente")
        sr_ref=sr
        audio_arrays.append(arr)
    natural=sum(len(a)/sr_ref for a in audio_arrays)
    if natural>59.2:
        raise RuntimeError(f"Guion demasiado largo: {natural:.2f}s; corregir texto, no velocidad")
    pause_each=max(.18,(51.0-natural)/len(audio_arrays))
    durations=[len(a)/sr_ref+pause_each for a in audio_arrays]
    duration=sum(durations)
    if not 50<=duration<=60:
        raise RuntimeError(f"Duración no cumple: {duration:.2f}s")
    with tempfile.TemporaryDirectory() as td:
        tmp=Path(td);images=[]
        for i,dur in enumerate(durations):
            path=tmp/f"scene-{i:02d}.png"
            if i==0:cover(day,stamp,notes,path)
            elif i<=6:story(day,stamp,notes[i-1],i,path)
            else:closing(day,stamp,path)
            images.append(path)
        joined=np.concatenate([np.concatenate([
            arr,np.zeros(round(pause_each*sr_ref),dtype=np.float32)
        ]) for arr in audio_arrays])
        sound=tmp/"voice.wav"
        sf.write(sound,joined,sr_ref)
        concat=tmp/"images.txt"
        concat.write_text("".join(
            f"file '{p}'\nduration {dur:.6f}\n"
            for p,dur in zip(images,durations)
        )+f"file '{images[-1]}'\n",encoding="utf-8")
        video=out/("ORBIUNO_"+day+"_"+slot.replace(":","")+"_6_NOTICIAS.mp4")
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","concat","-safe","0","-i",str(concat),
            "-i",str(sound),"-map","0:v","-map","1:a",
            "-vf","fps=24,format=yuv420p","-c:v","libx264",
            "-preset","veryfast","-crf","24","-c:a","aac","-b:a","144k",
            "-movflags","+faststart","-shortest",str(video))
        info=json.loads(run("ffprobe","-v","error","-show_entries",
                            "format=duration,size:stream=codec_type,codec_name,width,height",
                            "-of","json",str(video)).stdout)
    d=float(info["format"]["duration"])
    vs=[s for s in info["streams"] if s["codec_type"]=="video"]
    aus=[s for s in info["streams"] if s["codec_type"]=="audio"]
    if not (50<=d<=60 and video.stat().st_size>100000 and
            vs and vs[0].get("width")==W and vs[0].get("height")==H and
            vs[0].get("codec_name")=="h264" and aus and aus[0].get("codec_name")=="aac"):
        raise RuntimeError("MP4 no pasó inspección audiovisual completa")
    sha=hashlib.sha256(video.read_bytes()).hexdigest()
    manifest={"edition":day,"slot":slot,"newsCount":6,
              "newsIds":[n["id"] for n in notes],"voice":"ef_dora",
              "voiceSpeed":1.25,"width":W,"height":H,"duration":d,
              "sha256":sha,"video":video.name,"sourceOnly":True,
              "news":[{"id":n["id"],"title":n["title"],
                       "sourceUrl":n["sources"][0]["url"]} for n in notes],
              "published":False,"instagramId":None,"instagramPermalink":None}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("MP4_VALIDATED",str(video),round(d,2),sha)

if __name__=="__main__":
    main()
