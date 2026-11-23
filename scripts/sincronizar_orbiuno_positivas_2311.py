#!/usr/bin/env python3
"""Reemplaza solo la edición visible ORBIUNO del 23/11, mantiene MyCar intacto.

Las antiguas publicaciones Meta NO se borran aquí: el propietario lo hará.
Conserva el antiguo HTML en el historial para auditoría, sin mostrarlo como hoy.
"""
from __future__ import annotations
import json,re,shutil
from pathlib import Path
from scripts.prepare_site import build

ROOT=Path(__file__).resolve().parents[1]
DAY="2026-11-23"; SLOT="11:30"
MEDIA=ROOT/"media"/DAY/"edicion-1130-positivas"
RESEARCH=ROOT/"editions/research/2026-11-23-1130-positivas.json"
PAGE="orbiuno-2026-11-23-1130.html"

def main():
    src=json.loads(RESEARCH.read_text(encoding="utf-8"))
    manifest=json.loads((MEDIA/"orbiuno_manifest.json").read_text(encoding="utf-8"))
    assert src["editionDate"]==DAY and src["brand"]=="ORBIUNO"
    assert len(src["news"])==6 and manifest["newsCount"]==6
    assert manifest["audioSegments"]==7 and manifest["fullNewsAudioFiles"]==6
    assert manifest["openingSpeech"] is False and manifest["openingCover"] is False
    assert manifest["slot"]==SLOT and manifest["imagesCount"]==6 and manifest["logosCount"]==6
    shutil.copyfile(MEDIA/"orbiuno_edition.html",ROOT/PAGE)

    dbpath=ROOT/"noticias.json"
    db=json.loads(dbpath.read_text(encoding="utf-8"))
    # Eliminar de la portada actual las seis anteriores de 10:00, no su HTML,
    # fuentes, audios ni evidencia de publicación en GitHub/Drive.
    db["news"]=[
        n for n in db["news"]
        if not (n.get("date")==DAY and n.get("editionSlot")=="10:00"
                and str(n.get("id","")).startswith("orbiuno-20261123-1000-"))
        and not str(n.get("id","")).startswith("orbiuno-20261123-1130-")
    ]
    for i,(n,c) in enumerate(zip(src["news"],manifest["photoCredits"]),1):
        assert n["order"]==i and n["originalArticleReviewed"]
        assert c["rightsVerified"] and c["author"] and c["license"] and c["source"]
        db["news"].append({
            "id":f"orbiuno-20261123-1130-{i}","date":DAY,"editionSlot":SLOT,
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
            "originalArticleIsOwnWork":True,"imageType":"commons_licensed_photo",
            "imageRightsVerified":True,
            "imageUrl":f"./media/2026-11-23/edicion-1130-positivas/foto-orbiuno-{i:02d}.jpg",
            "imageCredit":c["author"],"imageLicense":c["license"],
            "imageSourceUrl":c["source"],"imageCaption":c["context"],
            "imageAlt":c["context"],"photoMatchReviewed":True,
            "instagramReelOrder":i,
            "audioFullTextEs":n["originalArticleTextEs"]
        })
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
        r'<nav id="orbiuno-positivas-2311".*?</nav>\s*'
        r'<script>\(function\(\).*?</script>',"",template,flags=re.S)
    output=build(db,template,as_of=DAY)
    bar=(
        '<nav id="orbiuno-positivas-2311" style="background:#0e344b;'
        'padding:14px;color:white;text-align:center">'
        '<strong>Hoy · 23/11/2026 · 11:30 a. m. Colombia</strong>'
        '<p><a style="color:#69ffe4;font-weight:700" href="./'+PAGE+'">'
        '▶ ORBIUNO: seis noticias positivas, fuentes y audios completos</a></p>'
        '<p><a style="color:#ffe89b" href="./mycar-2026-11-23-1000.html">'
        '▶ MyCar: cinco noticias del motor</a></p>'
        '</nav>'
        '<script>(function(){var d=new Intl.DateTimeFormat("en-CA",'
        '{timeZone:"America/Bogota",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());'
        'if(d!=="2026-11-23"){var x=document.getElementById("orbiuno-positivas-2311");'
        'if(x)x.remove();}})();</script>'
    )
    if "<body>" not in output:
        raise RuntimeError("Portada inválida")
    idx.write_text(output.replace("<body>","<body>"+bar,1),encoding="utf-8")
    # El feed RSS se regenera después y conserva fuentes/última edición.
    print("ORBIUNO_WEB_POSITIVAS_20261123_1130_OK",len(db["news"]),flush=True)

if __name__=="__main__":
    main()
