# ORBIUNO Publicador propio — 12 nov 2026

## Lo que existe
- **Programar**: [GitHub Actions → ORBIUNO | Crear publicación sin Metricool](https://github.com/willsonballesteros-ui/colombia-al-dia/actions/workflows/orbiuno-agendar-publicacion.yml) permite guardar cada noticia en `data/publishing_queue.json` con URL pública HTTPS, fuente, texto, fecha y permiso de uso.
- **Publicar**: [GitHub Actions → ORBIUNO | Publicar por API Meta sin Metricool](https://github.com/willsonballesteros-ui/colombia-al-dia/actions/workflows/orbiuno-publicador-autonomo.yml) revisa la cola cada 15 minutos y usa la API oficial de Meta.
- **Trazabilidad**: `data/publishing_queue.json` registra estado, ID confirmado de Meta, enlace si está disponible, fecha y error. Los errores ambiguos exigen revisión humana antes de reintento, para evitar duplicados.
- **Pruebas**: `tests/test_publishing_queue.py` comprueba prevención de publicaciones duplicadas, fecha futura, derechos de imagen, noticia con fuente y fallas inciertas.

## Falta para activar publicaciones reales
El repositorio requiere cuatro secrets en **Settings → Secrets and variables → Actions**:
- `ORBIUNO_IG_USER_ID`
- `ORBIUNO_IG_ACCESS_TOKEN` con autorización `instagram_business_content_publish`
- `ORBIUNO_FB_PAGE_ID`
- `ORBIUNO_FB_PAGE_ACCESS_TOKEN`

Los tokens deben proceder de los flujos autorizados de Meta. Nunca subir credenciales al repositorio ni enviarlas por chat.
Para Instagram los medios han de tener URL pública e imagen JPEG aceptada por su API; no basta con un enlace compartido de Google Drive. La noticia exige una fotografía con permiso de publicación y fuente original.

## Estado de publicación extraordinaria 12/11/2026
La publicación enviada anteriormente por Metricool falló por `You have reached your Metricool account limit`. **No afirmar publicada.** El código nuevo no ha probado aún una publicación contra Meta porque no se han confirmado las credenciales; la cola está vacía para evitar un envío falso o una publicación con imagen sin licencia.

## Alcance actual
Este es el motor programable de ORBIUNO, no una réplica completa de Metricool: faltan pantalla visual de administración, carga y conversión de JPG, Reels y carruseles, OAuth de renovación y adaptación a MyCar. No modificar la producción ni los repositorios de MyCar sin comprobar versiones.

## Regla editorial
Para Colombia, únicamente noticias positivas y comprobadas. Todas las noticias deben incluir fuente y fecha. No usar fotografías ajenas sin autorización. Nunca informar publicación completada sin ID de Meta y, cuando se reciba, vínculo público.
