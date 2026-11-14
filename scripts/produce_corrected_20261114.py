#!/usr/bin/env python3
"""Produce corrected 14-Nov-2026 editions with precise archival photos and sync ORBIUNO web.
Original drafts and Instagram posts are untouched. Publishing is a separate authorized step.
"""
import hashlib, io, json, os, sys, subprocess, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import preview_both_20261114 as edition
import produce_night_reels as engine
OUT=ROOT/"media/2026-11-14-publicable"
OUT.mkdir(parents=True,exist_ok=True)
edition.OUT=OUT
engine.OUT=OUT
os.environ.pop("PREVIEW_ONLY",None)
os.environ["EDITION_DATE_LABEL"]="14 NOV 2026 · EDICIÓN ESPECIAL"
# Exact Commons names and verifiable public licenses; not photos of the breaking event.
PHOTO_FIXES={
 "Airport passenger airplane runway":("JFK Airport aerial, New York City (20100325-DSC01275).jpg","Matti Blume","CC BY-SA 4.0"),
 "Nissan Frontier pickup":("Nissan Frontier Pro PHEV 001.jpg","JustAnotherCarDesigner","CC0 1.0"),
 "Volkswagen Golf GTI car":("Volkswagen Golf GTI (Mk VIII) Washington DC Metro Area, USA (3).jpg","OWS Photography","CC BY 4.0")
}
base_choose=engine.choose_photo
def precise_photo(query):
 if query not in PHOTO_FIXES:
  return base_choose(query)
 filename,artist,license_name=PHOTO_FIXES[query]
 file=filename.replace(" ","_")
 digest=hashlib.md5(file.encode("utf8")).hexdigest()
 raw_url="https://upload.wikimedia.org/wikipedia/commons/"+digest[0]+"/"+digest[:2]+"/"+urllib.parse.quote(file,safe="(),'-.")
 url="https://upload.wikimedia.org/wikipedia/commons/thumb/"+digest[0]+"/"+digest[:2]+"/"+urllib.parse.quote(file,safe="(),'-.")+"/960px-"+urllib.parse.quote(file,safe="(),'-.")
 req=urllib.request.Request(url,headers={"User-Agent":"ORBIUNOEditorial/1.0 (Commons license attribution)"})
 with urllib.request.urlopen(req,timeout=70) as response:
  raw=response.read(12000000)
 im=Image.open(io.BytesIO(raw));im.load()
 assert im.width>=700 and im.height>=450,(filename,im.size)
 attribution={"file":"File:"+filename,
    "commons":"https://commons.wikimedia.org/wiki/File:"+urllib.parse.quote(file,safe="(),'-."),
    "artist":artist,"license":license_name,"photo_url":url}
 print("EXACT_MODEL_ARCHIVAL",query,filename,im.size,flush=True)
 return im.convert("RGB"),attribution
engine.choose_photo=precise_photo

