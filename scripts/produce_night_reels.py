#!/usr/bin/env python3
"""Produce two factual evening Reels with real licensed Commons archive photos and Kokoro Dora.
Never silently substitute a synthetic image, another voice, or an unlicensed photo.
Results: media/2026-11-12-2200/{orbiuno,mycar}.mp4 plus attribution JSON.
"""
import hashlib, io, json, os, re, subprocess, sys, tempfile, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"media/2026-11-12-2200"
OUT.mkdir(parents=True,exist_ok=True)
FONTS="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
def font(sz,bold=False):return ImageFont.truetype(FONTS if bold else REG,sz)
def get_json(url):
 req=urllib.request.Request(url,headers={"User-Agent":"OrbiunoMyCarEditorial/1.0 (contact editorial via github; image license attribution)"})
 with urllib.request.urlopen(req,timeout=40) as r:return json.load(r)
def download(url):
 req=urllib.request.Request(url,headers={"User-Agent":"OrbiunoMyCarEditorial/1.0"})
 with urllib.request.urlopen(req,timeout=45) as r:return r.read()
def text_lines(draw,text,ft,width):
 words=text.split();lines=[];line=""
 for w in words:
  trial=(line+" "+w).strip()
  if draw.textbbox((0,0),trial,font=ft)[2]>width and line:lines.append(line);line=w
  else:line=trial
 if line:lines.append(line)
 return lines
def choose_photo(query):
 endpoint="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode({
  "action":"query","generator":"search","gsrsearch":"filetype:bitmap "+query,"gsrnamespace":6,
  "gsrlimit":20,"prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1000,
  "format":"json"
 })
 if "Ford Transit" in query:
  endpoint="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","titles":"File:Ford Transit Custom.jpg","prop":"imageinfo","iiprop":"url|size|extmetadata","iiurlwidth":1000,"format":"json"})
 obj=get_json(endpoint)
 for p in sorted(obj.get("query",{}).get("pages",{}).values(),key=lambda p:p.get("index",999)):
  title=p.get("title","").lower()
  if "Ford Transit" in query and "transit" not in title: continue
  if "FAW automobile" in query and not any(w in title for w in ("faw","bestune","hongqi","joyee")): continue
  if "Scout Motors" in query and "scout" not in title: continue
  info=(p.get("imageinfo") or [{}])[0];meta=info.get("extmetadata") or {}
  license_name=re.sub("<[^>]+>","",meta.get("LicenseShortName",{}).get("value","")).strip()
  artist=re.sub("<[^>]+>","",meta.get("Artist",{}).get("value","")).strip()[:160]
  url=info.get("thumburl") or info.get("url") or ""
  if not any(k in license_name.lower() for k in ["cc0","cc by","public domain"]):continue
  if info.get("width",0)<700 or info.get("height",0)<500:continue
  if not url.lower().split("?")[0].endswith((".jpg",".jpeg",".png")):continue
  try:
   raw=download(url)
   im=Image.open(io.BytesIO(raw)).convert("RGB");im.load()
   if len(raw)>7500000:continue
   return im,{"file":p["title"],"commons":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(p["title"].replace(" ","_")),"artist":artist or "Autor identificado en Commons","license":license_name,"photo_url":url}
  except Exception as e:
   print("Candidate unavailable",p["title"],str(e)[:130],flush=True)
 raise RuntimeError("No license-confirmed real photo for query "+query)
