from pathlib import Path
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import json

root = Path(__file__).resolve().parent
repo = Path(os.environ.get("ORBIUNO_REPO_ROOT", root.parent / "repo")).resolve()
day = "2026-11-07"
slot = "20:00"
media_path = "media/2026-11-07-2000"
media = repo / media_path
media.mkdir(parents=True, exist_ok=True)
lr = "La República"
rows = [
    ("metro", "Colombia", "Tres grupos pasan a la licitación de la Línea 2 del Metro de Bogotá",
     "La precalificación deja tres grupos en carrera para un proyecto subterráneo de 15,5 kilómetros y 11 estaciones.",
     [(lr, "https://www.larepublica.co/economia/las-tres-companias-de-la-linea-2-del-metro-de-bogota-pasaran-a-licitacion-4519879"),
      ("Alcaldía de Bogotá", "https://bogota.gov.co/mi-ciudad/movilidad/2026-11/tres-grupos-participaran-en-licitacion-de-linea-2-del-metro-de-bogota")],
     "Metro de Bogotá: tres grupos a licitación",
     "Según La República, tres grupos pasan a la licitación de la segunda línea del Metro de Bogotá.",
     "metro.webp", "ShijiKamio", "CC0 1.0", "Viaducto_L%C3%ADnea_1_en_Portal_Am%C3%A9ricas.jpg", "Archivo · Viaducto de la Línea 1",
     """La Empresa Metro de Bogotá se dispone a solicitar ofertas para su segunda línea después de que tres grupos empresariales superaran la etapa de precalificación. La Alcaldía anunció el resultado de la evaluación y explicó que las agrupaciones habilitadas podrán presentar propuestas técnicas y económicas. La República reportó el anuncio y detalló la composición de los grupos.

La futura línea está prevista como un corredor subterráneo de 15,5 kilómetros con once estaciones. Su trazado pasará por Chapinero, Barrios Unidos, Engativá y Suba. El proceso reúne en un mismo contrato el diseño y la construcción, además de la financiación, la operación y el mantenimiento de la infraestructura.

La lista de precalificados define quiénes pueden competir en la fase siguiente. La selección del contratista dependerá de las ofertas que se presenten y de su evaluación. La Alcaldía ubica la adjudicación en el primer semestre de 2027, como fecha prevista en el cronograma del proceso. En esta fase, los grupos deberán convertir su interés en ofertas formales."""),
    ("emiratos", "Economía", "Acuerdo con Emiratos prevé acceso sin aranceles para el 85 % de los productos colombianos",
     "El acuerdo superó su primer debate en el Senado y las preferencias dependerán de su entrada en vigor.",
     [(lr, "https://www.larepublica.co/economia/colombia-tendra-acceso-sin-aranceles-para-85-de-sus-productos-en-emiratos-arabes-4519866")],
     "Acuerdo comercial con Emiratos",
     "La República informa que el acuerdo con Emiratos prevé arancel cero para el ochenta y cinco por ciento de los productos colombianos.",
     "cafe.jpg", "Shaun McRae", "CC BY 2.5", "Cafe_Quimbaya_2005-08-27.jpg", "Archivo · Cultivo de café en Quimbaya",
     """El acuerdo económico entre Colombia y Emiratos Árabes Unidos avanzó en el Congreso tras superar su primer debate en la Comisión Segunda del Senado. La República informó que, cuando el tratado entre en vigor, el 85 % de los productos colombianos tendrá acceso al mercado emiratí sin aranceles. El texto también contempla una reducción gradual de aranceles para otro 13 % durante cinco años.

Entre los productos con acceso preferente figuran café, frutas, flores, cacao y manufacturas como calzado, muebles y prendas de vestir. El acceso dependerá del cumplimiento de las reglas de origen y, según el bien, de los requisitos técnicos y sanitarios. Entre enero y agosto de 2026, las exportaciones colombianas no mineroenergéticas a Emiratos sumaron 35,1 millones de dólares, según el mismo reporte.

El tratado fue firmado en 2024 y aún debe completar el trámite en el Congreso y la revisión de la Corte Constitucional. Hasta que se cumplan los procedimientos internos y el acuerdo entre en vigor, el acceso preferente sigue siendo una condición prevista en el texto del tratado."""),
    ("municipios", "Economía", "706 municipios siguen en riesgo o deterioro fiscal, según el DNP",
     "El índice fiscal municipal de 2025 mejoró frente a 2024. El 64 % de los municipios quedó por debajo de 60 puntos.",
     [("DNP", "https://dnp.gov.co/Prensa_/Noticias/Paginas/departamento-nacional-de-planeacion-revela-resultados-del-indice-de-desempeno-fiscal-idf-de-municipios-2025.aspx")],
     "706 municipios en riesgo o deterioro fiscal",
     "El D N P reporta setecientos seis municipios en riesgo o deterioro fiscal.",
     "girardota.jpg", "XalD", "CC BY-SA 4.0", "Paisaje_de_Girardota.jpg", "Archivo · Girardota, líder del índice",
     """El Departamento Nacional de Planeación divulgó los resultados de la vigencia 2025 del Índice de Desempeño Fiscal municipal. El promedio del país llegó a 57,25 puntos de 100, una mejora de 1,40 puntos frente a 2024. El DNP atribuyó el avance principalmente al componente que mide los resultados fiscales de las entidades territoriales.

El informe registra 706 municipios con menos de 60 puntos, equivalentes al 64 % del total. Ese umbral reúne los rangos de riesgo y deterioro. La cifra se redujo en 74 municipios frente a la medición anterior. En el otro extremo, siete alcanzaron la categoría sostenible, definida a partir de los 80 puntos, frente a uno en 2024.

Girardota, en Antioquia, encabezó el ranking con 83,92 puntos. El índice combina ocho indicadores sobre resultados fiscales y gestión financiera, y permite comparar la evolución de los municipios de un año a otro. El DNP habilitó un visor de consulta pública para revisar los resultados por territorio y vigencia. Allí se pueden contrastar los puntajes con los de años anteriores."""),
    ("tiktok", "Tecnología", "Bruselas cuestiona el algoritmo de TikTok en una investigación preliminar",
     "La Comisión Europea considera que el sistema «Para ti» puede encadenar recomendaciones de contenido perjudicial.",
     [("El Espectador · AFP", "https://www.elespectador.com/economia/empresas/la-union-europea-exige-a-tiktok-cambiar-su-algoritmo-por-riesgos-para-la-salud-mental/"),
      ("Comisión Europea", "https://digital-strategy.ec.europa.eu/es/news/commission-preliminarily-finds-tiktoks-you-feed-breach-digital-services-act-harmful-rabbit-holes")],
     "Bruselas cuestiona el algoritmo de TikTok",
     "El Espectador reporta objeciones preliminares de Bruselas al algoritmo de TikTok.",
     "bruselas.jpg", "almathias", "CC0 1.0", "Berlaymont_building_in_Brussels.jpg", "Archivo · Sede de la Comisión Europea",
     """La Comisión Europea comunicó una conclusión preliminar sobre el sistema de recomendaciones de TikTok. Según el organismo, el funcionamiento de la sección «Para ti» podría incumplir obligaciones del Reglamento de Servicios Digitales relacionadas con la evaluación y la mitigación de riesgos. El Espectador publicó el reporte de la agencia AFP sobre el pronunciamiento.

La investigación examina cómo un interés inicial puede llevar a que el usuario reciba repetidamente videos sobre un mismo asunto. La Comisión señaló como ejemplos contenidos sobre soledad, tristeza o autoestima. Su preocupación se concentra en la exposición repetida y en sus posibles efectos sobre personas vulnerables y menores de edad.

Bruselas también cuestionó la eficacia de las medidas que la plataforma ya introdujo para controlar esas secuencias. El pronunciamiento describe la posición preliminar de la Comisión dentro del procedimiento. La determinación definitiva y las medidas que eventualmente se adopten dependerán del resultado de la investigación."""),
]

