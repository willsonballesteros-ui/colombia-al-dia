#!/usr/bin/env python3
"""ORBIUNO: Reel de seguimiento aprobado, sin noticias duplicadas ni subtítulos.

Portada + dos bloques de cuatro noticias, resalte sincronizado, imágenes
fotográficas libres verificadas, crédito visible y voz ef_dora a 1,25.
Salida de trabajo editorial: NO publica ni programa Instagram.
"""
import io
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT=Path(__file__).resolve().parents[1]
DATE="2026-11-06"
DATA=ROOT/"editorial"/"2026-11-06-reemplazo-1330.json"
OUT=ROOT/"media"/DATE
NAME="reel_reemplazo_1330"
W,H=1080,1920
BG="#0D232A"; WHITE="#FAFAF8"; GOLD="#F9CC68"
CORAL="#FF745F"; AQUA="#62D9C7"; LAV="#C3A8FD"
SOFT="#17363D"; MUTED="#BCD5D7"
COLORS=[CORAL,AQUA,GOLD,LAV]
FONT=Path("/usr/share/fonts/truetype/dejavu")
VOICE="ef_dora"; RATE=1.25

def font(size,bold=True):
    return ImageFont.truetype(str(FONT/("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")),size)

def wrap(draw,value,size,max_width,limit=2):
    f=font(size); result=[]; line=""
    for word in str(value).split():
        trial=(line+" "+word).strip()
        if draw.textbbox((0,0),trial,font=f)[2] <= max_width:
            line=trial
        else:
            if line: result.append(line)
            line=word
    if line: result.append(line)
    if len(result)>limit:
        result=result[:limit]
        while result[-1] and draw.textbbox((0,0),result[-1]+"…",font=f)[2]>max_width:
            result[-1]=result[-1][:-1]
        result[-1]+="…"
    return result

def textlines(draw,s,x,y,size,max_width,max_lines=2,color=WHITE,line_gap=8):
    for line in wrap(draw,s,size,max_width,max_lines):
        draw.text((x,y),line,font=font(size),fill=color)
        y+=size+line_gap
    return y

def remote(url,required=False):
    if not url.startswith("https://"): raise ValueError("Se requieren URLs HTTPS")
    err=None
    for attempt in range(3):
        try:
            req=Request(url,headers={"User-Agent":"ORBIUNO newsroom / noncommercial editorial photo credit (contact via github.com/willsonballesteros-ui/colombia-al-dia)","Accept":"image/*"})
            with urlopen(req,timeout=24) as resp:
                raw=resp.read(10_000_000)
                if not raw or len(raw)>=10_000_000: raise RuntimeError("Imagen vacía o excesiva")
            im=Image.open(io.BytesIO(raw)); im.load()
            return im.convert("RGB")
        except Exception as e:
            err=e; time.sleep(1.5*(attempt+1))
    if required: raise RuntimeError("No se pudo verificar/descargar fotografía real: "+url+" "+str(err))
    return None

def photo_file(item):
    p=item.get("photo")
    if not p: return None
    if p.get("license") not in ("CC BY 4.0","CC BY 2.0"):
        raise RuntimeError("Fotografía sin licencia apta: "+item["id"])
    if not p.get("credit") or not p.get("page","").startswith("https://commons.wikimedia.org/wiki/File:"):
        raise RuntimeError("Fotografía sin autoría o ficha de licencia: "+item["id"])
    return remote(p["url"],required=True)

def favicon(item):
    host=(urlsplit(item["url"]).hostname or "").lower()
    if not re.fullmatch(r"[a-z0-9.-]+",host):return None
    icon=remote("https://www.google.com/s2/favicons?domain="+quote(host,safe="")+"&sz=128")
    return icon

def new_canvas():
    im=Image.new("RGB",(W,H),BG)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,20),fill=CORAL)
    d.rounded_rectangle((65,259,1015,437),radius=24,fill=SOFT)
    d.text((92,283),"ORBIUNO",font=font(66),fill=WHITE)
    d.text((96,372),"VIERNES 06 NOV 2026",font=font(27),fill=AQUA)
    d.rounded_rectangle((744,354,991,408),radius=12,fill=GOLD)
    d.text((778,367),"13:30",font=font(30),fill=BG)
    return im,ImageDraw.Draw(im)

def footer(d,count=8):
    d.rounded_rectangle((67,1504,1018,1653),radius=22,fill="#24464C")
    d.text((91,1528),"ESCUCHA EL DESARROLLO COMPLETO",font=font(33),fill=GOLD)
    d.text((93,1594),"@resumen.noticias  ·  enlace del perfil",font=font(26),fill=WHITE)
    d.text((78,1680),"colombia-al-dia.pages.dev",font=font(30),fill=AQUA)

