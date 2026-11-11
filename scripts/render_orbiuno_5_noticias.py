#!/usr/bin/env python3
"""ORBIUNO · cinco noticias, portada sincronizada con voz, y cinco escenas.
Sin imágenes no autorizadas: usa diseño tipográfico y créditos de fuentes.
No publica por Instagram; genera un MP4 y manifiesto verificable.
"""
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

ROOT = Path(__file__).resolve().parents[1]
W, H = 720, 1280
BG, PANEL, WHITE, TEAL, GOLD = "#081c34", "#163753", "#ffffff", "#53e3cf", "#ffcd63"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans"
def face(n, bold=True):
    return ImageFont.truetype(FONT + ("-Bold" if bold else "") + ".ttf", n)

def wrapped(draw, text, f, maxw, maxlines=4):
    result, buf = [], ""
    for word in str(text).split():
        trial = (buf + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=f)[2] <= maxw:
            buf = trial
        else:
            if buf: result.append(buf)
            buf = word
    if buf: result.append(buf)
    if len(result) > maxlines: raise RuntimeError("Texto demasiado largo para la lámina: " + text[:80])
    return result

def para(draw, text, x, y, f, width, ink=WHITE, step=None, limit=4):
    for line in wrapped(draw, text, f, width, limit):
        draw.text((x, y), line, font=f, fill=ink)
        y += step or int(f.size * 1.35)
    return y

def base(day, label):
    im=Image.new("RGB",(W,H), BG)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,15),fill=TEAL)
    d.text((44,48),"ORBIUNO",font=face(62),fill=WHITE)
    d.text((47,125),day+" · COLOMBIA Y EL MUNDO",font=face(20,False),fill=TEAL)
    d.rounded_rectangle((40,1160,680,1240),radius=19,fill=PANEL)
    d.text((62,1182),"@resumen.noticias",font=face(24),fill=WHITE)
    d.text((62,1212),"colombia-al-dia.pages.dev",font=face(18,False),fill=TEAL)
    return im,d

def cover(day,notes,active,out):
    im,d=base(day,"PORTADA")
    d.text((44,198),"5 NOTICIAS · EDICIÓN DE HOY",font=face(27),fill=GOLD)
    for i,n in enumerate(notes):
        y=276+i*162
        d.rounded_rectangle((41,y,679,y+148),radius=17,fill=TEAL if i==active else PANEL)
        ink=BG if i==active else WHITE
        d.text((58,y+15),f"{i+1:02d}",font=face(31),fill=ink)
        name=n["category"].upper()[:27]
        d.text((128,y+17),name,font=face(18),fill=ink)
        para(d,n["title"],128,y+51,face(23),510,ink,31,3)
    im.save(out)

