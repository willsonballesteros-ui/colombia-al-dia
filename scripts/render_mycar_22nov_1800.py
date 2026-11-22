#!/usr/bin/env python3
"""MyCar 22 Nov: render de cinco noticias con fotos reales Unsplash, voz Salomé y QA.

No llama Meta; genera material PM verificado para hospedar una sola vez. Los enlaces originales y los créditos
se registran en archivos junto a los MP4. No inventa imágenes de acontecimientos.
"""
import json,os,re,sys,subprocess,shutil,html,math,io
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image,ImageDraw,ImageFont,ImageOps,ImageFilter
import requests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build"/"mycar_22nov18"
OUT.mkdir(parents=True,exist_ok=True)
ED=json.loads((ROOT/"editions"/"mycar-2026-11-22-pm-5.json").read_text(encoding="utf-8"))
UA="ORBIUNO-Editorial-Preview/1.0 (https://colombia-al-dia.pages.dev; Wikimedia Commons media selection)"
SESSION=requests.Session();SESSION.headers.update({"User-Agent":UA})
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans"
ALLOW=("CC BY","CC0","PUBLIC DOMAIN","PD-","PUBLIC DOMAIN MARK")
# Archivo concreto comprobado editorialmente, nunca confiar solo en ranking de búsqueda.
PHOTOS = [
  {
    "id": "photo-1790137751714-476f99f978bf",
    "page": "https://unsplash.com/photos/white-sedan-on-tree-lined-road-4fDKrHjYgfk",
    "author": "Emmanuel Munoz",
    "caption": "Sedán blanco genérico en fotografía de archivo de 2026, no es Dongfeng 007."
  },
  {
    "id": "photo-1785188672333-32c669e6dd92",
    "page": "https://unsplash.com/photos/front-view-of-a-modern-electric-suv-parked-indoors-dLiAnuEU3o4",
    "author": "Patrick Nguyen",
    "caption": "Rivian R1S eléctrico expuesto en sala, archivo de otra marca, no IM Motors."
  },
  {
    "id": "photo-1712912854219-5279e0274fdd",
    "page": "https://unsplash.com/photos/a-close-up-of-a-motorcycle-parked-on-the-street-0pY6dSciGGQ",
    "author": "Shawn Powar",
    "caption": "Royal Enfield Bullet 350 estacionada en Reno, archivo ilustrativo, no es AKT."
  },
  {
    "id": "photo-1646728502468-06d9c7b3c2c2",
    "page": "https://unsplash.com/photos/a-white-suv-driving-down-a-dirt-road-w9U6U3zN0PA",
    "author": "Hyundai Motor Group",
    "caption": "Hyundai Santa Fe de archivo en carretera, no Lynk & Co 07 GT ni la prueba de seguridad."
  },
  {
    "id": "photo-1745193592657-05dc10ce804f",
    "page": "https://unsplash.com/photos/an-suv-is-off-roading-on-a-rugged-landscape-8xFEH8jbBds",
    "author": "Lens Head Media",
    "caption": "Mercedes Clase G en rocas de Georgia, fotografía de archivo, no MHero E0."
  }
]

N=24
def probe(file):
 r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(file)],capture_output=True,text=True,check=True)
 return float(r.stdout.strip())
def get_photo(query, folder, filename):
    index = int(re.search(r"(\d+)", filename).group(1))
    meta = PHOTOS[index]
    image_url = "https://images.unsplash.com/" + meta["id"] + "?auto=format&fit=crop&w=1600&q=80"
    response = SESSION.get(image_url, timeout=45)
    response.raise_for_status()
    if response.url.split("/")[2] != "images.unsplash.com":
        raise RuntimeError("Servidor fotográfico no autorizado")
    if len(response.content) < 12000 or len(response.content) > 12000000:
        raise RuntimeError("Foto ausente o demasiado grande")
    with Image.open(io.BytesIO(response.content)) as img:
        img.load()
        if min(img.size) < 650:
            raise RuntimeError("Fotografía sin resolución suficiente")
        img = img.convert("RGB")
        dest = folder / filename
        img.save(dest, "JPEG", quality=87, optimize=True)
    return {"commons":meta["page"],"image_file":filename,"image_title":meta["id"],
            "license":"Unsplash License","author":meta["author"],"visual":meta["caption"]}

def fetch_source_icon(source_url, dest):
    """Icono servido para el dominio ORIGINAL, nunca inventar logo.
    Verificar que sea una imagen PNG cuadrada legible; si no, usar texto de fuente.
    """
    try:
        host=urlsplit(source_url).hostname
        if not host or not re.fullmatch(r"[a-z0-9.-]+",host.lower()):return None
        url="https://www.google.com/s2/favicons?domain="+host+"&sz=256"
        res=SESSION.get(url,timeout=15);res.raise_for_status()
        if len(res.content)<150:return None
        dest.write_bytes(res.content)
        with Image.open(dest) as im:
            im.load()
            if min(im.size)<32 or abs(im.width-im.height)>max(im.size)*.1:
                dest.unlink(missing_ok=True);return None
        return dest
    except Exception:
        dest.unlink(missing_ok=True)
        return None