def intro(items,target):
    im,d=new_canvas()
    d.text((76,466),"ACTUALIZACIÓN · SIN REPETIR",font=font(38),fill=GOLD)
    d.text((79,519),f"{len(items)} NOVEDADES VERIFICADAS",font=font(29),fill=WHITE)
    for i,item in enumerate(items):
        col=i//4; row=i%4
        x=71+col*474; y=578+row*216
        w=458
        d.rounded_rectangle((x,y,x+w,y+195),radius=19,fill=SOFT)
        d.rectangle((x,y,x+11,y+195),fill=COLORS[i%4])
        d.text((x+27,y+21),item["category"],font=font(20),fill=COLORS[i%4])
        textlines(d,item["title"],x+27,y+65,30,w-55,3,WHITE)
    footer(d)
    im.save(target,optimize=True)

def photo_preview(im,photo_rect):
    x0,y0,x1,y1=photo_rect
    return ImageOps.fit(im,(x1-x0,y1-y0),method=Image.Resampling.LANCZOS,centering=(.5,.45))

def block(items,first,active,photos,logos,target):
    im,d=new_canvas()
    d.text((75,465),("BLOQUE UNO" if first==0 else "BLOQUE DOS"),font=font(35),fill=GOLD)
    photo_owner=next((x for x in items[first:first+4] if x.get("photo")),None)
    if photo_owner:
        rect=(659,529,1016,1347)
        frame=photo_preview(photos[photo_owner["id"]],rect)
        im.paste(frame,(rect[0],rect[1]))
        d=ImageDraw.Draw(im)
        d.rounded_rectangle((662,1315,1018,1437),radius=14,fill=BG)
        d.text((680,1325),"FOTO DE ARCHIVO",font=font(18),fill=GOLD)
        textlines(d,photo_owner["photo"]["credit"]+" · "+photo_owner["photo"]["license"],680,1360,17,305,2,MUTED)
    else:
        d.rounded_rectangle((659,529,1016,1437),radius=20,fill=SOFT)
        d.text((690,965),"FUENTES",font=font(27),fill=GOLD)
        d.text((690,1005),"VERIFICADAS",font=font(27),fill=WHITE)
    for j,item in enumerate(items[first:first+4]):
        i=first+j
        x0=73; x1=635; y0=530+j*224; y1=y0+208
        selected=(i==active)
        bg=COLORS[i%4] if selected else SOFT
        fg=BG if selected else WHITE
        small=BG if selected else MUTED
        d.rounded_rectangle((x0,y0,x1,y1),radius=19,fill=bg)
        d.text((x0+18,y0+13),f"{i+1:02d}",font=font(27),fill=fg)
        d.text((x0+78,y0+19),item["category"],font=font(19),fill=small)
        textlines(d,item["title"],x0+23,y0+61,31,514,2,fg)
        icon=logos.get(item["source"])
        if icon:
            icon=ImageOps.contain(icon,(37,37))
            # Real favicon of the cited publisher, not an invented brand mark.
            im.paste(icon,(x0+25,y1-50))
            d=ImageDraw.Draw(im)
        d.text((x0+76,y1-47),item["source"],font=font(20),fill=small)
    footer(d)
    im.save(target,optimize=True)

def end(target):
    im,d=new_canvas()
    textlines(d,"LAS NOTICIAS SIGUEN EN NUESTRA WEB",81,559,53,915,3,GOLD,15)
    textlines(d,"Escoge la que te interese y escucha el reportaje completo, con sus fuentes.",86,820,39,895,4,WHITE,14)
    d.rounded_rectangle((81,1190,993,1395),radius=28,fill=CORAL)
    d.text((112,1246),"ENLACE EN LA BIO  ↓",font=font(43),fill=BG)
    footer(d)
    im.save(target,optimize=True)

def command(*args):
    cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    if cp.returncode: raise RuntimeError("Fallo de ffmpeg/ffprobe: "+cp.stderr[-1800:])
    return cp.stdout

