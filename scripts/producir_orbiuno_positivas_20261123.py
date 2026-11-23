#!/usr/bin/env python3
"""ORBIUNO seis noticias positivas sin introducción ni portada para 23/11/2026.
Fotos de Commons con licencia, logo del medio, voz Salomé 1.25x, 9:16, MP4.
No llama a Meta; solo publica un operador tras QA y sincronización web.
"""
from __future__ import annotations
import io
import json
import hashlib
import html
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont
import requests

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-23"
SLOT="11:30"
WORK=ROOT/"build"/"edicion-20261123-1130-positivas"
OUT=ROOT/"media"/DAY/"edicion-1130-positivas"
RESEARCH=ROOT/"editions"/"research"/"2026-11-23-1130-positivas.json"
BASE_FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans"
LINKS={"orbiuno":"https://colombia-al-dia.pages.dev/",
       "mycar":"https://busco-autos.pages.dev/"}
HANDLES={"orbiuno":"@resumen.noticias","mycar":"@mycar.buscoautos"}
PHOTOS={
"orbiuno":[
 ["Students using a computer laptop.jpg","Estudiantes con computador en otro país. Archivo ilustrativo, NO muestra Olimpiadas STEM+ Colombia."],
 ["Surfer running for the waves (Unsplash).jpg","Fotografía de archivo de surf, NO muestra a Freddy Marimón ni Mundial de 2026."],
 ["Laboratory equipment.jpg","Equipos de laboratorio de otro país. Archivo, NO corresponde al laboratorio de EPQ."],
 ["Plastic pellets.jpg","Plásticos de archivo, NO son las resinas empleadas por los científicos del CSIC."],
 ["ROV JASON AT42-22.jpg","Robot submarino Jason en otra expedición, NO muestra hallazgo de 2026."],
 ["Foto no exif (3).jpg","Clínica en Eritrea en 2008, NO muestra la certificación de OMS de 2026."],
],
"mycar":[
 ["Toyota Yaris Cross 1.5 S HEV Hybrid 2026.jpg","Toyota Yaris Cross híbrida de otro mercado; ilustrativa, NO es la versión brasileña anunciada para Colombia."],
 ["Tank 700 PHEV 001.jpg","GWM Tank 700 PHEV, imagen de archivo; equipamiento y versión pueden diferir de Colombia."],
 ["Foton Tunland EV 001.jpg","Foton Tunland EV de 2019, ARCHIVO DE MODELO ANTERIOR; NO muestra la eTunland presentada en 2026."],
 ["Nissan Kicks e-Power P15 FL 1.2 LE Plus Aquamarine Metallic with Black roof 01.jpg","Nissan Kicks e-POWER de otra versión y mercado; ilustrativa, no es la unidad exhibida en Bogotá."],
 ["Citroën C3 (4th generation) DSC 8021.jpg","Citroën C3 europeo de cuarta generación; foto de archivo, puede diferir de la variante híbrida colombiana."],
]}

def run(*args):
    return subprocess.run([str(a) for a in args],check=True,capture_output=True,text=True)

def font(sz,bold=True):
    return ImageFont.truetype(BASE_FONT+("-Bold" if bold else "")+".ttf",sz)

def lines(d,content,sz,maxwidth,maxlines=3):
    f=font(sz);res=[];line=""
    for word in content.split():
        proposed=(line+" "+word).strip()
        if line and d.textbbox((0,0),proposed,font=f)[2]>maxwidth:
            res.append(line);line=word
        else:line=proposed
    if line:res.append(line)
    if len(res)>maxlines:raise ValueError("Titular no cabe: "+content)
    return res

def photo_and_credit(brand,idx,directory):
    from scripts.orbiuno_media_assets import commons_info,fetch,decode_image
    title,context=PHOTOS[brand][idx]
    meta=commons_info("File:"+title)
    assert meta.get("author") and meta.get("license") and meta.get("page")
    assert ("creativecommons" not in meta["license"].lower())
    raw=fetch(meta["url"])
    im=decode_image(raw)
    name=f"foto-{idx+1:02d}.jpg"
    im.save(directory/name,quality=87,optimize=True)
    credit={"file":name,"title":title,"source":meta["page"],"license":meta["license"],
            "author":meta["author"],"context":context,"rightsVerified":True,
            "imageType":"archival_relevant_photo","originalUrl":meta.get("original_url",""),
            "modified":True}
    return credit

