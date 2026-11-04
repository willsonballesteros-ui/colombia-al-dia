# ORBIUNO — sitio y preparación automática de noticias

**Estado comprobado el 4 nov 2026:** Sitio desplegado en https://colombia-al-dia.pages.dev/ y repositorio en la rama `main`. Instagram histórico: https://www.instagram.com/resumen.noticias/. La ingesta y el carrusel son procesos automatizados, pero la **publicación audiovisual completa 3 veces al día todavía NO es autónoma**. No afirmar que existe lip-sync de la presentadora o publicación confirmada sin verificarlos.


## Arquitectura operativa actual y límites reales (4 nov 2026)

- Preparación de titulares: GitHub Actions a las 07:30, 11:30 y 17:30 (Bogotá). Este horario es de **preparación**, NO confirmación de publicaciones.
- Selección automática: `scripts/sync_sources.py` prioriza temas de impacto (economía, política, infraestructura, seguridad, tecnología e IA). Aplica filtros de descarte a noticias de entretenimiento. Este es un **puntaje heurístico de titulares**, nunca una verificación de hechos.
- Control editorial: los registros `source_only` importados de RSS no pasan a `editorial_verified` sin comprobación independiente. No generar un noticiero de diez noticias verificadas solo con RSS.
- Portada: `scripts/prepare_site.py` sincroniza `index.html` con el JSON y precarga hasta diez noticias verificadas para usuarios y buscadores sin JavaScript. Se incluyeron `robots.txt` y `sitemap.xml`.
- Material gráfico: `generar-carrusel.yml` produce diez PNG y una historia sin códigos QR solo si existe una edición de diez notas editoriales; generar medios **no** significa publicarlos.
- Instagram: cuenta Metricool conectada desde ChatGPT, pero no se han configurado en GitHub las credenciales de una API de autopublicación. Primeros comentarios y stickers clicables pueden fallar o exigir intervención nativa. **No registrar secretos ni tokens en el repositorio**.
- Video: los intentos de HeyGen del 3 de noviembre fallaron por límites de Avatar IV y créditos regulares insuficientes; **no** hay un render nuevo con sincronización labial. No iniciar GPU, APIs de voz, modelos de pago ni otros cargos sin consentimiento.
- Fiabilidad: los cron de GitHub Actions pueden retrasarse y las publicaciones programadas deben comprobarse en el proveedor, incluido el enlace real al post. Ningún workflow debe inventar publicación exitosa.

## Qué incluye

- `index.html`: interfaz móvil y desktop con búsqueda, filtros por fecha, tarjetas y enlaces de fuentes.
- `noticias.json`: ediciones editoriales y titulares de seguimiento, incluidas diez noticias verificadas en la edición del 3 de noviembre de 2026.
- `scripts/sync_sources.py`: incorporación automática, sin API de pago, de **titulares de medios externos con enlace** a partir de feeds RSS/Atom; no inventa resúmenes ni confirma afirmaciones no comprobadas. Conserva el historial y evita duplicados.
- `scripts/validate_news.py`: valida fechas, enlaces HTTPS, integridad de identificadores y etiquetas de titulares automáticos.
- `.github/workflows/actualizar-noticias.yml`: tarea GitHub Actions, tres veces al día, con commits únicamente si hay cambios en el archivo; Cloudflare Pages despliega el commit si se conecta el repositorio.
- `tests/fixtures/feed.xml`: prueba ficticia LOCAL, **nunca publicada ni incluida en el `noticias.json` de producción**.
- `_headers`: control de caché para mostrar nuevas ediciones.

## Requisito editorial imprescindible

**Una noticia publicada por un medio no equivale a una noticia comprobada por nuestra redacción.** Por ello hay dos clases diferenciadas en la web:

1. **Edición revisada por la redacción:** registros originales dentro de `noticias.json` con categorías y análisis redactados y contrastados.
2. **Titular atribuido a una fuente / pendiente de verificación editorial:** registros nuevos importados automáticamente. En estos solo se ofrece un titular atribuido, la fecha y un enlace. El texto de «Qué pasó / Por qué importa / Qué sigue» es una advertencia de seguimiento, NO una narración de hechos no comprobados.

Los enlaces procedentes de Google Noticias pueden abrir primero el agregador, no directamente el medio original. No publicar la frase «ver fuente original directamente» cuando corresponda a ese caso. Las fuentes son externas y pueden modificar sus feeds o condiciones de uso.

## Horarios de Bogotá

El workflow incluye el cron UTC:

```yaml
- cron: '30 12,16,22 * * *'
```

Bogotá es UTC-5, por lo que corresponde a **07:30, 11:30 y 17:30** en Colombia, treinta minutos antes de las franjas de 08:00, 12:00 y 18:00. Las ejecuciones de GitHub Actions pueden retrasarse; no son una garantía de puntualidad absoluta. No hace falta pagar un scheduler. Revisar mensualmente los límites de GitHub Actions/Cloudflare Pages según el plan.

## Guía histórica de instalación (ya realizada para este repositorio)