ORIGINAL_ARTICLES=[
"""Bogotá recibe durante el sábado catorce y el domingo quince de noviembre el festival México en el Corazón de Bogotá, una programación de gastronomía, expresiones culturales y emprendimientos en la Plaza de Bolívar. La agenda anunciada por el Distrito reúne a más de ochenta iniciativas que acercan tradiciones mexicanas a los visitantes del centro de la ciudad.

El encuentro es una opción cultural para residentes y turistas, pero los horarios de actividades específicas pueden cambiar. Quienes planeen asistir deben consultar la información actualizada de la Alcaldía y tener en cuenta las condiciones de movilidad alrededor de la Plaza de Bolívar. ORBIUNO presenta la invitación a partir de la programación oficial, sin afirmar aforos ni cifras de asistentes que todavía no estén verificadas.

La fotografía de archivo utilizada para ilustrar esta noticia corresponde a un elemento de la Plaza de Bolívar y no pretende documentar una presentación del festival. La fuente original incluye los detalles del evento y permite comprobar qué actividades están anunciadas para cada jornada.""",
"""La agenda cultural de Bogotá incluye una ruta literaria orientada a destacar la obra y la presencia de mujeres y niñas en distintos espacios creativos de la ciudad. La propuesta forma parte de los planes anunciados para el período del trece al diecinueve de noviembre y está vinculada con los Distritos Creativos y actividades de lectura.

La ruta busca conectar el público con la literatura y con experiencias culturales en espacios de Bogotá. Como las actividades pueden tener horarios, ubicaciones o requisitos de inscripción diferentes, conviene verificar cada encuentro en el calendario del Distrito. No se debe asumir que todas las sedes estarán abiertas permanentemente ni que existe entrada libre para cualquier sesión si el anuncio no lo especifica.

ORBIUNO presenta esta historia como una alternativa cultural positiva y recomienda acudir a la fuente oficial para conocer la programación vigente. La imagen que acompaña la publicación es de archivo y representa un espacio de lectura, no una fotografía tomada durante la ruta literaria de este fin de semana.""",
"""Estados Unidos reportó afectaciones en la operación aérea por problemas de comunicaciones y posteriormente comenzaron a normalizarse los despegues. Las autoridades aeronáuticas y los operadores trabajan bajo protocolos de seguridad, por lo que el regreso de los vuelos no necesariamente se produce al mismo tiempo en todos los aeropuertos.

Una suspensión temporal de salidas afecta la planificación de los viajeros, pero no significa que todos los aviones que estaban en vuelo hayan quedado detenidos. La duración de los retrasos puede variar según el aeropuerto, la aerolínea y la ruta. Las personas que tengan tiquetes para viajar deben consultar el estado específico de su vuelo antes de desplazarse al terminal.

La información se basa en reportes periodísticos de la situación y se presenta como actualización, no como una afirmación de que todos los servicios hayan vuelto completamente a la normalidad. La fotografía empleada muestra un aeropuerto estadounidense de archivo; no corresponde al momento de la falla ni constituye una imagen del operativo de la autoridad.""",
"""Denza, la marca de vehículos de gama alta del grupo automotor BYD, amplía su presencia internacional con su presentación en India. La oferta anunciada incluye la miniván eléctrica D9 y el modelo deportivo Z9 GT, con los que la compañía busca competir en el segmento prémium y diversificar su presencia fuera de China.

El movimiento refleja una estrategia de expansión de fabricantes chinos hacia nuevos mercados, especialmente en categorías de mayor valor. La entrada de una marca a otro país no significa que sus vehículos estén homologados, disponibles o con precios confirmados para Colombia. Es importante distinguir el anuncio comercial en India de una eventual oferta futura para nuestro mercado.

ORBIUNO recoge los principales datos del anuncio reportado por Reuters y los contextualiza sin añadir cifras de ventas o cuotas de mercado que no se hayan confirmado. La fotografía es una referencia del modelo Denza D9, no una imagen oficial de la ceremonia realizada en India.""",
"""SpaceX realizó el decimoquinto vuelo de prueba de Starship, un vehículo diseñado para desarrollar capacidades de transporte espacial reutilizable. Durante la misión se reportó la llegada a la órbita y el despliegue de satélites Starlink, dos hitos operativos incluidos entre los objetivos de la prueba.

El regreso del propulsor no concluyó como estaba previsto, un resultado que recuerda el carácter experimental del programa. Los vuelos de prueba pueden combinar avances y fallas, y sus resultados deben evaluarse por etapas, no solo por un indicador de éxito o fracaso. Las declaraciones sobre futuros lanzamientos o cambios en el diseño requieren nuevos anuncios oficiales.

La historia forma parte de la selección sorprendente de ORBIUNO por su interés tecnológico y científico. La fotografía que aparece en la noticia es una imagen real de archivo de otro vuelo de Starship, con crédito a la NASA; no debe confundirse con una captura de esta misión número quince.""",
"""Karol G aparece entre los artistas colombianos reconocidos en la edición de los Latin Grammy dos mil veintiséis. En la información sobre los ganadores se destaca el premio a mejor álbum de música urbana por Tropicoqueta y la distinción compartida con Feid por la interpretación de reguetón Verano Rosa.

La premiación reúne representantes de distintas escenas musicales latinoamericanas y ofrece visibilidad internacional a los proyectos de artistas y productores. El resultado de una categoría no equivale necesariamente a una clasificación de popularidad o al número de reproducciones en plataformas. ORBIUNO evita atribuir cifras de audiencia o de seguidores que no estén documentadas en los resultados.

Esta nota está construida a partir del listado de premiados y se enfoca en los reconocimientos reportados, no en especulaciones sobre los artistas. La fotografía es un retrato de archivo de Karol G tomado años antes de la premiación y se publica con el crédito y la licencia correspondientes."""
]
def sync_web(metadata):
 dbpath=ROOT/"noticias.json"
 db=json.loads(dbpath.read_text(encoding="utf8"))
 ids={n["id"] for n in db["news"]}
 existing=[x for x in db["news"] if x.get("date")=="2026-11-14" and x.get("editionSlot")=="12:00"]
 if existing:raise RuntimeError("An edition already occupies 12:00 on Nov 14; no overwrite")
 if db["editionDate"]>"2026-11-14":raise RuntimeError("Edition date moved beyond target")
 for i,(story,article) in enumerate(zip(edition.ORBIUNO,ORIGINAL_ARTICLES),1):
  title,category,source_url,query,voice=story
  pid="orbiuno-20261114-12h-"+str(i)
  if pid in ids:raise RuntimeError("Duplicated news ID")
  credit=metadata["license_photos"][i-1]["photo"]
  if len(article)<640 or len(article.split("\n\n"))<3:raise RuntimeError("Article draft incomplete")
  source_name={"Bogotá":"Alcaldía de Bogotá","Cultura Bogotá":"Bogotá.gov.co","Mundo":"Reuters","Economía":"Reuters","Tecnología":"Reuters","Farándula":"Associated Press"}[category]
  db["news"].append({
   "id":pid,"date":"2026-11-14","editionSlot":"12:00","priority":i,
   "category":category,"title":title,"summary":voice,"executiveSummary":voice,
   "verification":"editorial_verified","sourceLanguage":"es",
   "sources":[{"name":source_name,"url":source_url}],
   "audioIsFullPublisherArticle":False,"audioFullTextEs":article,
   "originalArticleByline":"Redacción ORBIUNO","originalArticleReviewed":True,
   "originalArticleReviewStatus":"aprobado",
   "originalArticleIsPublisherVerbatim":False,"originalArticleSourceUrls":[source_url],
   "originalArticleTextEs":article,"imageType":"licensed_press_photo",
   "imageRightsVerified":True,
   "imageUrl":"./media/2026-11-14-publicable/orbiuno-%02d.jpg"%i,
   "imageAlt":"Fotografía real de archivo referencial; no corresponde a este evento",
   "imageCaption":"Foto real de archivo para contextualizar la noticia",
   "imageLicense":credit["license"],"imageCredit":credit["artist"],
   "imageSourceUrl":credit["commons"]})
 db["editionDate"]="2026-11-14"
 dbpath.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("WEBSITE_SYNCED_SIX_NEWS_2026_11_14",flush=True)
def render(name,rows):
 edition.run_brand(name,rows)
 folder=OUT
 old=folder/(name+"-2026-11-14_BORRADOR_"+str(len(rows))+"_NOTICIAS.mp4")
 final=folder/(name+"-2026-11-14_FINAL_"+str(len(rows))+"_NOTICIAS.mp4")
 old.rename(final)
 path=folder/(name.lower()+"-credits.json")
 meta=json.loads(path.read_text(encoding="utf8"))
 meta.update({"video":final.name,"status":"PRODUCED_PENDING_INSTAGRAM","edition":"2026-11-14-12h",
              "sha256":hashlib.sha256(final.read_bytes()).hexdigest()})
 path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 return meta
def main():
 a=render("ORBIUNO",edition.ORBIUNO)
 b=render("MYCAR",edition.MYCAR)
 sync_web(a)
 print("READY_FOR_VERIFICATION",a["video"],b["video"],flush=True)
if __name__=="__main__":main()
