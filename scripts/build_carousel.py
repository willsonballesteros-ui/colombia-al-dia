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
    d.text((68,55),"COLOMBIA AL DÍA",font=f(58,True),fill="white")
    d.text((70,142),"10 NOTICIAS · COLOMBIA Y EL MUNDO",font=f(23,True),fill=YELLOW)
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
if __name__=="__main__":main()