def source_logo(url,directory,idx):
    from urllib.parse import urlsplit
    h=urlsplit(url).hostname
    if not h or not re.fullmatch(r"[a-z0-9.-]+",h):raise ValueError("Fuente sin dominio")
    res=requests.get("https://www.google.com/s2/favicons",
        params={"domain":h,"sz":"256"},timeout=20,headers={"User-Agent":"ORBIUNO-media/1.0"})
    res.raise_for_status()
    if len(res.content)<200:raise ValueError("Favicon fuente demasiado pequeño")
    with Image.open(io.BytesIO(res.content)) as f:
        f.load()
        if min(f.size)<16:raise ValueError("Icono de fuente no legible")
        icon=f.convert("RGBA")
        if min(icon.size)<96:
            icon=ImageOps.contain(icon,(128,128),method=Image.Resampling.NEAREST)
        icon.save(directory/f"fuente-{idx+1:02d}.png")
    return f"fuente-{idx+1:02d}.png"

def frame(brand,n,credit,logo,number,mode,path,day=DAY,slot=SLOT):
    W,H=1080,1920
    cover=Image.open(path.parent/credit["file"])
    img=ImageOps.fit(ImageOps.exif_transpose(cover.convert("RGB")),(W,H),method=Image.Resampling.LANCZOS)
    cover.close()
    d=ImageDraw.Draw(img,"RGBA")
    accent="#51E0D4" if brand=="orbiuno" else "#FFD65B"
    d.rectangle((0,0,W,145),fill=(5,22,45,246))
    d.rectangle((0,0,W,12),fill=accent)
    d.text((52,37),"ORBIUNO" if brand=="orbiuno" else "MYCAR",font=font(60),fill="white")
    d.rounded_rectangle((54,380,905,474),radius=20,fill=(6,20,40,242))
    d.text((74,401),"23/11/2026 · 11:30 A. M. · CO",font=font(37),fill="#FFDD85")
    if mode=="outro":
        d.rounded_rectangle((60,610,1030,1370),radius=25,fill=(5,22,45,242))
        segments=["ESCUCHA LA LECTURA","COMPLETA DE CADA NOTICIA","EN EL ENLACE DEL PERFIL",
                  HANDLES[brand],LINKS[brand].removeprefix("https://")]
        for i,t in enumerate(segments):
            for sz in (48,45,42,39,34,30):
                try:
                    ll=lines(d,t,sz,900,2);break
                except ValueError:continue
            for j,l in enumerate(ll):
                d.text((88,700+i*126+j*(sz+5)),l,font=font(sz),fill=accent if i in (0,2) else "white")
        img.save(path,quality=90);return
    # Logo grande fuera de controles inferiores de IG
    d.rounded_rectangle((54,1292,925,1440),radius=20,fill=(5,22,45,244))
    if logo:
        with Image.open(path.parent/logo) as lo:
            stamp=ImageOps.contain(lo.convert("RGBA"),(118,118))
            tile=Image.new("RGBA",(132,132),"white")
            tile.alpha_composite(stamp,((132-stamp.width)//2,(132-stamp.height)//2))
            img.paste(tile.convert("RGB"),(61,1300))
    d=ImageDraw.Draw(img,"RGBA")
    src=n["source"].upper()
    for sz in (44,40,36,32,28):
        try:
            ss=lines(d,src,sz,680 if logo else 850,2);break
        except ValueError:continue
    for i,t in enumerate(ss):d.text((212 if logo else 75,1320+i*(sz+7)),t,font=font(sz),fill=accent)
    d.rectangle((0,1450,W,1780),fill=(5,22,45,248))
    d.rectangle((0,1450,W,1463),fill=accent)
    kicker="PORTADA · "+("6 NOTICIAS" if brand=="orbiuno" else "5 NOTICIAS") if mode=="cover" else f"NOTICIA {number:02d} DE {6 if brand=='orbiuno' else 5}"
    d.text((60,1468),kicker,font=font(30),fill=accent)
    for size in (58,54,50,46,42,38,34):
        try:
            title_lines=lines(d,n["title"],size,915,3);break
        except ValueError:continue
    else:raise ValueError("Titular imposible")
    for i,l in enumerate(title_lines):d.text((60,1517+i*(size+13)),l,font=font(size),fill="white")
    # Crédito reducido con procedencia exacta en descripción y web
    d.rounded_rectangle((54,1810,935,1875),radius=12,fill=(5,22,45,237))
    d.text((67,1825),("IMAGEN ILUSTRATIVA · " if brand=="mycar" else "FOTO DE ARCHIVO · ")+credit["author"][:35],font=font(18),fill="white")
    img.save(path,quality=91)

def duration(file):
    return float(run("ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1",file).stdout.strip())

def encode_frame(image,audio,out):
    run("ffmpeg","-v","error","-y","-loop","1","-framerate","30","-i",image,
        "-i",audio,"-t",str(duration(audio)+.06),"-map","0:v","-map","1:a",
        "-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","25",
        "-r","30","-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",out)

def compile_brand(brand,items):
    n_expected=6 if brand=="orbiuno" else 5
    assert len(items)==n_expected
    folder=WORK/brand
    folder.mkdir(parents=True,exist_ok=True)
    creds=[]; logos=[]
    for i,n in enumerate(items):
        if n.get("originalArticleReviewed") is not True or len(n.get("originalArticleTextEs",""))<640:
            raise ValueError("Artículo no aprobado "+n["title"])
        if not n["url"].startswith("https://") or n.get("originalArticleSourceUrls")!=[n["url"]]:
            raise ValueError("Fuente original no aprobada")
        creds.append(photo_and_credit(brand,i,folder))
        logos.append(source_logo(n["url"],folder,i))
        print("MEDIA_CHECK",brand,i+1,creds[-1]["license"],creds[-1]["author"],flush=True)
    # Sin saludo de ORBIUNO, sin portada resumen; primera lámina es noticia 1.
    outro="Escucha la lectura completa de cada noticia en el enlace de nuestro perfil: colombia al día punto pages punto dev."
    ids=[f"n{i:02d}" for i in range(1,n_expected+1)]+["despedida"]
    scripts=[(n.get("spoken") or n.get("reelLine") or n["summary"]) for n in items]+[outro]
    voices={"segments":[{"id":sid,"text":text} for sid,text in zip(ids,scripts)]}
    voice_input=folder/"voice_input.json"
    voice_input.write_text(json.dumps(voices,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    audio=folder/"audio"
    run(sys.executable,ROOT/"scripts/generate_voice.py","--input",voice_input,"--out",audio)
    report=json.loads((audio/"audio_report.json").read_text())
    assert report["status"]=="ok" and report["voice"]=="es-CO-SalomeNeural"
    assert report["tempo"]==1.25 and len(report["segments"])==n_expected+1
    scenes=[(n,credit,lo,"story",i) for i,(n,credit,lo) in enumerate(zip(items,creds,logos),1)]
    scenes.append((items[0],creds[0],logos[0],"outro",n_expected+1))
    segments=[]
    for i,(n,credit,lo,mode,number) in enumerate(scenes):
        filename=folder/f"slide-{i:02}.jpg"
        frame(brand,n,credit,lo,number,mode,filename)
        ap=audio/(ids[i]+".mp3")
        if not ap.exists():raise ValueError("Audio ausente")
        part=folder/f"part-{i:02}.mp4"
        encode_frame(filename,ap,part)
        segments.append(part)
    playlist=folder/"parts.txt"
    playlist.write_text("".join("file '"+str(x.absolute())+"'\n" for x in segments),encoding="utf-8")
    final=OUT/("ORBIUNO_2026-11-23_1130_6_NOTICIAS_POSITIVAS.mp4" if brand=="orbiuno" else "MYCAR_2026-11-23_1000_5_NOTICIAS.mp4")
    OUT.mkdir(parents=True,exist_ok=True)
    run("ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",playlist,
        "-c","copy","-movflags","+faststart",final)
    assert final.stat().st_size>200_000
    sec=duration(final)
    assert 15<sec<180
    sha=hashlib.sha256(final.read_bytes()).hexdigest()
    url=LINKS[brand]
    caption=[f"{'ORBIUNO' if brand=='orbiuno' else 'MYCAR'} | Lunes 23/11/2026 · 11:30 a. m. · Colombia",
        f"{n_expected} noticias verificadas con enlaces a las fuentes originales."]
    for i,n in enumerate(items,1):
        caption.append(f"{i}. {n['title']}\n{n['url']}")
    caption.extend(["",f"Escucha la lectura completa en el enlace del perfil {HANDLES[brand]}:",url,"",
     "Fotografías de archivo ilustrativas, con autor y licencias identificados.",
     "#ORBIUNO #NoticiasColombia" if brand=="orbiuno" else "#MyCar #AutosColombia",
     f"[{brand.upper()}-2026-11-23-1130-POSITIVAS-V2]"])
    cap="\n\n".join(caption)
    assert len(cap)<=2200
    (OUT/f"{brand}_caption.txt").write_text(cap,encoding="utf-8")
    (OUT/f"{brand}_media_credits.json").write_text(json.dumps(creds,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Dejar audios completos, crédito y fragmentos de la web accesibles con la edición.
    for i,c in enumerate(creds):
        shutil.copyfile(folder/c["file"],OUT/c["file"].replace("foto-","foto-"+brand+"-"))
        shutil.copyfile(folder/logos[i],OUT/f"{brand}-logo-{i+1:02d}.png")
    # Narración WEB COMPLETA: redactado propio íntegro, sin leer resumen.
    full_input=folder/"full_voice_input.json"
    full_input.write_text(json.dumps({"segments":[{"id":f"full{i:02d}",
        "text":n["originalArticleTextEs"]} for i,n in enumerate(items,1)]},
        ensure_ascii=False),encoding="utf-8")
    full_audio=folder/"full_audio"
    run(sys.executable,ROOT/"scripts/generate_voice.py","--input",full_input,"--out",full_audio)
    full_report=json.loads((full_audio/"audio_report.json").read_text())
    assert full_report["status"]=="ok" and full_report["tempo"]==1.25
    assert len(full_report["segments"])==n_expected
    for i in range(1,n_expected+1):
        full_file=full_audio/f"full{i:02d}.mp3"
        assert full_file.is_file() and full_file.stat().st_size>1000
        shutil.copyfile(full_file,OUT/f"{brand}-noticia-{i:02d}.mp3")
    safe=lambda x:html.escape(str(x),quote=True)
    articles=[]
    for i,(n,c) in enumerate(zip(items,creds),1):
        paragraphs="".join("<p>"+safe(p)+"</p>" for p in n["originalArticleTextEs"].split("\n\n"))
        im="/media/2026-11-23/edicion-1000/foto-"+brand+f"-{i:02d}.jpg"
        mp3="/media/2026-11-23/edicion-1000/"+brand+f"-noticia-{i:02d}.mp3"
        articles.append(f'<article><img src="{im}" alt="{safe(c["context"])}" loading="lazy"><h2>{i}. {safe(n["title"])}</h2>'
             f'<p><strong>{safe(n["source"])}</strong></p><audio controls src="{mp3}"></audio>'
             +paragraphs+f'<p><a href="{safe(n["url"])}">Fuente original</a></p>'
             f'<p class="credit">Foto de archivo: {safe(c["author"])} · {safe(c["license"])} · <a href="{safe(c["source"])}">Ficha y autoría</a>. {safe(c["context"])}</p></article>')
    page=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand.upper()} · 23 noviembre 2026 · 11:30 AM</title>
<style>body{{background:#0b2136;color:#fff;font:16px/1.55 system-ui;max-width:800px;margin:auto;padding:16px}}
a{{color:#6ce2df}}article{{background:#15304a;border-radius:16px;margin:20px 0;padding:18px}}
article img{{width:100%;height:auto;max-height:460px;object-fit:cover;border-radius:12px}}audio{{width:100%}}
.credit{{font-size:12px;color:#c8d3e2}}video{{width:100%;max-height:580px}}
</style></head><body><h1>{brand.upper()} Noticias · Lunes 23/11/2026 · 11:30 a. m. Colombia</h1>
<p>{n_expected} noticias verificadas, con fotos reales de archivo, créditos, lectura de cada nota y enlaces originales.</p>
<video controls playsinline src="/media/2026-11-23/edicion-1000/{final.name}"></video>
{''.join(articles)}<p>Más noticias: <a href="{url}">{url}</a></p></body></html>'''
    (OUT/f"{brand}_edition.html").write_text(page,encoding="utf-8")
    manifest={"brand":brand,"edition":DAY,"slot":SLOT,"newsCount":n_expected,
       "video":final.name,"duration":sec,"sha256":sha,
       "photoCredits":creds,"voice":"es-CO-SalomeNeural","voiceSpeed":1.25,
       "sourceUrls":[n["url"] for n in items],"imagesCount":len(creds),
       "logosCount":len(logos),"audioSegments":n_expected+1,"openingSpeech":False,"openingCover":False,"fullNewsAudioFiles":n_expected,
       "published":False,"qa":"media_licenses_and_render_verified"}
    (OUT/f"{brand}_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("READY_TO_SYNC_WEB",brand,final.name,sec,sha,flush=True)
    return manifest

def main():
    data=json.loads(RESEARCH.read_text(encoding="utf-8"))
    assert data["editionDate"]==DAY
    assert data["brand"]=="ORBIUNO" and len(data["news"])==6
    compiled={"orbiuno":compile_brand("orbiuno",data["news"])}
    (OUT/"qa.json").write_text(json.dumps({"readyForWebSync":True,
      "brands":{k:{"video":v["video"],"sha256":v["sha256"],"duration":v["duration"]}
                for k,v in compiled.items()}},indent=2)+"\n",encoding="utf-8")
    print("ORBIUNO_POSITIVAS_QA_SUCCESS",flush=True)

if __name__=="__main__":
    main()
