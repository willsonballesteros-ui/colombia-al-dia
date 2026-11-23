#!/usr/bin/env python3
"""Publicar en los archivos web de ORBIUNO/MyCar los videos y textos comprobados.

Mantiene el historial. No contacta Instagram/Facebook; la publicación social
se realiza sólo después de que los MP4, licencias y web estén confirmados.
"""
from pathlib import Path
import json
import shutil
from scripts.prepare_site import build
ROOT=Path(__file__).resolve().parents[1]
DATE="2026-11-23"
MEDIA=ROOT/"media"/DATE/"edicion-1000"
SOURCE=ROOT/"editions/research/2026-11-23-am-source-checked.json"
SITE_ROOT="https://raw.githubusercontent.com/willsonballesteros-ui/colombia-al-dia/main/media/2026-11-23/edicion-1000/"
def main():
    doc=json.loads(SOURCE.read_text(encoding="utf-8"))
    dbpath=ROOT/"noticias.json"
    db=json.loads(dbpath.read_text(encoding="utf-8"))
    assert doc["editionDate"]==DATE
    if any(n.get("date")==DATE and n.get("editionSlot")=="10:00" and n.get("verification")=="editorial_verified" for n in db["news"]):
        raise RuntimeError("Edición de las 10:00 ya existe: evitar duplicados")
    for brand in ("orbiuno","mycar"):
        m=json.loads((MEDIA/(brand+"_manifest.json")).read_text(encoding="utf-8"))
        assert m["edition"]==DATE and m["slot"]=="10:00"
        assert m["newsCount"]==len(doc[brand]) and len(m["photoCredits"])==len(doc[brand])
        name=f"{brand}-2026-11-23-1000.html"
        shutil.copyfile(MEDIA/(brand+"_edition.html"),ROOT/name)
        if brand=="orbiuno":
            for i,(n,p) in enumerate(zip(doc[brand],m["photoCredits"]),1):
                row={"id":f"orbiuno-20261123-1000-{i}",
                  "date":DATE,"editionSlot":"10:00","priority":i,
                  "title":n["title"],"category":n["category"],
                  "level":"Verificada y publicada con fotografía Commons",
                  "sources":[{"name":n["source"],"url":n["url"]}],
                  "summary":n["summary"],"executiveSummary":n["summary"],
                  "reelLine":n.get("spoken") or n["reelLine"],
                  "verification":"editorial_verified",
                  "sourceLanguage":"es",
                  "originalArticleTextEs":n["originalArticleTextEs"],
                  "originalArticleByline":"Redacción ORBIUNO",
                  "originalArticleSourceUrls":[n["url"]],
                  "originalArticleReviewed":True,
                  "originalArticleReviewStatus":"aprobada",
                  "originalArticleIsPublisherVerbatim":False,
                  "audioIsFullPublisherArticle":False,
                  "imageType":"commons_licensed_photo",
                  "imageRightsVerified":True,
                  "imageUrl":f"./media/2026-11-23/edicion-1000/foto-orbiuno-{i:02d}.jpg",
                  "imageCredit":p["author"],
                  "imageLicense":p["license"],
                  "imageSourceUrl":p["source"],
                  "imageCaption":p["context"],
                  "imageAlt":p["context"],
                  "photoMatchReviewed":True,
                  "originalArticleIsOwnWork":True,
                  "instagramReelOrder":i,
                  }
                db["news"].append(row)
        else:
            feedpath=ROOT/"data/mycar-noticias.json"
            feed=json.loads(feedpath.read_text(encoding="utf-8")) if feedpath.is_file() else {"editions":[]}
            key="MYCAR-2026-11-23-1000"
            if any(e.get("edition_id")==key for e in feed.get("editions",[])):
                raise RuntimeError("Edición MyCar ya existe en el feed")
            items=[{"title":n["title"],"summary":n["summary"],"source":n["source"],"source_url":n["url"],
                    "image_file_title":p["title"],"photo_credit":p["author"],
                    "photo_license":p["license"],"photo_page":p["source"]} for n,p in zip(doc[brand],m["photoCredits"])]
            feed["editions"].insert(0,{"edition_id":key,"date":DATE,"slot":"10:00",
                "title":doc["mycar"][0]["title"],"video_url":SITE_ROOT+m["video"],
                "instagram_url":None,"items":items,"published_status":"WEB_PREPARED_SOCIAL_PENDING"})
            feed["updated_date"]=DATE
            feedpath.parent.mkdir(parents=True,exist_ok=True)
            feedpath.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    db["editionDate"]=DATE
    dbpath.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    # Actualizar índice usando el generador existente; no insertar banners de fechas antiguas.
    template=(ROOT/"index.html").read_text(encoding="utf-8")
    from scripts.prepare_site import build
    output=build(db,template,as_of=DATE)
    # Inserción discreta de enlaces a dos ediciones del MISMO día. El enlace MyCar
    # no altera el flujo de noticias ORBIUNO, y el historial queda en sección propia.
    link_panel=(
        '<nav id="ediciones-matinales-23nov" data-edition-date="2026-11-23" '
        'style="background:#123e52;color:#fff;text-align:center;padding:12px">'
        '<strong>Ediciones de hoy · 23/11/2026 · 10:00 a. m. Colombia</strong>'
        '<p><a style="color:#85f5ee" href="./orbiuno-2026-11-23-1000.html">'
        '▶ ORBIUNO: seis noticias y sus audios</a></p>'
        '<p><a style="color:#ffe692" href="./mycar-2026-11-23-1000.html">'
        '▶ MyCar: cinco noticias y sus audios</a></p></nav>'
        '<script>(function(){var d=new Intl.DateTimeFormat("en-CA",'
        '{timeZone:"America/Bogota",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());'
        'if(d!=="2026-11-23"){var e=document.getElementById("ediciones-matinales-23nov");'
        'if(e)e.remove();}})();</script>'
    )
    if "ediciones-matinales-23nov" not in output:
        output=output.replace("<body>","<body>"+link_panel,1)
    (ROOT/"index.html").write_text(output,encoding="utf-8")
    print("ORBIUNO_AND_MYCAR_WEB_STAGED_2026_11_23",len(db["news"]),flush=True)
if __name__=="__main__":
    main()
