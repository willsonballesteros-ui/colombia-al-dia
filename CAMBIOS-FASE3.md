# ORBIUNO Fase 3 | Rama de validación

- El Reel mantiene las cuatro noticias en la misma composición vertical y resalta cada bloque al ritmo de la narración. La Story usa una portada y un cierre propios en un MP4 corto.
- El generador de Fase 3 vive en `scripts/render_orbiuno_edition.py`. Los renderizadores y el ensamblador anteriores conservan sus puntos de entrada.
- GitHub Actions verifica la voz Kokoro ef_dora y permite generar una vista previa desde una edición de cuatro noticias. Los MP4 y el informe de inteligibilidad se entregan como artefactos.
- El control web requiere titulares en los encabezados de la portada pública y reportajes propios revisados de al menos tres párrafos. Un titular presente únicamente en los datos embebidos no supera el control.
- Metricool sigue a cargo de Instagram. La integración de Meta se prueba con dobles de prueba y el comando `python scripts/publish_meta.py --edition AAAA-MM-DD-HHMM --dry-run` comprueba manifiesto y medios públicos sin llamar a Meta.
- Para una vista previa editorial, completar las cuatro noticias de la plantilla en `editions/<id>.json`. Para una simulación pública completa se necesita una edición aprobada y sus medios accesibles en la web.
