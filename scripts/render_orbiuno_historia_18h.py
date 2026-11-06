#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"media"/"2026-11-06"/"historia_18pm.png";OUT.parent.mkdir(parents=True,exist_ok=True)
im=Image.new("RGB",(1080,1920),"#101A24");d=ImageDraw.Draw(im)
fdir="/usr/share/fonts/truetype/dejavu"
def f(n,bold=True):return ImageFont.truetype(fdir+("/DejaVuSans-Bold.ttf" if bold else "/DejaVuSans.ttf"),n)
c="#F7F6F0";teal="#6EE7DA";coral="#FF785F";amber="#FFC857"
d.rectangle((0,0,1080,18),fill=coral)
d.text((105,285),"ORBIUNO",font=f(92),fill=c)
d.text((108,389),"COLOMBIA AL DÍA",font=f(35),fill=teal)
d.rounded_rectangle((710,291,977,368),radius=18,fill=amber)
d.text((742,309),"18:00",font=f(43),fill="#14202B")
d.text((109,466),"VIERNES 6 NOVIEMBRE",font=f(27),fill=amber)
sections=[
("COLOMBIA · CARACOL RADIO",["Contraloría pide respuestas","por fallas de radar en El Dorado"]),
("MUNDO · THE GUARDIAN",["Amenazas de bomba afectan","vuelos en Europa"]),
("IA · REUTERS",["Estados Unidos prueba IA","para revisar datos agrícolas"]),
]
for i,(src,headline) in enumerate(sections):
 y=570+i*285
 d.rounded_rectangle((95,y,982,y+252),radius=26,fill=["#213A45","#29394A","#343047"][i])
 d.rectangle((95,y+15,110,y+234),fill=[coral,teal,amber][i])
 d.text((133,y+29),src,font=f(25),fill=amber)
 for j,line in enumerate(headline):d.text((135,y+98+j*58),line,font=f(32),fill=c)
d.rounded_rectangle((97,1418,977,1525),radius=15,fill=coral)
d.rectangle((128,1445,149,1480),fill="#13202A")
d.polygon([(116,1471),(160,1471),(138,1496)],fill="#13202A")
d.text((186,1433),"ESCUCHA CADA NOTICIA",font=f(33),fill="#13202A")
d.text((186,1483),"ENLACE DEL PERFIL",font=f(25),fill="#13202A")
im.save(OUT,optimize=True)
print(OUT)
