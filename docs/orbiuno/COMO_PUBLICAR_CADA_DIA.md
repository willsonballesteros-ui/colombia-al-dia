# ORBIUNO — Procedimiento diario desde el 17/11/2026

## Orden fácil del propietario

En ChatGPT, dentro del proyecto ORBIUNO/Colombia al Día, escribir:

**Publica ORBIUNO de hoy. Usa Drive y GitHub, verifica seis noticias del día, produce web y Reel, publica Instagram @resumen.noticias, Historia y página Facebook ORBIUNO Noticias. Comprueba los tres IDs y evita duplicados.**

También sirve: «Publica ORBIUNO de hoy, edición de las 8 a. m.» o «Publica ORBIUNO de hoy, edición de las 6 p. m.».

ChatGPT coordina. Claude puede producir código; no debe publicar. No compartir tokens o claves en chat ni Drive.

## Procedimiento técnico vigente

1. Consultar la bitácora original y el último manifiesto verificable. Bitácora central: https://docs.google.com/document/d/1DJITJOsxlWLnZSZCjsz1aXN48mTFRpuZjzBNSXgIkrw/edit
2. Comprobar publicaciones reales recientes de @resumen.noticias por ID, fecha, hora y marcador ORBIUNO-AAAA-MM-DD-HHMM antes de crear nada. No repetir emisiones publicadas ni reintentar resultados ambiguos.
3. Elegir exactamente seis noticias contrastadas del día, preferiblemente dos Colombia y cuatro mundo. Fuentes HTTPS a los artículos originales, no portada de periódicos. Tres párrafos propios por noticia, con firma Redacción ORBIUNO y estado editorial_verified únicamente después de revisión. Evitar noticias repetidas sin actualización sustantiva.
4. Portada con seis titulares, fecha y hora grandes. Una lámina por noticia, fuente destacada, cierre hacia colombia-al-dia.pages.dev. Voz Kokoro ef_dora sintética a 1,25x, formato MP4 1080×1920 H.264/AAC 50–60 segundos. Para fotografías reales: procedencia, permiso y crédito; no fotografías IA de hechos noticiosos. La mejora de logos gráficos originales grandes y de fotografía periodística verificable sigue pendiente cuando falten assets autorizados. Si no hay una foto autorizada, usar tarjeta tipográfica con fuente real, sin atribuir imagen ficticia al acontecimiento.
5. Crear una sola vez la edición JSON en la ruta editions/daily/AAAA-MM-DD-HHMM.json, con editionDate, editionSlot, editionKey y seis news. Tomar como referencia de esquema editions/2026-11-16-1900.json. No crear un workflow nuevo cada día.
6. El push de ese JSON a main inicia .github/workflows/orbiuno-edicion-diaria.yml. scripts/orbiuno_import_daily.py comprueba fecha Bogotá, seis IDs únicos, orden, textos originales y fuentes directas, preservando el histórico. Se producen seis audios completos web, HTML y un MP4 con SHA256.
7. Verificar el resultado success del workflow, el manifiesto media/AAAA-MM-DD/orbiuno_HHMM_6_noticias_manifest.json y PREFLIGHT_PASS de scripts/orbiuno_daily_preflight.py. Confirmar en web pública exactamente los seis IDs, titulares, fuentes, orden y seis MP3. No confundir un job en verde con publicación en Meta.
8. Preparar caption con seis enlaces originales y marcador ORBIUNO-AAAA-MM-DD-HHMM. Consultar de nuevo Instagram para deduplicar. Publicar UNA vez vía Windsor.ai: connector instagram, account 17841438062554418, action create_video_post, video URL pública, share_to_feed true. Confirmar media_id y media_permalink en lectura posterior.
9. Publicar Instagram Story una vez con create_story cuando el MP4 sea aceptado, y publicación Facebook SOLO en ORBIUNO Noticias (facebook_organic account 1516359454884058), con enlace al Reel. Identificarla como post con enlace, no como Reel nativo.
10. Actualizar el mismo manifiesto con estado e IDs y anexar la evidencia a la misma bitácora Drive. Nunca marcar published=true antes de la respuesta real de Meta.

## Bloqueos

No publicar si faltan noticias contrastadas, origen original, seis audios, concordancia web–Instagram, derechos de una imagen usada, MP4 reproducible o acceso a Meta. No reciclar el MP4 de ayer como si fuese de hoy. No afirmar que la voz ef_dora es una grabación de una locutora humana ni que se comprobó un acento regional solo por metadatos.

## Referencia de éxito verificado — 16 noviembre 2026

- Reel real: https://www.instagram.com/reel/Df1BQaBk0Bc/ — ID 17901197808394267.
- Historia IG: ID 18659166343029231.
- Facebook página ORBIUNO Noticias 1516359454884058, post 1516359454884058_122111167299535309 (enlace, no Reel nativo).
- Manifiesto: media/2026-11-16/orbiuno_6_noticias_manifest.json.
- MP4: 55,691 segundos, 1080×1920, SHA256 f385cfab881b81e0ae713bc053371b476e1d6e107a94b22b5b1fa46eb0f8cbef.
- Workflow comprobado: https://github.com/willsonballesteros-ui/colombia-al-dia/actions/runs/44013169932

## Límite real de automatización

El nuevo workflow prepara y verifica el contenido; no publica automáticamente en Meta por sí mismo. La publicación se ejecuta mediante el conector Windsor.ai desde ChatGPT una vez comprobada la edición. La automatización ya existente de avisos revisa las franjas de las 08:00 y 18:00 hora Bogotá, pero su ejecución no demuestra que haya contenido publicado.
