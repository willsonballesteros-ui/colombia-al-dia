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
OUT=ROOT/"build"/"mycar_22nov5"
OUT.mkdir(parents=True,exist_ok=True)
ED=json.loads((ROOT/"editions"/"mycar-2026-11-22-am-5.json").read_text(encoding="utf-8"))
UA="ORBIUNO-Editorial-Preview/1.0 (https://colombia-al-dia.pages.dev; Wikimedia Commons media selection)"
SESSION=requests.Session();SESSION.headers.update({"User-Agent":UA})
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans"
ALLOW=("CC BY","CC0","PUBLIC DOMAIN","PD-","PUBLIC DOMAIN MARK")
# Archivo concreto comprobado editorialmente, nunca confiar solo en ranking de búsqueda.
PHOTOS = [
  {
    "id": "photo-1757922589579-e1adec93a5ff",
    "page": "https://unsplash.com/photos/a-dark-blue-suv-parked-on-a-forest-road-sREh9Nsw70o",
    "author": "Michail Dementiev",
    "caption": "SUV Geely de otro modelo, fotografía de archivo en Rusia."
  },
  {
    "id": "photo-1793002814597-32fed695f754",
    "page": "https://unsplash.com/photos/blue-byd-electric-suv-on-shore-cXE1omey8F8",
    "author": "Dragon White Munthe",
    "caption": "BYD Atto 3 en imagen de archivo, no es la Atto 8."
  },
  {
    "id": "photo-1772171386187-bc14e6cd7804",
    "page": "https://unsplash.com/photos/car-dashboard-displaying-autonomous-driving-interface-dkEShdYwnZ0",
    "author": "Josh Sorenson",
    "caption": "Interior Tesla Model Y en foto de archivo, no Cybercab."
  },
  {
    "id": "photo-1703860271535-27d4543db10a",
    "page": "https://unsplash.com/photos/a-woman-is-charging-a-car-in-a-parking-lot-beZxk_OHN7s",
    "author": "Stephan Schwebe",
    "caption": "Carga de vehículo eléctrico Hyundai, archivo; no Leapmotor."
  },
  {
    "id": "photo-1757852664672-b947b893136c",
    "page": "https://unsplash.com/photos/cars-displayed-at-an-indoor-exhibition-hall-with-visitors-MzaAOnOVs0I",
    "author": "Ryo Harianto",
    "caption": "Museo del automóvil en Japón, fotografía de archivo, no Corferias."
  }
]

N=24
def probe(file):
 r=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(file)],capture_output=True,text=True,check=True)
 return float(r.stdout.strip())
def get_photo(query, folder, filename):
    index = int(re.search(r"(\\d+)", filename).group(1))
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
 base=Image.new("RGB",(W,H),(5,18,34));draw=ImageDraw.Draw(base)
 with Image.open(photo) as f:
  raw=ImageOps.exif_transpose(f).convert("RGB")
  bg=ImageOps.fit(raw,(W,H),method=Image.Resampling.LANCZOS)
  bg=bg.filter(ImageFilter.GaussianBlur(13))
  bg=Image.blend(bg,Image.new("RGB",(W,H),(5,18,34)),0.53)
  base.paste(bg)
  big=ImageOps.contain(raw,(1080,1190))
  base.paste(big,((W-big.width)//2,180+(1180-big.height)//2))
 draw=ImageDraw.Draw(base,"RGBA")
 # Safe-area dark-glass text panel below image, enormous headline.
 rect(draw,(42,1050,1038,1780),42,(6,20,35,240))
 draw.rectangle((42,1050,1038,1063),fill=(239,196,53,255) if brand=="MYCAR" else (58,227,216,255))
 title=item["title"];fs=72 if not cover else 88
 for sz in range(fs,48,-4):
  try:lines,f=wrap(draw,title,sz,890,4);break
  except RuntimeError:continue
 for j,line in enumerate(lines):
  draw.text((96,1150+j*(sz+22)),line,font=f,fill=(255,255,255,255))
 draw.text((96,1100),("NOTICIA DESTACADA · " if cover else f"{index:02d} / {total:02d} · ")+brand,
           font=font(34),fill=(96,239,222,255) if brand=="ORBIUNO" else (239,196,53,255))
 rect(draw,(76,1600,1004,1725),22,(240,197,57,252) if brand=="MYCAR" else (82,233,224,244))
 sfsize=min(54,max(34,760//max(1,len(item["source"]))*19))
 icon_x=105
 if source_icon and Path(source_icon).is_file():
  try:
   with Image.open(source_icon) as im:
    icon=ImageOps.contain(im.convert("RGBA"),(92,92))
    base.paste(icon,(106,1616),icon)
    icon_x=225
  except Exception:pass
 # No pretender que un favicon sea el logotipo oficial completo.
 draw=ImageDraw.Draw(base,"RGBA")
 draw.text((icon_x,1627),item["source"].upper(),font=font(sfsize),fill=(6,20,35,255))
 # Brand, date and no fake original logos.
 rect(draw,(52,60,1028,152),24,(5,18,34,230))
 draw.text((83,80),brand,font=font(52),fill=(255,255,255,255))
 draw.text((658,88),day,font=font(28),fill=(245,230,176,255))
 draw.text((84,1735),"FOTO: "+str(item.get("photo_credit","WIKIMEDIA COMMONS"))[:48],font=font(23),fill=(218,225,233,255))
 draw.text((83,1800),"BUSCO-AUTOS.PAGES.DEV · NOTICIAS DE CARROS",font=font(23),fill=(255,255,255,255))
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
  slide(brand,item,ph,"22 NOV 2026 · MAÑANA",len(news),i,len(news),dest,iscover,icons[icon_index])
  slides.append(dest)
 manifest=folder/"slides.txt"
 # Duration of full audio must match frames and natural scene time.
 manifest.write_text("".join(f"file '{p.absolute()}'\nduration {max(.5,t):.6f}\n" for p,t in zip(slides,durations))+f"file '{slides[-1].absolute()}'\n")
 vid=OUT/(brand+"_22_NOV_2026_0930_5_NOTICIAS.mp4")
 subprocess.run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(manifest),"-i",str(audio/"full.mp3"),
                 "-map","0:v","-map","1:a","-vf","fps=24,format=yuv420p","-c:v","libx264","-preset","veryfast","-crf","24",
                 "-c:a","aac","-b:a","160k","-movflags","+faststart","-shortest",str(vid)],check=True)
 d=probe(vid)
 if abs(d-probe(audio/"full.mp3"))>1.2:raise RuntimeError("duración audio/video no coincide")
 captions=[f"{brand} AL DÍA 🚘 | 22 de noviembre de 2026 · edición matutina 9:30 a. m.","","Cinco novedades del mundo del automóvil:"]
 captions.extend("• "+n["title"] for n in news)
 captions.extend(["","Más del sector automotor: https://busco-autos.pages.dev/","", "Fuentes originales:"])
 captions.extend(n["source"]+": "+n["url"] for n in news)
 captions.extend(["","Créditos de fotografía (Wikimedia Commons):"])
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
