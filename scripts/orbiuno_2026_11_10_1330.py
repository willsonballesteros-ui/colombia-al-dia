#!/usr/bin/env python3
"""Edicion manual ORBIUNO 2026-11-10. No publica en Meta."""
import json, os, subprocess, tempfile, wave
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont

DAY="2026-11-10"
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"media"/DAY
W,H=720,1280
NAVY="#091a35"; BLUE="#132c55"; CYAN="#70e6e0"; WHITE="#ffffff"; MUTED="#bdcee4"
BASE="/usr/share/fonts/truetype/dejavu/"
stories=[
 {"title":"HACIENDA PROPONE RECORTES AL GASTO","category":"COLOMBIA · ECONOMIA","source":"Ministerio de Hacienda","date":"10 nov 2026","url":"https://www.minhacienda.gov.co/home","speech":"El Ministerio de Hacienda presento este diez de noviembre su Operacion Rescate. Segun la entidad, la propuesta busca ahorros de veintitres billones de pesos, mediante ajustes de personal, funcionamiento y contratacion. Se trata de una propuesta del Gobierno, no de una medida ya aprobada."},
 {"title":"ECOPETROL EMITE BONOS POR DOS MIL MILLONES DE DOLARES","category":"ECONOMIA","source":"Caracol Radio","date":"9 nov 2026","url":"https://caracol.com.co/actualidad/economia/","speech":"Ecopetrol informo una emision internacional de bonos por dos mil millones de dolares. La operacion busca optimizar su perfil de deuda y, segun el reporte de Caracol Radio, atrajo a mas de doscientos treinta y cinco inversionistas internacionales."},
 {"title":"RUSIA Y UCRANIA RETOMAN CONVERSACIONES","category":"INTERNACIONAL","source":"Reuters","date":"10 nov 2026","url":"https://www.reuters.com/world/europe/russia-ukraine-meet-us-backed-talks-after-trump-says-broad-deal-possible-2026-11-10/","speech":"Representantes de Rusia y Ucrania iniciaron en Abu Dabi nuevas conversaciones con mediacion de Estados Unidos. Reuters informa que siguen diferencias importantes sobre territorios y garantias de seguridad. Por ahora, las conversaciones no representan un acuerdo de paz."},
 {"title":"ACUERDO INTERNACIONAL PARA SEGURIDAD DE LA IA","category":"TECNOLOGIA · IA","source":"Agencia EFE","date":"10 nov 2026","url":"https://efe.com/ciencia-y-tecnologia/2026-11-10/macron-reunion-seguridad-ia/","speech":"Gobiernos, investigadores y companias tecnologicas respaldaron en Paris un llamamiento para mejorar la seguridad de la inteligencia artificial. La iniciativa propone evaluaciones independientes de modelos avanzados, alertas tempranas y mayores responsabilidades para sus desarrolladores."}
]
def font(n,bold=True):
 return ImageFont.truetype(BASE+("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),n)
def wrap(d,s,f,width):
 words=s.split(); lines=[]; cur=""
 for w in words:
  t=(cur+" "+w).strip()
  if d.textbbox((0,0),t,font=f)[2]<=width: cur=t
  else:
   if cur: lines.append(cur)
   cur=w
 if cur: lines.append(cur)
 return lines
def lineblock(d,s,x,y,f,width,color,spacing=12):
 for line in wrap(d,s,f,width):
  d.text((x,y),line,font=f,fill=color);y+=f.size+spacing
 return y
def slide(kind,item,out):
 im=Image.new("RGB",(W,H),NAVY);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,14),fill=CYAN)
 d.rounded_rectangle((40,75,680,217),radius=24,fill=BLUE)
 d.text((66,102),"ORBIUNO",font=font(57),fill=WHITE)
 d.text((66,180),"MARTES 10 NOV 2026 · 13:30",font=font(20),fill=CYAN)
 if kind=="intro":
  d.text((52,295),"EDICION DEL DIA",font=font(32),fill=CYAN)
  lineblock(d,"4 NOTICIAS EN MENOS DE UN MINUTO",52,400,font(55),610,WHITE,16)
  lineblock(d,"Colombia · Economia · Mundo · Inteligencia artificial",52,760,font(30,False),600,MUTED)
 elif kind=="outro":
  lineblock(d,"¿QUIERES SABER MAS?",52,362,font(55),610,WHITE,16)
  lineblock(d,"Lee los enlaces originales y los desarrollos completos en nuestra web.",52,590,font(34,False),595,MUTED)
  d.rounded_rectangle((48,850,670,1010),radius=24,fill=CYAN)
  d.text((72,895),"ENLACE EN LA BIO",font=font(38),fill=NAVY)
 else:
  d.text((54,294),item["category"],font=font(28),fill=CYAN)
  lineblock(d,item["title"],52,383,font(42),616,WHITE,17)
  d.rounded_rectangle((45,780,675,1040),radius=20,fill=BLUE)
  d.text((69,817),"FUENTE VERIFICADA",font=font(21),fill=CYAN)
  lineblock(d,item["source"],69,866,font(34),563,WHITE)
  d.text((69,970),"PUBLICADO: "+item["date"],font=font(20),fill=MUTED)
 d.rectangle((0,1170,W,H),fill=BLUE)
 d.text((45,1192),"@resumen.noticias",font=font(24),fill=WHITE)
 d.text((45,1236),"colombia-al-dia.pages.dev",font=font(21),fill=CYAN)
 im.save(out)
