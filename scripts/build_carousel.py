#!/usr/bin/env python3
"""ORBIUNO: carrusel rápido, un titular + dos líneas + fuente por lámina.

Las fotos se reproducen SOLO con derechos verificados. En su ausencia se
muestra favicon REAL del sitio periodístico, no una fotografía inventada.
La portada está destinada al Reel/preview, no se publica como diapositiva azul.
"""
import io
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps
from prepare_site import image_verified

ROOT=Path(__file__).resolve().parents[1]
W,H=1080,1350
NAVY="#071B46"
BLUE="#174B99"
WHITE="#FFFFFF"
PAPER="#FAFBFD"
INK="#16213A"
GOLD="#E9BE66"
MUTED="#657187"
FONTS=Path("/usr/share/fonts/truetype/dejavu")
_ICON_CACHE={}


def font(size,bold=False):
    return ImageFont.truetype(str(FONTS/("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")),size)


def wrap(d,text,ft,width,max_lines):
    out=[];line=""
    for word in str(text or "").split():
        guess=(line+" "+word).strip()
        if d.textbbox((0,0),guess,font=ft)[2]<=width:
            line=guess
        else:
            if line:out.append(line)
            line=word
    if line:out.append(line)
    if len(out)>max_lines:
        out=out[:max_lines]
        while out[-1] and d.textbbox((0,0),out[-1]+"…",font=ft)[2]>width:
            out[-1]=out[-1][:-1]
        out[-1]+="…"
    return out


def paragraph(d,text,x,y,ft,color,width=952,max_lines=3,gap=12):
    for line in wrap(d,text,ft,width,max_lines):
        d.text((x,y),line,font=ft,fill=color)
        y+=ft.size+gap
    return y


def favicon(note):
    """Descarga solo el favicon público real del dominio citado, sin claves."""
    source=note["sources"][0]
    host=(urlsplit(source["url"]).hostname or "").lower()
    if not host or not all(ch.isalnum() or ch in ".-" for ch in host):
        return None
    if host not in _ICON_CACHE:
        try:
            url="https://www.google.com/s2/favicons?domain="+quote(host,safe="")+"&sz=128"
            request=Request(url,headers={"User-Agent":"ORBIUNO-source-identity/1.0"})
            with urlopen(request,timeout=3) as reply:
                content=reply.read(250_000)
            with Image.open(io.BytesIO(content)) as icon:
                _ICON_CACHE[host]=icon.convert("RGBA").copy()
        except (OSError,ValueError,TypeError):
            _ICON_CACHE[host]=None
    return _ICON_CACHE[host]


def verified_photo(note):
    if not image_verified(note):return None
    url=str(note["imageUrl"])
    if not url.startswith("./media/"):return None
    path=ROOT/url[2:]
    return path if path.is_file() and path.suffix.lower() in (".png",".jpg",".jpeg",".webp") else None


def font_for_lines(draw, text, width, count, preferred=34, minimum=24):
    """Ajustar fuente para que el resumen quede completo en dos líneas."""
    for size in range(preferred, minimum-1, -1):
        face=font(size)
        if len(wrap(draw,text,face,width,99))<=count:
            return face
    return font(minimum)


def base():
    image=Image.new("RGB",(W,H),PAPER)
    d=ImageDraw.Draw(image)
    d.rectangle((0,0,W,160),fill=NAVY)
    d.rectangle((0,0,W,9),fill=GOLD)
    d.text((60,25),"ORBIUNO",font=font(64,True),fill=WHITE)
    d.text((65,111),"COLOMBIA AL DÍA · NOTICIAS",font=font(22,True),fill=GOLD)
    return image


def source_panel(image,note):
    """Una identidad editorial REAL del medio, nunca un logotipo inventado."""
    d=ImageDraw.Draw(image)
    box=(60,207,1020,684)
    d.rounded_rectangle(box,radius=18,fill="#E7EFFA")
    d.rounded_rectangle((91,245,989,647),radius=14,fill=NAVY)
    icon=favicon(note)
    if icon is not None:
        icon.thumbnail((158,158),resample=Image.Resampling.LANCZOS)
        x=540-icon.width//2
        y=286
        image.paste(icon,(x,y),icon)
        d=ImageDraw.Draw(image)
    d.text((126,472),"FUENTE PERIODÍSTICA",font=font(22,True),fill=GOLD)
    paragraph(d,note["sources"][0]["name"],124,519,font(48,True),WHITE,840,2,10)
    # En caso de no estar accesible un favicon, el nombre verídico de la fuente
    # sigue visible y NO se simula ninguna fotografía.


