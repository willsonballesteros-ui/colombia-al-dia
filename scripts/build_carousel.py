#!/usr/bin/env python3
"""ORBIUNO: carrusel compacto, máximo cinco noticias verificadas por lámina.

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
    cached=ROOT/"media"/"source-icons"/(host+".png")
    if cached.exists():
        return Image.open(cached).convert("RGBA")
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


def licensed_image(note):
    """Fotografías documentadas: archivo local o Wikimedia Commons con licencia y crédito."""
    if not image_verified(note):
        return None
    local=verified_photo(note)
    try:
        if local:
            with Image.open(local) as original:
                return original.convert("RGB").copy()
        u=str(note.get("imageUrl",""))
        p=urlsplit(u)
        if p.scheme!="https" or p.hostname!="commons.wikimedia.org" or not p.path.startswith("/wiki/Special:FilePath/"):
            return None
        req=Request(u,headers={"User-Agent":"ORBIUNO-newsroom/1.0 (editorial image with documented credit)","Accept":"image/avif,image/webp,image/png,image/jpeg"})
        with urlopen(req,timeout=7) as response:
            content=response.read(4_000_001)
        if len(content)>4_000_000:
            return None
        with Image.open(io.BytesIO(content)) as original:
            if original.width*original.height>22_000_000:
                return None
            return original.convert("RGB").copy()
    except (OSError,ValueError,TypeError):
        return None


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
    """Formato ORBIUNO compacto: hasta cinco noticias en una lámina, nunca una por noticia."""
    if not 1 <= len(notes) <= 5:
        raise ValueError("Máximo cinco noticias en una lámina")
    im = Image.new("RGB", (W, H), "#160F2B")
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 153), fill="#1B1939")
    d.rectangle((0, 0, W, 13), fill="#FF715B")
    d.text((50, 28), "ORBIUNO", font=font(62, True), fill=WHITE)
    d.text((52, 108), "COLOMBIA AL DÍA  ·  INFORMACIÓN VERIFICADA", font=font(21, True), fill="#62E4D3")
    d.text((55, 175), f"NOTICIAS {first_number:02d} A {first_number+len(notes)-1:02d}   ·   LÁMINA {group_index}/{total_groups}",
           font=font(29, True), fill="#FFCE6B")
    colors = ["#FF8066", "#F9D16C", "#65E5D2", "#BF9EFF", "#FF9BC4"]
    start = 248
    gap = 16
    card_height = min(290, int((936 - gap*(len(notes)-1)) / len(notes)))
    for i, n in enumerate(notes):
        y = start + i*(card_height+gap)
        color = colors[i%len(colors)]
        d.rounded_rectangle((46, y, 1033, y+card_height), radius=19, fill="#2D2442")
        d.rounded_rectangle((46, y, 62, y+card_height), radius=8, fill=color)
        d.text((87, y+16), f"{first_number+i:02d}", font=font(34, True), fill=color)
        d.text((176, y+22), str(n.get("category","ACTUALIDAD")).upper()[:29],
               font=font(18, True), fill="#C8BDEE")
        title = str(n.get("socialHeadline") or n["title"])
        preferred = 34 if len(notes)>=4 else 43
        title_ft = font_for_lines(d, title, 820, 2, preferred=preferred,
                                  minimum=27 if len(notes)>=4 else 35, bold=True)
        paragraph(d, title, 87, y+58, title_ft, WHITE, 815, 2, 4)
        source = str(n["sources"][0]["name"])[:48]
        d.text((89, y+card_height-38), "FUENTE: "+source,
               font=font(19, True), fill=color)
        ico = favicon(n)
        if ico is not None:
            ico = ico.copy()
            ico.thumbnail((44,44), resample=Image.Resampling.LANCZOS)
            d.rounded_rectangle((947, y+card_height-62, 1011, y+card_height-4),
                                radius=9, fill="#FFFFFF")
            im.paste(ico, (957+(44-ico.width)//2,
                           y+card_height-57+(44-ico.height)//2), ico)
            d = ImageDraw.Draw(im)
    d.rectangle((0, 1224, W, H), fill="#1B1939")
    d.rectangle((0, 1224, W, 1232), fill="#65E5D2")
    d.text((53, 1245), "ESCUCHA EL REPORTE COMPLETO", font=font(28, True), fill="#FFCE6B")
    d.text((53, 1293), "colombia-al-dia.pages.dev  ·  @resumen.noticias",
           font=font(22, True), fill=WHITE)
    im.save(out, optimize=True)


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


def single_card(note,num,day,out):
    im=Image.new("RGB",(W,H),"#162044"); d=ImageDraw.Draw(im)
    accents=["#FFCF4B","#65F0D4","#FF8B71","#CCAEFF"]
    accent=accents[(num-1)%4]
    d.rectangle((0,0,W,14),fill=accent)
    d.text((60,42),"ORBIUNO",font=font(64,True),fill="#FFFFFF")
    d.text((62,128),f"{day}  /  "+("EDICIÓN DE LA MAÑANA" if datetime.now(ZoneInfo("America/Bogota")).hour<11 else "EDICIÓN DE MEDIODÍA" if datetime.now(ZoneInfo("America/Bogota")).hour<17 else "EDICIÓN DE LAS 18:00"),font=font(24,True),fill=accent)
    d.rounded_rectangle((60,207,1020,288),radius=16,fill=accent)
    d.text((87,224),f"{num:02d} / 10  ·  {note['category'].upper()}",font=font(31,True),fill="#162044")
    title=note.get("socialHeadline") or note["title"]
    ft=font_for_lines(d,title,940,5,preferred=68,minimum=48,bold=True)
    paragraph(d,title,65,345,ft,"#FFFFFF",940,5,15)
    d.line((65,820,1015,820),fill=accent,width=5)
    paragraph(d,note["executiveSummary"],68,866,font(34),"#E1E9FF",935,4,12)
    icon=favicon(note)
    if icon is not None:
        icon=icon.copy();icon.thumbnail((78,78),Image.Resampling.LANCZOS)
        d.rounded_rectangle((62,1090,154,1180),radius=14,fill="#FFFFFF")
        im.paste(icon,(68,1096),icon);d=ImageDraw.Draw(im)
    d.text((178,1102),"FUENTE",font=font(21,True),fill=accent)
    paragraph(d,note["sources"][0]["name"],178,1137,font(30,True),"#FFFFFF",820,1)
    d.rectangle((0,1220,W,H),fill=accent)
    d.text((62,1242),"FUENTES Y DESARROLLO EN LA WEB",font=font(26,True),fill="#162044")
    d.text((62,1291),"colombia-al-dia.pages.dev  ·  @resumen.noticias",font=font(22,True),fill="#162044")
    im.save(out,optimize=True)


def story_card(day, news, out):
    """Historia 9:16 segura en Instagram: marca, horario y CTA nunca ocultos.

    La interfaz cubre aproximadamente los 260 px superiores y los 390 px
    inferiores. Limitar el contenido esencial a x=100..940, y=260..1530.
    """
    im=Image.new("RGB",(1080,1920),"#1B142C")
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,18),fill="#FFCF69")  # Solo decoración fuera de zona segura
    now_hour=datetime.now(ZoneInfo("America/Bogota")).hour
    slot="08:00" if now_hour<10 else "12:00" if now_hour<16 else "18:00"

    # Cabecera compacta dentro de la zona segura; no se tapa en Reels/Stories.
    d.rounded_rectangle((108,278,240,398),radius=24,fill="#283268")
    d.text((132,297),"OU",font=font(65,True),fill="#FFCF69")
    d.text((273,284),"ORBIUNO",font=font(59,True),fill="#FFFFFF")
    d.text((275,364),"COLOMBIA AL DÍA · NOTICIAS",font=font(20,True),fill="#83EADD")
    d.rounded_rectangle((737,292,938,375),radius=18,fill="#FFD76A")
    d.text((757,307),slot,font=font(43,True),fill="#241832")

    d.text((109,476),"PANORAMA INFORMATIVO",font=font(44,True),fill="#FFFFFF")
    d.text((112,547),f"{len(news)} NOTICIAS VERIFICADAS",font=font(33,True),fill="#FFD76A")
    topics=[
        ("COLOMBIA Y MUNDO","#FF82AA"),
        ("ECONOMÍA Y TECNOLOGÍA","#78E6D6"),
        ("INTELIGENCIA ARTIFICIAL","#FFC266"),
        ("DEPORTES Y ENTRETENIMIENTO","#D4B7FF")
    ]
    for idx,(title,color) in enumerate(topics):
        y=626+idx*134
        d.rounded_rectangle((108,y,942,y+105),radius=18,fill="#30243E")
        d.rounded_rectangle((108,y,122,y+105),radius=5,fill=color)
        d.text((151,y+32),title,font=font(30,True),fill="#FFFFFF")

    # CTA completo y legible antes del área inferior tapada por Instagram.
    d.rounded_rectangle((108,1206,942,1524),radius=30,fill="#FFF0BD")
    d.text((142,1236),"ESCUCHA CADA NOTICIA",font=font(38,True),fill="#241832")
    d.text((142,1294),"UNA POR UNA, EN LA WEB",font=font(33,True),fill="#241832")
    d.text((142,1370),"↓ ENLACE DEL PERFIL",font=font(35,True),fill="#096C77")
    d.text((142,1440),"colombia-al-dia.pages.dev",font=font(29,True),fill="#39274A")
    im.save(out,optimize=True)


def main():
    data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=data["editionDate"]
    news=sorted((x for x in data["news"] if x.get("date")==day and
                x.get("verification")=="editorial_verified"),
                key=lambda x:x.get("priority",999))
    if not (1 <= len(news) <= 4) or len({x["id"] for x in news}) != len(news):
        raise RuntimeError("CONTROL EDITORIAL: no publicar carruseles incompletos; se requieren entre una y cuatro noticias verificadas únicas")
    for x in news:
        if not x.get("sources") or not str(x["sources"][0]["url"]).startswith("https://"):
            raise RuntimeError("Falta fuente HTTPS")
    out=ROOT/"media"/day;out.mkdir(parents=True,exist_ok=True)
    cover(day,news,out/"portada.png")
    story_card(day,news,out/"historia-orbiuno.png")
    # La versión publicada nunca utiliza una diapositiva por noticia.
    blocks=[news[i:i+2] for i in range(0,len(news),2)]
    start=1
    for i,group in enumerate(blocks,1):
        grouped_card(group,start,i,len(blocks),out/f"grupo-{i:02d}.png")
        start+=len(group)
    compact={
       "editionDate":day,"format":"compact_carousel_2_per_slide",
       "slides":["portada.png"]+[f"grupo-{i:02d}.png" for i in range(1,len(blocks)+1)],
       "newsCounts":[len(group) for group in blocks],
       "maxNewsPerSlide":2,
       "sourceNewsIds":[n["id"] for n in news],
       "fullAudioInImages":False,
       "noRepublishWithoutSubstantiveUpdates":True,
       "note":"Portada y hasta dos láminas de dos noticias. No reutilizar en boletines de seguimiento sin novedades acreditadas."
    }
    (out/"instagram-compacto.json").write_text(json.dumps(compact,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Generadas portada y láminas editoriales de máximo dos noticias cada una.")


if __name__=="__main__":
    main()

