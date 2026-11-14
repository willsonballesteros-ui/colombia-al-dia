# Configuración segura: Facebook Reels de ORBIUNO y MyCar

**Estado al 14 de noviembre de 2026:** ambas páginas conectadas al conector Windsor Facebook Organic, pero ese conector no ofrece subir Reels de video. El publicador directo de GitHub está preparado y **NO** puede publicar sin un Page Access Token específico por cada página. No se incluyen tokens ni contraseñas en este repositorio.

## Páginas verificadas

| Marca | Facebook Page ID | Instagram |
| --- | --- | --- |
| ORBIUNO Noticias | `1516359454884058` | `@resumen.noticias` |
| MyCar | `100141169648736` | `@mycar.buscoautos` |

## Autorización que debe completar la persona propietaria

1. En https://developers.facebook.com/apps/ iniciar sesión con su cuenta administradora y seleccionar o registrar una aplicación propia apropiada para publicación en páginas. Meta puede pedir registro como desarrollador, permisos o revisión de la aplicación. **No crear otra página ni otro portafolio para eludir restricciones.**
2. En https://developers.facebook.com/tools/explorer/ elegir esa aplicación y solicitar permisos mínimos adecuados para publicación de páginas: `pages_show_list`, `pages_read_engagement` y `pages_manage_posts`. Confirmar que su rol en ambas páginas autoriza crear contenido. No solicitar permisos publicitarios para esta tarea.
3. Comprobar los dos Page IDs mediante el panel autorizado de Meta y obtener, para cada página, un **Page Access Token** válido para la aplicación. No compartir el token por WhatsApp, correo o ChatGPT. Evaluar expiración y renovación según el tipo de autorización; los tokens temporales de prueba no garantizan automatización estable.
4. Abrir **únicamente** https://github.com/willsonballesteros-ui/colombia-al-dia/settings/secrets/actions y crear estos secretos de GitHub Actions (Repository secrets):
    - `ORBIUNO_FB_PAGE_ID` = `1516359454884058`
    - `ORBIUNO_FB_PAGE_ACCESS_TOKEN` = token de **ORBIUNO Noticias**
    - `MYCAR_FB_PAGE_ID` = `100141169648736`
    - `MYCAR_FB_PAGE_ACCESS_TOKEN` = token de **MyCar**
5. Ejecutar desde **Actions → Facebook | Reels ORBIUNO y MyCar (Meta API oficial) → Run workflow**, primero con `publish=false` para cada página. Si la prueba confirma identidad, permisos, datos y no duplicados, ejecutar con `publish=true` solo para la edición **específica**, después de comprobar qué publicaciones están ya en Facebook.

## Seguridad y límites

- Nunca escribir secretos en archivos versionados, entradas de workflow, logs, Issues, mensajes o capturas.
- Mantener permisos solo de páginas y publicación, sin anuncios ni audiencias.
- La restricción publicitaria del portafolio MyCar **permanece separada**; si Meta deniega una operación por permisos o integridad, detenerla y solicitar revisión oficial, no buscar otra cuenta ni ruta para saltar el bloqueo.
- La conexión Windsor Facebook Organic ofrece publicaciones de texto/foto, no el envío de Reels MP4.
- El botón `publish=false` no publica. Una respuesta de API que confirma fin de carga puede requerir verificación adicional de disponibilidad pública del Reel.
- El flujo contiene controles de fuente, derechos y duplicados; conserva las publicaciones anteriores.

## Implementación

- `scripts/publish_facebook_reels.py`
- `.github/workflows/facebook-reels-directo.yml`
- Documentación oficial: https://developers.facebook.com/docs/graph-api/reference/page/video_reels/