def news_slide(day,n,index,out):
    im,d=base(day,"NOTICIA")
    d.text((44,198),f"NOTICIA {index}/5 · {n['category'].upper()[:24]}",font=face(25),fill=GOLD)
    y=280
    y=para(d,n["title"],43,y,face(36),634,WHITE,49,4)
    # Fotografía únicamente cuando existe archivo local y permiso documentado.
    photo=n.get("imageUrl","")
    valid=n.get("imageRightsVerified") is True and n.get("imageLicense") and n.get("imageCredit")
    local=(ROOT/photo.removeprefix("./")) if photo.startswith("./media/") else None
    if valid and local and local.is_file():
        picture=Image.open(local).convert("RGB")
        picture.thumbnail((626,390))
        im.paste(picture,(47+(626-picture.width)//2,570+(390-picture.height)//2))
        d=ImageDraw.Draw(im)
        d.text((47,980),"FOTO: "+n["imageCredit"][:42],font=face(18,False),fill=TEAL)
    else:
        d.rounded_rectangle((43,550,677,946),radius=24,fill=PANEL)
        d.text((72,606),"PANORAMA INFORMATIVO",font=face(26),fill=TEAL)
        para(d,n["summary"],73,674,face(25,False),568,WHITE,39,6)
    source=n["sources"][0]
    d.rounded_rectangle((43,1011,677,1110),radius=15,fill="#234e68")
    d.text((60,1031),"FUENTE ORIGINAL",font=face(20),fill=TEAL)
    para(d,source["name"].split(" · ")[0][:39],60,1065,face(17,False),577,WHITE,23,1)
    im.save(out)
    return bool(valid and local and local.is_file())

def cmd(*args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)

def main():
    data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=data["editionDate"]
    if day != datetime.now(ZoneInfo("America/Bogota")).date().isoformat():
        raise RuntimeError("La fecha editorial no corresponde a hoy")
    slot=os.getenv("ORBIUNO_EDITION_SLOT","12:00")
    notes=sorted([n for n in data["news"] if n.get("date")==day and n.get("editionSlot")==slot and n.get("verification")=="editorial_verified"],key=lambda x:x.get("instagramReelOrder",x.get("priority",999)))
    if len(notes)!=5 or len({n["id"] for n in notes})!=5:
        raise RuntimeError("Se requieren exactamente cinco noticias verificadas, únicas y de la edición seleccionada")
    for n in notes:
        if not n.get("sources") or not n["sources"][0]["url"].startswith("https://"): raise RuntimeError("Noticia sin fuente original")
    out=ROOT/"dist"/("orbiuno-"+day+"-"+slot.replace(":",""))
    out.mkdir(parents=True,exist_ok=True)
    opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
    session=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=opts,providers=["CPUExecutionProvider"])
    voice=Kokoro.from_session(session,"/tmp/voices-v1.0.bin")
    clips=[];pictures=[];timeline=[];t=0.0
    with tempfile.TemporaryDirectory() as temp:
        scratch=Path(temp)
        # Portada con todos los titulares visibles; realce calculado de la duración de cada frase.
        phrases=[f"ORBIUNO. {day}. Cinco noticias de Colombia y el mundo."]
        phrases += [f"Noticia {i+1}. {n['title']}." for i,n in enumerate(notes)]
        # Breve desarrollo de cada noticia con fuente atribuida.
        phrases += [f"{n['summary']} Fuente: {n['sources'][0]['name']}." for n in notes]
        phrases += ["ORBIUNO. Lee y escucha las noticias y sus fuentes en el enlace de nuestro perfil."]
        for j,phrase in enumerate(phrases):
            audio,sr=voice.create(phrase,"ef_dora",speed=1.25,lang="es",sentence_pause=.12,clause_pause=.06)
            arr=np.asarray(audio,dtype=np.float32)
            if not arr.size or max(abs(arr))<.01: raise RuntimeError("Voz vacía")
            pause=np.zeros(int(sr*.20),dtype=np.float32)
            clip=np.concatenate([arr,pause])
            clips.append(clip)
            length=len(clip)/sr
            frame=scratch/f"{j:02d}.png"
            if j < 6: cover(day,notes,max(0,j-1),frame) if j else cover(day,notes,-1,frame)
            elif j < 11: news_slide(day,notes[j-6],j-5,frame)
            else: cover(day,notes,-1,frame)
            pictures.append((frame,length))
            timeline.append({"scene":j,"from":round(t,3),"to":round(t+length,3),"voiceText":phrase,"newsId":notes[j-1]["id"] if 1<=j<=5 else notes[j-6]["id"] if 6<=j<=10 else None})
            t+=length
        joined=np.concatenate(clips)
        audio_path=scratch/"voice.wav";sf.write(audio_path,joined,sr)
        listing=scratch/"list.txt"
        listing.write_text("".join("file '"+str(p)+"'\nduration "+str(round(length,6))+"\n" for p,length in pictures)+"file '"+str(pictures[-1][0])+"'\n")
        target=out/("ORBIUNO_"+day+"_5_NOTICIAS.mp4")
        # Música original: cama ambiental sencilla, atenuada al 4 % bajo la narración.
        dur=t
        filter_audio="[1:a]aresample=48000,volume=1.0[v];[2:a]volume=0.035[m];[v][m]amix=inputs=2:duration=first:dropout_transition=0[a]"
        cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","concat","-safe","0","-i",str(listing),"-i",str(audio_path),
            "-f","lavfi","-i",f"sine=frequency=220:sample_rate=48000:duration={dur:.3f}",
            "-filter_complex",filter_audio,"-map","0:v","-map","[a]","-vf","fps=24,format=yuv420p",
            "-c:v","libx264","-preset","veryfast","-crf","25","-c:a","aac","-b:a","144k",
            "-pix_fmt","yuv420p","-movflags","+faststart","-shortest",str(target))
        probe=json.loads(cmd("ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,width,height","-of","json",str(target)).stdout)
        streams=probe["streams"];runtime=float(probe["format"]["duration"])
        if not (any(s.get("codec_type")=="audio" for s in streams) and any(s.get("codec_type")=="video" and s.get("width")==W and s.get("height")==H for s in streams) and 35<=runtime<=150):
            raise RuntimeError("MP4 inválido: falta pista o duración fuera de rango")
        digest=hashlib.sha256(target.read_bytes()).hexdigest()
        meta={"date":day,"slot":slot,"newsCount":5,"voice":"ef_dora","speed":1.25,"duration":runtime,"sha256":digest,"video":target.name,"scenes":timeline,"sources":[{"title":n["title"],"url":n["sources"][0]["url"]} for n in notes],"photoPolicy":"Solo fotografías con licencia verificada y archivo local; si no, lámina editorial con fuente","publishedToInstagram":False}
        (out/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("MP4_VERIFICADO",target,round(runtime,1),digest,flush=True)
if __name__=="__main__":
    main()
