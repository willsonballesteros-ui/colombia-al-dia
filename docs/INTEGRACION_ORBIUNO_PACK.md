# ORBIUNO pack: compuerta final, licencias, logos, audio, aprobación y publicación simulada

Complementa el PR #15 sin modificar `preflight_carousel.py` ni el esquema.
Todo corre con Python 3.12 + Pillow + ffmpeg. No usa red.

## Archivos (rutas exactas, copiar tal cual a la rama feat/carrusel-orbiuno)
scripts/orbiuno_media_registry.py · orbiuno_audio_check.py · orbiuno_approval.py ·
orbiuno_idempotency.py · orbiuno_meta_publish.py · orbiuno_gate.py
tests/test_orbiuno_gate.py · .github/workflows/carrusel-publicar.yml
branding/logos/registry.example.json (renombrar a registry.json al completarlo)

## Contrato por edición (carpeta editions/<id>/)
manifest.json (PR #15) + evidence.json (nuevo) + approval.json + 6 PNG + audios + web-manifest.json.
evidence.json: {"noticias": {"<id>": {"fuente_id", "guion", "foto": {"licencia_codigo",
"licencia_url", "sha256_foto", "evidencia": {"archivo", "sha256"}}}}}

## Configuración necesaria en GitHub (no se puede hacer desde el código)
- Entorno `editorial-approval` con revisores obligatorios y secreto ORBIUNO_APPROVAL_KEY.
- Entorno `instagram-production` con revisores obligatorios (sin secretos de Meta todavía).
- editorial/approvers.json (lista de usuarios aprobadores) y editorial/publicaciones.json ({}).
- Marcar la compuerta como verificación obligatoria en la protección de `main`.

## Posibles conflictos
- La compuerta ejecuta scripts/preflight_carousel.py: debe existir y aceptar --web-manifest.
- web-manifest.json debe salir del despliegue real (aún no hay extractor).
- jsonschema debe instalarse en CI para el preflight.
