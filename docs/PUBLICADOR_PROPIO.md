# ORBIUNO / MyCar — Centro de publicación propia (MVP 1)

Este módulo **no depende de Metricool**. Usa APIs oficiales de Meta y GitHub Actions como operador. Ya existen:
- Instagram: `scripts/publish_instagram_direct.py`
- Facebook: `scripts/publish_facebook_direct.py`
- Formulario manual: **Actions → ORBIUNO | Publicar directo sin Metricool → Run workflow**

## Estado y limitaciones reales
Código cargado en GitHub, **sin prueba de publicación vía API oficial Meta**. No se ha probado la validez ni los permisos de ninguna credencial. No está habilitada la programación recurrente, ni un panel web, ni OAuth. No hay publicación directa demostrada.
El formulario exige URL HTTPS pública, título/caption con fuente y confirmación de derechos de imagen. No hay contenido generado por IA por defecto.

## Activación segura — repositorio ORBIUNO
Configurar en GitHub > Settings > Secrets and variables > Actions > Repository secrets:
- `ORBIUNO_IG_USER_ID`: ID profesional de Instagram.
- `ORBIUNO_IG_ACCESS_TOKEN`: token de Instagram Login autorizado para `instagram_business_basic` y `instagram_business_content_publish`, sujeto a requisitos vigentes de Meta.
- Para Facebook, `ORBIUNO_FB_PAGE_ID` y `ORBIUNO_FB_PAGE_ACCESS_TOKEN`, emitido con permisos de página autorizados.

Nunca guardar los tokens en código, captions, imágenes ni archivos GitHub.
Con las credenciales y una imagen pública licenciada, ejecutar **Actions > ORBIUNO | Publicar directo sin Metricool** y revisar el enlace/media_id devuelto. Un job verde sin enlace verificable no equivale por sí solo a prueba pública del post.
**No ejecutar dos veces sin verificar la primera**, para evitar duplicados. Reels, carruseles, programación por calendario, panel visual, reintentos idempotentes, auditoría persistente y soporte MyCar en otro repositorio quedan para siguientes fases.

## Criterios editoriales
Colombia: noticias positivas y verificadas. Otras secciones: información internacional/tecnología pertinente. Fuente original visible, imágenes con licencia o autorización, cero simulación de publicación.

## API
Instagram Login usa `https://graph.instagram.com/{version}/{ig_user_id}/media` → espera `FINISHED` → `/media_publish`.
Facebook Pages usa `https://graph.facebook.com/{version}/{page_id}/photos`.
Revisar versión, restricciones y scopes en documentación oficial de Meta antes de producción.
