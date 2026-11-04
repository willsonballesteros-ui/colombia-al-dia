# ORBIUNO | Colombia al Día

**Portal público:** https://colombia-al-dia.pages.dev/  
**Instagram:** https://www.instagram.com/resumen.noticias/  
**Rama de producción:** `willsonballesteros-ui/colombia-al-dia:main`

## Estado funcional — 4 nov 2026

- **Portal implementado**: titulares, síntesis visibles en dos líneas, enlaces HTTPS a fuentes y Web Speech API con controles de escucha, pausa, reanudación y detención, sin servicios pagos.
- **Edición**: diez noticias contrastadas en `noticias.json`. Los registros importados por RSS mantienen `verification=source_only` hasta su verificación editorial. Los textos públicos no muestran las secciones largas «Qué pasó», «Por qué importa», «Qué sigue».
- **Material social**: `scripts/build_carousel.py` crea diez láminas de noticias (`top10-01.png`…`top10-10.png`) más un `portada.png` para Reel/preview. Instagram admite hasta 10 imágenes por carrusel; no subir 11.
- **Escena hablada**: preparada la canalización `scripts/assemble_reel.py` + `.github/workflows/reel-presentadora.yml`, pero requiere un **clip de presentadora generado y autorizado** para montar el Reel. No afirmar que ese video existe si no está en `media/`.
- **Programación**: 08:00 / 12:00 / 18:00 Bogotá mediante tarea conectada; GitHub Actions realiza preparación a las 07:30 / 11:30 / 17:30 y renderiza las láminas al cambiar la edición. Verificar publicaciones en Metricool antes de confirmarlas.
- **Límite comercial**: la API directa de Metricool para scripts GitHub Actions necesita acceso Advanced/Custom; este proyecto no tiene configurado token de API ni habilita compras. La conexión de Metricool a ChatGPT es distinta de esa API directa.

## Archivos principales

- `noticias.json`: edición, fuentes originales, `executiveSummary` y clasificación editorial.
- `index.html`: web móvil, SSR editorial, TTS local y enlaces.
- `scripts/prepare_site.py`: sincronización de HTML inicial y JSON embebido.
- `scripts/sync_sources.py`: ingesta de RSS sin convertir titulares en noticias verificadas.
- `scripts/validate_news.py`: integridad y licencias de imágenes.
- `scripts/build_carousel.py`: diez láminas de noticias + portada, sin fotos ficticias.
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

Ver política exacta en [EDITORIAL.md](EDITORIAL.md).
