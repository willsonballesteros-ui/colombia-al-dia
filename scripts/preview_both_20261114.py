#!/usr/bin/env python3
"""Preview-only editions, 14 Nov 2026. Never publish to Instagram/Facebook.
Real Commons pictures only, licensed and attributed. Original Kokoro Dora 1.25x.
Do not mutate site or previous editions.
"""
import json,sys,os,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import produce_night_reels as engine
OUT=ROOT/"media/2026-11-14-borradores"
OUT.mkdir(exist_ok=True,parents=True)
engine.OUT=OUT
os.environ["PREVIEW_ONLY"]="1"
os.environ["EDITION_DATE_LABEL"]="14 NOV 2026 · BORRADOR"
ORBIUNO=[
 ("Bogotá recibe festival de cultura mexicana","Bogotá","https://bogota.gov.co/que-hacer/cultura/2026-11/planes-gratis-festival-mexico-en-el-corazon-de-bogota-noviembre14-y-15","Bogota Plaza Bolivar Colombia","Hoy y mañana, la Plaza de Bolívar recibe el festival México en el corazón de Bogotá. Más de ochenta emprendimientos presentan gastronomía, artesanías y música. La entrada es gratuita. Fuente: Alcaldía de Bogotá."),
 ("Bogotá celebra a escritoras y lectoras","Cultura Bogotá","https://bogota.gov.co/que-hacer/cultura/2026-11/planes-y-eventos-imperdibles-en-bogota-del-13-al-19-de-noviembre-2026","Bogota Biblioteca Virgilio Barco","Bogotá propone una ruta literaria por sus distritos creativos para reconocer las voces de escritoras colombianas y latinoamericanas. Consulta los horarios oficiales. Fuente: Alcaldía de Bogotá."),
 ("Estados Unidos normaliza vuelos tras fallas","Mundo","https://www.reuters.com/world/us/faa-issues-national-ground-stop-due-extraordinary-circumstance-reasons-safety-2026-11-13/","Airport passenger airplane runway","Estados Unidos reanuda gradualmente operaciones aéreas después de una falla de comunicaciones. Los pasajeros deben verificar directamente con sus aerolíneas. Fuente: información de aviación divulgada el catorce de noviembre."),
 ("Denza, marca de lujo de BYD, debuta en India","Economía","https://www.reuters.com/markets/emerging/byd-launches-luxury-brand-denza-india-taking-mercedes-toyota-2026-11-13/","Denza D9 car","La marca de lujo Denza, propiedad de BYD, debuta en India con la miniván eléctrica D nueve y el deportivo Z nueve G T. Compite en el segmento prémium. Fuente: Reuters."),
 ("¡WOW! Starship despliega satélites en órbita","Tecnología","https://www.reuters.com/science/spacex-attempt-first-starship-spacecraft-recovery-land-15th-flight-2026-11-13/","SpaceX Starship rocket","La misión número quince de Starship alcanzó órbita y desplegó satélites Starlink. El propulsor no completó la recuperación prevista. Fuente: Reuters."),
 ("Karol G obtiene dos Latin Grammy","Farándula","https://abc7.com/amp/post/lista-completa-de-ganadores-del-latin-grammy-2026/20037510/","Karol G singer","Karol G ganó el premio a mejor álbum de música urbana por Tropicoqueta y, junto a Feid, mejor interpretación de reguetón por Verano Rosa. Fuente: Associated Press.")
]
MYCAR=[
 ("Frontier Pro híbrida llega a Colombia","Lanzamientos","https://www.elcarrocolombiano.com/lanzamientos/nissan-frontier-pro-colombia-hibrida-precios-ficha-tecnica/","Nissan Frontier pickup","Nissan presenta la Frontier Pro híbrida enchufable en Colombia, con trescientos cincuenta caballos. Anuncia hasta novecientos sesenta y seis kilómetros de autonomía combinada bajo homologación, no una prueba de carretera. Fuente: El Carro Colombiano."),
 ("Golf GTI regresa con 261 caballos","Lanzamientos","https://www.elcarrocolombiano.com/novedades/volkswagen-golf-gti-colombia-lanzamiento-precio/","Volkswagen Golf GTI car","Volkswagen presentó el nuevo Golf G T I en Colombia, con doscientos sesenta y un caballos, después de seis años de ausencia. Fuente: El Carro Colombiano."),
 ("Próxima Honda CR-V será solo híbrida","Tecnología","https://www.elcarrocolombiano.com/autos-del-mundo/honda-cr-v-le-dice-adios-a-la-gasolina-la-proxima-generacion-sera-100-hibrida/","Honda CR-V SUV","La próxima generación de Honda C R V se venderá exclusivamente híbrida en Norteamérica. Se espera como modelo dos mil veintiocho. Esto no se ha confirmado para Colombia. Fuente: El Carro Colombiano."),
 ("Denza estrena sus eléctricos de lujo en India","Mundo","https://www.reuters.com/markets/emerging/byd-launches-luxury-brand-denza-india-taking-mercedes-toyota-2026-11-13/","Denza D9 car","Denza, marca prémium de B Y D, llegó a India con dos eléctricos: el vehículo familiar D nueve y el deportivo Z nueve G T. Fuente: Reuters.")
]
def run_brand(name,data):
    os.environ["ORBIUNO_REEL_COUNT"]=str(len(data))
    stories=[{"title":t,"source":s,"source_url":u,"photo_query":q} for t,s,u,q,v in data]
    audio=engine.dora([v for t,s,u,q,v in data],name.lower()+"-14nov")
    engine.render(name,stories,audio,"")
    previous=OUT/(name.lower()+"-2026-11-12-noche.mp4")
    final=OUT/(name.upper()+"-2026-11-14_BORRADOR_"+str(len(data))+"_NOTICIAS.mp4")
    previous.rename(final)
    meta=OUT/(name.lower()+"-credits.json")
    m=json.loads(meta.read_text())
    m.update({"date":"2026-11-14","edition":"preview-only","status":"DRAFT_NOT_PUBLISHED",
    "stories":[{"title":t,"source":u} for t,s,u,q,v in data],"video":final.name,
    "sha256":hashlib.sha256(final.read_bytes()).hexdigest()})
    meta.write_text(json.dumps(m,ensure_ascii=False,indent=2))
    streams=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(final)]))
    assert len(m["license_photos"])==len(data)
    assert any(s["codec_type"]=="audio" for s in streams["streams"])
    assert any(s["codec_type"]=="video" and s.get("width")==720 and s.get("height")==1280 for s in streams["streams"])
    print("PREVIEW_READY",name,final.name,streams["format"]["duration"],final.stat().st_size,flush=True)
if __name__=="__main__":
    name=sys.argv[1] if len(sys.argv)>1 else "all"
    if name in ("all","orbiuno"):run_brand("ORBIUNO",ORBIUNO)
    if name in ("all","mycar"):run_brand("MYCAR",MYCAR)
