#!/usr/bin/env python3
"""ORBIUNO: carrusel rápido, un titular + dos líneas + fuente por lámina.

Las fotos se reproducen SOLO con derechos verificados. En su ausencia se
muestra favicon REAL del sitio periodístico, no una fotografía inventada.
La portada es la primera diapositiva del carrusel estático de Instagram.
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


def font_for_lines(draw, text, width, count, preferred=34, minimum=24, bold=False):
    """Ajustar fuente para que el resumen quede completo en dos líneas."""
    for size in range(preferred, minimum-1, -1):
        face=font(size,bold=bold)
        if len(wrap(draw,text,face,width,99))<=count:
            return face
    return font(minimum,bold=bold)


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
    """Diez noticias con jerarquía EQUITATIVA: cinco filas por dos columnas."""
    im=Image.new("RGB",(W,H),"#F5F7FD"); d=ImageDraw.Draw(im)
    navy="#121A35"
    d.rectangle((0,0,W,183),fill=navy)
    d.rectangle((0,0,W,13),fill="#FF684E")
    d.text((49,23),"ORBIUNO",font=font(65,True),fill="#FFFFFF")
    d.text((50,105),"COLOMBIA AL DÍA  /  PANORAMA COMPLETO",font=font(23,True),fill="#66F3D7")
    stamp=datetime.now(ZoneInfo("America/Bogota")).strftime("%H:%M")
    d.rounded_rectangle((770,45,1032,121),radius=18,fill="#FCDF59")
    d.text((793,57),"CORTE "+stamp,font=font(28,True),fill=navy)
    date_display=datetime.strptime(day,"%Y-%m-%d").strftime("%d/%m/%Y")
    hour=datetime.now(ZoneInfo("America/Bogota")).hour
    edition_name=("EDICIÓN DE LA MAÑANA" if hour<11 else "EDICIÓN DE MEDIODÍA" if hour<17 else "EDICIÓN NOCTURNA")
    d.text((46,193),date_display+" · "+edition_name,font=font(23,True),fill=navy)
    d.text((46,229),f"{len(news)} NOTICIAS. TODAS EN PORTADA.",font=font(30,True),fill="#E9466B")
    fills=["#FFF0E6","#E3F8F6","#F1EAFE","#E6F1FF","#FFF0F5"]
    accents=["#FF6747","#00AFA7","#8A57DE","#3184D5","#E84682"]
    for i,n in enumerate(news[:10]):
        col=i%2; row=i//2
        x=42+col*505; y=285+row*173
        accent=accents[row]; bg=fills[row]
        d.rounded_rectangle((x,y,x+491,y+162),radius=16,fill=bg)
        d.rounded_rectangle((x,y,x+10,y+162),radius=5,fill=accent)
        d.text((x+21,y+13),f"{i+1:02d}",font=font(31,True),fill=accent)
        cat=str(n.get("category","NOTICIAS")).upper()[:24]
        d.text((x+91,y+18),cat,font=font(16,True),fill="#414E67")
        title=str(n.get("socialHeadline") or n["title"]).strip()
        ft=font_for_lines(d,title,448,2,preferred=27,minimum=21,bold=True)
        paragraph(d,title,x+21,y+54,ft,navy,450,2,3)
        icon=favicon(n)
        if icon is not None:
            icon=icon.copy();icon.thumbnail((44,44),resample=Image.Resampling.LANCZOS)
            d.rounded_rectangle((x+17,y+117,x+67,y+159),radius=7,fill="#FFFFFF")
            im.paste(icon,(x+20,y+116),icon);d=ImageDraw.Draw(im)
        source=str(n["sources"][0]["name"]).split(" · ")[0].split(" / ")[0][:37]
        d.text((x+78,y+126),source,font=font(20,True),fill="#394560")
    d.rectangle((0,1175,W,H),fill=navy)
    d.rectangle((0,1175,W,1185),fill="#00CDB9")
    d.text((45,1202),f"ESCUCHA LAS {len(news)} NOTICIAS EN NUESTRA WEB",font=font(28,True),fill="#FCDF59")
    d.text((46,1251),"colombia-al-dia.pages.dev",font=font(27,True),fill="#FFFFFF")
    d.text((47,1298),"@resumen.noticias  ·  FUENTES Y ENLACES ORIGINALES",font=font(19),fill="#A9C4E2")
    im.save(out,optimize=True)


def grouped_card(notes, first_number, group_index, total_groups, out):
    """Dos noticias por lámina; colores vivos y logos de las fuentes en tamaño legible."""
    if len(notes)!=2: raise ValueError("Se requieren exactamente dos noticias por lámina")
    im=Image.new("RGB",(W,H),"#F5F7FD")
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,W,166),fill="#121A35")
    d.rectangle((0,0,W,12),fill="#FF684E")
    d.text((50,25),"ORBIUNO",font=font(63,True),fill="#FFFFFF")
    d.text((51,109),"COLOMBIA AL DÍA   /   NOTICIAS VERIFICADAS",font=font(21,True),fill="#66F3D7")
    d.text((52,180),f"PANORAMA  ·  LÁMINA {group_index} DE {total_groups}",font=font(29,True),fill="#152447")
    tones=[("#182347","#FFCE4E","#E4EFFB"),("#35214E","#62F1D9","#F6E9FD")]
    for i,n in enumerate(notes):
        y=244+i*478; col,accent,light=tones[i]
        d.rounded_rectangle((44,y,1036,y+457),radius=22,fill=col)
        d.rounded_rectangle((44,y,58,y+457),radius=9,fill=accent)
        d.rounded_rectangle((76,y+22,172,y+96),radius=16,fill=accent)
        d.text((94,y+36),f"{first_number+i:02d}",font=font(36,True),fill=col)
        d.text((192,y+42),str(n.get("category","ACTUALIDAD")).upper()[:30],
               font=font(26,True),fill=accent)
        title=str(n.get("socialHeadline") or n["title"])
        title_ft=font_for_lines(d,title,910,3,preferred=55,minimum=39,bold=True)
        paragraph(d,title,89,y+119,title_ft,"#FFFFFF",885,3,8)
        d.line((90,y+304,989,y+304),fill=accent,width=4)
        detail=str(n.get("socialDetail") or n.get("executiveSummary") or n.get("summary",""))
        ft=font_for_lines(d,detail,892,2,preferred=27,minimum=23)
        paragraph(d,detail,91,y+321,ft,light,883,2,7)
        ico=favicon(n)
        if ico is not None:
            ico=ico.copy();ico.thumbnail((59,59),resample=Image.Resampling.LANCZOS)
            d.rounded_rectangle((83,y+391,152,y+453),radius=11,fill="#FFFFFF")
            im.paste(ico,(88,y+391),ico);d=ImageDraw.Draw(im)
        d.text((166,y+406),"FUENTE: "+str(n["sources"][0]["name"])[:52],
               font=font(23,True),fill=accent)
    d.rectangle((0,1227,W,H),fill="#121A35")
    d.rectangle((0,1227,W,1235),fill="#FF684E")
    d.text((52,1248),"ESCUCHA EL DESARROLLO EN ORBIUNO",font=font(27,True),fill="#FFCE4E")
    d.text((52,1293),"colombia-al-dia.pages.dev    ·    @resumen.noticias",
           font=font(21,True),fill="#FFFFFF")
    im.save(out,optimize=True)


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
    if len(news) != 10 or len({x["id"] for x in news}) != 10:
        raise RuntimeError("CONTROL EDITORIAL: no publicar carruseles incompletos; se requieren diez noticias verificadas únicas")
    for x in news:
        if not x.get("sources") or not str(x["sources"][0]["url"]).startswith("https://"):
            raise RuntimeError("Falta fuente HTTPS")
    out=ROOT/"media"/day;out.mkdir(parents=True,exist_ok=True)
    cover(day,news,out/"portada.png")
    for i,n in enumerate(news,1):
        news_card(n,i,day,out/f"top10-{i:02d}.png")
    if len(news) >= 10:
        combined_sports_card(news[8],news[9],out/"top10-09.png")
    # Carrusel editorial con portada + cinco parejas (10 noticias).
    blocks=[news[i:i+2] for i in range(0,len(news),2)]
    start=1
    for i,group in enumerate(blocks,1):
        (grouped_card(group,start,i,len(blocks),out/f"grupo-{i:02d}.png") if len(group)==2 else news_card(group[0],start,day,out/f"grupo-{i:02d}.png"))
        start+=len(group)
    compact={
       "editionDate":day,"format":"compact_carousel",
       "slides":["portada.png"]+[f"grupo-{i:02d}.png" for i in range(1,len(blocks)+1)],
       "newsCounts":[len(group) for group in blocks],
       "fullAudioInImages":False,
       "note":"Carrusel estático de seis imágenes, sin video. La narración completa está disponible en la web."
    }
    (out/"instagram-compacto.json").write_text(json.dumps(compact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Generadas portada y laminas editoriales de hasta dos noticias cada una.")


if __name__=="__main__":
    main()
