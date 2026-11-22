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
  # Fotografía real de borde a borde: reemplaza el gran recuadro superpuesto.
  base=ImageOps.fit(raw,(W,H),method=Image.Resampling.LANCZOS)
 draw=ImageDraw.Draw(base,"RGBA")
 accent=(239,196,53,255) if brand=="MYCAR" else (58,227,216,255)
 # Cabecera compacta con marca y fecha/hora, fuera del área central de la foto.
 rect(draw,(0,0,W,148),0,(5,18,34,252))
 draw.rectangle((0,0,W,11),fill=accent)
 draw.text((52,32),brand,font=font(54),fill=(255,255,255,255))
 draw.text((548,52),day,font=font(28),fill=(245,230,176,255))
 # Panel inferior compacto, máximo 490 de 1920 pixeles.
 rect(draw,(0,1430,W,H),0,(5,18,34,250))
 draw.rectangle((0,1430,W,1442),fill=accent)
 kicker="NOTICIA DESTACADA" if cover else f"NOTICIA {index:02d} DE {total:02d}"
 draw.text((60,1460),kicker,font=font(29),fill=accent)
 title=item["title"]
 for sz in (58,54,50,46,42,38):
  try:
   lines,f=wrap(draw,title,sz,965,3)
   break
  except RuntimeError:
   continue
 else: raise RuntimeError("Titular fuera de panel compacto: "+title)
 for j,line in enumerate(lines):
  draw.text((60,1514+j*(sz+12)),line,font=f,fill=(255,255,255,255))
 # Fuente en una línea o dos con logo discreto.
 rect(draw,(60,1740,1020,1829),15,accent)
 icon_x=77
 if source_icon and Path(source_icon).is_file():
  try:
   with Image.open(source_icon) as im:
    icon=ImageOps.contain(im.convert("RGBA"),(70,70))
    base.paste(icon,(76,1749),icon)
    icon_x=165
  except Exception:pass
 draw=ImageDraw.Draw(base,"RGBA")
 src=item["source"].upper()
 fsize=35 if len(src)<26 else 28
 for j,line in enumerate(wrap(draw,src,fsize,825 if icon_x==165 else 900,2)[0]):
  draw.text((icon_x,1754+j*32),line,font=font(fsize),fill=(6,20,35,255))
 draw.text((60,1851),"BUSCO-AUTOS.PAGES.DEV · MYCAR",font=font(23),fill=(255,255,255,255))
 draw.text((60,1890),"FOTO: "+str(item.get("photo_credit","WIKIMEDIA COMMONS"))[:58],font=font(19),fill=(218,225,233,255))
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
 parts=[config["intro"]]+[n["say"] for n in news]+[config["outro"]]
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