def main():
    if datetime.now(ZoneInfo("America/Bogota")).date().isoformat()!=DATE:
        raise SystemExit("Edición caducada: no renderizar boletín de otra fecha")
    data=json.loads(DATA.read_text(encoding="utf-8"))
    items=data["items"]
    assert data["editionDate"]==DATE and 2<=len(items)<=10
    ids=set(); urls=set()
    for item in items:
        assert item["id"] not in ids and item["url"] not in urls
        assert urlsplit(item["url"]).scheme=="https" and len(item["speech"].split())>=15
        assert item["source"] and item["category"] and item["title"]
        ids.add(item["id"]); urls.add(item["url"])
    assert items[-1]["category"]=="ORBIUNO TE SORPRENDE"
    assert len(items)==8, "La edición de seguimiento acordada trae 8 novedades contrastadas"
    OUT.mkdir(parents=True,exist_ok=True)
    photos={}
    for item in items:
        if item.get("photo"): photos[item["id"]]=photo_file(item)
    assert set(photos)=={"maluma-gira","juanes"}, "Faltan fotografías reales acreditadas"
    logos={}
    for item in items:
        if item["source"] not in logos: logos[item["source"]]=favicon(item)
    opts=ort.SessionOptions(); opts.intra_op_num_threads=2; opts.inter_op_num_threads=1
    model=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=opts,providers=["CPUExecutionProvider"])
    speech=Kokoro.from_session(model,"/tmp/voices-v1.0.bin")
    phrases=[data["intro"]]+[x["speech"] for x in items]+[data["outro"]]
    with tempfile.TemporaryDirectory(prefix="orbiuno-reemplazo-") as d:
        scratch=Path(d); frames=[]; parts=[]
        rate=24000
        for i,phrase in enumerate(phrases):
            audio,sr=speech.create(phrase,VOICE,speed=RATE,lang="es",sentence_pause=.1,clause_pause=.06)
            a=np.asarray(audio,dtype="float32")
            if sr!=rate or a.size<1000 or np.max(np.abs(a))<.01: raise RuntimeError("Voz femenina ausente o silenciosa")
            pad=np.zeros(int(sr*.22),dtype="float32")
            parts.extend((a,pad))
            png=scratch/f"frame_{i:02}.png"
            if i==0:intro(items,png)
            elif i==len(phrases)-1:end(png)
            else:
                idx=i-1
                block(items,0 if idx<4 else 4,idx,photos,logos,png)
            frames.append((png,(a.size+pad.size)/sr))
        sf.write(scratch/"voice.wav",np.concatenate(parts),rate,subtype="PCM_16")
        listing=scratch/"frames.txt"
        with listing.open("w",encoding="utf-8") as f:
            for fn,duration in frames:
                f.write(f"file '{fn}'\n"); f.write(f"duration {duration:.6f}\n")
            f.write(f"file '{frames[-1][0]}'\n")
        output=OUT/(NAME+".mp4")
        command("ffmpeg","-hide_banner","-loglevel","error","-y","-nostdin",
                "-f","concat","-safe","0","-i",str(listing),"-i",str(scratch/"voice.wav"),
                "-vf","fps=24","-c:v","libx264","-preset","veryfast","-crf","27",
                "-pix_fmt","yuv420p","-c:a","aac","-b:a","128k","-movflags","+faststart",
                "-shortest",str(output))
        probe=json.loads(command("ffprobe","-v","error","-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height","-of","json",str(output)))
        duration=float(probe["format"]["duration"])
        if not 30 <=duration<=90: raise RuntimeError(f"Duración incompatible {duration:.2f}s")
        if not any(s.get("codec_type")=="audio" and s.get("codec_name")=="aac" for s in probe["streams"]):
            raise RuntimeError("Audio AAC no encontrado")
        if not any(s.get("codec_type")=="video" and s.get("width")==W and s.get("height")==H for s in probe["streams"]):
            raise RuntimeError("Video 9:16 no encontrado")
        if int(probe["format"]["size"])<100000: raise RuntimeError("MP4 sospechosamente corto")
        # Keep 3 proof frames for visual quality inspection.
        intro(items,OUT/(NAME+"_portada.png"))
        block(items,0,0,photos,logos,OUT/(NAME+"_bloque1.png"))
        block(items,4,7,photos,logos,OUT/(NAME+"_bloque2.png"))
        manifest={
          "editionDate":DATE,"scheduledSlot":"13:30 America/Bogota",
          "newsCount":len(items),"newsIds":[x["id"] for x in items],
          "format":"portada, 4 noticias, 4 noticias, cierre",
          "newsRepeatedFromMorning":0,"subtitles":False,"headlineSynchronized":True,
          "voice":"ef_dora","voiceEngine":"kokoro-onnx","voiceSpeed":RATE,
          "durationSeconds":round(duration,2),"resolution":[W,H],
          "photoCredits":[{"id":x["id"],**x["photo"]} for x in items if x.get("photo")],
          "logosPresent":{name:logos[name] is not None for name in logos},
          "sourceUrls":[x["url"] for x in items],
          "audioStreamVerified":True,"publicationVerified":False,"fileName":output.name
        }
        (OUT/(NAME+".json")).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print("ORBIUNO_REEMPLAZO_VALIDADO",json.dumps(manifest,ensure_ascii=False),flush=True)

if __name__=="__main__":main()
