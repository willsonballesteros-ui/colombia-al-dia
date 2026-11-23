#!/usr/bin/env python3
"""Reconstruir las ediciones del 22/11 con formato corregido y sin tocar originales.

Salida única y trazable: media/2026-11-22/correcciones-v2/. NO publica en Meta.
Utiliza únicamente noticias verificadas, fotos/creditos y audios aprobados.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/"media/2026-11-22"
OUTPUT=MEDIA/"correcciones-v2"
OUTPUT.mkdir(parents=True,exist_ok=True)

def run(*args):
    return subprocess.run([str(x) for x in args],check=True,capture_output=True,text=True)

def probe(path):
    d=json.loads(run("ffprobe","-v","error","-show_format","-show_streams","-of","json",path).stdout)
    video=next(x for x in d["streams"] if x.get("codec_type")=="video")
    audio=next(x for x in d["streams"] if x.get("codec_type")=="audio")
    assert video["codec_name"]=="h264" and video["width"]==1080 and video["height"]==1920
    assert audio["codec_name"]=="aac"
    sec=float(d["format"]["duration"])
    assert 15<sec<180,("Duración inválida",sec)
    return sec

def caption_orbiuno(m):
    out=["ORBIUNO Noticias | Edición corregida del 22/11/2026 · 6:00 p. m.",
         "Nueva versión con fecha visible, fuentes ampliadas y cierre narrado.",
         "Seis noticias y sus fuentes originales:"]
    for idx,item in enumerate(m["news"],1):
        out += [f'{idx}. {item["title"]}',item["sourceUrl"]]
    out += ["", "Escucha cada noticia completa en el enlace del perfil:",
            "https://colombia-al-dia.pages.dev/",
            "Fotografías reales de archivo ilustrativas; créditos y licencia en la web.",
            "#ORBIUNO #NoticiasColombia #Actualidad",
            "[ORBIUNO-2026-11-22-1800-CORREGIDA-V2]"]
    return "\n".join(out)

def make_orbiuno():
    from scripts.render_orbiuno_aprobado import render
    assets=MEDIA/"1800_assets"
    original=json.loads((MEDIA/"orbiuno_1800_6_noticias_manifest.json").read_text())
    assert original["newsCount"]==6
    build=ROOT/"build/correcciones-v2/orbiuno"
    m=render(news_file=ROOT/"noticias.json",day="2026-11-22",slot="18:00",
             assets=assets,output=build)
    assert m["newsIds"]==original["newsIds"] and m["spokenOutro"] is True
    assert m["logosCount"]==m["imagesCount"]==6
    video=build/m["video"]
    assert probe(video)>20
    target=OUTPUT/"ORBIUNO_2026-11-22_1800_6_NOTICIAS_CORREGIDA_V2.mp4"
    target.write_bytes(video.read_bytes())
    expected=hashlib.sha256(target.read_bytes()).hexdigest()
    cap=caption_orbiuno(m)
    assert len(cap)<2100
    (OUTPUT/"orbiuno_caption.txt").write_text(cap,encoding="utf-8")
    (OUTPUT/"orbiuno_manifest.json").write_text(json.dumps({**m,"video":target.name,"sha256":expected,
       "correctionVersion":2,"originalVideoUnchanged":True,"originalMediaId":"18080741297758859",
       "publishStatus":"not_published"},ensure_ascii=False,indent=2)+"\n")
    print("CORRECTION_ORBIUNO_QA_OK",target.name,expected,flush=True)
    return {"video":target.name,"duration":probe(target),"sha256":expected}

def make_mycar():
    from scripts.render_mycar_22nov_1800 import slide,fetch_source_icon
    from scripts.generate_voice import main as _voice_main
    folder=MEDIA/"mycar-pm-5"
    news=json.loads((folder/"editorial.json").read_text(encoding="utf-8"))
    pics=json.loads((folder/"credits.json").read_text(encoding="utf-8"))
    assert len(news)==len(pics)==5
    wd=ROOT/"build/correcciones-v2/mycar"
    wd.mkdir(parents=True,exist_ok=True)
    voice_input=wd/"outro_input.json"
    voice_input.write_text(json.dumps({"segments":[{"id":"despedida_v2",
       "text":"Gracias por acompañarnos en MyCar Noticias. Para escuchar la lectura completa "
              "de cada noticia, entra al enlace de nuestro perfil y visita "
              "busco autos punto pages punto dev."}]},ensure_ascii=False))
    # Esta llamada genera voz Salomé 1.25x con validación ffprobe y falla cerrado.
    run(sys.executable,ROOT/"scripts/generate_voice.py","--input",voice_input,
        "--out",wd/"voice")
    report=json.loads((wd/"voice/audio_report.json").read_text())
    assert report["status"]=="ok" and report["voice"]=="es-CO-SalomeNeural"
    assert report["tempo"]==1.25 and len(report["segments"])==1
    audios=[folder/"saludo.mp3"]+[folder/f"n{i:02d}.mp3" for i in range(1,6)]+[wd/"voice/despedida_v2.mp3"]
    assert all(p.is_file() and p.stat().st_size>3000 for p in audios)
    slide_paths=[]
    cover={"title":"Cinco noticias del motor para cerrar el domingo",
           "source":news[0]["source"],"photo_credit":pics[0]["author"]}
    scenes=[(cover,0,True)]
    scenes += [({**n,"photo_credit":pics[i]["author"]},i,False) for i,n in enumerate(news)]
    scenes += [({"title":"Escucha la lectura completa en el enlace del perfil",
                "source":"MYCAR","photo_credit":pics[0]["author"]},0,False)]
    for ix,(item,photo_ix,cover_flag) in enumerate(scenes):
        image=folder/f"photo-{photo_ix:02d}.jpg"
        assert image.is_file()
        icon=fetch_source_icon(news[photo_ix]["url"],wd/f"fuente-{photo_ix:02d}.png") if ix<6 else None
        dest=wd/f"slide-{ix:02d}.jpg"
        slide("MYCAR",item,image,"22 NOV 2026 · 18:00",5,ix,5,dest,cover_flag,icon)
        assert Image.open(dest).size==(1080,1920)
        slide_paths.append(dest)
    concat=wd/"slides.txt"
    durations=[float(run("ffprobe","-v","error","-show_entries","format=duration",
                 "-of","default=nw=1:nk=1",p).stdout.strip()) for p in audios]
    concat.write_text("".join("file '"+str(p.resolve())+"'\nduration "+str(max(.5,d))+"\n"
             for p,d in zip(slide_paths,durations))+
             "file '"+str(slide_paths[-1].resolve())+"'\n")
    audlist=wd/"audios.txt"
    audlist.write_text("".join("file '"+str(p.resolve())+"'\n" for p in audios))
    full=wd/"full.mp3"
    run("ffmpeg","-hide_banner","-v","error","-y","-f","concat","-safe","0",
        "-i",audlist,"-c:a","libmp3lame","-b:a","160k",full)
    target=OUTPUT/"MYCAR_2026-11-22_1800_5_NOTICIAS_CORREGIDA_V2.mp4"
    run("ffmpeg","-hide_banner","-v","error","-y","-f","concat","-safe","0",
        "-i",concat,"-i",full,"-map","0:v","-map","1:a",
        "-vf","fps=30,format=yuv420p","-c:v","libx264","-preset","veryfast",
        "-crf","23","-c:a","aac","-ar","48000","-b:a","160k",
        "-movflags","+faststart","-shortest",target)
    length=probe(target)
    assert abs(length-sum(durations))<2,(length,sum(durations))
    caption=["MYCAR Noticias | Edición corregida del 22/11/2026 · 6:00 p. m.",
             "Cinco noticias con fecha visible, fuentes más grandes y despedida narrada.",
             "Fuentes originales:"]
    caption += [f'{i}. {n["title"]}\n{n["url"]}' for i,n in enumerate(news,1)]
    caption += ["", "Escucha las noticias completas desde el enlace del perfil:",
                "https://busco-autos.pages.dev/",
                "Fotografías reales de archivo ilustrativo, no de los modelos exactos. Créditos en la web.",
                "#MyCar #BuscoAutos #NoticiasMotor",
                "[MYCAR-2026-11-22-1800-CORREGIDA-V2]"]
    text="\n".join(caption)
    assert len(text)<2200
    (OUTPUT/"mycar_caption.txt").write_text(text,encoding="utf-8")
    sha=hashlib.sha256(target.read_bytes()).hexdigest()
    m={"edition":"2026-11-22","slot":"18:00","newsCount":5,"video":target.name,
       "sha256":sha,"duration":length,"sources":[x["url"] for x in news],
       "voices":7,"voice":"es-CO-SalomeNeural","tempo":1.25,
       "correctionVersion":2,"originalVideoUnchanged":True,"publishStatus":"not_published"}
    (OUTPUT/"mycar_manifest.json").write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n")
    print("CORRECTION_MYCAR_QA_OK",target.name,sha,flush=True)
    return {"video":target.name,"duration":length,"sha256":sha}

def main():
    data={"orbiuno":make_orbiuno(),"mycar":make_mycar()}
    (OUTPUT/"qa.json").write_text(json.dumps(data,indent=2)+"\n")
    print("CORRECTIONS_READY",json.dumps(data),flush=True)

if __name__=="__main__":
    main()
