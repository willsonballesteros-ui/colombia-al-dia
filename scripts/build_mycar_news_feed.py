#!/usr/bin/env python3
"""Feed público MyCar a partir de ediciones realmente alojadas con créditos.

Solo usa MP4, editorial.json y credits.json presentes y coherentes. Preserva
ediciones históricas y permalinks de Instagram previamente comprobados.
"""
from __future__ import annotations
import datetime
import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"media"
OUTPUT=ROOT/"data"/"mycar-noticias.json"
PUBLIC="https://raw.githubusercontent.com/willsonballesteros-ui/colombia-al-dia/main/"
def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def valid_source(value):
    if not isinstance(value,str) or len(value)>2000:
        return False
    try:
        url=urlparse(value)
        return url.scheme=="https" and bool(url.hostname)
    except ValueError:
        return False


def modern_editions():
    """Consume the current five-story Salomé producer without touching ORBIUNO."""
    import hashlib
    for manifest in sorted(BASE.glob("????-??-??/edicion-*-mycar/mycar_manifest.json")):
        folder=manifest.parent
        m=load(manifest)
        date=m.get("edition","")
        slot=m.get("slot","")
        if m.get("brand")!="mycar" or date!=folder.parent.name or slot not in ("08:00","10:00","18:00"):
            continue
        if m.get("newsCount")!=5 or m.get("imagesCount")!=5 or m.get("fullNewsAudioFiles")!=5 or m.get("voice")!="es-CO-SalomeNeural" or m.get("voiceSpeed")!=1.25:
            raise RuntimeError("QA audiovisual incompleta: "+str(manifest))
        if m.get("qa")!="media_licenses_and_render_verified":
            raise RuntimeError("Falta QA de licencias y render: "+str(manifest))
        stamp=slot.replace(":","")
        key="MYCAR-"+date+"-"+stamp
        research=ROOT/"editions"/"research"/("mycar-"+date+"-"+stamp+"-ready.json")
        if not research.is_file():
            raise RuntimeError("Falta la selección editorial: "+str(research))
        ed=load(research)
        items,credits=ed.get("news",[]),m.get("photoCredits",[])
        if ed.get("editorialApproved") is not True or ed.get("sourceOnly") is not False or len(items)!=5 or len(credits)!=5:
            raise RuntimeError("Edición no aprobada: "+str(research))
        if ed.get("editionDate")!=date or ed.get("editionSlot")!=slot:
            raise RuntimeError("Fecha/franja incoherente: "+str(research))
        if [n.get("url") for n in items]!=m.get("sourceUrls") or len(set(m["sourceUrls"]))!=5:
            raise RuntimeError("Fuentes distintas a las del video")
        video_name=m.get("video","")
        if Path(video_name).name!=video_name or not video_name.endswith(".mp4"):
            raise RuntimeError("Nombre de video inválido")
        video=folder/video_name
        if not video.is_file() or video.stat().st_size<200000:
            raise RuntimeError("MP4 inexistente/incompleto")
        h=hashlib.sha256()
        with video.open("rb") as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b""):
                h.update(chunk)
        if h.hexdigest()!=m.get("sha256"):
            raise RuntimeError("MP4 distinto al aprobado")
        notes=[]
        for i,(n,c) in enumerate(zip(items,credits),1):
            photo=folder/f"foto-mycar-{i:02d}.jpg"
            audio=folder/f"mycar-noticia-{i:02d}.mp3"
            if (n.get("originalArticleReviewed") is not True or not valid_source(n.get("url"))
                or n.get("originalArticleSourceUrls")!=[n["url"]] or not n.get("title") or not n.get("source")
                or c.get("rightsVerified") is not True or not all(c.get(k) for k in ("author","license","source","title"))
                or not photo.is_file() or photo.stat().st_size<1000 or not audio.is_file() or audio.stat().st_size<1000):
                raise RuntimeError("Noticia sin derechos, audio o foto: "+str(i))
            notes.append({"title":n["title"],"summary":n["summary"],"source":n["source"],"source_url":n["url"],
                          "image_file_title":c["title"],"photo_credit":c["author"],"photo_license":c["license"],
                          "photo_page":c["source"],"photo_context":c.get("context",""),
                          "audio_url":"https://colombia-al-dia.pages.dev/"+audio.relative_to(ROOT).as_posix(),
                          "image_url":"https://colombia-al-dia.pages.dev/"+photo.relative_to(ROOT).as_posix()})
        page=ROOT/("mycar-"+date+"-"+stamp+".html")
        if not page.is_file():
            raise RuntimeError("Página de lectura completa ausente")
        yield key,{"edition_id":key,"date":date,"slot":slot,"title":notes[0]["title"],
                   "video_url":"https://colombia-al-dia.pages.dev/"+video.relative_to(ROOT).as_posix(),
                   "edition_url":"https://colombia-al-dia.pages.dev/"+page.name,
                   "instagram_url":None,"items":notes}


