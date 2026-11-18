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
        slot="18:00" if dir.name.endswith("-pm") else "08:00"
        key="MYCAR-"+date+("-PM" if slot=="18:00" else "-AM")
        editorial=dir/"editorial.json"
        credits=dir/"credits.json"
        mp4s=list(dir.glob("MYCAR_*_REEL_PUBLICAR.mp4"))
        if not editorial.exists() or not credits.exists() or len(mp4s)!=1:
            continue
        mp4=mp4s[0]
        if mp4.stat().st_size<100000:
            continue
        notes=load(editorial); rights=load(credits)
        if not isinstance(notes,list) or len(notes)!=4 or not isinstance(rights,list) or len(rights)!=4:
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
        if previous.get(key)!=row:
            additions+=1
        previous[key]=row
    rows=sorted(previous.values(),key=lambda x:(x.get("date",""),x.get("slot","")),reverse=True)
    if any(len(e.get("items",[]))!=4 or not valid_source(e.get("video_url")) for e in rows):
        raise RuntimeError("No se puede publicar feed inconsistente")
    data={"schema_version":1,"brand":"MYCAR AL DÍA","website":"https://busco-autos.pages.dev/",
          "updated_date":datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
          "editions":rows[:90]}
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MYCAR_FEED_OK editions={len(rows)} new_or_changed={additions}")

if __name__=="__main__":
    produce()
