# ORBIUNO — carrusel fail-closed (rama de desarrollo)

Esta implementación inicial **no modifica producción, no genera imágenes, no publica y no valida licencias legalmente**. Solo agrega esquema y una herramienta preliminar de bloqueo.

## Contrato de manifiesto

Edición: `editions/AAAA-MM-DD-am/manifest.json` o `editions/AAAA-MM-DD-pm/manifest.json`.
Todos los archivos de foto, logo y audio son rutas relativas al directorio de esa edición. No se aceptan rutas que salgan de él.

El manifiesto exige cinco noticias. Para permitir menos cuando no hay cinco verificadas se requiere una política editorial separada; esta versión **bloquea** la edición.

## Ejecución

```bash
pip install jsonschema Pillow
python scripts/preflight_carousel.py editions/2026-11-12-am/manifest.json --web-manifest /tmp/web-publicada.json
```

Requiere `ffprobe` y `ffmpeg`. Un código 1 impide publicar.

**Faltantes deliberados:** verificación humana real de autoría/licencia, cotejo semántico de foto y noticia, autenticación y sincronización contra despliegue público, voz colombiana validada en dispositivo, integración de API Meta y chequeo visual de seis PNG. El campo `revision_humana: true` es una declaración, no prueba automática de derechos; debe respaldarse con auditoría registrada.

**No integrar el PR hasta completar esas comprobaciones y sus pruebas.**