def font(size,bold=True):
 return ImageFont.truetype(FONT+("-Bold" if bold else "")+".ttf",size)
def wrap(draw,text,size,maxw,maxlines=4):
 f=font(size)
 words=text.split();lines=[];line=""
 for w in words:
  s=(line+" "+w).strip()
  if draw.textbbox((0,0),s,font=f)[2]<=maxw:line=s
  else:
   if line:lines.append(line)
   line=w
 if line:lines.append(line)
 if len(lines)>maxlines:raise RuntimeError("Titular fuera de zona segura: "+text)
 return lines,f
def rect(draw,xy,r,fill):draw.rounded_rectangle(xy,radius=r,fill=fill)
def slide(brand,item,photo,day,part,index,total,out,cover=False,source_icon=None):
 W,H=1080,1920
 with Image.open(photo) as original:
  raw=ImageOps.exif_transpose(original).convert("RGB")
  base=ImageOps.fit(raw,(W,H),method=Image.Resampling.LANCZOS)
 draw=ImageDraw.Draw(base,"RGBA")
 accent=(239,196,53,255) if brand=="MYCAR" else (58,227,216,255)
 # Fecha dentro del video, debajo del encabezado y fuera de los controles superiores.
 rect(draw,(0,0,W,145),0,(5,18,34,248))
 draw.rectangle((0,0,W,11),fill=accent)
 draw.text((54,40),brand,font=font(57),fill=(255,255,255,255))
 rect(draw,(55,380,890,473),19,(5,18,34,238))
 draw.text((77,402),day,font=font(37),fill=(255,230,165,255))

 if index>total:
  # Cierre explícito en vez del erróneo "NOTICIA 06 DE 05".
  rect(draw,(55,570,1020,1335),25,(5,18,34,234))
  for line,y,sz,color in (
   ("ESCUCHA LA LECTURA",675,49,accent),
   ("COMPLETA DE CADA",760,48,(255,255,255,255)),
   ("NOTICIA",847,60,(255,255,255,255)),
   ("EN EL ENLACE",982,52,accent),
   ("DE NUESTRO PERFIL",1059,49,accent),
   ("@mycar.buscoautos",1192,43,(255,255,255,255)),
   ("busco-autos.pages.dev",1255,34,(255,230,165,255)),
  ):
   draw.text((78,y),line,font=font(sz),fill=color)
  base.save(out,quality=91)
  return

 # Logo auténtico y nombre de fuente antes del titular: zona a salvo del pie de IG.
 rect(draw,(54,1300,925,1438),21,(5,18,34,236))
 source_x=78
 if source_icon and Path(source_icon).is_file():
  try:
   with Image.open(source_icon) as original_icon:
    logo=ImageOps.contain(original_icon.convert("RGBA"),(116,116),method=Image.Resampling.LANCZOS)
    tile=Image.new("RGBA",(128,128),(255,255,255,255))
    tile.alpha_composite(logo,((128-logo.width)//2,(128-logo.height)//2))
    base.paste(tile.convert("RGB"),(63,1305))
    source_x=211
  except Exception:
   pass
 draw=ImageDraw.Draw(base,"RGBA")
 src=item["source"].upper()
 for fsize in (43,39,35,31):
  try:
   src_lines,_=wrap(draw,src,fsize,700 if source_x==211 else 830,2)
   break
  except RuntimeError:
   continue
 else: raise RuntimeError("Nombre de fuente demasiado largo")
 for j,line in enumerate(src_lines):
  draw.text((source_x,1322+j*(fsize+5)),line,font=font(fsize),fill=accent)

 # Panel breve y con texto dentro del rectángulo seguro de Instagram.
 rect(draw,(0,1450,W,1780),0,(5,18,34,248))
 draw.rectangle((0,1450,W,1462),fill=accent)
 kicker="NOTICIA DESTACADA" if cover else f"NOTICIA {index:02d} DE {total:02d}"
 draw.text((60,1468),kicker,font=font(30),fill=accent)
 title=item["title"]
 for sz in (56,52,48,44,40,36,32):
  try:
   lines,f=wrap(draw,title,sz,925,3)
   break
  except RuntimeError:
   continue
 else: raise RuntimeError("Titular fuera de zona segura: "+title)
 for j,line in enumerate(lines):
  draw.text((60,1520+j*(sz+13)),line,font=f,fill=(255,255,255,255))
 # Crédito discreto; información completa en caption y web.
 rect(draw,(54,1820,935,1868),10,(5,18,34,198))
 draw.text((68,1832),"FOTO DE ARCHIVO: "+str(item.get("photo_credit","UNSPLASH"))[:43],
           font=font(18),fill=(255,255,255,255))
 base.save(out,quality=91)
def render(brand,config):
 folder=OUT/brand.lower();folder.mkdir(exist_ok=True)
 news=config["news"];ids=["saludo"]+[f"n{i:02d}" for i in range(1,len(news)+1)]+["despedida"]
 photo=[];ledger=[];icons=[]
 for i,n in enumerate(news):
  info=get_photo(n["image_query"],folder,f"photo-{i:02d}.jpg")
  photo.append(folder/info["image_file"])
  icon=fetch_source_icon(n["url"],folder/f"sourceicon-{i:02d}.png")
  icons.append(icon)
  ledger.append({"headline":n["title"],"source":n["url"],"source_icon":icon.name if icon else None,**info})
 # Build audio script matching all displayed headlines, NOT the old sample.
 input_file=folder/"audio_input.json"
 outro=(config["outro"].rstrip(". ") +
         ". Para escuchar la lectura completa de cada noticia, entra al enlace de "
         "nuestro perfil, en busco autos punto pages punto dev.")
 parts=[config["intro"]]+[n["say"] for n in news]+[outro]
 input_file.write_text(json.dumps({"segments":[{"id":sid,"text":s} for sid,s in zip(ids,parts)]},ensure_ascii=False,indent=2))
 audio=folder/"audio";audio.mkdir(exist_ok=True)
 cmd=[sys.executable,str(ROOT/"scripts"/"generate_voice.py"),"--input",str(input_file),"--out",str(audio)]
 env=dict(os.environ);env.pop("AZURE_SPEECH_KEY",None);env.pop("AZURE_SPEECH_REGION",None) # explicit edge preview, never expose credentials
 subprocess.run(cmd,check=True,env=env)
 report=json.loads((audio/"audio_report.json").read_text())
 if report["status"]!="ok":raise RuntimeError("audio_report blocked")
 if [x["id"] for x in report["segments"]]!=ids:raise RuntimeError("order mismatch")
 durations=[probe(audio/(sid+".mp3")) for sid in ids]
 # Visual cover follows protagonist, each headline video scene follows its own clip.
 coveridx=config["cover"]["news_index"]
 coverdict={"title":config["cover"]["title"],"source":news[coveridx]["source"]}
 slides=[]
 scenes=[({**coverdict,"photo_credit":ledger[coveridx]["author"]},photo[coveridx],True)]
 scenes.extend(({**x,"photo_credit":ledger[i]["author"]},photo[i],False) for i,x in enumerate(news))
 scenes.append(({"title":"Escucha las noticias y sus fuentes en nuestra web","source":"ORBIUNO" if brand=="ORBIUNO" else "BUSCO AUTOS"},photo[0],False))
 for i,(item,ph,iscover) in enumerate(scenes):
  dest=folder/f"slide-{i:02d}.jpg"
  icon_index=coveridx if i==0 else min(i-1,len(icons)-1)
  slide(brand,item,ph,"22 NOV 2026 · 18:00",len(news),i,len(news),dest,iscover,icons[icon_index])
  slides.append(dest)
 manifest=folder/"slides.txt"
 # Duration of full audio must match frames and natural scene time.
 manifest.write_text("".join(f"file '{p.absolute()}'\nduration {max(.5,t):.6f}\n" for p,t in zip(slides,durations))+f"file '{slides[-1].absolute()}'\n")
 vid=OUT/(brand+"_22_NOV_2026_1800_5_NOTICIAS.mp4")
 subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(manifest),"-i",str(audio/"full.mp3"),
                 "-map","0:v","-map","1:a","-vf","fps=24,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","24",
                 "-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(vid)],check=True)
 d=probe(vid)
 if abs(d-probe(audio/"full.mp3"))>1.2:raise RuntimeError("duración audio/video no coincide")
 captions=[f"{brand} AL DÍA 🚘 | 22 de noviembre de 2026 · edición 6:00 p. m.","","Cinco novedades del mundo del automóvil:"]
 captions.extend("• "+n["title"] for n in news)
 captions.extend(["","Más del sector automotor: https://busco-autos.pages.dev/","", "Fuentes originales:"])
 captions.extend(n["source"]+": "+n["url"] for n in news)
 captions.extend(["","Créditos de fotografía (Unsplash; archivo ilustrativo):"])
 captions.extend(x["author"]+" · "+x["license"]+" · "+x["commons"] for x in ledger)
 captions.extend(["","#MyCar #BuscoAutos #AutosColombia #NoticiasMotor"])

 caption_text="\n".join(captions)
 if len(caption_text)>2200:raise RuntimeError("Caption IG supera 2200 caracteres")
 (OUT/(brand+"_caption.txt")).write_text(caption_text,encoding="utf-8")
 (folder/"credits.json").write_text(json.dumps(ledger,ensure_ascii=False,indent=2))
 (folder/"editorial.json").write_text(json.dumps(news,ensure_ascii=False,indent=2))
 print("READY",brand,str(vid),"seconds",d,"engines",[(x["id"],x["engine"]) for x in report["segments"]],flush=True)
 return d
def main():
 assert len(ED["mycar"]["news"])==5
 for brand in ["MYCAR"]:render(brand,ED[brand.lower()])
 print("DONE: five-story MyCar final rendered, NO Meta publication in this script")
if __name__=="__main__":main()
