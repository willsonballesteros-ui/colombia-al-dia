#!/usr/bin/env python3
"""ORBIUNO actualización visual 14-11-2026.
Recapitula seis noticias al inicio, conserva EXACTAMENTE las seis láminas reales del visor
y audio ya verificado. Nunca publica ni elimina Instagram.
"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from datetime import datetime
from zoneinfo import ZoneInfo
import json,os,hashlib,subprocess,tempfile
from kokoro_onnx import Kokoro
import onnxruntime as ort
import soundfile as sf
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"media/2026-11-14-publicable"
OUT=ROOT/"media/2026-11-14-orbiuno-actualizacion"
OUT.mkdir(exist_ok=True,parents=True)
meta=json.loads((SRC/"orbiuno-credits.json").read_text())
assert len(meta["stories"])==6 and len(meta["license_photos"])==6
# Segmentos existentes: los seis audios y las seis imágenes publicadas; no modificar ni sustituir.
for i in range(1,7):
 assert (SRC/f"orbiuno-{i:02d}.jpg").is_file()
 assert (SRC/f"orbiuno-14nov-{i:02d}.wav").is_file()
P="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
R="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def font(n,b=True):return ImageFont.truetype(P if b else R,n)
def wrap(d,text,ft,max_w):
 lines=[];s=""
 for word in text.split():
  test=(s+" "+word).strip()
  if d.textbbox((0,0),test,font=ft)[2]>max_w and s:
   lines.append(s);s=word
  else:s=test
 if s:lines.append(s)
 return lines
titles=[
 "Bogotá celebra la cultura mexicana",
 "Ruta literaria de escritoras en Bogotá",
 "Estados Unidos normaliza vuelos",
 "Denza de BYD debuta en India",
 "Starship despliega satélites",
 "Karol G obtiene dos Latin Grammy"
]
# Collage de las mismas fotos reales utilizadas por el visor: extraer solo sección fotográfica superior.
cover=Image.new("RGB",(720,1280),(5,19,35)); d=ImageDraw.Draw(cover)
d.rectangle((0,0,720,216),fill=(8,30,53))
d.text((30,20),"ORBIUNO",font=font(66),fill=(255,209,46))
d.text((32,107),"SÁBADO 14 NOVIEMBRE 2026",font=font(27),fill="white")
now=datetime.now(ZoneInfo("America/Bogota"))
label=now.strftime("%I:%M %p").lstrip("0").replace("AM","A. M.").replace("PM","P. M.")
d.rectangle((30,153,690,210),fill=(255,205,40))
d.text((45,164),"HORA DE PRODUCCIÓN: "+label,font=font(25),fill=(7,24,41))
for i in range(6):
 x=30+(i%2)*342;y=237+(i//2)*301
 im=Image.open(SRC/f"orbiuno-{i+1:02d}.jpg").convert("RGB")
 # La fotografía ocupa el área superior de la lámina; quitar el panel inferior de texto.
 photo=im.crop((0,99,im.width,842))
 photo=ImageOps.fit(photo,(326,215),Image.Resampling.LANCZOS)
 cover.paste(photo,(x,y))
 d.rectangle((x,y+213,x+326,y+282),fill=(5,22,40))
 for j,line in enumerate(wrap(d,f"{i+1}. {titles[i]}",font(19),310)[:2]):
  d.text((x+8,y+223+j*22),line,font=font(19),fill="white")
d.rectangle((0,1175,720,1280),fill=(7,25,46))
d.text((24,1193),"PRIMERO: LAS 6 NOTICIAS EN RESUMEN",font=font(26),fill=(255,209,46))
d.text((26,1232),"Después, cada noticia con su foto real y fuente",font=font(17,False),fill="white")
cover_path=OUT/"portada-resumen-seis-fotos.jpg"
cover.save(cover_path,quality=90)
speech=("Orbiuno, actualización del sábado catorce de noviembre. "
 "Primero, el resumen de nuestras seis noticias. "
 "Bogotá celebra un festival de cultura mexicana. "
 "Una ruta literaria destaca a las escritoras. "
 "Estados Unidos normaliza sus vuelos después de fallas. "
 "Denza, la marca de lujo de B Y D, debuta en India. "
 "Starship despliega satélites en órbita. "
 "Y Karol G recibe dos premios Latin Grammy. "
 "Ahora, vamos con los detalles y las imágenes reales de referencia.")
session=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",providers=["CPUExecutionProvider"])
tts=Kokoro.from_session(session,"/tmp/voices-v1.0.bin")
audio,sr=tts.create(speech,"ef_dora",speed=1.25,lang="es",sentence_pause=.10,clause_pause=.06)
cover_wav=OUT/"resumen-dora.wav"
sf.write(cover_wav,np.asarray(audio,dtype=np.float32),sr)
def duration(f):
 return float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(f)]).decode())
with tempfile.TemporaryDirectory() as tmp:
 tmp=Path(tmp)
 segments=[(cover_path,cover_wav)]+[(SRC/f"orbiuno-{i:02d}.jpg",SRC/f"orbiuno-14nov-{i:02d}.wav") for i in range(1,7)]
 parts=[]
 for index,(photo,wav) in enumerate(segments):
  part=tmp/f"part{index}.mp4"
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-framerate","25","-i",str(photo),"-i",str(wav),
      "-vf","scale=720:1280,format=yuv420p","-c:v","libx264","-preset","veryfast","-tune","stillimage","-crf","27","-r","25",
      "-c:a","aac","-b:a","128k","-t",str(duration(wav)+.25),"-shortest",str(part)],check=True)
  parts.append(part)
 (tmp/"parts.txt").write_text("".join("file '"+str(x)+"'\n" for x in parts))
 final=OUT/"ORBIUNO-2026-11-14_ACTUALIZADO_RESUMEN_VISOR.mp4"
 subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(tmp/"parts.txt"),"-c","copy","-movflags","+faststart",str(final)],check=True)
 probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)]))
 assert 55<float(probe["format"]["duration"])<120
 assert any(x["codec_type"]=="audio" for x in probe["streams"])
 assert any(x["codec_type"]=="video" and x["width"]==720 and x["height"]==1280 for x in probe["streams"])
 assert all((SRC/f"orbiuno-{i:02d}.jpg").is_file() for i in range(1,7))
 log={"brand":"ORBIUNO","edition_date":"2026-11-14","time_of_production_bogota":now.isoformat(),
   "original_media_id":"18192745753363245","status":"VIDEO_READY_NOT_PUBLISHED",
   "video":str(final.relative_to(ROOT)),"duration_seconds":float(probe["format"]["duration"]),
   "sha256":hashlib.sha256(final.read_bytes()).hexdigest(),"opening_summary_seconds":duration(cover_wav),
   "original_photos_from":str(SRC.relative_to(ROOT)),
   "credits":meta["license_photos"],"source_video":meta["video"]}
 (OUT/"edicion-manifiesto.json").write_text(json.dumps(log,ensure_ascii=False,indent=2))
 print("VALIDATED_UPDATED_ORBIUNO",final,log["duration_seconds"],log["sha256"],flush=True)
