#!/usr/bin/env python3
"""ORBIUNO six-story edition: real licensed imagery, original Dora audio, verified MP4.
No Meta publishing here; separate gate checks six stories, rights and exact video URL.
"""
import hashlib, json, os, subprocess, sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import produce_night_reels as p
DATE="2026-11-13"
OUT=ROOT/"media"/DATE
OUT.mkdir(parents=True,exist_ok=True)
p.OUT=OUT
os.environ["ORBIUNO_REEL_COUNT"]="6"
os.environ["EDITION_DATE_LABEL"]="13 NOV 2026 · EDICIÓN 18H"
NEWS_URL="https://www.vanguardia.com/entretenimiento/tendencias/2026/11/13/j-balvin-conmovio-a-daddy-yankee-al-entregarle-el-premio-persona-del-ano-en-los-latin-grammy-2026/"
SIXTH_ID="orbiuno-20261113-18h-6"
SIXTH={
 "id": SIXTH_ID,
 "date": DATE, "editionSlot":"18:00", "priority":6,
 "category":"Farándula",
 "title":"J Balvin homenajea a Daddy Yankee en los Latin Grammy",
 "summary":"J Balvin destacó la influencia de Daddy Yankee al rendirle homenaje durante los Latin Grammy 2026.",
 "executiveSummary":"J Balvin destacó la influencia de Daddy Yankee al rendirle homenaje durante los Latin Grammy 2026.",
 "verification":"editorial_verified","sourceLanguage":"es",
 "sources":[{"name":"Vanguardia","url":NEWS_URL}],
 "audioIsFullPublisherArticle":False,
 "audioFullTextEs":(
  "El cantante colombiano J Balvin protagonizó un momento emotivo durante los Latin Grammy de dos mil veintiséis. "
  "Al entregar un reconocimiento a Daddy Yankee, destacó la huella que ha dejado el artista puertorriqueño en la música urbana y en la proyección internacional de la cultura latina. "
  "En su intervención, Balvin recordó que el crecimiento de este movimiento musical no solo benefició a los intérpretes: también abrió espacios para compositores, productores, bailarines y otros profesionales. "
  "El homenaje pone en primer plano la influencia de Daddy Yankee en distintas generaciones de artistas y explica por qué el momento ha llamado la atención de la prensa de entretenimiento. "
  "La información fue publicada este viernes trece de noviembre por el diario Vanguardia. "
  "La fotografía que acompaña esta noticia es de archivo y no corresponde necesariamente a la ceremonia de este año."
 ),
 "imageType":"licensed_press_photo","imageRightsVerified":True
}
VOICE=[
 "Bogotá celebra la Noche de Museos con más de ochenta espacios culturales. Consulta la programación de cada sede. Fuente: Alcaldía de Bogotá.",
 "Casi seis mil estudiantes deportistas llegan a Bogotá para la final nacional de los Juegos Intercolegiados. Fuente: IDRD y Alcaldía de Bogotá.",
 "En Dublín, líderes europeos debaten inversión, competitividad y seguridad de la inteligencia artificial. Fuente: Reuters.",
 "Maloka abre actividades gratuitas para la Noche de Museos, entre las cinco y las ocho de la noche, con cupos sujetos a disponibilidad. Fuente: Maloka.",
 "Y el dato sorprendente: el Disco de Oro de las sondas Voyager lleva sonidos e imágenes de la Tierra. Maloka prepara una charla para el veintiuno de noviembre. Fuente: Maloka y NASA.",
 "Y en farándula: J Balvin emocionó con su homenaje a Daddy Yankee en los Latin Grammy. El colombiano resaltó cómo la música urbana abrió oportunidades para toda una industria. Fuente: Vanguardia."
]
def main():
 db_path=ROOT/"noticias.json"
 data=json.loads(db_path.read_text(encoding="utf-8"))
 items=sorted([x for x in data["news"] if x.get("date")==DATE and x.get("editionSlot")=="18:00" and x.get("verification")=="editorial_verified"],key=lambda x:x.get("priority",999))
 if [x["id"] for x in items]!=[f"orbiuno-20261113-18h-{i}" for i in range(1,6)]:
  raise RuntimeError("La edición base cambió; no modificar ni publicar otra versión")
 provenance=json.loads((OUT/"provenance.json").read_text(encoding="utf-8"))
 if len(provenance.get("credits",[]))!=5:raise RuntimeError("Faltan créditos anteriores")
 original_choose=p.choose_photo
 photo,credit=original_choose("J Balvin singer Colombian")
 if "balvin" not in credit["file"].lower():raise RuntimeError("La imagen de archivo no identifica con certeza a J Balvin")
 license_name=credit["license"]
 if not any(t in license_name.lower() for t in ("cc by","cc0","public domain")):raise RuntimeError("Licencia de foto no comprobada")
 photo.save(OUT/"foto-6.jpg",quality=90)
 SIXTH.update({"imageUrl":"./media/2026-11-13/foto-6.jpg",
  "imageAlt":"J Balvin, fotografía de archivo; no corresponde a la ceremonia de 2026",
  "imageCaption":"J Balvin, fotografía de archivo",
  "imageSourceUrl":credit["commons"],"imageCredit":credit["artist"],"imageLicense":license_name})
 stories=[]
 for i,item in enumerate(items,1):
  stories.append({"title":item["title"],"source":item["sources"][0]["name"],
   "source_url":item["sources"][0]["url"],"photo_query":f"archival-{i}"})
 stories.append({"title":SIXTH["title"],"source":"Vanguardia","source_url":NEWS_URL,"photo_query":"archive-j-balvin"})
 def photo_for(query):
  if query=="archive-j-balvin":return photo,credit
  index=int(query.split("-")[-1])
  im=Image.open(OUT/f"foto-{index}.jpg").convert("RGB")
  author,license_name,description=provenance["credits"][index-1]
  return im,{"file":description,"commons":items[index-1]["imageSourceUrl"],
     "artist":author,"license":license_name}
 p.choose_photo=photo_for
 audios=p.dora(VOICE,"orbiuno-six")
 p.render("ORBIUNO",stories,audios,"https://colombia-al-dia.pages.dev/")
 src=OUT/"orbiuno-2026-11-12-noche.mp4"
 final=OUT/"ORBIUNO_2026-11-13_18H_6_NOTICIAS.mp4"
 src.rename(final)
 meta=json.loads((OUT/"orbiuno-credits.json").read_text(encoding="utf-8"))
 meta.update({"date":DATE,"editionSlot":"18:00","status":"READY_FOR_INSTAGRAM_PREFLIGHT",
  "news_count":6,"story_ids":[x["id"] for x in items]+[SIXTH_ID],
  "output":str(final.relative_to(ROOT)), "sha256":hashlib.sha256(final.read_bytes()).hexdigest(),
  "source_urls":[x["sources"][0]["url"] for x in items]+[NEWS_URL]})
 (OUT/"orbiuno-credits.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 data["news"].append(SIXTH)
 db_path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("OK 6 news",final,final.stat().st_size,meta["duration"],flush=True)
if __name__=="__main__":main()