def news_card(note,num,day,out):
    image=base()
    d=ImageDraw.Draw(image)
    d.text((65,175),f"{num:02d} / 10   ·   {note['category'].upper()}",font=font(25,True),fill=MUTED)
    photo=verified_photo(note)
    if photo:
        with Image.open(photo) as real:
            image.paste(ImageOps.fit(real.convert("RGB"),(960,475),
                            method=Image.Resampling.LANCZOS),(60,207))
        d=ImageDraw.Draw(image)
        d.rounded_rectangle((70,621,1010,676),radius=8,fill=NAVY)
        paragraph(d,"FOTO: "+str(note["imageCredit"]),83,635,font(19),WHITE,906,1,0)
    else:
        source_panel(image,note)
    d=ImageDraw.Draw(image)
    paragraph(d,note["title"],65,729,font(47,True),INK,943,3,10)
    d.line((68,970,1011,970),fill="#D4DFEF",width=3)
    summary=note.get("executiveSummary") or note.get("summary","")
    shortface=font_for_lines(d,summary,947,2,preferred=33,minimum=23)
    paragraph(d,summary,69,999,shortface,INK,947,2,12)
    d.rectangle((0,1233,W,H),fill=NAVY)
    paragraph(d,"FUENTE: "+note["sources"][0]["name"],65,1252,
              font(20,True),WHITE,950,1,0)
    d.text((66,1296),"ESCUCHA LA NOTICIA EN LA WEB · colombia-al-dia.pages.dev",
           font=font(18,True),fill=GOLD)
    image.save(out,optimize=True)


def cover(day, news, out):
    """Portada con una noticia protagonista y las otras nueve en lectura rápida."""
    image=base()
    d=ImageDraw.Draw(image)
    hour=datetime.now(ZoneInfo("America/Bogota")).hour
    slot=("MAÑANA · 08:00" if hour<11 else
          "MEDIODÍA · 12:00" if hour<17 else
          "NOCHE · 18:00")
    d.text((62,181), "EDICIÓN "+slot+" · "+day[8:10]+"/"+day[5:7]+"/"+day[:4],
           font=font(25,True),fill=BLUE)
    d.rounded_rectangle((56,227,1024,570),radius=22,fill=NAVY)
    d.rounded_rectangle((80,252,464,305),radius=12,fill=GOLD)
    d.text((98,264),"01 · NOTICIA PRINCIPAL",font=font(24,True),fill=NAVY)
    principal=str(news[0]["title"])
    main_ft=font_for_lines(d,principal,875,3,preferred=53,minimum=38)
    paragraph(d,principal,91,329,main_ft,WHITE,876,3,10)
    d.text((90,527),"FUENTE: "+str(news[0]["sources"][0]["name"])[:55],
           font=font(19,True),fill=GOLD)
    d.text((63,592),"ADEMÁS, EN ESTA EDICIÓN",font=font(30,True),fill=INK)
    d.line((63,641,1015,641),fill=GOLD,width=5)
    # Distribuir nueve titulares en dos columnas, sin repetir síntesis.
    remaining=news[1:]
    for i,note in enumerate(remaining):
        col=i%2
        row=i//2
        x=60+col*490
        y=662+row*106
        d.rounded_rectangle((x,y,x+470,y+94),radius=13,
                            fill="#EDF3FB" if row%2==0 else "#E4ECF7")
        d.rounded_rectangle((x+12,y+15,x+62,y+62),radius=10,fill=NAVY)
        d.text((x+18,y+22),f"{i+2:02d}",font=font(23,True),fill=WHITE)
        title_ft=font_for_lines(d,note["title"],382,2,preferred=27,minimum=22)
        paragraph(d,note["title"],x+76,y+11,title_ft,INK,381,2,5)
    d.rectangle((0,1208,W,H),fill=NAVY)
    d.text((59,1228),"ESCUCHA EL BOLETÍN COMPLETO EN LA WEB",font=font(27,True),fill=GOLD)
    d.text((62,1280),"colombia-al-dia.pages.dev  ·  @resumen.noticias",
           font=font(22,True),fill=WHITE)
    image.save(out,optimize=True)


