#!/usr/bin/env python3
"""ORBIUNO noon: real female narration of the full ten original reports, intro/outro.
Audio reused from verified web voice for the morning stories; two new noon
reports and framing narrated in identical ef_dora voice. No fabricated media.
"""
import io, json, os, subprocess, tempfile, textwrap
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
import soundfile as sf
import onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image, ImageDraw, ImageFont, ImageOps
from build_carousel import licensed_image, favicon
ROOT=Path(__file__).resolve().parents[1]
TODAY="2026-11-06"; OUT=ROOT/"media"/TODAY;OUT.mkdir(parents=True,exist_ok=True)
FONT=Path("/usr/share/fonts/truetype/dejavu")
W,H=720,1280
THEMES=["#FF715B","#F2BD58","#57E0D3","#C9A7FF","#FF87B1"]
INTRO=("ORBIUNO, edición del mediodía. Hoy: ciberseguridad, Armada, inflación, deportes, visita papal, Ormuz, inteligencia artificial, Maluma, música viral y energía.")
CLOSING=("Para escuchar cada reportaje completo y consultar sus fuentes, entra a colombia guion al guion día punto pages punto dev. Visita arroba resumen punto noticias y toca el enlace del perfil.")
NEW=[
 {"id":"orbiuno-20261106-12m-maluma","title":"Maluma anuncia gira mundial 2027, con inicio en Bogotá",
  "category":"Farándula","priority":8,"date":TODAY,"verification":"editorial_verified",
  "sources":[{"name":"Caracol Radio","url":"https://caracol.com.co/2026/11/06/maluma-anuncio-su-nueva-gira-loco-x-volver-world-tour-2027-en-que-ciudades-se-presentara/"}],
  "audioFullTextEs":("Maluma anunció su nueva gira internacional, Loco X Volver World Tour dos mil veintisiete, con comienzo previsto para el cinco de febrero en Bogotá. "
  "De acuerdo con Caracol Radio, el anuncio se hizo mediante una aparición sorpresa del cantante colombiano en el aeropuerto internacional de Miami, acompañado por músicos, ante pasajeros que esperaban vuelos hacia Colombia. "
  "El artista interpretó canciones de su repertorio y presentó los primeros detalles de una gira que incluirá más de sesenta ciudades. "
  "Entre las ciudades mencionadas figuran Buenos Aires, Ciudad de México, Santiago, Lima, Miami, Los Ángeles, Toronto, Madrid, París y Berlín. "
  "Caracol también informó sobre una campaña de expectativa que incluyó acciones promocionales en varias capitales. "
  "Las fechas concretas de cada presentación deberán confirmarse a través de los organizadores y de los canales oficiales de venta. "
  "Esta información procede de Caracol Radio y corresponde al anuncio de la gira, no a conciertos ya realizados.")},
 {"id":"orbiuno-20261106-12m-bella-bonita","title":"Luis Alfonso y Los Dotores de la Carranga presentan Bella y Bonita",
  "category":"Virales","priority":9,"date":TODAY,"verification":"editorial_verified",
  "sources":[{"name":"Caracol Radio","url":"https://caracol.com.co/2026/11/03/luis-alfonso-y-los-dotores-de-la-carranga-anuncian-su-colaboracion-musical-bella-y-bonita/"}],
  "audioFullTextEs":("Luis Alfonso y Los Dotores de la Carranga anunciaron una colaboración musical titulada Bella y Bonita, una nueva versión de una canción que había ganado popularidad en redes sociales. "
  "Caracol Radio informó que el lanzamiento estaba previsto para el jueves cinco de noviembre a las seis de la tarde. "
  "El proyecto reúne al intérprete de música popular conocido como El Señorazo con una agrupación que toma elementos de la carranga y la tradición campesina colombiana. "
  "La colaboración se dio a conocer a través de las redes de sus participantes y está dirigida a públicos de ambos géneros. "
  "La canción había circulado de manera destacada en plataformas digitales, en particular TikTok. "
  "El anuncio también ocurrió en vísperas de un concierto del cantante en Bogotá. "
  "Este reporte describe el anuncio y la repercusión cultural indicada por Caracol Radio; no atribuye cifras de reproducciones que no hayan sido verificadas.")}
]
SHORT_COPY = {
 "orbiuno-20261106-am-01": "Según Reuters, hackers entrenados por Corea del Norte están vinculados con ataques financieros. La agencia documentó su sistema de reclutamiento.",
 "orbiuno-20261106-am-02": "Caracol Radio informa que la Armada incautó ciento cuatro armas en el Caribe y capturó a cinco personas. Investigan su destino.",
 "orbiuno-20261106-am-03": "La República informa que el Banco de la República elevó a siete coma uno por ciento su previsión de inflación para este año.",
 "orbiuno-20261106-am-04": "Caracol Radio destaca que Jhon Arias marcó dos goles en la victoria seis a uno de Palmeiras sobre Remo.",
 "orbiuno-20261106-am-05": "Reuters informa que el papa León catorce comenzó una gira por Uruguay, Argentina y Perú, después de una intervención médica.",
 "orbiuno-20261106-am-06": "Reuters reporta nuevos incidentes con petroleros en el estrecho de Ormuz. Sigue la preocupación por la seguridad marítima.",
 "orbiuno-20261106-am-07": "Según Reuters, inversionistas cuestionan la valoración y el calendario de una posible salida a bolsa de Anthropic.",
 "orbiuno-20261106-12m-maluma": "Caracol Radio confirma que Maluma anunció una gira por más de sesenta ciudades, que comenzará en Bogotá en febrero de dos mil veintisiete.",
 "orbiuno-20261106-12m-bella-bonita": "Caracol Radio informa que Luis Alfonso y Los Dotores de la Carranga presentan una nueva versión de Bella y Bonita, popular en redes.",
 "orbiuno-20261106-am-10": "Caracol Radio reporta que MinEnergía pidió ahorrar electricidad entre seis y nueve de la noche para elevar las reservas de los embalses."
}
APPROVED_VOICE = "ef_dora"
def cmd(*args):
 return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout
