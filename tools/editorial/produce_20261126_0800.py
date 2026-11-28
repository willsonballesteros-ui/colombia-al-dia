#!/usr/bin/env python3
"""Produce approved daily editions using the last working renderer."""
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

ROOT=Path(__file__).resolve().parents[2]
from datetime import datetime, date
from zoneinfo import ZoneInfo
DAY=os.environ.get("EDITION_DAY", datetime.now(ZoneInfo("America/Bogota")).date().isoformat())
SLOT=os.environ.get("EDITION_SLOT", "08:00")
assert date.fromisoformat(DAY).isoformat()==DAY and SLOT in ("08:00","18:00")
STAMP=SLOT.replace(":","")
LABEL=date.fromisoformat(DAY).strftime("%d/%m/%Y")+" · "+("08:00 a. m." if SLOT=="08:00" else "06:00 p. m.")+" · Colombia"
BRAND=os.environ["NEWS_BRAND"]
assert BRAND in ("orbiuno","mycar")
WORK=ROOT/"build"/f"edicion-{DAY}-{STAMP}"/BRAND
OUT=ROOT/"media"/DAY/(f"edicion-{STAMP}-"+BRAND)
RESEARCH=ROOT/"editions"/"research"/(f"{BRAND}-{DAY}-{STAMP}-ready.json")
BASE_FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans"
LINKS={"orbiuno":"https://colombia-al-dia.pages.dev/","mycar":"https://busco-autos.pages.dev/"}
HANDLES={"orbiuno":"@resumen.noticias","mycar":"@mycar.buscoautos"}


def run(*args):
    result=subprocess.run([str(a) for a in args],capture_output=True,text=True,timeout=600)
    if result.returncode:
        print(result.stdout[-3000:],flush=True)
        print(result.stderr[-3000:],file=sys.stderr,flush=True)
        result.check_returncode()
    return result

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

def photo_and_credit(brand,idx,directory,story):
    from urllib.parse import urlsplit
    from scripts.orbiuno_media_assets import decode_image
    alt=story.get("alternatePhoto")
    if alt:
        if alt.get("license")!="Unsplash License" or urlsplit(alt["page"]).hostname!="unsplash.com" or urlsplit(alt["url"]).hostname!="images.unsplash.com":
            raise ValueError("Proveedor o licencia alternativa inválidos")
        if not all(alt.get(k) for k in ("title","author","context")):
            raise ValueError("Faltan créditos")
        with requests.get(alt["url"],timeout=(10,35),stream=True,allow_redirects=False) as r:
            r.raise_for_status()
            if r.status_code!=200 or not r.headers.get("Content-Type","").startswith("image/"):
                raise RuntimeError("Foto alternativa no disponible")
            raw=bytearray()
            for chunk in r.iter_content(65536):
                raw.extend(chunk)
                if len(raw)>12000000:
                    raise ValueError("Foto demasiado grande")
        im=decode_image(bytes(raw))
        name=f"foto-{idx+1:02d}.jpg"
        im.save(directory/name,quality=87,optimize=True)
        return {"file":name,"title":alt["title"],"source":alt["page"],"license":alt["license"],"author":alt["author"],
                "context":alt["context"],"rightsVerified":True,"imageType":"archival_relevant_photo","originalUrl":alt["url"],"modified":True}

    from scripts.orbiuno_media_assets import commons_info,fetch,decode_image
    title,context=(story.get("photoCommonsTitle") or "").removeprefix("File:"),story["photoCaption"]
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
    try:
        res=requests.get("https://www.google.com/s2/favicons",
            params={"domain":h,"sz":"256"},timeout=20,headers={"User-Agent":"ORBIUNO-media/1.0"})
    except requests.RequestException:
        print("SOURCE_ICON_UNAVAILABLE_SHOW_NAME",h,flush=True)
        return None
    if res.status_code!=200:
        # No inventar un logotipo; el nombre del medio queda en texto grande.
        print("SOURCE_FAVICON_UNAVAILABLE_SHOW_NAME",h,flush=True)
        return None
    if len(res.content)<200:return None
    with Image.open(io.BytesIO(res.content)) as f:
        f.load()
        if min(f.size)<16:return None
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
    d.text((74,401),LABEL,font=font(37),fill="#FFDD85")
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
    d.text((67,1825),"FOTO DE ARCHIVO · "+credit["author"][:35],font=font(18),fill="white")
    img.save(path,quality=91)

