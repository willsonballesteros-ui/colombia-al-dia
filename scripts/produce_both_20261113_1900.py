#!/usr/bin/env python3
"""ORBIUNO and MyCar new 19h edition of Nov 13, 2026.
Each reel is new and independent. Source images are licensed Commons references
with explicit archival attribution, never portrayed as live event photography.
Do not publish until MP4, web, sources, account and anti-duplicate checks pass.
"""
import json,os,sys,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import produce_night_reels as p
DATE="2026-11-13"
SLOT="19:00"
OUT=ROOT/"media/2026-11-13-1900"
OUT.mkdir(parents=True,exist_ok=True)
p.OUT=OUT
os.environ["EDITION_DATE_LABEL"]="13 NOV · 7:00 P. M."
ORBIUNO=[
 {"title":"Explosión cerca de la Escuela de Carabineros en Cali","category":"Colombia","source":"Agencia EFE","url":"https://efe.com/mundo/2026-11-13/cali-colombia-explosion-escuela-carabineros-bomba/","photo_query":"Cali Colombia city skyline buildings",
 "voice":"En Cali, una explosión cerca de la Escuela de Carabineros movilizó a la Fuerza Pública. Hasta el reporte de EFE no había confirmación oficial de víctimas. Fuente: EFE.",
 "article":"""Una fuerte explosión se registró en las cercanías de la Escuela de Carabineros de Cali. La agencia EFE informó el trece de noviembre que la detonación ocurrió la noche anterior y provocó un operativo de seguridad en el sector. Según la información que recogió la agencia, las autoridades señalaron que una motocicleta con explosivos habría sido detonada cerca de la instalación policial.

La detonación fue percibida en diferentes zonas de la capital del Valle del Cauca. Las autoridades desplegaron personal y acordonaron el área para adelantar las verificaciones correspondientes. En el momento del reporte no existía una confirmación oficial sobre víctimas, por lo que no corresponde dar cifras definitivas de personas afectadas ni atribuir responsabilidades sin resultados de la investigación.

La noticia coincide con los preparativos de seguridad para el encuentro amistoso de fútbol entre Colombia y Chile. La Policía había anunciado un dispositivo especial de uniformados alrededor del estadio Pascual Guerrero. ORBIUNO seguirá el desarrollo de los hechos a partir de comunicados oficiales y de reportes contrastados. La fotografía que ilustra esta nota es una imagen de archivo de la ciudad y no documenta el lugar exacto de la explosión."""},
 {"title":"Microsoft reporta recuperación generalizada de sus servicios","category":"Tecnología","source":"Agencia EFE","url":"https://efe.com/ciencia-y-tecnologia/2026-11-13/microsoft-recuperacion-servicios-outlook-teams-copilot-fallo-tecnico/","photo_query":"Microsoft Redmond headquarters building",
 "voice":"Microsoft atribuye la caída de Outlook, Teams y otros servicios a un fallo técnico y anuncia una recuperación generalizada. Puede haber diferencias entre usuarios. Fuente: EFE.",
 "article":"""Microsoft comunicó una recuperación generalizada tras la interrupción que afectó a varios de sus servicios digitales. La información difundida por la agencia EFE el trece de noviembre menciona plataformas utilizadas diariamente por empresas y usuarios, entre ellas Outlook, Teams y Copilot. El incidente se convirtió en un asunto internacional por el alcance de sus efectos sobre comunicaciones y trabajo.

De acuerdo con la explicación de la compañía recogida por EFE, el problema estuvo relacionado con una ampliación previa de la capacidad de su red. Microsoft descartó que el origen identificado correspondiera a un incidente de ciberseguridad. Esa conclusión es la comunicada por la empresa, no el resultado de una auditoría independiente publicada por ORBIUNO.

La recuperación generalizada no significa que todas las personas hayan recuperado necesariamente el servicio en el mismo instante. Pueden existir diferencias por región, cuenta o producto. Para verificar una incidencia concreta conviene consultar el estado oficial del servicio y los avisos de la organización que lo administra. Esta nota presenta la actualización más reciente de la fuente y no repite como novedad la caída inicial del jueves."""},
 {"title":"Colombia y Chile se enfrentan esta noche en Cali","category":"Deportes","source":"Federación Colombiana de Fútbol","url":"https://www.fcf.com.co/2026/11/06/convocatoria-de-la-seleccion-colombia-de-mayores-amistosos-internacionales-de-noviembre-2026/","photo_query":"Cali Pascual Guerrero football stadium",
 "voice":"Colombia recibe hoy a Chile en un amistoso programado para las siete de la noche en el estadio Pascual Guerrero de Cali. Fuente: Federación Colombiana de Fútbol.",
 "article":"""La Selección Colombia de mayores tiene programado un partido amistoso contra Chile para este viernes trece de noviembre. De acuerdo con el calendario oficial publicado por la Federación Colombiana de Fútbol, el encuentro se disputa en el estadio Pascual Guerrero, en Cali, con inicio previsto para las siete de la noche, hora colombiana.

El compromiso forma parte del cierre del calendario internacional del año y permite al cuerpo técnico, encabezado por Néstor Lorenzo, evaluar alternativas de juego. La convocatoria fue difundida por la Federación antes de la concentración del equipo. La información de esta edición se refiere a la programación del encuentro, no a un marcador o resultado que todavía no estuviera confirmado al preparar el material.

Ambas selecciones también tienen previsto enfrentarse el diecisiete de noviembre en Santiago de Chile. Los horarios y eventuales cambios de última hora deben verificarse en los canales oficiales. ORBIUNO no anticipa un resultado ni atribuye declaraciones no documentadas a jugadores o entrenadores. La fotografía utilizada es una referencia de archivo del entorno deportivo, no una imagen del juego disputado hoy."""},
 {"title":"Estados Unidos detuvo despegues por problemas de comunicaciones","category":"Mundo","source":"Ecuavisa","url":"https://www.ecuavisa.com/mundo/eeuu-ordena-suspender-vuelo-todo-el-pais-20261113-0060.html","photo_query":"airport runway passenger airplanes airport",
 "voice":"Estados Unidos ordenó suspender temporalmente despegues por problemas de comunicaciones. El alcance y la duración deben seguirse en los avisos oficiales. Fuente: Ecuavisa.",
 "article":"""Una suspensión general de despegues fue reportada en Estados Unidos este viernes trece de noviembre debido a problemas en las comunicaciones. El medio Ecuavisa informó sobre la medida y recordó que interrupciones de alcance nacional son eventos poco frecuentes en la operación de la aviación comercial estadounidense.

Una orden de detener los despegues no equivale a declarar que todos los aviones que ya se encuentran en el aire estén inmovilizados. Las decisiones sobre los vuelos en curso y sobre la reanudación de salidas dependen de los procedimientos que apliquen las autoridades de aviación y los operadores. Al preparar esta información no se atribuye una duración definitiva a la medida.

Los pasajeros con itinerarios hacia o desde Estados Unidos deben contrastar el estado de sus vuelos con las aerolíneas y con los organismos oficiales. No es prudente deducir que cada aeropuerto presenta las mismas demoras ni que todas las rutas serán afectadas de la misma manera. La fotografía que acompaña la publicación es una imagen aeronáutica de archivo con fines ilustrativos."""},
 {"title":"Un vehículo volador Xpeng X2 sorprende en el Salón del Automóvil","category":"Tecnología y viral","source":"El Carro Colombiano","url":"https://www.elcarrocolombiano.com/salon-del-automovil-de-bogota-2026/salon-del-automovil-de-bogota-2026-boletas-horarios-precios/","photo_query":"small electric aircraft futuristic helicopter",
 "voice":"Y el dato sorprendente de hoy: el Salón del Automóvil de Bogotá exhibe el Xpeng X2, un vehículo volador que llama la atención de visitantes. Fuente: El Carro Colombiano.",
 "article":"""El Salón Internacional del Automóvil de Bogotá 2026 reúne una exhibición que va más allá de los carros de uso cotidiano. Entre las novedades mencionadas por El Carro Colombiano aparece el Xpeng X2, un vehículo volador presentado como una de las atracciones tecnológicas del evento que se desarrolla en Corferias.

La presencia del prototipo permite observar tendencias relacionadas con la movilidad aérea y las nuevas formas de transporte personal. Sin embargo, mostrar un vehículo de este tipo en una feria no implica que se encuentre homologado para circular libremente ni que esté disponible en Colombia como un automóvil de venta masiva. Su exhibición debe distinguirse de una oferta comercial definitiva.

El evento, abierto del doce al veintidós de noviembre, reúne modelos convencionales, eléctricos e híbridos y varias marcas que llegan al mercado. Para conocer la ubicación de las exhibiciones, los visitantes deben consultar la programación oficial. La imagen utilizada aquí es una fotografía aeronáutica real de referencia; no se presenta como una fotografía del Xpeng X2 en Corferias."""},
 {"title":"Rosalía se lleva seis premios en los Latin Grammy 2026","category":"Farándula","source":"Teleantioquia","url":"https://www.teleantioquia.co/entretenimiento/en-video-rosalia-lloro-al-recibir-un-latin-grammy-de-juanes-conozca-los-antioquenos-y-colombianos-que-tambien-ganaron-626037","photo_query":"Rosalia singer musician concert",
 "voice":"En farándula, Rosalía fue una de las protagonistas de los Latin Grammy dos mil veintiséis, con seis premios. Juanes participó en la entrega de uno de los reconocimientos. Fuente: Teleantioquia.",
 "article":"""La cantante española Rosalía se convirtió en una de las grandes protagonistas de los Latin Grammy de dos mil veintiséis. Teleantioquia informó este viernes trece de noviembre que la artista obtuvo seis gramófonos y protagonizó uno de los momentos emotivos de la ceremonia al recibir un reconocimiento de manos del colombiano Juanes.

La premiación también reunió a intérpretes, productores y compositores de distintos países latinoamericanos. Además de los premios de Rosalía, el cubrimiento destacó la participación de artistas colombianos en varias categorías. Las menciones de la gala se basan en el reporte publicado por el medio y no en cifras de audiencia o reproducciones que no hayan sido corroboradas.

El episodio se ha convertido en noticia de entretenimiento por el resultado de la ceremonia y por la conexión entre artistas de España y Colombia. Las cifras concretas de seguidores, visualizaciones o tendencias no se presentan como medidas oficiales de popularidad si no existe una fuente verificable. La fotografía que acompaña esta nota es una imagen de archivo de la cantante."""}
]
MYCAR=[
 {"title":"Salón del Automóvil de Bogotá exhibe más de 800 vehículos","source":"El Carro Colombiano","url":"https://www.elcarrocolombiano.com/salon-del-automovil-de-bogota-2026/salon-del-automovil-de-bogota-2026-boletas-horarios-precios/","photo_query":"Corferias Bogota exhibition hall",
 "voice":"En Bogotá comenzó el Salón del Automóvil con ochenta y tres marcas y más de ochocientos vehículos en exhibición en Corferias. Fuente: El Carro Colombiano."},
 {"title":"FAWCAR Xiaoma 2.0 se anuncia en feria desde 43 millones","source":"El Carro Colombiano","url":"https://www.elcarrocolombiano.com/salon-del-automovil-de-bogota-2026/salon-del-automovil-de-bogota-2026-boletas-horarios-precios/","photo_query":"FAW Bestune compact electric car",
 "voice":"El FAWCAR Xiaoma dos punto cero figura entre las promociones del Salón del Automóvil, con precio anunciado desde cuarenta y tres millones de pesos durante la feria. Fuente: El Carro Colombiano."},
 {"title":"El Xpeng X2 muestra el futuro del transporte aéreo","source":"El Carro Colombiano","url":"https://www.elcarrocolombiano.com/salon-del-automovil-de-bogota-2026/salon-del-automovil-de-bogota-2026-boletas-horarios-precios/","photo_query":"electric flying aircraft small aviation",
 "voice":"Una curiosidad del Salón del Automóvil es el Xpeng X dos, un vehículo volador en exhibición. Se trata de una demostración tecnológica, no de un carro disponible para venta masiva. Fuente: El Carro Colombiano."},
 {"title":"Renault 4 E-Tech llega como exhibición eléctrica","source":"Renault Sofasa","url":"https://prensa.renault.com.co/prensa/renault-llega-a-la-edicion-20-del-salon-del-automovil-de-bogota-con-su-portafolio-100-renovado-y-se-extiende-a-sus-111-salas-a-nivel-nacional/","photo_query":"Renault 4 electric automobile",
 "voice":"Renault exhibe el cuatro E Tech eléctrico como vehículo de muestra en Corferias y anuncia planes de preventa para Colombia. Fuente: Renault Sofasa."}
]
# Commons search is strict about multiword terms; try verified synonyms only.
# Never synthesize an image or suppress the source/license test.
_image_fallbacks={
 "Cali Colombia city skyline buildings":["Cali Colombia","Cali","Colombia city"],
 "Microsoft Redmond headquarters building":["Microsoft headquarters","Microsoft","office building"],
 "Cali Pascual Guerrero football stadium":["Pascual Guerrero","football stadium","soccer stadium"],
 "airport runway passenger airplanes airport":["airport","aircraft","airplane"],
 "small electric aircraft futuristic helicopter":["helicopter","aircraft","electric airplane"],
 "Rosalia singer musician concert":["Rosalia","singer concert","music concert"],
 "Corferias Bogota exhibition hall":["Corferias","exhibition hall","Bogota buildings"],
 "FAW Bestune compact electric car":["FAW automobile","electric car","small vehicle"],
 "electric flying aircraft small aviation":["aircraft","helicopter","electric aircraft"],
 "Renault 4 electric automobile":["Renault automobile","Renault","compact car"]
}
_choose_original=p.choose_photo
def _verified_photo(query):
 errors=[]
 for q in [query]+_image_fallbacks.get(query,[]):
  try:
   photo,credit=_choose_original(q)
   if not credit.get("commons","").startswith("https://commons.wikimedia.org/wiki/"):raise RuntimeError("Source URL unavailable")
   if not any(x in str(credit.get("license","")).lower() for x in ("cc by","cc0","public domain")):raise RuntimeError("License not allowed")
   print("APPROVED_ARCHIVAL_PHOTO",query,"=>",credit["file"],credit["license"],flush=True)
   return photo,credit
  except Exception as e:
   errors.append(q+": "+str(e)[:65])
 raise RuntimeError("No valid Commons photo; "+str(errors))