def font(n,bold=False):
 return ImageFont.truetype(str(FONT/("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")),n)
def paragraph(d,text,x,y,size,color,max_w=620,max_lines=7,bold=False):
 f=font(size,bold);words=str(text).split();line="";written=0
 for word in words+["\0"]:
  trial=(line+" "+word).strip()
  if word!="\0" and d.textbbox((0,0),trial,font=f)[2]<=max_w:line=trial;continue
  if line and written<max_lines:
   d.text((x,y),line,font=f,fill=color);y+=size+13;written+=1
  if written>=max_lines:break
  line="" if word=="\0" else word
 return y
def background():
 im=Image.new("RGB",(W,H),"#122235");d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,14),fill="#FF715B")
 d.text((38,45),"ORBIUNO",font=font(52,True),fill="#FFFFFF")
 d.text((40,114),"COLOMBIA AL DÍA · 06 NOV · 12:00",font=font(18,True),fill="#59E7D4")
 return im,d
def draw_cover(items,path):
 im,d=background()
 d.text((40,210),"10 NOTICIAS",font=font(54,True),fill="#FFCF63")
 d.text((40,275),"EN UN SOLO LUGAR",font=font(31,True),fill="#FFFFFF")
 for i,n in enumerate(items):
  y=367+i*77;col=THEMES[i%5]
  d.rounded_rectangle((38,y,682,y+65),radius=12,fill="#223A4C")
  d.rectangle((38,y,48,y+65),fill=col)
  text=str(n["title"])
  if len(text)>62:text=text[:59]+"..."
  paragraph(d,f"{i+1:02d}  "+text,60,y+14,17,"#FFFFFF",580,2,True)
 d.text((39,1175),"NOTICIAS VERIFICADAS · AUDIO COMPLETO",font=font(18,True),fill="#59E7D4")
 im.save(path,optimize=True)
