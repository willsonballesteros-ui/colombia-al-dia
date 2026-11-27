#!/usr/bin/env python3
"""Reemplaza solo la edición visible ORBIUNO del 23/11, mantiene MyCar intacto.

Las antiguas publicaciones Meta NO se borran aquí: el propietario lo hará.
Conserva el antiguo HTML en el historial para auditoría, sin mostrarlo como hoy.
"""
from __future__ import annotations
import json,re,shutil,os
from datetime import datetime,date
from zoneinfo import ZoneInfo
from pathlib import Path
from scripts.prepare_site import build

ROOT=Path(__file__).resolve().parents[2]
DAY=os.environ.get("EDITION_DAY",datetime.now(ZoneInfo("America/Bogota")).date().isoformat())
SLOT=os.environ.get("EDITION_SLOT","08:00")
assert date.fromisoformat(DAY).isoformat()==DAY and SLOT in ("08:00","18:00")
STAMP=SLOT.replace(":",""); KEY=DAY.replace("-","")+"-"+STAMP
LABEL=date.fromisoformat(DAY).strftime("%d/%m/%Y")+" · "+("08:00 a. m." if SLOT=="08:00" else "06:00 p. m.")+" Colombia"
MEDIA=ROOT/"media"/DAY/f"edicion-{STAMP}-orbiuno"
RESEARCH=MEDIA/"selected_news.json"
PAGE=f"orbiuno-{DAY}-{STAMP}.html"

def main():
    src=json.loads(RESEARCH.read_text(encoding="utf-8"))
    manifest=json.loads((MEDIA/"orbiuno_manifest.json").read_text(encoding="utf-8"))
    assert src["editionDate"]==DAY and src["brand"]=="ORBIUNO"
    assert len(src["news"])==6 and manifest["newsCount"]==6
    assert manifest["audioSegments"]==7 and manifest["fullNewsAudioFiles"]==6
    assert manifest["openingSpeech"] is False and manifest["openingCover"] is False
    assert manifest["slot"]==SLOT and manifest["imagesCount"]==6 and manifest["sourceLabelsCount"]==6
    shutil.copyfile(MEDIA/"orbiuno_edition.html",ROOT/PAGE)

    dbpath=ROOT/"noticias.json"
    db=json.loads(dbpath.read_text(encoding="utf-8"))
    # Eliminar de la portada actual las seis anteriores de 10:00, no su HTML,
    # fuentes, audios ni evidencia de publicación en GitHub/Drive.
    if any(n.get("date")==DAY and n.get("editionSlot")==SLOT and n.get("verification")=="editorial_verified" for n in db["news"]):
        raise RuntimeError("Edición ya registrada; no duplicar")
    for i,(n,c) in enumerate(zip(src["news"],manifest["photoCredits"]),1):
        assert n["order"]==i and n["originalArticleReviewed"]
        assert c["rightsVerified"] and c["author"] and c["license"] and c["source"]
        db["news"].append({
            "id":f"orbiuno-{KEY}-{i}","date":DAY,"editionSlot":SLOT,
            "priority":i,"title":n["title"],"category":n["category"],
            "level":"Noticia verificada · enfoque constructivo",
            "sources":[{"name":n["source"],"url":n["url"]}],
            "summary":n["summary"],"executiveSummary":n["summary"],
            "reelLine":n["spoken"],"verification":"editorial_verified",
            "sourceLanguage":"es",
            "originalArticleTextEs":n["originalArticleTextEs"],
            "originalArticleByline":"Redacción ORBIUNO",
            "originalArticleSourceUrls":[n["url"]],"originalArticleReviewed":True,
            "originalArticleReviewStatus":"aprobada","originalArticleIsPublisherVerbatim":False,
            "originalArticleIsOwnWork":True,"imageType":"licensed_archival_photo",
            "imageRightsVerified":True,
            "imageUrl":f"./media/{DAY}/edicion-{STAMP}-orbiuno/foto-orbiuno-{i:02d}.jpg",
            "imageCredit":c["author"],"imageLicense":c["license"],
            "imageSourceUrl":c["source"],"imageCaption":c["context"],
            "imageAlt":c["context"],"photoMatchReviewed":True,
            "instagramReelOrder":i,
            "audioFullTextEs":n["originalArticleTextEs"]
        })
    voice_path=ROOT/"media/web-voice/manifest.json"
    voice=json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {"items":{}}
    for i,n in enumerate(src["news"],1):
        audio=MEDIA/f"orbiuno-noticia-{i:02d}.mp3"
        assert audio.stat().st_size>1000
        voice.setdefault("items",{})[f"orbiuno-{KEY}-{i}"]={"url":"./"+audio.relative_to(ROOT).as_posix(),"text":n["originalArticleTextEs"],"voice":"es-CO-SalomeNeural","tempo":1.25}
    voice_path.parent.mkdir(parents=True,exist_ok=True)
    voice_path.write_text(json.dumps(voice,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    db["editionDate"]=DAY
    dbpath.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    idx=ROOT/"index.html"
    template=idx.read_text(encoding="utf-8")
    # La web no debe seguir promocionando la edición antigua como actual.
    template=re.sub(
        r'<nav id="ediciones-matinales-23nov".*?</nav>\s*'
        r'<script>\(function\(\).*?</script>',"",template,flags=re.S)
    # Eliminar una versión previa de esta propia promoción, sin duplicarla.
    template=re.sub(
        r'<nav id="(?:orbiuno-manana-2611|orbiuno-manana-2511|orbiuno-tarde-2511|orbiuno-positivas-2311|orbiuno-edicion-actual)".*?</nav>\s*'
        r'<script>\(function\(\).*?</script>',"",template,flags=re.S)
    output=build(db,template,as_of=DAY)
    bar=(
        '<nav id="orbiuno-edicion-actual" style="background:#0e344b;'
        'padding:14px;color:white;text-align:center">'
        '<strong>Hoy · '+LABEL+'</strong>'
        '<p><a style="color:#69ffe4;font-weight:700" href="./'+PAGE+'">'
        '▶ ORBIUNO: seis noticias positivas, fuentes y audios completos</a></p>'
        '<p><a style="color:#ffe89b" href="./mycar-'+DAY+'-'+STAMP+'.html">'
        '▶ MyCar: cinco noticias del motor</a></p>'
        '</nav>'
        '<script>(function(){var d=new Intl.DateTimeFormat("en-CA",'
        '{timeZone:"America/Bogota",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());'
        'if(d!=="'+DAY+'"){var x=document.getElementById("orbiuno-edicion-actual");'
        'if(x)x.remove();}})();</script>'
    )
    if "<body>" not in output:
        raise RuntimeError("Portada inválida")
    idx.write_text(output.replace("<body>","<body>"+bar,1),encoding="utf-8")
    # El feed RSS se regenera después y conserva fuentes/última edición.
    print("ORBIUNO_WEB_SYNC_OK",len(db["news"]),flush=True)

if __name__=="__main__":
    main()
