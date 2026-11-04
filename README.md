# Colombia al Día — noticias, web e Instagram

**Sitio público:** https://colombia-al-dia.pages.dev/  
**Instagram operativo:** https://www.instagram.com/resumen.noticias/  
**Repositorio:** `willsonballesteros-ui/colombia-al-dia`, rama `main`.

## Directriz editorial vigente — 4 de noviembre de 2026

Somos un medio informativo serio, ágil y sin amarillismo.

- **Prohibidos:** avatares, presentadoras virtuales, dibujos inventados, fotografías sintéticas o animación de caras.
- **Imágenes reales solamente:** fotografía oficial o de prensa autorizada, o documento oficial, con crédito, URL de procedencia, licencia y confirmación editorial de derechos. Si falta cualquiera, se utiliza **diseño tipográfico**, sin imagen.
- **10 hechos:** titular conciso, QUÉ PASÓ, POR QUÉ IMPORTA, QUÉ SIGUE y fuente verificada con URL original. Los titulares importados por RSS quedan pendientes de verificación y no pueden presentarse como hechos confirmados.
- **Portal:** portada limpia, tarjetas con dos líneas visibles de resumen, enlace a fuente, detalles desplegables y botón `▶ Escuchar resumen` basado en `window.speechSynthesis` (voz del dispositivo, sin API externa).
- **Carrusel:** 12 láminas de 1080×1350: primera portada con pregunta, diez noticias, última cierre con CTA. No dibujar botones ficticios ni códigos QR. El enlace a la web está en la biografía y los vínculos de fuentes son clicables desde las tarjetas del portal.
- **Instagram:** los stickers **Enlace**, **Encuesta** y **Cuestionario** son recursos nativos de **Historias**, no del carrusel. El archivo `sugerencias-stickers.json` guarda únicamente una guía; jamás afirma haber insertado stickers ni convierte una imagen en enlace clicable. La app de Instagram puede requerir intervención para añadirlos.
- **Publicación:** programar mediante Metricool donde esté disponible, pero declarar publicado únicamente si el proveedor devuelve estado `PUBLISHED` y enlace real. No repetir noticias antiguas como si fueran actuales.

## Infraestructura activa

| Módulo | Función |
| --- | --- |
| `noticias.json` | Archivo editorial y enlaces atribuidos; `imageUrl` únicamente con procedencia y derechos. |
| `scripts/validate_news.py` | Valida noticias, URLs HTTPS y derechos de imágenes. |
| `scripts/prepare_site.py` | Actualiza HTML inicial accesible y JSON embebido. |
| `scripts/build_carousel.py` | Genera portada + 10 láminas tipográficas/fotos documentadas + cierre e historia. |
| `scripts/sync_sources.py` | Importación RSS como material `source_only`, no verificación editorial automática. |
| `scripts/build_feed.py` | RSS propio de las noticias revisadas. |
| `.github/workflows/actualizar-noticias.yml` | Preparación GitHub Actions a las 07:30/11:30/17:30 Bogotá. |
| `.github/workflows/generar-carrusel.yml` | Render y commit de imágenes, sujeto a la existencia de 10 noticias revisadas. |

El proyecto **no** incluye ya workflows ni scripts para generar presentadoras o personajes virtuales. Se retiró de la portada el video animado anterior; los artefactos multimedia de la edición reformulada se generan sin dibujos.

## Autenticidad de imágenes

La web y el renderizador únicamente admiten medios con:
```json
{
  "imageType": "official_photo",
  "imageUrl": "https://servidor-oficial/imagen-autorizada.jpg",
  "imageSourceUrl": "https://servidor-oficial/comunicado",
  "imageCredit": "Nombre de la fuente",
  "imageLicense": "Licencia o permiso exacto",
  "imageRightsVerified": true
}
```

Otros valores aceptados para `imageType`: `licensed_press_photo`, `official_document`. No basta la atribución para autorizar una reproducción: verificar también la licencia o el permiso. El generador del carrusel requiere que la imagen autorizada ya esté incorporada localmente bajo `media/` y, si no está disponible, crea la lámina en texto. Las URLs del ejemplo son **ilustrativas del esquema, no licencias reales**.

## Validaciones

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/validate_news.py noticias.json
python scripts/prepare_site.py
python scripts/build_carousel.py
```

Los workflows comprueban las dimensiones, 12 láminas y que no vuelvan a introducirse imágenes ficticias. Si no existe una edición de 10 noticias contrastadas, debe detenerse el render en lugar de inventar historias.

## Horarios y límites

El horario de preparación `30 12,16,22 * * *` está en UTC y equivale a 07:30, 11:30 y 17:30 Bogotá. Se espera distribución a 08:00, 12:00 y 18:00 mediante las herramientas efectivamente conectadas; un cron de GitHub no garantiza puntualidad de publicación. Tampoco confirma, por sí solo, el envío a Instagram ni la edición periodística de cada noticia.

No se han activado servicios externos de pago por esta política. El usuario debe aprobar cualquier contratación nueva. Los enlaces en descripciones de Instagram no sustituyen el enlace clicable de la biografía o el sticker nativo de las Historias.

Guía editorial detallada: [EDITORIAL.md](EDITORIAL.md).