def duration(file):
    return float(run("ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=nw=1:nk=1",file).stdout.strip())

def encode_frame(image,audio,out):
    run("ffmpeg","-v","error","-y","-loop","1","-framerate","30","-i",image,
        "-i",audio,"-t",str(duration(audio)+.06),"-map","0:v","-map","1:a",
        "-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","25",
        "-r","30","-c:a","aac","-b:a","128k","-movflags","+faststart","-shortest",out)

def compile_brand(brand,items,reserves=()):
    n_expected=6 if brand=="orbiuno" else 5
    assert len(items)==n_expected
    folder=WORK/brand
    folder.mkdir(parents=True,exist_ok=True)
    creds=[]; logos=[]; selected=[]; seen=set()
    for n in list(items)+list(reserves):
        if len(selected)==n_expected: break
        i=len(selected)
        if n.get("url") in seen: continue
        try:
            if n.get("originalArticleReviewed") is not True or len(n.get("originalArticleTextEs",""))<640:
                raise ValueError("Artículo no aprobado")
            if not n["url"].startswith("https://") or n.get("originalArticleSourceUrls")!=[n["url"]]:
                raise ValueError("Fuente original no aprobada")
            credit=photo_and_credit(brand,i,folder,n)
            logo=source_logo(n["url"],folder,i)
            if not logo: raise RuntimeError("Logo de fuente no disponible")
        except (ValueError, OSError, RuntimeError, KeyError, AssertionError, requests.RequestException) as exc:
            if getattr(getattr(exc,"response",None),"status_code",None)==429 or "429" in str(exc): raise
            print("CANDIDATE_REJECTED", n.get("url"), type(exc).__name__, str(exc)[:120] if isinstance(exc, ValueError) else "", flush=True)
            continue
        n=dict(n,order=i+1);selected.append(n);seen.add(n["url"]);creds.append(credit);logos.append(logo)
        print("MEDIA_CHECK",brand,i+1,credit["license"],credit["author"],flush=True)
    if len(selected)!=n_expected: raise RuntimeError("Reservas verificadas insuficientes")
    items=selected
    # Sin saludo de ORBIUNO, sin portada resumen; primera lámina es noticia 1.
    outro="Escucha la lectura completa de cada noticia en el enlace de nuestro perfil."
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
    final=OUT/f"{brand.upper()}_{DAY}_{STAMP}_{n_expected}_NOTICIAS.mp4"
    OUT.mkdir(parents=True,exist_ok=True)
    run("ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",playlist,
        "-c","copy","-movflags","+faststart",final)
    assert final.stat().st_size>200_000
    sec=duration(final)
    assert 15<sec<180
    sha=hashlib.sha256(final.read_bytes()).hexdigest()
    url=LINKS[brand]
    caption=[f"{'ORBIUNO' if brand=='orbiuno' else 'MYCAR'} | {LABEL}",
        f"{n_expected} noticias verificadas con enlaces a las fuentes originales."]
    for i,n in enumerate(items,1):
        caption.append(f"{i}. {n['title']}\n{n['url']}")
    caption.extend(["",f"Escucha la lectura completa en el enlace del perfil {HANDLES[brand]}:",url,"",
     "Fotografías de archivo ilustrativas, con autor y licencias identificados.",
     "#ORBIUNO #NoticiasColombia" if brand=="orbiuno" else "#MyCar #AutosColombia",
     f"[{brand.upper()}-{DAY}-{STAMP}]"])
    cap="\n\n".join(caption)
    cap += "\n\nCréditos fotográficos y licencias, con recorte de imágenes: https://colombia-al-dia.pages.dev/"+brand+"-"+DAY+"-"+STAMP+".html"
    assert len(cap)<=2200
    (OUT/f"{brand}_caption.txt").write_text(cap,encoding="utf-8")
    (OUT/f"{brand}_media_credits.json").write_text(json.dumps(creds,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Dejar audios completos, crédito y fragmentos de la web accesibles con la edición.
    for i,c in enumerate(creds):
        shutil.copyfile(folder/c["file"],OUT/c["file"].replace("foto-","foto-"+brand+"-"))
        if logos[i]:
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
        im=f"/media/{DAY}/edicion-{STAMP}-{brand}/foto-"+brand+f"-{i:02d}.jpg"
        mp3=f"/media/{DAY}/edicion-{STAMP}-{brand}/"+brand+f"-noticia-{i:02d}.mp3"
        articles.append(f'<article><img src="{im}" alt="{safe(c["context"])}" loading="lazy"><h2>{i}. {safe(n["title"])}</h2>'
             f'<p><strong>{safe(n["source"])}</strong></p><audio controls src="{mp3}"></audio>'
             +paragraphs+f'<p><a href="{safe(n["url"])}">Fuente original</a></p>'
             f'<p class="credit">Foto de archivo: {safe(c["author"])} · {safe(c["license"])} · <a href="{safe(c["source"])}">Ficha y autoría</a>. {safe(c["context"])}</p></article>')
    page=f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{brand.upper()} · {LABEL}</title>
<style>body{{background:#0b2136;color:#fff;font:16px/1.55 system-ui;max-width:800px;margin:auto;padding:16px}}
a{{color:#6ce2df}}article{{background:#15304a;border-radius:16px;margin:20px 0;padding:18px}}
article img{{width:100%;height:auto;max-height:460px;object-fit:cover;border-radius:12px}}audio{{width:100%}}
.credit{{font-size:12px;color:#c8d3e2}}video{{width:100%;max-height:580px}}
</style></head><body><h1>{brand.upper()} Noticias · {LABEL}</h1>
<p>{n_expected} noticias verificadas, con fotos reales de archivo, créditos, lectura de cada nota y enlaces originales.</p>
<video controls playsinline src="/media/{DAY}/edicion-{STAMP}-{brand}/{final.name}"></video>
{''.join(articles)}<p>Más noticias: <a href="{url}">{url}</a></p></body></html>'''
    (OUT/f"{brand}_edition.html").write_text(page,encoding="utf-8")
    manifest={"brand":brand,"edition":DAY,"slot":SLOT,"newsCount":n_expected,
       "video":final.name,"duration":sec,"sha256":sha,
       "photoCredits":creds,"voice":"es-CO-SalomeNeural","voiceSpeed":1.25,
       "sourceUrls":[n["url"] for n in items],"imagesCount":len(creds),
       "logosCount":sum(bool(x) for x in logos),"sourceLabelsCount":n_expected,"audioSegments":n_expected+1,"openingSpeech":False,"openingCover":False,"fullNewsAudioFiles":n_expected,
       "published":False,"qa":"media_licenses_and_render_verified"}
    (OUT/f"{brand}_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT/"selected_news.json").write_text(json.dumps({"editionDate":DAY,"editionSlot":SLOT,"brand":brand.upper(),"news":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("READY_TO_SYNC_WEB",brand,final.name,sec,sha,flush=True)
    return manifest

def main():
    from datetime import datetime
    from zoneinfo import ZoneInfo
    assert datetime.now(ZoneInfo("America/Bogota")).date().isoformat()==DAY
    data=json.loads(RESEARCH.read_text(encoding="utf-8"))
    assert data["editionDate"]==DAY and data["editionSlot"]==SLOT
    assert data["brand"]==BRAND.upper() and data["editorialApproved"] is True
    assert not (OUT/"qa.json").exists(), "No duplicar la edición"
    m=compile_brand(BRAND,data["news"],data.get("reserveNews",[]))
    (OUT/"qa.json").write_text(json.dumps({"readyForWebSync":True,"brands":{BRAND:{"video":m["video"],"sha256":m["sha256"],"duration":m["duration"]}}},indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