def make_frame(name,num,title,source,photo,credit):
 img=ImageOps.fit(photo,(720,1280),method=Image.Resampling.LANCZOS,centering=(.5,.40))
 # use distinct real photographic content in upper 70%; opaque panels below
 draw=ImageDraw.Draw(img)
 draw.rectangle((0,0,720,97),fill=(6,22,41))
 draw.text((28,17),name,font=font(49,True),fill=(255,214,56))
 draw.text((28,75),os.environ.get("EDITION_DATE_LABEL","12 NOV 2026 · NOCHE"),font=font(18,True),fill="white")
 if os.environ.get("PREVIEW_ONLY")=="1":
  draw.rectangle((0,775,720,839),fill=(89,22,29))
  draw.text((180,789),"BORRADOR · NO PUBLICADO",font=font(28,True),fill="white")
 draw.rectangle((0,845,720,1280),fill=(5,20,36))
 draw.rectangle((27,855,140,904),fill=(255,212,51))
 draw.text((43,863),f"{num:02d} / {int(os.environ.get('ORBIUNO_REEL_COUNT', '4')):02d}",font=font(24,True),fill=(5,20,36))
 y=925
 for line in text_lines(draw,title,font(36,True),654)[:5]:
  draw.text((30,y),line,font=font(36,True),fill="white");y+=49
 draw.text((30,1192),"Fuente: "+source[:43],font=font(18),fill=(244,217,118))
 draw.text((30,1222),"FOTO REAL DE ARCHIVO / REFERENCIA",font=font(17,True),fill=(213,222,231))
 draw.text((30,1248),credit[:66],font=font(12),fill=(190,203,214))
 img.save(OUT/(name.lower()+f"-{num:02d}.jpg"),quality=87,optimize=True)
 return OUT/(name.lower()+f"-{num:02d}.jpg")
def run(cmd):
 print("RUN", " ".join(str(x) for x in cmd)[:250],flush=True)
 subprocess.run([str(x) for x in cmd],check=True)
