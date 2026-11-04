"""Dibuja imágenes contextuales originales, no fotos de los hechos."""
import unicodedata
from PIL import Image, ImageDraw, ImageFont

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
COLORS=["#153d77","#236b8a","#5a478c","#146c7a","#3266af","#517b7a","#324c89","#5667a6","#5e577b","#12758e"]

def topic(title):
 s=unicodedata.normalize("NFKD",title.lower())
 s="".join(c for c in s if not unicodedata.combining(c))
 for k,words in {"VOTACIÓN":("eleccion","votan"),"CONGRESO":("congreso","sometimiento"),"ECONOMÍA":("tribut","salario","contable"),"ENERGÍA":("rusia","ucrania","energetic"),"TECNOLOGÍA":("nvidia","amd","inteligencia artificial"),"TRANSPORTE":("ormuz","petrolero"),"SEGURIDAD":("apple","autorizacion")}.items():
  if any(w in s for w in words):return k
 return "MUNDO"

def visual(item,number,path):
 w,h=1080,600; navy="#0d2956";gold="#ffdc81";white="#f2f8ff"
 im=Image.new("RGB",(w,h),COLORS[(number-1)%10]);d=ImageDraw.Draw(im)
 for k in range(5):
  off=45*k
  d.ellipse((350+off,-170+off,1120-off,560-off),outline="#8bc5de",width=4)
 for x in range(65,340,40):
  for y in range(100,520,40):d.ellipse((x,y,x+3,y+3),fill="#98c5e8")
 d.rounded_rectangle((500,75,949,521),radius=85,fill=navy,outline="#8fc8e8",width=7)
 t=topic(item["title"])
 if t in ("ECONOMÍA","ENERGÍA"):
  d.line((560,439,893,439),fill=white,width=12)
  for x,z in ((580,120),(677,194),(773,270)):
   d.rounded_rectangle((x,435-z,x+69,435),radius=9,fill=gold)
  d.line([(561,320),(668,283),(766,216),(864,161)],fill=white,width=15)
 elif t=="TECNOLOGÍA":
  d.rounded_rectangle((631,192,819,402),radius=24,fill=white)
  d.rounded_rectangle((661,228,790,368),radius=17,fill="#4a85c7")
  d.ellipse((694,264,760,330),fill=gold)
  for x in (662,721,783):
   d.line((x,147,x,189),fill=gold,width=13);d.line((x,404,x,448),fill=gold,width=13)
 elif t in ("VOTACIÓN","CONGRESO"):
  d.polygon([(550,270),(725,144),(898,270)],fill=white)
  for x in (591,665,747,825):d.rectangle((x,295,x+35,438),fill=white)
  d.rectangle((553,451,893,482),fill=gold)
 elif t=="TRANSPORTE":
  d.polygon([(541,342),(916,342),(863,444),(632,444)],fill=white)
  d.rectangle((651,255,814,338),fill=gold);d.rectangle((703,211,760,252),fill=white)
  d.arc((545,457,915,545),0,180,fill=gold,width=14)
 else:
  d.ellipse((588,169,875,457),outline=white,width=14)
  d.ellipse((654,169,809,457),outline=gold,width=11)
  d.line((588,314,875,314),fill=white,width=11)
 d.text((52,32),"ORBIUNO  /  "+t,font=ImageFont.truetype(FONT,27),fill=white)
 d.text((52,556),"ILUSTRACIÓN EDITORIAL · NO ES FOTOGRAFÍA",font=ImageFont.truetype(FONT,20),fill=white)
 path.parent.mkdir(parents=True,exist_ok=True)
 im.save(path,optimize=True)