def grouped_card(notes, first_number, group_index, total_groups, out):
    """Lámina editorial de DOS noticias, letras grandes y cero paneles vacíos."""
    if len(notes)!=2:
        raise ValueError("El nuevo formato requiere dos noticias por lámina")
    image=base()
    d=ImageDraw.Draw(image)
    d.text((62,182),f"ACTUALIDAD  ·  LÁMINA {group_index} DE {total_groups}",
           font=font(28,True),fill=BLUE)
    d.line((63,229,1016,229),fill=GOLD,width=5)
    for i,note in enumerate(notes):
        y=250+i*481
        x1,x2=60,1020
        d.rounded_rectangle((x1,y,x2,y+463),radius=22,fill=NAVY)
        d.rounded_rectangle((x1+16,y+18,x1+110,y+89),radius=12,fill=GOLD)
        d.text((x1+30,y+31),f"{first_number+i:02d}",font=font(37,True),fill=NAVY)
        category=str(note.get("category","NOTICIAS")).upper()[:23]
        d.text((x1+131,y+35),category,font=font(25,True),fill=GOLD)
        # Titular dominante. La síntesis añade contexto: no se imprime
        # nuevamente la misma frase en otro lugar.
        headline=str(note.get("socialHeadline") or note["title"])
        headline_ft=font_for_lines(d,headline,867,3,preferred=49,minimum=33)
        paragraph(d,headline,87,y+109,headline_ft,WHITE,865,3,7)
        d.line((88,y+294,988,y+294),fill="#D5AD59",width=3)
        summary=str(note.get("socialDetail") or
                    note.get("executiveSummary") or note.get("summary",""))
        # Las síntesis oficiales tienen fuente; nunca fabricar datos
        # para hacer más espectacular la lámina.
        summary_ft=font_for_lines(d,summary,881,3,preferred=29,minimum=23)
        paragraph(d,summary,89,y+309,summary_ft,WHITE,875,3,8)
        src=str(note["sources"][0]["name"])
        d.text((90,y+425),"FUENTE: "+src[:72],font=font(21,True),fill=GOLD)
    d.rectangle((0,1228,W,H),fill=NAVY)
    d.text((58,1245),"ESCUCHA TODAS LAS NOTICIAS EN ORBIUNO",font=font(26,True),fill=GOLD)
    d.text((60,1291),"colombia-al-dia.pages.dev  ·  @resumen.noticias",
           font=font(21,True),fill=WHITE)
    image.save(out,optimize=True)


def combined_sports_card(a,b,out):
    """Lámina combinada para cubrir 10 noticias en 10 medios con portada."""
    image=base()
    d=ImageDraw.Draw(image)
    d.text((65,190),"09 Y 10 / 10  ·  DEPORTES",font=font(32,True),fill=MUTED)
    for i,n in enumerate((a,b)):
        y=290+i*425
        d.rounded_rectangle((60,y,1020,y+385),radius=18,fill="#E7EFFA")
        d.rounded_rectangle((84,y+20,996,y+79),radius=10,fill=NAVY)
        d.text((105,y+30),f"{9+i:02d}  CHAMPIONS LEAGUE",font=font(25,True),fill=GOLD)
        paragraph(d,n["title"],102,y+110,font(45,True),INK,856,3,10)
        paragraph(d,n["executiveSummary"],102,y+262,font(26),INK,856,2,10)
    d.rectangle((0,1215,W,H),fill=NAVY)
    d.text((65,1240),"FUENTES: AS / CARACOL · VER ENLACES EN ORBIUNO",
           font=font(22,True),fill=WHITE)
    d.text((65,1293),"ESCUCHA LA NOTICIA EN colombia-al-dia.pages.dev",
           font=font(19,True),fill=GOLD)
    image.save(out,optimize=True)


def main():
    data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=data["editionDate"]
    news=sorted((x for x in data["news"] if x.get("date")==day and
                x.get("verification")=="editorial_verified"),
                key=lambda x:x.get("priority",999))
    if len(news)!=10 or len({x["id"] for x in news})!=10:
        raise RuntimeError("Se exigen diez noticias editoriales únicas")
    for x in news:
        if not x.get("sources") or not str(x["sources"][0]["url"]).startswith("https://"):
            raise RuntimeError("Falta fuente HTTPS")
    out=ROOT/"media"/day;out.mkdir(parents=True,exist_ok=True)
    cover(day,news,out/"portada.png")
    for i,n in enumerate(news,1):
        news_card(n,i,day,out/f"top10-{i:02d}.png")
    combined_sports_card(news[8],news[9],out/"top10-09.png")
    # Carrusel editorial con portada + cinco parejas (10 noticias).
    blocks=[news[i:i+2] for i in range(0,10,2)]
    start=1
    for i,group in enumerate(blocks,1):
        grouped_card(group,start,i,len(blocks),out/f"grupo-{i:02d}.png")
        start+=len(group)
    compact={
       "editionDate":day,"format":"compact_carousel",
       "slides":["portada.png"]+[f"grupo-{i:02d}.png" for i in range(1,6)],
       "newsCounts":[len(group) for group in blocks],
       "fullAudioInImages":False,
       "note":"Los PNG no incluyen audio. Para Instagram se debe producir un video narrado autorizado; la lectura completa ya existe en la web."
    }
    (out/"instagram-compacto.json").write_text(json.dumps(compact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Generadas portada y cinco laminas editoriales de dos noticias cada una.")


if __name__=="__main__":
    main()