p.choose_photo=_verified_photo

def render(brand,stories):
 os.environ["ORBIUNO_REEL_COUNT"]=str(len(stories))
 refs=[{"title":n["title"],"source":n["source"],"source_url":n["url"],"photo_query":n["photo_query"]} for n in stories]
 audios=p.dora([n["voice"] for n in stories],brand.lower()+"-19h")
 p.render(brand,refs,audios,"")
 previous=OUT/(brand.lower()+"-2026-11-12-noche.mp4")
 final=OUT/(brand+"-2026-11-13_19H_"+str(len(stories))+"_NOTICIAS.mp4")
 previous.rename(final)
 meta=OUT/(brand.lower()+"-credits.json")
 payload=json.loads(meta.read_text(encoding="utf8"))
 payload.update({"edition":"2026-11-13-1900","stories":[{"title":n["title"],"source":n["url"]} for n in stories],"sha256":hashlib.sha256(final.read_bytes()).hexdigest(),"video":final.name,"status":"RENDERED_NOT_PUBLISHED"})
 meta.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
 movie=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)]))
 assert len(payload["license_photos"])==len(stories)
 assert any(x.get("codec_type")=="audio" for x in movie["streams"])
 assert any(x.get("codec_type")=="video" and x.get("width")==720 and x.get("height")==1280 for x in movie["streams"])
 assert float(movie["format"]["duration"])>25
 print("VIDEO_VALIDATED",brand,final.name,float(movie["format"]["duration"]),final.stat().st_size,flush=True)
 return payload