def render(name,stories,audios,outro):
 attribution=[]
 with tempfile.TemporaryDirectory() as t:
  t=Path(t)
  parts=[]
  for i,(story,audio) in enumerate(zip(stories,audios),1):
   photo,credit=choose_photo(story["photo_query"])
   frame=make_frame(name,i,story["title"],story["source"],photo,credit["file"]+" · "+credit["license"])
   attribution.append({"headline":story["title"],"source":story["source_url"],"photo":credit,"note":"Fotografía real de archivo; no se presenta como una imagen del acontecimiento"})
   dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nokey=1:noprint_wrappers=1",str(audio)]).decode())+0.35
   part=t/f"part{i}.mp4"
   run(["ffmpeg","-hide_banner","-loglevel","error","-y","-loop","1","-framerate","25","-i",frame,"-i",audio,"-filter_complex","[0:v]scale=720:1280,format=yuv420p[v]","-map","[v]","-map","1:a:0","-c:v","libx264","-preset","veryfast","-tune","stillimage","-crf","28","-r","25","-c:a","aac","-b:a","128k","-t",str(dur),"-shortest",part])
   parts.append(part)
  listfile=t/"list.txt"
  listfile.write_text("".join("file '"+str(p)+"'\n" for p in parts))
  output=OUT/(name.lower()+"-2026-11-12-noche.mp4")
  run(["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",listfile,"-c","copy","-movflags","+faststart",output])
  info=get_json("file:///not/used") if False else None
  probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(output)]))
  duration=float(probe["format"]["duration"])
  if duration<25 or duration>180:raise ValueError("Invalid movie duration "+str(duration))
  if not any(s.get("codec_type")=="audio" for s in probe["streams"]):raise ValueError("MP4 without audio")
  meta={"brand":name,"date":"2026-11-12","duration":duration,"voice":"Kokoro ef_dora 1.25x","license_photos":attribution,"output":str(output),"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"status":"VIDEO_RENDERED_NOT_PUBLISHED"}
  (OUT/(name.lower()+"-credits.json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2))
  print(json.dumps({"brand":name,"video":str(output),"duration":duration,"bytes":output.stat().st_size}),flush=True)
def dora(texts,prefix):
 from kokoro_onnx import Kokoro
 import onnxruntime as ort
 import soundfile as sf
 session=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",providers=["CPUExecutionProvider"])
 k=Kokoro.from_session(session,"/tmp/voices-v1.0.bin")
 audios=[]
 for i,text in enumerate(texts,1):
  wav=OUT/(prefix+f"-{i:02d}.wav")
  audio,sr=k.create(text,"ef_dora",speed=1.25,lang="es",sentence_pause=.10,clause_pause=.06)
  sf.write(str(wav),np.asarray(audio,dtype=np.float32),sr)
  audios.append(wav)
 return audios
def orbiuno():
 news=json.loads((ROOT/"noticias.json").read_text())["news"]
 stories=sorted((n for n in news if n.get("date")=="2026-11-12" and n.get("editionSlot")=="21:00" and n.get("verification")=="editorial_verified"),key=lambda n:n["priority"])
 if len(stories)!=4:raise RuntimeError("Four verified night stories required")
 queries=["boxing ring sports arena","Bogota historic buildings colombia","Google Glass wearable","Twitter headquarters San Francisco"]
 texts=[
  "Colombia celebra una medalla en los Juegos Olímpicos de la Juventud. Evelin Trejos ganó plata en boxeo en Dakar, categoría de cincuenta y cuatro kilogramos. El Comité Olímpico Colombiano confirmó la noticia este jueves doce de noviembre. Esta es una imagen de archivo del deporte, no de la boxeadora.",
  "Bogotá inauguró La Divina Forma Humana, exposición de dibujos de gran formato del cantante y artista Valeriano Lanchas. Según la agenda cultural de la Alcaldía, la muestra podrá visitarse hasta febrero de dos mil veintisiete. Fotografía de archivo de Bogotá.",
  "Google anunció una nueva generación de gafas inteligentes con inteligencia artificial Gemini. La compañía enfatiza avances en privacidad. La información fue publicada por la agencia EFE el doce de noviembre. Imagen histórica de Google Glass para mostrar la tecnología, no el producto recién anunciado.",
  "La plataforma X amplió a veinte la cantidad de imágenes y videos que admite en una sola publicación, frente al antiguo límite de cuatro. La disponibilidad puede variar según la actualización de la aplicación. Fuente: Agencia EFE. Imagen de archivo de su antigua sede."
 ]
 audios=dora(texts,"orbiuno")
 for story,q in zip(stories,queries):
  story["photo_query"]=q;story["source"]=story["sources"][0]["name"];story["source_url"]=story["sources"][0]["url"]
 render("ORBIUNO",stories,audios,"https://colombia-al-dia.pages.dev/")
def mycar():
 obj=json.loads((ROOT/"editorial/mycar-2026-11-12-night.json").read_text())
 stories=obj["stories"]
 if len(stories)!=4:raise RuntimeError("4 car stories required")
 queries=["Ford Transit van exterior","FAW automobile SUV","Stellantis automobile manufacturing plant","Scout Motors pickup truck"]
 texts=[
  "Ford presentó Transit City, una nueva furgoneta eléctrica diseñada para el reparto y el trabajo urbano. Su autonomía anunciada llega a trescientos ochenta y un kilómetros. Usamos una foto de referencia de la familia Transit, no del modelo nuevo.",
  "En Colombia llega la FAWCAR Joyee S cero ocho, una camioneta híbrida enchufable. La autonomía publicitada corresponde al ciclo de homologación CLTC, no a una medición independiente en carretera. La imagen es referencial, de otro modelo de la marca.",
  "Stellantis y Leapmotor colaborarán en futuros vehículos eléctricos más económicos para Europa. La producción en Italia forma parte de planes anunciados, no de vehículos ya disponibles. Fuente: Reuters. Imagen de archivo industrial.",
  "Scout Motors inició el ensamblaje de vehículos de validación de sus modelos Terra y Traveler en Carolina del Sur. Son unidades para pruebas de producción, no automóviles disponibles para entrega al público. Fuente: Motor uno."
 ]
 audios=dora(texts,"mycar")
 for story,q in zip(stories,queries):
  story["photo_query"]=q;story["source_url"]=story["source"];story["source"]=story["sourceName"]
 render("MYCAR",stories,audios,"https://busco-autos.pages.dev/")
if __name__=="__main__":
 arg=sys.argv[1] if len(sys.argv)>1 else "all"
 if arg in ("all","orbiuno"):orbiuno()
 if arg in ("all","mycar"):mycar()
