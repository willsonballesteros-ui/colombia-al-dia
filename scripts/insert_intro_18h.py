#!/usr/bin/env python3
"""Inserta una introducción ORIGINAL hablada de la hora en el Reel ya verificado.
No publica ni reprograma: genera un nuevo MP4 para actualización del MISMO UUID Metricool.
La voz ef_dora se sintetiza de nuevo con el motor aprobado Kokoro.
"""
from pathlib import Path
import json, subprocess
import numpy as np, soundfile as sf, onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/"media"/"2026-11-06"
OLD=MEDIA/"reel_18pm.mp4"
NEW=MEDIA/"reel_18pm_con_intro.mp4"
WORK=Path("/tmp/orbiuno_intro_18")
WORK.mkdir(exist_ok=True,parents=True)
assert OLD.is_file() and OLD.stat().st_size>100000, "No existe Reel base"
def run(*args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
# Texto aprobado de apertura: puntual, informativo y no incluye una repetición del boletín de la mañana.
speech_text="Son las seis de la tarde, hora de Colombia. Bienvenidos a ORBIUNO, Colombia al Día. Estas son las diez noticias de esta edición, desde Colombia y el resto del mundo."
options=ort.SessionOptions()
options.intra_op_num_threads=2
options.inter_op_num_threads=1
options.enable_cpu_mem_arena=False
options.enable_mem_pattern=False
options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
s=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=options,providers=["CPUExecutionProvider"])
engine=Kokoro.from_session(s,"/tmp/voices-v1.0.bin")
audio,sr=engine.create(speech_text,"ef_dora",speed=1.25,lang="es",sentence_pause=.18,clause_pause=.10)
assert len(audio)>sr*4 and np.max(np.abs(audio))>.01
length=len(audio)/sr+0.45
sf.write(WORK/"introduccion.wav",np.asarray(audio,dtype=np.float32),sr,subtype="PCM_16")
# Lámina de presentadora tipográfica (sin avatar ficticio), texto dentro de área de seguridad.
im=Image.new("RGB",(1080,1920),"#102531")
d=ImageDraw.Draw(im)
p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def font(n):return ImageFont.truetype(p,n)
d.rectangle((0,0,1080,16),fill="#FF7659")
d.text((100,320),"ORBIUNO",font=font(110),fill="#FFFFFF")
d.text((106,450),"COLOMBIA AL DÍA",font=font(42),fill="#62DED0")
d.rounded_rectangle((100,590,980,1040),radius=44,fill="#173B47")
d.text((143,665),"SON LAS SEIS",font=font(65),fill="#FFC857")
d.text((143,782),"DE LA TARDE",font=font(65),fill="#FFFFFF")
d.text((143,905),"HORA DE COLOMBIA",font=font(32),fill="#62DED0")
d.text((110,1154),"LAS NOTICIAS DE",font=font(40),fill="#FFFFFF")
d.text((110,1220),"COLOMBIA Y EL MUNDO",font=font(38),fill="#FFFFFF")
d.text((110,1405),"VIERNES 6 DE NOVIEMBRE",font=font(27),fill="#FFC857")
d.text((110,1513),"🎙",font=font(30),fill="#62DED0") if False else None
im.save(WORK/"introduccion.png")
# Se preservan los primeros 3.18 segundos musicales del Reel ya aprobado,
# luego la apertura hablada, luego las diez noticias originales.
common=["-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p","-r","24","-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-movflags","+faststart"]
base=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y"]
run(*base,"-i",str(OLD),"-t","3.18",*common,str(WORK/"a.mp4"))
run(*base,"-loop","1","-framerate","24","-i",str(WORK/"introduccion.png"),"-i",str(WORK/"introduccion.wav"),
    "-filter_complex",f"[1:a]apad,atrim=duration={length:.3f}[aa]",
    "-map","0:v","-map","[aa]","-t",f"{length:.3f}",*common,str(WORK/"b.mp4"))
run(*base,"-ss","3.18","-i",str(OLD),*common,str(WORK/"c.mp4"))
(WORK/"list.txt").write_text("".join(f"file '{WORK/name}'\n" for name in ("a.mp4","b.mp4","c.mp4")),encoding="utf-8")
run(*base,"-f","concat","-safe","0","-i",str(WORK/"list.txt"),"-c","copy","-movflags","+faststart",str(NEW))
j=json.loads(run("ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,codec_name,width,height","-of","json",str(NEW)).stdout)
dur=float(j["format"]["duration"])
assert 55<dur<85,("Duración inesperada",dur)
assert any(z.get("codec_type")=="audio" for z in j["streams"])
assert any(z.get("codec_type")=="video" and z.get("width")==1080 and z.get("height")==1920 for z in j["streams"])
manifest={"edition":"2026-11-06 18:00 America/Bogota","publicationVerified":False,"introduccionHablada":speech_text,"voice":"ef_dora","nativeSpeed":1.25,"sonicLogoAtStart":True,"durationSeconds":dur,"output":NEW.name,"originalVideoPreserved":str(OLD.name),"newsCount":10}
(MEDIA/"reel_18pm_con_intro.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("REEL_CON_INTRO_VALIDADO",json.dumps(manifest,ensure_ascii=False),flush=True)
