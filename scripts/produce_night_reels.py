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
 obj=get_json(endpoint)
 for p in sorted(obj.get("query",{}).get("pages",{}).values(),key=lambda p:p.get("index",999)):
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
 draw.text((28,75),"12 NOV 2026 · NOCHE",font=font(18,True),fill="white")
 draw.rectangle((0,845,720,1280),fill=(5,20,36))
 draw.rectangle((27,855,140,904),fill=(255,212,51))
 draw.text((43,863),f"{num:02d} / 04",font=font(24,True),fill=(5,20,36))
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
def orbiuno():
 news=json.loads((ROOT/"noticias.json").read_text())["news"]
 stories=sorted((n for n in news if n.get("date")=="2026-11-12" and n.get("editionSlot")=="21:00" and n.get("verification")=="editorial_verified"),key=lambda n:n["priority"])
 if len(stories)!=4:raise RuntimeError("Four verified night stories required")
 manifests=json.loads((ROOT/"media/web-voice/manifest.json").read_text())
 queries=["boxing ring sports arena","Bogota historic buildings colombia","Google Glass wearable","Twitter headquarters San Francisco"]
 audios=[]
 for story,q in zip(stories,queries):
  m=manifests["items"].get(story["id"])
  if not m or m["text"]!=story["title"]+". Fuente: "+story["sources"][0]["name"]+". "+story["audioFullTextEs"]:raise RuntimeError("Dora manifest stale "+story["id"])
  p=ROOT/m["url"][2:]
  if not p.exists():raise RuntimeError("Missing real Dora audio "+str(p))
  audios.append(p)
  story["photo_query"]=q;story["source"]=story["sources"][0]["name"];story["source_url"]=story["sources"][0]["url"]
 render("ORBIUNO",stories,audios,"https://colombia-al-dia.pages.dev/")
def mycar():
 from kokoro_onnx import Kokoro
 import onnxruntime as ort
 obj=json.loads((ROOT/"editorial/mycar-2026-11-12-night.json").read_text())
 stories=obj["stories"]
 if len(stories)!=4:raise RuntimeError("4 car stories required")
 queries=["Ford Transit van exterior","FAW automobile SUV","Stellantis automobile manufacturing plant","Scout Motors pickup truck"]
 session=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",providers=["CPUExecutionProvider"])
 k=Kokoro.from_session(session,"/tmp/voices-v1.0.bin")
 audios=[]
 for i,(story,q) in enumerate(zip(stories,queries),1):
  story["photo_query"]=q;story["source_url"]=story["source"];story["source"]=story["sourceName"]
  wav=OUT/f"mycar-{i:02d}.wav"
  audio,sr=k.create(story["voiceText"],"ef_dora",speed=1.25,lang="es",sentence_pause=.13,clause_pause=.07)
  import soundfile as sf
  sf.write(str(wav),np.asarray(audio,dtype=np.float32),sr)
  audios.append(wav)
 render("MYCAR",stories,audios,"https://busco-autos.pages.dev/")
if __name__=="__main__":
 arg=sys.argv[1] if len(sys.argv)>1 else "all"
 if arg in ("all","orbiuno"):orbiuno()
 if arg in ("all","mycar"):mycar()
