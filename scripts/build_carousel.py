#!/usr/bin/env python3
"""Crea diez imágenes editoriales Instagram 1080x1350 con los datos verificables de noticias.json."""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H=1080,1350
NAVY="#071b46"
BLUE="#164aa4"
PAPER="#f5f8ff"
INK="#17223b"
YELLOW="#ffcc29"

def f(sz,bold=False):
    fp="/usr/share/fonts/truetype/dejavu/DejaVuSans-"+("Bold" if bold else "")+".ttf"
    if not bold: fp="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    return ImageFont.truetype(fp,sz)

def wrap(d,txt,ft,width,max_lines=6):
    words=str(txt or "").split()
    o=[]; line=""
    for w in words:
        q=w if not line else line+" "+w
        if d.textbbox((0,0),q,font=ft)[2]<=width: line=q
        else:
            if line:o.append(line)
            line=w
    if line:o.append(line)
    if len(o)>max_lines:
        o=o[:max_lines]
        while o[-1] and d.textbbox((0,0),o[-1]+"…",font=ft)[2]>width: o[-1]=o[-1][:-1]
        o[-1]+="…"
    return o

def block(d,txt,x,y,ft,fill,width,max_lines,spacing=12):
    for line in wrap(d,txt,ft,width,max_lines):
        d.text((x,y),line,font=ft,fill=fill)
        y+=ft.size+spacing
    return y

def draw_card(item,num,day,out):
    im=Image.new("RGB",(W,H),PAPER)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,275),NAVY)
    d.rectangle((0,0,W,14),YELLOW)
    d.ellipse((790,-270,1390,330),outline="#235399",width=26)
    d.text((68,55),"ORBIUNO",font=f(74,True),fill="white")
    d.text((70,151),"LAS NOTICIAS MÁS IMPORTANTES · 10 NOTICIAS",font=f(22,True),fill=YELLOW)
    d.rounded_rectangle((70,215,630,269),radius=22,fill="#17418a")
    d.text((92,226),f"{num:02d} / {item['category'].upper()}",font=f(23,True),fill="white")
    title=item["title"]
    ty=block(d,title,70,325,f(52,True),INK,945,5,16)
    d.line((70,ty+15,1000,ty+15),fill="#a7bce3",width=3)
    y=ty+53
    d.text((70,y),"QUÉ PASÓ",font=f(24,True),fill=BLUE)
    y+=42
    # Taller summaries are clamped to preserve room for source footer.
    y=block(d,item["summary"],70,y,f(28),INK,945,5,11)
    y+=23
    d.text((70,y),"POR QUÉ IMPORTA",font=f(24,True),fill=BLUE)
    y+=42
    block(d,item["why"],70,y,f(28),INK,945,4,11)
    d.rounded_rectangle((52,1154,1028,1312),radius=25,fill=NAVY)
    d.text((76,1182),"FUENTE PRINCIPAL",font=f(20,True),fill=YELLOW)
    block(d,item["sources"][0]["name"],76,1215,f(23),"white",915,2,5)
    d.text((76,1271),"colombia-al-dia.pages.dev",font=f(19,True),fill="#d4def7")
    d.text((855,1270),day[8:10]+"/"+day[5:7]+"/"+day[:4],font=f(16),fill="#d4def7")
    im.save(out,optimize=True)


def draw_story(day,out,url):
    """Historia vertical limpia. El sticker Enlace se añade dentro de Instagram.
    No usar QR ni dibujar botones que aparenten ser clicables.
    """
    w,h=1080,1920
    im=Image.new("RGB",(w,h),NAVY)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,w,26),fill=YELLOW)
    d.rectangle((0,26,w,43),fill="#1680e7")
    d.rectangle((0,43,w,58),fill="#e63145")
    d.ellipse((690,-235,1340,405),outline="#1c438c",width=38)
    d.text((76,130),"ORBIUNO",font=f(122,True),fill="white")
    d.text((82,270),"COLOMBIA · MUNDO · IA",font=f(32,True),fill=YELLOW)
    sy=block(d,"Las noticias más importantes de Colombia y el mundo, en un solo lugar",78,405,f(56,True),"white",920,5,17)
    d.rounded_rectangle((76,sy+70,1000,sy+245),radius=35,fill="#194293")
    d.text((108,sy+108),"10 NOTICIAS VERIFICADAS",font=f(40,True),fill="white")
    d.text((110,sy+173),day[8:10]+"/"+day[5:7]+"/"+day[:4],font=f(30),fill="#f2f5fd")
    d.text((100,1150),"LEE LAS 10 NOTICIAS",font=f(48,True),fill="white")
    d.text((100,1225),"Y COMPRUEBA SUS FUENTES",font=f(34,True),fill=YELLOW)
    d.line((103,1320,974,1320),fill="#91abd8",width=3)
    d.text((102,1375),"Enlace en nuestra biografía",font=f(39,True),fill="white")
    d.text((102,1442),"@resumen.noticias",font=f(34),fill="#d9e4ff")
    d.text((103,1510),"colombia-al-dia.pages.dev",font=f(31,True),fill="#e9f0ff")
    # Reservar espacio libre para que Instagram agregue sticker Enlace REAL.
    d.rounded_rectangle((98,1640,982,1790),radius=35,outline="#7b9ed5",width=3)
    d.text((180,1680),"ESPACIO PARA STICKER ENLACE",font=f(28,True),fill="#e8efff")
    im.save(out,optimize=True)

def main():
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/"noticias.json").read_text(encoding="utf-8"))
    day=data["editionDate"]
    chosen=sorted([v for v in data["news"] if v.get("date")==day and v.get("verification")=="editorial_verified"],key=lambda a:a.get("priority",999))
    if len(chosen)!=10: raise RuntimeError("Se requieren exactamente diez noticias verificadas, hay "+str(len(chosen)))
    outdir=root/"media"/day
    outdir.mkdir(parents=True,exist_ok=True)
    for i,item in enumerate(chosen,1):
        assert item.get("sources") and item["sources"][0].get("url","").startswith("https://")
        path=outdir/f"top10-{i:02d}.png"
        draw_card(item,i,day,path)
        print(path.relative_to(root))
    story=outdir/"historia-orbiuno.png"
    draw_story(day,story,"https://colombia-al-dia.pages.dev/")
    print(story.relative_to(root))
if __name__=="__main__":main()
