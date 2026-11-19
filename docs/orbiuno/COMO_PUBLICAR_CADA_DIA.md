# ORBIUNO — Procedimiento diario seguro desde el 19/11/2026

## Orden fácil del propietario

En ChatGPT, dentro del proyecto ORBIUNO/Colombia al Día, escribir:

**Publica ORBIUNO de hoy. Usa Drive y GitHub, verifica seis noticias del día, produce web y Reel, publica Instagram @resumen.noticias, Historia y página Facebook ORBIUNO Noticias. Comprueba los tres IDs y evita duplicados.**

También sirve: «Publica ORBIUNO de hoy, edición de las 8 a. m.» o «Publica ORBIUNO de hoy, edición de las 6 p. m.».

ChatGPT coordina. Claude puede producir código; no debe publicar. No compartir tokens o claves en chat ni Drive.

## Procedimiento técnico vigente

1. Consultar la bitácora original y el último manifiesto verificable. Bitácora central: https://docs.google.com/document/d/1DJITJOsxlWLnZSZCjsz1aXN48mTFRpuZjzBNSXgIkrw/edit
2. Comprobar publicaciones reales recientes de @resumen.noticias por ID, fecha, hora y marcador ORBIUNO-AAAA-MM-DD-HHMM antes de crear nada. No repetir emisiones publicadas ni reintentar resultados ambiguos.
3. Elegir exactamente seis noticias contrastadas del día, preferiblemente dos Colombia y cuatro mundo. Fuentes HTTPS a los artículos originales, no portada de periódicos. Tres párrafos propios por noticia, con firma Redacción ORBIUNO y estado editorial_verified únicamente después de revisión. Evitar noticias repetidas sin actualización sustantiva.
4. Portada con SEIS titulares y fecha/hora grandes. Una lámina por noticia con una FOTO REAL GRANDE de Wikimedia Commons cuyo archivo `photoCommonsTitle` sea exacto, `photoMatchReviewed=true` confirmado editorialmente (no inventar), `photoCaption` fiel, crédito de autor, licencia abierta y URL de ficha original comprobadas por Wikimedia API; icono/logotipo real legible del medio citado y nombre. Sin fotos suficientes o iconos legibles **NO SE PUBLICA**, nunca sustituir por tarjetas. Voz femenina colombiana `es-CO-SalomeNeural` a 1,25× mediante Azure Speech y respaldo edge-tts **de la misma voz**; prohibido ef_dora/Kokoro en el flujo diario. MP4 1080×1920 H.264/AAC, **duración flexible**, puede superar 60 s. En pantalla mostrar el CTA «Escucha las noticias completas en colombia-al-dia.pages.dev». Sin imágenes generadas por IA ni simulación de hechos.

5. Crear una sola vez la edición JSON en `editions/daily/AAAA-MM-DD-HHMM.json`, con editionDate, editionSlot, editionKey y seis news verificados. **Cada news debe incluir photoCommonsTitle, photoMatchReviewed=true y photoCaption**, respaldados por revisión real de la foto. Si falta, detener antes del push. Tomar como base el esquema vigente; no crear un workflow nuevo cada día.
6. El push a main inicia `.github/workflows/orbiuno-edicion-diaria.yml`. Tras validar la edición, `scripts/orbiuno_media_assets.py` consulta ficha de licencia real y descarga las seis fotos e iconos; `scripts/generate_web_voice_colombia.py` crea audios completos con Salomé; `scripts/render_orbiuno_aprobado.py` genera portada y seis láminas. `scripts/orbiuno_qa_aprobado.py` valida fuentes, créditos, imagen, pistas, duración positiva, MP4 y SHA. Un fallo bloquea sin publicar ni alterar noticias anteriores.
7. Verificar `success` del workflow, `orbiuno_HHMM_6_noticias_manifest.json`, seis fotos/licencias/logos, voz `es-CO-SalomeNeural` 1,25×, MP4 H264/AAC con decodificación completa y `PREFLIGHT_PASS` del sitio público, con seis artículos, fotos, fuentes, orden y MP3 completos idénticos. La voz configurada no equivale a auditar auditivamente el acento. Un job verde NO es una publicación en Meta.
8. La automatización existente de ChatGPT a las 08:00 y 18:00 revisa el workflow y, solo si ha pasado TODOS los controles, prepara caption con seis enlaces originales, créditos de fotografía y marcador ORBIUNO-AAAA-MM-DD-HHMM. Vuelve a comprobar Instagram para evitar duplicados y publica UNA sola vez vía Windsor.ai, instagram account 17841438062554418 create_video_post (share_to_feed=true). Leer media_id/permalink de Instagram después. GitHub Actions solo produce/verifica; **no activar un segundo publicador Meta paralelo**.
9. Publicar Historia de Instagram una sola vez únicamente si el video cumple límites y formato que la plataforma admita (la duración del Reel no se recorta para forzar una Story). Publicar en Facebook SOLO la página ORBIUNO Noticias (facebook_organic account 1516359454884058), con enlace al Reel; identificarse como post enlazado, nunca como Reel nativo.
10. Actualizar el mismo manifiesto con estado e IDs y anexar la evidencia a la misma bitácora Drive. Nunca marcar published=true antes de la respuesta real de Meta.

## Bloqueos

No publicar si falta CUALQUIERA de las seis fotografías reales, su correspondencia y licencia externamente comprobada, seis logos/iconos legibles, voz Salomé 1,25× en el Reel y en seis MP3 de la web, titulares/fecha/hora legibles, enlaces directos, revisión editorial, sincronización web–Instagram o acceso autenticado a Meta. Nunca degradar a tarjetas tipográficas ni a otra voz. La duración superior a un minuto NO es un error. No reciclar videos anteriores ni afirmar auditoría de acento únicamente por metadatos.

## Referencia de éxito verificado — 16 noviembre 2026

- Reel real: https://www.instagram.com/reel/Df1BQaBk0Bc/ — ID 17901197808394267.
- Historia IG: ID 18659166343029231.
- Facebook página ORBIUNO Noticias 1516359454884058, post 1516359454884058_122111167299535309 (enlace, no Reel nativo).
- Manifiesto: media/2026-11-16/orbiuno_6_noticias_manifest.json.
- MP4: 55,691 segundos, 1080×1920, SHA256 f385cfab881b81e0ae713bc053371b476e1d6e107a94b22b5b1fa46eb0f8cbef.
- Workflow comprobado: https://github.com/willsonballesteros-ui/colombia-al-dia/actions/runs/44013169932

## Límite real de automatización y prueba de activación

El workflow en GitHub produce y comprueba contenido, pero NO publica por sí solo en Meta. La automatización **existente** de ChatGPT de las 08:00 y 18:00 es el único orquestador del envío a Windsor.ai, después de comprobar GitHub y la web. No crear cron Meta duplicado ni publicar a la vez por GitHub y Windsor.ai.

El primer lanzamiento de esta corrección exige **una edición nueva** con seis fotos de licencia comprobable, ejecución satisfactoria del workflow, web accesible y publicación real verificada. Hasta observar dicho ciclo, el estado es «pipeline protegido; automatización extremo a extremo pendiente de prueba real», no «automatización demostrada». No habilitar una edición anterior con faltantes de imágenes.
