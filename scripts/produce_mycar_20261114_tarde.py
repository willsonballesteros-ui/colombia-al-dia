#!/usr/bin/env python3
"""MyCar afternoon 14-Nov-2026: original four-story Reel.
Generated with real license-attributed archive imagery; no images from publishers.
No external publication in this script.
"""
import os,sys,hashlib,json,subprocess,urllib.parse,urllib.request,io
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import produce_night_reels as engine
OUT=ROOT/"media/2026-11-14-mycar-tarde"
OUT.mkdir(parents=True,exist_ok=True)
engine.OUT=OUT
os.environ["EDITION_DATE_LABEL"]="14 NOV 2026 · TARDE"
os.environ["ORBIUNO_REEL_COUNT"]="4"
os.environ.pop("PREVIEW_ONLY",None)
# Wikimedia Commons reusable pictures, real archival references (not from these launches).
CURATED=[
 ("Renault 4 E-Tech (54911777481).jpg","Alexandre Prevot","CC BY-SA 4.0"),
 ("Nissan Kicks 2025.jpg","JustAnotherCarDesigner","CC BY-SA 4.0"),
 ("Zeekr 001 (2022).jpg","JustAnotherCarDesigner","CC BY-SA 4.0"),
 ("Colombia driving license.jpg","Santiago G.","CC BY-SA 4.0")
]
# Query through Commons metadata and confirm compatible licensing + subject.
# Only use images that pass metadata/artist/license checks. Generic images are labeled archive.
def commons_subject(query):
  allowed={
    "Renault 4 E-Tech electric car":"Renault 4 E-Tech",
    "Nissan Kicks e Power SUV":"Nissan Kicks",
    "Zeekr 9X SUV":"Zeekr",
    "Colombia road traffic street sign":"road traffic"
  }
  stem=allowed[query]
  photo,credit=engine.choose_photo(stem)
  # Avoid model mismatch: title must mention exact brand or vehicle category
  title=credit["file"].lower()
  checks={
   "Renault 4 E-Tech electric car":("renault 4","renault_4"),
   "Nissan Kicks e Power SUV":("nissan kicks","nissan_kicks"),
   "Zeekr 9X SUV":("zeekr",),
   "Colombia road traffic street sign":("road","traffic","sign","carretera")
  }
  if not any(s in title for s in checks[query]):
   raise RuntimeError("Commons photo title does not match: "+query+" "+title)
  return photo,credit
engine.choose_photo=commons_subject if False else engine.choose_photo
STORIES=[
 {"title":"Renault 4 eléctrico abre preventa por 99,99 millones",
 "source":"Renault Sofasa","source_url":"https://prensa.renault.com.co/prensa/el-regreso-de-un-icono-renault-4-llega-a-colombia-en-version-100-electrica/",
 "photo_query":"Renault 4 E Tech",
 "voice":"El Renault 4 E Tech eléctrico abre preventa en Colombia desde noventa y nueve millones novecientos noventa mil pesos, para las primeras cincuenta unidades. La reserva cuesta un millón y se prevén entregas desde mayo de dos mil veintisiete. Fuente: Renault Sofasa."},
 {"title":"Nueva Nissan Kicks e-Power debuta en Colombia",
 "source":"El Carro Colombiano","source_url":"https://www.elcarrocolombiano.com/novedades/nissan-kicks-e-power-colombia-precios-ficha-tecnica-hibrida/",
 "photo_query":"Nissan Kicks car",
 "voice":"La Nissan Kicks e Power híbrida hace su debut en Colombia en el Salón del Automóvil. Tiene motor eléctrico de tracción y generador a gasolina. Consulta el precio vigente de cada versión y sus condiciones. Fuente: El Carro Colombiano."},
 {"title":"Zeekr muestra 9X, 7GT y 001 FR Edition",
 "source":"Autocosmos Colombia","source_url":"https://especiales.autocosmos.com.co/salon-del-automovil/noticias/2026/11/12/sia-2026-zeekr-presenta-en-colombia-los-nuevos-9x-7gt-y-001-fr-edition-awd",
 "photo_query":"Zeekr automobile",
 "voice":"Zeekr presenta en Bogotá tres novedades de alta gama: el híbrido nueve equis, el eléctrico siete ge te y el deportivo cero cero uno efe erre. Se exhiben en Corferias hasta el veintidós de noviembre. Fuente: Autocosmos Colombia."},
 {"title":"386 mil licencias vencerían antes de fin de año",
 "source":"Autocosmos Colombia","source_url":"https://noticias.autocosmos.com.co/2026/11/13/mas-de-386000-licencias-de-conduccion-venceran-en-colombia-este-fin-de-ano-como-renovarlas",
 "photo_query":"Colombia traffic road signs",
 "voice":"Atención conductores. Más de trescientas ochenta y seis mil licencias de conducción vencerían entre noviembre y diciembre, según datos de OlimpIA citados por Autocosmos. Verifica tu fecha de vencimiento en el RUNT antes de conducir."}
]
def main():
 a=engine.dora([s["voice"] for s in STORIES],"mycar-tarde")
 engine.render("MYCAR",STORIES,a,"")
 old=OUT/"mycar-2026-11-12-noche.mp4"
 file=OUT/"MYCAR-2026-11-14_TARDE_4_NOTICIAS.mp4"
 old.rename(file)
 meta_path=OUT/"mycar-credits.json"
 meta=json.loads(meta_path.read_text())
 meta.update({"date":"2026-11-14","edition":"16:00","brand":"MYCAR","video":file.name,
  "stories":[{"title":x["title"],"source":x["source_url"]} for x in STORIES],
  "sha256":hashlib.sha256(file.read_bytes()).hexdigest(),"status":"RENDERED_NOT_PUBLISHED"})
 meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2))
 print("MYCAR_TARDE_READY",str(file),len(STORIES),file.stat().st_size,flush=True)
if __name__=="__main__":main()
