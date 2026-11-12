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

def base():
    im = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(im)
    draw.rectangle((0, 0, W, 15), fill=TEAL)
    return im, draw


def cover(day, slot, notes, active, out):
    im, draw = base()
    # Keep the entire cover inside the centered 720 x 720 feed crop.
    draw.text((48, 306), "ORBIUNO", font=face(55), fill=WHITE)
    draw.text((50, 374), f"{day}  ·  EDICIÓN {slot}  ·  5 NOTICIAS", font=face(22), fill=GOLD)
    for index, note in enumerate(notes):
        y = 422 + index * 99
        selected = index == active
        ink = BG if selected else WHITE
        draw.rounded_rectangle((47, y, 673, y + 91), radius=14, fill=TEAL if selected else PANEL)
        draw.text((62, y + 12), f"{index + 1:02d}", font=face(29), fill=ink)
        draw.text((119, y + 7), note["category"].upper()[:27], font=face(16), fill=ink)
        para(draw, note["title"], 119, y + 28, face(22), 535, ink, 20, 3)
    draw.text((51, 931), "@resumen.noticias · colombia-al-dia.pages.dev", font=face(18), fill=TEAL)
    im.save(out)


def news_slide(day, note, index, out):
    im, draw = base()
    draw.text((48, 306), "ORBIUNO", font=face(42), fill=WHITE)
    draw.text((49, 364), f"{day} · {index}/5 · {note['category'].upper()[:24]}", font=face(19), fill=GOLD)
    para(draw, note["title"], 48, 404, face(31), 620, WHITE, 36, 3)
    photo = note.get("imageUrl", "")
    valid = note.get("imageRightsVerified") is True and note.get("imageLicense") and note.get("imageCredit")
    local = (ROOT / photo.removeprefix("./")) if photo.startswith("./media/") else None
    has_photo = bool(valid and local and local.is_file())
    if has_photo:
        with Image.open(local) as original:
            picture = original.convert("RGB")
        picture.thumbnail((624, 286))
        im.paste(picture, (48 + (624 - picture.width) // 2, 524 + (286 - picture.height) // 2))
        draw.text((48, 817), "FOTO DE REFERENCIA" if note.get("imageCaption") else "FOTOGRAFÍA", font=face(15), fill=TEAL)
        para(draw, note["imageCredit"] + " · " + note["imageLicense"], 48, 842, face(16, False), 624, WHITE, 20, 2)
    else:
        draw.rounded_rectangle((48, 525, 672, 826), radius=18, fill=PANEL)
        para(draw, note["summary"], 67, 550, face(23, False), 585, WHITE, 31, 8)
    source = note["sources"][0]["name"].split(" · ")[0]
    draw.rounded_rectangle((48, 896, 672, 952), radius=12, fill="#234e68")
    para(draw, "FUENTE · " + source, 64, 912, face(22), 594, WHITE, 23, 1)
    im.save(out)
    return has_photo

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
    clips=[];pictures=[];timeline=[];photos=[];t=0.0
    with tempfile.TemporaryDirectory() as temp:
        scratch=Path(temp)
        # Portada con todos los titulares visibles; realce calculado de la duración de cada frase.
        phrases=[f"ORBIUNO. {day}. Cinco noticias de Colombia y el mundo."]
        phrases += [f"Noticia {i+1}. {n['title']}." for i,n in enumerate(notes)]
        # Breve desarrollo de cada noticia con fuente atribuida.
        phrases += [f"{n['summary']} Fuente: {n['sources'][0]['name']}." for n in notes]
        phrases += ["ORBIUNO. Síguenos en nuestra página web y escucha en voz alta la noticia que más te interese. El enlace está en el perfil."]
        for j,phrase in enumerate(phrases):
            audio,sr=voice.create(phrase,"ef_dora",speed=1.25,lang="es",sentence_pause=.12,clause_pause=.06)
            arr=np.asarray(audio,dtype=np.float32)
            if not arr.size or max(abs(arr))<.01: raise RuntimeError("Voz vacía")
            pause=np.zeros(int(sr*.20),dtype=np.float32)
            clip=np.concatenate([arr,pause])
            clips.append(clip)
            length=len(clip)/sr
            frame=scratch/f"{j:02d}.png"
            if j < 6: cover(day,slot,notes,max(0,j-1),frame) if j else cover(day,slot,notes,-1,frame)
            elif j < 11:
                note = notes[j-6]
                if news_slide(day, note, j-5, frame):
                    photos.append({
                        "newsId": note["id"],
                        "credit": note["imageCredit"],
                        "license": note["imageLicense"],
                        "sourceUrl": note.get("imageSourceUrl", ""),
                    })
            else: cover(day,slot,notes,-1,frame)
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
        meta={"date":day,"slot":slot,"newsCount":5,"voice":"ef_dora","speed":1.25,"duration":runtime,"sha256":digest,"video":target.name,"scenes":timeline,"photos":photos,"sources":[{"id":n["id"],"title":n["title"],"url":n["sources"][0]["url"]} for n in notes],"photoPolicy":"Solo fotografías con licencia verificada y archivo local; si no, lámina editorial con fuente","publishedToInstagram":False}
        (out/"manifest.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("MP4_VERIFICADO",target,round(runtime,1),digest,flush=True)
if __name__=="__main__":
    main()
