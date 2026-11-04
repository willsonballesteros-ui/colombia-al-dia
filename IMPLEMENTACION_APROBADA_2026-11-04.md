# ORBIUNO — Cuatro ajustes técnicos: implementación en `main`

**Fecha:** 4 de noviembre de 2026. **Ámbito:** redacción ampliada, Reel de respaldo, deportes mediodía y atribución Instagram→audio.

## 1. Reportajes originales de 3–4 párrafos

**Qué funciona:** `scripts/generate_full_reports.py` prepara reportajes PROPIOS de ORBIUNO con la API Responses, a partir de campos de noticias YA marcadas `editorial_verified` y URL de fuentes originales. No descarga ni copia textos íntegros del medio. La salida exige 3–4 párrafos y al menos 1000 caracteres, cifras ya existentes en la ficha y atribuciones. No genera noticias RSS `source_only`.

**Seguridad editorial:** los borradores se guardan con `originalArticleReviewed=false`, `originalArticleReviewStatus=pendiente_validacion_editorial`, `originalArticleIsPublisherVerbatim=false`. El portal solo activa «▶ Escuchar completo» cuando un reportaje propio ya está realmente revisado y tiene fuentes; de lo contrario ofrece «▶ Escuchar resumen», sin sacar al usuario de la web. Nunca marcar `originalArticleReviewed=true` automáticamente solo porque un modelo produjo texto. No añadir hechos nuevos ni inventar citas.

**Activación:** GitHub Actions → «ORBIUNO - redactar borradores extendidos con IA (opt-in)» → `workflow_dispatch` → activar `autorizar_consumo_api` solo con presupuesto autorizado. Requiere secreto `OPENAI_API_KEY` y variable `ORBIUNO_LLM_MODEL` con nombre de modelo disponible. No hay llamada de pago predeterminada y no se ha confirmado que esas credenciales estén configuradas. La API puede generar cargos independientes de cualquier suscripción a ChatGPT. Tras generar, un editor debe validar cada texto antes de activar audio completo.

## 2. Presentadora: prioridad al video real, fallback animado local

`scripts/assemble_reel.py` compone once escenas mediante FFmpeg: presentación con video auténtico aprobado o fotografía con zoom suave y onda de audio, después diez láminas de noticias. Esta alternativa no mueve los labios ni finge sincronización facial. Requiere derechos documentados, imagen de persona autorizada, voz y guion verificado.

**Fallback opcional:** `scripts/prepare_presenter_voice.py` usa Edge-TTS y voz sintética femenina `es-CO-SalomeNeural` para leer los diez titulares y producir `presentadora-voz.wav`. Se activa solo cuando `ORBIUNO_EDGE_TTS_OPT_IN=1` en variables del repositorio y el manifiesto `media/FECHA/presentadora-foto.json` contiene `rightsVerified`, `consentVerified`, `voiceAuthorized`, `scriptChecked`, `imageRightsVerified`, `ttsCommercialUseApproved` verdaderos. También debe existir `presentadora-foto.jpg`. Revisar los términos comerciales del proveedor y la licencia de la imagen antes de activar. Edge-TTS es un servicio online externo y puede fallar o cambiar sin aviso; no se garantiza funcionamiento ni costes nulos. El código de `.github/workflows/reel-presentadora.yml` prepara audio si está habilitado y ensambla video, pero **no hace publicaciones en Instagram por sí solo**.

**No presentado como ejecutado:** no se ha verificado un nuevo Reel con presentadora generado ni publicado con esta vía; si falta imagen, autorización o audio, NO se sustituye por un Reel azul fijo engañoso.

## 3. Deportes al mediodía

`scripts/sync_sources.py` incluye feeds candidatos de Selección Colombia, Champions League, F1 y deportistas colombianos, con mayor prioridad entre 11:00 y 14:59 Bogotá. Los artículos RSS siguen `source_only`, por lo que no son automáticamente noticias confirmadas.

