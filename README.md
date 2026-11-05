# ORBIUNO | Colombia al Día

**Portal público:** https://colombia-al-dia.pages.dev/  
**Instagram:** https://www.instagram.com/resumen.noticias/  
**Rama de producción:** `willsonballesteros-ui/colombia-al-dia:main`

## Estado funcional — 4 nov 2026

- **Portal implementado**: titulares, síntesis visibles en dos líneas, enlaces HTTPS a fuentes y Web Speech API con controles de escucha, pausa, reanudación y detención, sin servicios pagos.
- **Edición**: diez noticias contrastadas en `noticias.json`. Los registros importados por RSS mantienen `verification=source_only` hasta su verificación editorial. Los textos públicos no muestran las secciones largas «Qué pasó», «Por qué importa», «Qué sigue».
- **Material social**: `scripts/build_carousel.py` crea cinco láminas editoriales (`grupo-01.png`…`grupo-05.png`) con dos noticias cada una más una `portada.png` de resumen. Los `top10` individuales quedan como recursos auxiliares. El flujo de publicación de Metricool se limitará a 10 imágenes por carrusel; reservar portada.png para Reel/Historia.
- **Escena hablada**: preparada la canalización `scripts/assemble_reel.py` + `.github/workflows/reel-presentadora.yml`, pero requiere un **clip de presentadora generado y autorizado** para montar el Reel. No afirmar que ese video existe si no está en `media/`.
- **Programación**: 08:00 / 12:00 / 18:00 Bogotá mediante tarea conectada; GitHub Actions realiza preparación a las 07:30 / 11:30 / 17:30 y renderiza las láminas al cambiar la edición. Verificar publicaciones en Metricool antes de confirmarlas.
- **Límite comercial**: la API directa de Metricool para scripts GitHub Actions necesita acceso Advanced/Custom; este proyecto no tiene configurado token de API ni habilita compras. La conexión de Metricool a ChatGPT es distinta de esa API directa.

## Archivos principales

- `noticias.json`: edición, fuentes originales, `executiveSummary` y clasificación editorial.
- `index.html`: web móvil, SSR editorial, TTS local y enlaces.
- `scripts/prepare_site.py`: sincronización de HTML inicial y JSON embebido.
- `scripts/sync_sources.py`: ingesta de RSS sin convertir titulares en noticias verificadas.
- `scripts/validate_news.py`: integridad y licencias de imágenes.
- `scripts/build_carousel.py`: cinco láminas de dos noticias + portada, sin fotos ficticias.
- `scripts/assemble_reel.py`: concatena video real de presentadora autorizada y diez láminas; no produce avatares por su cuenta.
- `.github/workflows/actualizar-noticias.yml`: pruebas y despliegue.
- `.github/workflows/generar-carrusel.yml`: genera PNG.
- `.github/workflows/reel-presentadora.yml`: compone el MP4 solo cuando existe el clip de introducción autorizado.

## Cómo activar el Reel cuando exista la presentadora

1. Generar clip 9:16 de presentadora femenina natural, **que realmente pronuncie los diez titulares** (servicio autorizado).
2. Publicar `media/<fecha>/presentadora-intro.mp4` y `media/<fecha>/presentadora-intro.json`, con `source`, `rightsVerified`, `consentVerified`, `voiceAuthorized`, `scriptChecked`, `speaksAllTenHeadlines` revisados por la persona responsable.
3. El workflow ensambla los once segmentos y valida audio/video, guarda `reel-presentadora.mp4`, sin afirmar que esté publicado en Instagram.
4. Programar ese MP4 con Metricool `autoPublish=true` y confirmar `PUBLISHED` y enlace público. No generar Reel falso sin clip.

No incluir contraseñas/tokens en GitHub. No activar cuotas de pago sin consentimiento explícito.

## Cuatro mejoras técnicas aprobadas

- **Redacción ampliada original:** `scripts/generate_full_reports.py` y workflow manual `generar-reportajes-extendidos.yml` (opt-in, puede facturar API). Los textos generados quedan como borradores hasta revisión.
- **Respaldo audiovisual local:** `scripts/assemble_reel.py` + `scripts/prepare_presenter_voice.py` (Edge-TTS opcional con derechos de imagen, consentimiento y términos comerciales verificados; no simula lip-sync).
- **Deportes 12:00:** fuentes de Selección, Champions, F1 y colombianos; `publicationReady=false` si no hay una o dos noticias deportivas verificadas.
- **Instagram→web→audio:** UTM diferenciados para bio, historia, caption y comentario; `index.html` emite `landing_view`, `audio_play` y finalización. `functions/api/audio-event.js` registra en Cloudflare Analytics Engine **solamente si el binding `ANALYTICS_ENGINE` está configurado**.

**Guía de implementación y pendientes:** [IMPLEMENTACION_APROBADA_2026-11-04.md](IMPLEMENTACION_APROBADA_2026-11-04.md).

Ver política exacta en [EDITORIAL.md](EDITORIAL.md).