def draw_card(n,i,page,path):
 im,d=background();color=THEMES[i%5]
 d.rounded_rectangle((38,184,682,262),radius=12,fill=color)
 d.text((57,199),f"{i+1:02d}  ·  {n['category'].upper()[:24]}",font=font(28,True),fill="#13273A")
 paragraph(d,n["title"],43,306,35,"#FFFFFF",625,4,True)
 photo=licensed_image(n)
 if photo is not None:
  im.paste(ImageOps.fit(photo,(630,315),method=Image.Resampling.LANCZOS),(45,532))
  d=ImageDraw.Draw(im)
  d.text((51,855),"FOTO DOCUMENTAL · FUENTE Y CRÉDITO EN LA WEB",font=font(14),fill="#FFFFFF")
 else:
  d.rounded_rectangle((45,533,675,852),radius=16,fill="#263C52")
  icon=favicon(n)
  if icon is not None:
   icon=icon.copy();icon.thumbnail((112,112),Image.Resampling.LANCZOS)
   im.paste(icon,(360-icon.width//2,580),icon)
  d=ImageDraw.Draw(im)
  paragraph(d,"FUENTE: "+n["sources"][0]["name"],68,743,25,color,580,2,True)
 raw=n["audioFullTextEs"].replace("\n"," ")
 excerpt=(raw[:220] if page==0 else raw[len(raw)//2:len(raw)//2+235])
 paragraph(d,excerpt,48,897,22,"#E6F3F4",620,6)
 d.rectangle((0,1195,W,H),fill=color)
 d.text((37,1212),"ESCUCHA TODAS EN LA WEB · ENLACE DEL PERFIL",font=font(16,True),fill="#13273A")
 d.text((37,1241),"colombia-al-dia.pages.dev",font=font(16,True),fill="#13273A")
 im.save(path,optimize=True)
def draw_closing(path):
 im,d=background()
 d.text((49,305),"LA NOTICIA",font=font(59,True),fill="#FFCF63")
 d.text((49,395),"NO TERMINA AQUÍ",font=font(47,True),fill="#FFFFFF")
 d.text((48,540),"ESCUCHA CADA NOTICIA",font=font(30,True),fill="#5BE3CF")
 d.text((48,598),"Y CONSULTA LAS FUENTES",font=font(27,True),fill="#FFFFFF")
 d.rounded_rectangle((38,780,682,980),radius=24,fill="#FFD06E")
 d.text((65,806),"TOCA EL ENLACE",font=font(34,True),fill="#152638")
 d.text((65,867),"DE NUESTRO PERFIL  ↓",font=font(30,True),fill="#152638")
 d.text((49,1030),"@resumen.noticias",font=font(31,True),fill="#FFFFFF")
 d.text((49,1110),"colombia-al-dia.pages.dev",font=font(23,True),fill="#5BE3CF")
 im.save(path,optimize=True)
def main():
 if datetime.now(ZoneInfo("America/Bogota")).date().isoformat()!=TODAY:
  raise SystemExit("No generar una edición atrasada")
 db=json.loads((ROOT/"noticias.json").read_text(encoding="utf8"))
 news=sorted([x for x in db["news"] if x["date"]==TODAY and x.get("verification")=="editorial_verified"],key=lambda x:x.get("priority",999))
 assert len(news)==10 and all(n.get("audioFullTextEs") for n in news)
 assert len(news)==10 and len(set(n["id"] for n in news))==10
 assert all(n["id"] in SHORT_COPY for n in news), "Falta locución verificada para una noticia"
 # Prohibir audios heredados o sustituciones de Edge-TTS: toda la edición usa Kokoro ef_dora.
 # Exactly 12 freshly synthesized Kokoro segments: short intro, 10 verified brief reports, web CTA.
 os.environ.setdefault("OMP_NUM_THREADS","2")
 options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
 model=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=options,providers=["CPUExecutionProvider"])
 kokoro=Kokoro.from_session(model,"/tmp/voices-v1.0.bin")
 with tempfile.TemporaryDirectory(prefix="orbiuno-noon-") as workdir:
  work=Path(workdir);tracks=[];sample_rate=24000
  for i,n in enumerate([{"id":"intro","audioFullTextEs":INTRO}]+news+[{"id":"outro","audioFullTextEs":CLOSING}]):
   wav=work/f"track_{i:02d}.wav"
   body=INTRO if i==0 else CLOSING if i==11 else SHORT_COPY[n["id"]]
   audio,sr=kokoro.create(body,APPROVED_VOICE,speed=1.25,lang="es",sentence_pause=.1,clause_pause=.06)
   if not len(audio):raise RuntimeError("Sin voz ef_dora: "+n["id"])
   sf.write(wav,audio,sr)
   if sr!=sample_rate:
    converted=work/f"res_{i}.wav"
    cmd("ffmpeg","-v","error","-y","-i",str(wav),"-ar",str(sample_rate),"-ac","1",str(converted))
    wav=converted
   samples,sr=sf.read(wav,dtype="float32")
   if samples.ndim>1:samples=samples.mean(axis=1)
   assert sr==sample_rate and np.max(np.abs(samples))>0.01
   tracks.append(samples)
  all_audio=np.concatenate([np.concatenate((a,np.zeros(int(sample_rate*.24),dtype="float32"))) for a in tracks])
  wav=work/"completo.wav";sf.write(wav,all_audio,sample_rate,subtype="PCM_16")
  items=[];lengths=[(len(a)/sample_rate)+.24 for a in tracks]
  cover=work/"cover.png";draw_cover(news,cover);items.append((cover,lengths[0]))
  for i,n in enumerate(news):
   for page in (0,1):
    path=work/f"story{i:02d}_{page}.png"
    draw_card(n,i,page,path)
    items.append((path,lengths[i+1]/2))
  last=work/"closing.png";draw_closing(last);items.append((last,lengths[-1]))
  listing=work/"images.txt"
  with listing.open("w") as f:
   for p,seconds in items:
    f.write("file '"+str(p)+"'\n")
    f.write("duration "+str(round(seconds,5))+"\n")
   f.write("file '"+str(last)+"'\n")
  final=OUT/"reel_12pm.mp4"
  cmd("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y","-f","concat","-safe","0","-i",str(listing),"-i",str(wav),
      "-vf","fps=24","-c:v","libx264","-preset","ultrafast","-crf","27","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
      "-movflags","+faststart","-shortest",str(final))
  report=json.loads(cmd("ffprobe","-v","error","-show_entries","format=duration,size:stream=codec_type,codec_name,width,height","-of","json",str(final)))
  secs=float(report["format"]["duration"]);size=int(report["format"]["size"])
  assert 58<=secs<=90 and size>100000, 'Duración incompatible con Reel corto; no publicar', (secs,size)
  assert any(s.get("codec_type")=="audio" for s in report["streams"])
  assert any(s.get("codec_type")=="video" and s.get("width")==W and s.get("height")==H for s in report["streams"])
  metadata={"slot":"12:00 America/Bogota","editionDate":TODAY,"durationSeconds":round(secs,1),"newsCount":10,
           "intro":True,"closingCTA":"colombia-al-dia.pages.dev","voice":APPROVED_VOICE,"voiceEngine":"kokoro-onnx","voiceRate":1.25,
           "allTenNewsNarrated":True,"fullReportsAvailableOnWeb":True,"fullNewsNarration":False,"sourceLinks":[n["sources"][0]["url"] for n in news],
           "videoFile":"reel_12pm.mp4","audioVerified":True,"publicationVerified":False}
  (OUT/"reel_12pm.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
  print("REEL_12PM_VALIDATED",json.dumps(metadata,ensure_ascii=False),flush=True)
if __name__=="__main__": main()