def cmd(args,**kwargs):
 subprocess.run(args,check=True,stdout=subprocess.DEVNULL,**kwargs)
def main():
 if datetime.now(ZoneInfo("America/Bogota")).date().isoformat()!=DAY:
  raise RuntimeError("No producir una edicion vencida")
 OUT.mkdir(parents=True,exist_ok=True)
 o=ort.SessionOptions();o.intra_op_num_threads=2;o.inter_op_num_threads=1;o.enable_cpu_mem_arena=False;o.enable_mem_pattern=False
 s=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=o,providers=["CPUExecutionProvider"])
 k=Kokoro.from_session(s,"/tmp/voices-v1.0.bin")
 scenes=[("intro",None,"ORBIUNO. Edicion del diez de noviembre. Cuatro noticias verificadas."),*[("news",x,x["speech"]+" Fuente: "+x["source"]+".") for x in stories],("outro",None,"Encuentra los detalles y los enlaces originales en Colombia al dia. Visita nuestra pagina desde el perfil de ORBIUNO.")]
 with tempfile.TemporaryDirectory() as td:
  tmp=Path(td); parts=[]
  for i,(kind,item,speech) in enumerate(scenes):
   png=tmp/f"{i:02d}.png";wav=tmp/f"{i:02d}.wav";mp4=tmp/f"{i:02d}.mp4"
   slide(kind,item,png)
   audio,sr=k.create(speech,"ef_dora",speed=1.25,lang="es",sentence_pause=.15,clause_pause=.07)
   data=np.asarray(audio,dtype=np.float32)
   cmd(["ffmpeg","-v","error","-y","-f","f32le","-ar",str(sr),"-ac","1","-i","pipe:0","-ar","48000","-ac","2",str(wav)],input=data.tobytes())
   cmd(["ffmpeg","-v","error","-y","-loop","1","-framerate","24","-i",str(png),"-i",str(wav),"-shortest","-vf","format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","26","-r","24","-c:a","aac","-b:a","128k","-ar","48000","-ac","2",str(mp4)])
   parts.append(mp4)
  listing=tmp/"concat.txt";listing.write_text("".join("file '"+str(p)+"'\n" for p in parts))
  final=OUT/"ORBIUNO_2026-11-10_1330.mp4"
  cmd(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(listing),"-c","copy","-movflags","+faststart",str(final)])
  probe=subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type","-of","json",str(final)])
  meta=json.loads(probe)
  assert {"audio","video"}.issubset({x["codec_type"] for x in meta["streams"]})
  assert int(meta["format"]["size"])>100000
  (OUT/"ORBIUNO_2026-11-10_1330_fuentes.json").write_text(json.dumps({"editionDate":DAY,"voice":"ef_dora","speed":1.25,"sources":stories,"technical":meta},ensure_ascii=False,indent=2))
  print("REAL_MP4",str(final),meta["format"],flush=True)
if __name__=="__main__":main()