def produce():
    old=load(OUTPUT) if OUTPUT.exists() else {"editions":[]}
    previous={ed["edition_id"]:ed for ed in old.get("editions",[]) if isinstance(ed,dict) and ed.get("edition_id")}
    additions=0
    for dir in sorted(BASE.glob("????-??-??/mycar*")):
        if not dir.is_dir():
            continue
        date=dir.parent.name
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            continue
        if dir.name.endswith("-pm-5"):
            slot="Noche"
            key="MYCAR-"+date+"-PM-5"
        else:
            slot="18:00" if dir.name.endswith("-pm") else "08:00"
            key="MYCAR-"+date+("-PM" if slot=="18:00" else "-AM")
        editorial=dir/"editorial.json"
        credits=dir/"credits.json"
        mp4s=list(dir.glob("MYCAR_*_REEL_PUBLICAR.mp4")) if dir.name!="mycar-pm-5" else list(dir.glob("MYCAR_*_5_NOTICIAS.mp4"))
        if not editorial.exists() or not credits.exists() or len(mp4s)!=1:
            continue
        mp4=mp4s[0]
        if mp4.stat().st_size<100000:
            continue
        notes=load(editorial); rights=load(credits)
        if not isinstance(notes,list) or len(notes) not in (4,5) or not isinstance(rights,list) or len(rights)!=len(notes):
            raise RuntimeError("Estructura editorial inválida: "+str(dir))
        news=[]
        for note,credit in zip(notes,rights):
            if note.get("title")!=credit.get("headline") or note.get("url")!=credit.get("source"):
                raise RuntimeError("Desajuste fuente/medio: "+str(dir))
            if not all(isinstance(note.get(v),str) and note[v].strip() for v in ("title","say","source")):
                raise RuntimeError("Noticias incompletas: "+str(dir))
            if not valid_source(note.get("url")) or not all(credit.get(v) for v in ("license","author","commons","image_title")):
                raise RuntimeError("Fuente o licencia faltante: "+str(dir))
            news.append({"title":note["title"],"summary":note["say"],"source":note["source"],
                         "source_url":note["url"],"image_file_title":credit["image_title"],
                         "photo_credit":credit["author"],"photo_license":credit["license"],
                         "photo_page":credit["commons"]})
        row={"edition_id":key,"date":date,"slot":slot,"title":news[0]["title"],
             "video_url":PUBLIC+mp4.relative_to(ROOT).as_posix(),
             "instagram_url":previous.get(key,{}).get("instagram_url"),"items":news}
        # Keep confirmed publication IDs on rebuild; absent metadata stays absent.
        for published_field in ("instagram_media_id", "facebook_post_id", "facebook_post_type", "published_status"):
            if published_field in previous.get(key, {}):
                row[published_field] = previous[key][published_field]
        if previous.get(key)!=row:
            additions+=1
        previous[key]=row
    for key,row in modern_editions():
        old_row=previous.get(key,{})
        for field in ("instagram_url","instagram_media_id","facebook_post_id","facebook_post_type","published_status"):
            if field in old_row:
                row[field]=old_row[field]
        if old_row!=row:
            additions+=1
        previous[key]=row
    rows=sorted(previous.values(),key=lambda x:(x.get("date",""),x.get("slot","")),reverse=True)
    if any(len(e.get("items",[])) not in (4,5) or not valid_source(e.get("video_url")) for e in rows):
        raise RuntimeError("No se puede publicar feed inconsistente")
    data={"schema_version":1,"brand":"MYCAR AL DÍA","website":"https://busco-autos.pages.dev/",
          "updated_date":datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
          "editions":rows[:90]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MYCAR_FEED_OK editions={len(rows)} new_or_changed={additions}")

if __name__=="__main__":
    produce()