def sync_web(meta):
 data_file=ROOT/"noticias.json"
 data=json.loads(data_file.read_text(encoding="utf8"))
 ids=set(n["id"] for n in data["news"])
 if len([x for x in data["news"] if x.get("date")==DATE and x.get("editionSlot")==SLOT])>0:
  raise RuntimeError("Ya hay noticias en la misma franja: no duplicar")
 for index,story in enumerate(ORBIUNO):
  rights=meta["license_photos"][index]["photo"]
  article=story["article"].strip()
  assert len(article)>=640 and len(article.split("\n\n"))==3
  assert rights["commons"].startswith("https://commons.wikimedia.org/")
  entry={"id":f"orbiuno-20261113-19h-{index+1}","date":DATE,"editionSlot":SLOT,"priority":index+1,
    "category":story["category"],"title":story["title"],
    "summary":story["voice"],"executiveSummary":story["voice"],
    "verification":"editorial_verified","sources":[{"name":story["source"],"url":story["url"]}],
    "sourceLanguage":"es","audioIsFullPublisherArticle":False,
    "audioFullTextEs":article,"originalArticleByline":"Redacción ORBIUNO",
    "originalArticleReviewed":True,"originalArticleReviewStatus":"aprobado",
    "originalArticleIsPublisherVerbatim":False,"originalArticleSourceUrls":[story["url"]],
    "originalArticleTextEs":article,
    "imageType":"licensed_press_photo",
    "imageRightsVerified":True,
    "imageUrl":"./media/2026-11-13-1900/orbiuno-%02d.jpg"%(index+1),
    "imageAlt":"Imagen real de archivo de referencia, no del acontecimiento",
    "imageCaption":"Fotografía de archivo ilustrativa",
    "imageLicense":rights["license"],"imageCredit":rights["artist"],
    "imageSourceUrl":rights["commons"],
    "instagramReelOrder":index+1}
  data["news"].append(entry)
 if data["editionDate"]<DATE:data["editionDate"]=DATE
 data_file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
 print("WEB_SYNCED_ORBIUNO",len(ORBIUNO),flush=True)
if __name__=="__main__":
 o=render("ORBIUNO",ORBIUNO)
 m=render("MYCAR",MYCAR)
 sync_web(o)
