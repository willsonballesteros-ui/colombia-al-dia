#!/usr/bin/env python3
"""Review-only real photographic assets and Kokoro ef_dora voice for 13 Nov 2026.
No social media actions or tokens. Fail on unsupported photo license.
"""
from pathlib import Path
import urllib.request,urllib.parse,json,re,time,io,hashlib
import numpy as np
import soundfile as sf
import onnxruntime as ort
from kokoro_onnx import Kokoro
from PIL import Image

root=Path("dist/revision-13nov"); root.mkdir(parents=True,exist_ok=True)
photos={
"mycar-01":"File:Renault Kwid - Facelift (2026).png",
"mycar-02":"File:Golf GTi (3).jpg",
"mycar-03":"File:Corolla-Cross-Hybrid-2026-Facelift.jpg",
"mycar-04":"File:ICAR V23.jpg",
"orbiuno-04":"File:Maloka.jpg",
"orbiuno-05":"File:Voyager.jpg",
}
credits={}
for code,title in photos.items():
 url="https://commons.wikimedia.org/w/api.php?"+urllib.parse.urlencode({"action":"query","titles":title,"prop":"imageinfo","iiprop":"url|extmetadata|size","iiurlwidth":1100,"format":"json"})
 req=urllib.request.Request(url,headers={"User-Agent":"ORBIUNO-EditorialResearch/1.0 (GitHub public project; credit check)"})
 try:
  with urllib.request.urlopen(req,timeout=40) as f:d=json.load(f)
  page=next(iter(d["query"]["pages"].values()))
  ii=page["imageinfo"][0]
  meta=ii.get("extmetadata",{})
  license_name=re.sub("<[^>]*>","",meta.get("LicenseShortName",{}).get("value","")).strip()
  artist=re.sub("<[^>]*>","",meta.get("Artist",{}).get("value","")).strip()
  if not any(x in license_name.lower() for x in ("cc0","cc by","public domain","pd-nasa")):raise ValueError(f"License not verified {title} {license_name}")
  photo=ii.get("thumburl",ii["url"])
  with urllib.request.urlopen(urllib.request.Request(photo,headers={"User-Agent":"ORBIUNO-EditorialResearch/1.0"}),timeout=45) as f:raw=f.read()
  im=Image.open(io.BytesIO(raw)).convert("RGB")
  im.thumbnail((1100,1100))
  im.save(root/(code+".jpg"),quality=88)
  credits[code]={"title":title,"artist":artist[:150],"license":license_name,"commons":"https://commons.wikimedia.org/wiki/"+urllib.parse.quote(title.replace(" ","_")),"sha256":hashlib.sha256(raw).hexdigest()}
  print("Photo OK",code,title,license_name,flush=True)
  time.sleep(1.1)
 except Exception as e:
  print("Photo FAILED",code,str(e),flush=True)
  raise
(root/"credits.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2))
speech={
"orbiuno-intro":"Hola, bienvenidos a Orbiuno. Hoy viernes trece de noviembre resumimos cinco noticias de Colombia y el mundo. La última te sorprenderá.",
"orbiuno-01":"Bogotá se prepara para la Noche de Museos, con más de ochenta espacios culturales y actividades gratuitas o de acceso especial. Consulta los horarios de cada sede. Fuente: Alcaldía de Bogotá.",
"orbiuno-02":"Comienzan en Bogotá las finales de los Juegos Intercolegiados. Participarán cinco mil novecientos cincuenta y siete jóvenes atletas de todo el país. Fuente: Instituto Distrital de Recreación y Deporte.",
"orbiuno-03":"Europa debate en Dublín cómo impulsar la inteligencia artificial, su financiación y seguridad. Son conversaciones en curso, no acuerdos aprobados. Fuente: Reuters.",
"orbiuno-04":"El museo Maloka participará hoy en la Noche de Museos, con entrada gratuita entre cinco y ocho de la noche. Habrá Cine Domo y experiencias con títeres. Último ingreso, a las siete. Fuente: Maloka.",
"orbiuno-05":"Y la sorpresa: el disco de oro de Voyager transporta sonidos e imágenes de nuestro planeta a través del espacio. Maloka organiza una charla para explorar este asombroso mensaje de la Tierra. Fuente: Maloka y NASA.",
"orbiuno-outro":"Consulta las fuentes y escucha los reportajes en nuestra web. Síguenos para más noticias. Orbiuno.",
"mycar-intro":"Hola, esto es MyCar. Cuatro noticias del motor que debes conocer hoy en Colombia y el mundo. Comenzamos.",
"mycar-01":"El nuevo Renault Kwid dos mil veintisiete llega a Colombia. Precio anunciado desde cuarenta y nueve millones novecientos noventa mil pesos y seis airbags. Foto del Kwid renovado. Fuente: Renault Sofasa.",
"mycar-02":"Volkswagen anunció el regreso del Golf G T I al mercado colombiano durante el Salón del Automóvil de Bogotá. La fotografía es de una generación anterior. Fuente: El Carro Colombiano.",
"mycar-03":"El mercado de híbridos en Colombia llegó a ochenta y cinco mil ochenta y una matrículas entre enero y octubre. Esto representa un aumento de cincuenta y nueve coma ocho por ciento. Fuente: La República, Fenalco y ANDI.",
"mycar-04":"El iCaur V veintitrés presenta sus versiones Retro y Armor con cambios de apariencia y accesorios. La foto muestra el V veintitrés base, no esas versiones específicas. Fuente: El Carro Colombiano.",
"mycar-outro":"¿Buscas o vendes carro? Descubre la plataforma Busco Autos. Sigue a MyCar y comparte este resumen."
}
o=ort.SessionOptions();o.intra_op_num_threads=2
session=ort.InferenceSession("/tmp/kokoro-v1.0.onnx",sess_options=o,providers=["CPUExecutionProvider"])
k=Kokoro.from_session(session,"/tmp/voices-v1.0.bin")
for key,script in speech.items():
 audio,sr=k.create(script,"ef_dora",speed=1.25,lang="es",sentence_pause=.11,clause_pause=.07)
 wav=root/(key+".wav")
 sf.write(str(wav),np.asarray(audio,dtype=np.float32),sr)
 print("VOICE",key,wav.stat().st_size,flush=True)
(root/"narration.txt").write_text("\n\n".join(f"{key}\n{v}" for key,v in speech.items()),encoding="utf-8")