1. **Conectar GitHub a ChatGPT** desde la sugerencia de conector de GitHub, o crear un repositorio nuevo manualmente con la cuenta del propietario. No entregar contraseñas, tokens ni secretos en chat o Drive. Recomendación: repositorio nuevo exclusivo para Colombia al Día; no mezclar con otros proyectos. Si se requiere privado, comprobar las cuotas incluidas del plan GitHub.
2. Subir **todos los archivos del ZIP incluyendo la carpeta oculta `.github`** a la raíz del repositorio, rama `main`. No descomprimir únicamente `index.html` y `noticias.json`.
3. En GitHub, revisar que el workflow `.github/workflows/actualizar-noticias.yml` aparece en **Actions**. Si está deshabilitado, habilitarlo. El permiso de escritura del token integrado `GITHUB_TOKEN` debe poder generar commits al repositorio (si la política impide commits de Actions, ajustar la configuración del repositorio; sin introducir tokens ajenos).
4. Entrar en https://dash.cloudflare.com/ → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**. Escoger el repositorio nuevo de Colombia al Día. Seleccionar rama `main`, framework `None` / `Other`, **Build command vacío**, directorio de publicación `/` (raíz de repositorio, o `.` si el panel requiere texto). Confirmar que se está usando el plan gratuito.
5. Esperar a que el primer deployment quede **Success** y abrir el `*.pages.dev` devuelto por Cloudflare. Comprobar que la página muestre las ocho noticias históricas, filtros y enlaces HTTPS. **No inventar el subdominio ni cambiar el enlace de la bio antes de verificarlo.**
6. En GitHub → **Actions** → `Actualizar titulares con fuente` → **Run workflow**. Inspeccionar logs: debe indicar cuántos feeds respondieron y cuántos titulares se añadieron; en cero feeds exitosos el trabajo falla explícitamente y no actualiza el portal. Verificar el commit y esperar a que Cloudflare haga un nuevo deployment.
7. Abrir `*.pages.dev`, actualizar con Ctrl+Shift+R y verificar que aparecen los nuevos titulares atribuidos, la fecha/hora de consulta automática y los filtros; luego probar desde un teléfono.
8. **Solamente después de estas pruebas**, cambiar el enlace de Instagram a la nueva página. El dominio antiguo `resumen-noticias-consulta-ia.willsonballesteros.chatgpt.site` no puede conservarse automáticamente al migrar si su panel de edición no permite redirecciones. No borrar el enlace antiguo prematuramente.

## Operación habitual

- Cada ejecución obtiene entradas recientes (<=36 horas) de fuentes RSS. Si los feeds responden, añade como máximo nueve titulares en seguimiento y mantiene los anteriores.
- Si algún feed falla, sigue con los que respondieron y registra el número de fallos. Si todos fallan, **NO se publican titulares ni timestamps nuevos**.
- Cloudflare Pages conectado a GitHub despliega automáticamente cada commit del workflow.
- El cliente web también consulta `noticias.json` cada cinco minutos sin caché para detectar cambios.
- La fecha de la **última edición revisada por la redacción** no se modifica automáticamente; indica lo que es realmente verificado.
- El archivo JSON es la fuente de la verdad para el historial del sitio; Google Drive sirve como respaldo, pero subir un JSON a Drive no altera la versión desplegada.
- Los reels y las publicaciones de Instagram siguen siendo un proceso diferente; actualizar una web no publica un Reel.

## Límites y permisos

- Para convertir un titular en noticia verificada con análisis de «Qué pasó, Por qué importa y Qué sigue» hay que hacer investigación contrastada (ChatGPT/Gemini o edición humana) y luego publicar cambios al **repositorio GitHub**. El flujo automático de titulares no reemplaza el chequeo periodístico.
- El script guarda solamente titulares y enlaces atribuidos (no reproduce artículos íntegros). Aun así, comprobar términos de uso del RSS si el portal se comercializa.
- GitHub Actions no equivale a cron local. Los cron pueden demorarse; el flujo en proyectos públicos puede deshabilitarse tras inactividad prolongada, según políticas de GitHub. Verificar logs ocasionalmente.
- No se conocen los permisos del alojamiento `willsonballesteros.chatgpt.site` ni del GitHub/Cloudflare del propietario. Este paquete **no tiene capacidad por sí solo para modificar ese dominio público**.
- Una vez haya un repositorio conectado y autorizado, ChatGPT puede colaborar en publicar cambios solo mediante capacidades efectivamente disponibles. No confundir el hecho de sugerir un conector con estar conectado.

## Pruebas

Sin acceder a fuentes externas:

```bash
python scripts/validate_news.py noticias.json
cp noticias.json /tmp/ensayo-noticias.json
python scripts/sync_sources.py --data /tmp/ensayo-noticias.json --fixture tests/fixtures/feed.xml --now '2026-11-02T21:50:00-05:00'
python scripts/validate_news.py /tmp/ensayo-noticias.json
```

La ejecución con `--fixture` modifica exclusivamente `/tmp/ensayo-noticias.json`, NO el archivo de producción.

## Resultado esperado realista

**Se automatiza el refresco del portal con titulares recientes atribuidos y conserva el historial. NO se automatiza por sí mismo la verificación editorial, el análisis profundo, la publicación de Reels ni la administración del dominio antiguo.** No contratar servicios ni activar facturación adicional para ello.