def edition_news():
    items = []
    for priority, row in enumerate(rows, 1):
        key, category, title, summary, links, short, narration, photo, credit, license_, origin, caption, article = row
        urls = [url for _, url in links]
        assert len(article) >= 1000, (key, len(article))
        items.append(dict(
            id=f"orbiuno-20261107-20h-{key}", date=day, editionSlot=slot, category=category,
            level="Noticia contrastada · Edición especial", title=title, summary=summary, executiveSummary=summary,
            verification="editorial_verified", priority=priority, sourceLanguage="es",
            sources=[dict(name=name, url=url) for name, url in links],
            originalArticleTextEs=article, originalArticleByline="Redacción ORBIUNO", originalArticleReviewed=True,
            originalArticleReviewStatus="revisado", originalArticleSourceUrls=urls, originalArticleIsPublisherVerbatim=False,
            audioFullTextEs=article, audioIsFullPublisherArticle=False,
            imageUrl=f"./{media_path}/foto-{key}.jpg", imageType="licensed_press_photo", imageRightsVerified=True,
            imageCredit=credit, imageLicense=license_, imageSourceUrl=f"https://commons.wikimedia.org/wiki/File:{origin}",
            imageCaption=caption, imageAlt=caption, reelShort=short, reelNarrationEs=narration,
        ))
    return items

if __name__ == "__main__":
    path = repo / "noticias.json"
    db = json.loads(path.read_text())
    items = edition_news()
    ids = {item["id"] for item in items}
    db["editionDate"] = day
    db["editedAtBogota"] = datetime.now(ZoneInfo("America/Bogota")).strftime("%Y-%m-%d %H:%M")
    db["news"] = items + [item for item in db["news"] if item["id"] not in ids]
    path.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n")