`scripts/build_caption.py` produce `publicationReady=false` para la edición de las 12:00 si no incluye **de una a dos** noticias `Deportes` con `editorial_verified`. El bot de despacho debe respetar el bloqueo y completar la verificación antes de publicar; no inventar deportivas para cumplir la cuota.

## 4. Enlaces UTM y conversión real

`scripts/build_caption.py` prepara enlaces **diferentes** para:
- `utm_source=instagram&utm_medium=bio&utm_campaign=edicion_AAAAMMDD_FRANJA`
- `utm_source=instagram&utm_medium=story&utm_campaign=edicion_AAAAMMDD_FRANJA`
- `utm_source=instagram&utm_medium=caption&utm_campaign=edicion_AAAAMMDD_FRANJA`
- `utm_source=instagram&utm_medium=comment&utm_campaign=edicion_AAAAMMDD_FRANJA`

Los cuatro links se guardan en `media/FECHA/instagram-publicacion.json` y `instagram-enlaces-utm.txt`. La biografía de Instagram y los stickers de Historias son lugares potencialmente clicables; las URL en captions y comentarios suelen ser texto, aunque se dejan en línea aparte para fácil copia. **Generar enlaces no cambia automáticamente la biografía del perfil.**

La web `index.html` recibe UTMs y despacha eventos:
- `landing_view` cuando entra una visita con origen Instagram (aproximación por sesión/campaña);
- `audio_play`, `audio_paused`, `audio_resumed`, `audio_finished` con el ID de noticia, modalidad completa/resumen, velocidad, timbre y atribución UTM.

El envío se realiza a `/api/audio-event`, implementado en `functions/api/audio-event.js` (Cloudflare Pages Functions), y adicionalmente a `gtag` o `zaraz.track` **solo si ya están instalados**. No se almacenan nombres, IP, correos ni identificadores de usuario en el payload.

**Paso pendiente para estadísticas persistentes:** en Cloudflare Pages → proyecto `colombia-al-dia` → Settings → Bindings → Analytics Engine, asociar el binding exactamente `ANALYTICS_ENGINE` con el dataset `orbiuno_audio` (o el dataset elegido), y volver a desplegar. Sin ese binding el endpoint responde `recorded:false`; no se pueden afirmar conversiones registradas. Para obtener el porcentaje de sesiones que iniciaron audio se compara `audio_play` frente a `landing_view` de Instagram de igual campaña. El tráfico en captions sin clic real no se puede contar automáticamente como visitas al sitio.

## 5. Qué está aprobado, qué requiere acción externa

| Componente | Código implementado | Activación externa pendiente |
|---|---|---|
| Borradores propios extendidos (3–4 párrafos) | Sí, con validaciones | API y presupuesto autorizados, además de revisión editorial |
| Clip de presentadora alternativo con FFmpeg y voz | Sí, condicionado | Imagen aprobada, manifiesto legal y servicio de voz operativo |
| Noticias deportivas del mediodía | Sí, buscador/prioridad/bloqueo | Contrastar 1–2 noticias actuales para cada nueva edición |
| UTMs por ubicación y campaña | Sí | Actualizar enlace de bio y publicar Historias con sticker |
| Analítica de audio | Sí, cliente y endpoint | Configurar binding Analytics Engine o herramienta equivalente |

## 6. Verificación y publicación

Las pruebas se ejecutan con `.github/workflows/actualizar-noticias.yml`, y las imágenes con `.github/workflows/generar-carrusel.yml`. La automatización ORBIUNO de 08:00, 12:00 y 18:00 Bogotá debe utilizar `publicationReady`, verificar material vigente, no duplicar posts, y consultar **PUBLISHED** y URL pública de Metricool antes de declarar éxito. GitHub Actions no publica en Instagram por sí mismo ni sustituye supervisión periodística.

**Regla final:** las cuatro piezas se consideran integradas al código; el estado de actividad real depende de autorizaciones y conexiones. Nunca equiparar «implementado» con «publicado» o «registrado» sin comprobarlo.
