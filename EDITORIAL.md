# ORBIUNO · Colombia al Día — Directiva editorial y técnica vigente

**4 de noviembre de 2026. Sustituye la directriz anterior de textos largos y prohibición absoluta de presentadoras digitales.**

## Identidad y noticias

Noticiero de Colombia y el mundo: información seria, sobria, comprensible y breve. Cada una de las diez noticias debe llevar **titular**, **resumen ejecutivo de hasta dos líneas visibles** y **fuente original con enlace HTTPS**. El campo `executiveSummary` almacena esa síntesis (idealmente 100 a 145 caracteres). No publicar en la interfaz ni en las láminas las etiquetas «Qué pasó», «Por qué importa» o «Qué sigue». El archivo histórico puede conservar observaciones internas, pero no se muestran al público.

Priorizar economía, tecnología/IA, infraestructura, seguridad y panorama global, con hechos contrastados e incertidumbre atribuida. No elevar RSS `source_only` a noticia `editorial_verified` sin comprobación.

## Sitio web

- Encabezado mínimo «ORBIUNO | Colombia al Día» y texto corto, sin cajas de fecha ni avisos llamativos.
- **UX móvil horizontal comprimida:** icono real de la fuente (favicon del dominio) o fotografía licenciada a la izquierda; titular, resumen, ▶ y Fuente a la derecha. Objetivo: visualizar 3 o 4 noticias por desplazamiento de pantalla.
- Tarjetas de lectura rápida, con máximo dos líneas visibles de `executiveSummary`, fuente original clicable y audio gratuito del navegador.
- TTS de `window.speechSynthesis` mediante clic expreso del lector; ▶️ Escuchar resumen / Pausar / Reanudar / Detener. No se afirma una voz natural idéntica en todos los dispositivos.
- Las advertencias de atribución y metodología se mantienen en el pie, no sobre los titulares.

## Reproductor de audio y derechos de artículos completos

El lector puede elegir **voz en español** desde un selector discreto situado encima de las tarjetas. La lista procede de las voces reales que ofrece el dispositivo mediante `speechSynthesis.getVoices()`; se prefiere una voz femenina/neuronal de buena claridad cuando el nombre la identifica, sin inventar voces ausentes. Se memoriza la selección en el navegador cuando su almacenamiento local está disponible. Velocidad: 1x, 1,25x, 1,5x y 2x; si cambia mientras escucha, se reinicia solo la frase actual. El audio se reproduce sin expandir las noticias.

**No presentar resúmenes como artículos íntegros.** `audioFullTextEs` contiene una narración editorial AMPLIADA redactada por ORBIUNO, no el texto completo de Reuters, EFE, Financial Times, etc. Su botón se llama `Escuchar versión ampliada`, independientemente de su longitud. `Escuchar toda la noticia` es exclusivo de `fullArticleTextEs` cuando se haya verificado la licencia original para reproducir el artículo entero, la URL exacta de su fuente y, si se traduce del inglés al español, el derecho de traducción.

Campos obligatorios para habilitar artículo original completo: `fullArticleTextEs` (traducción íntegra autorizada si corresponde), `fullArticleRightsVerified=true`, `fullArticleIsVerbatimSource=true`, `fullArticleLicense`, `fullArticleSourceUrl` coincidente con un enlace de `sources` y `fullArticleTranslationAuthorized=true` para fuentes `sourceLanguage=en`. Los validadores bloquean cualquier entrada incompleta. No automatizar scraping/republicación íntegra de sitios comerciales sin convenio de distribución.

Para los medios sin permiso de reproducción, mostrar `Artículo completo ↗` con el vínculo original y permitir escuchar la **versión ampliada de ORBIUNO en español**. El navegador no puede acceder y leer íntegramente un sitio ajeno mediante JavaScript por restricciones de origen y derechos. El usuario puede activar la lectura de página nativa desde su navegador, cuando la página de origen lo permita.

## Imágenes reales y marcas

Para noticias, priorizar fotografía real con derechos de reproducción confirmados. Campos: `imageUrl`, `imageType` (`official_photo`, `licensed_press_photo`, `official_document`), `imageCredit`, `imageLicense`, `imageRightsVerified=true`, `imageSourceUrl`. Sin esos datos, se puede consultar el **favicon real del dominio de la fuente** y mostrar su nombre en una tarjeta. El favicon identifica al medio, NO representa una foto del hecho, y no se inventan marcas ni logotipos. La presentadora virtual solicitada debe identificarse y tener derechos de uso y autorización de voz verificables; nunca afirmar que una foto inventada documenta un hecho.

## Dos formatos sociales diferentes

- **Reel vertical:** once escenas de video: **presentadora virtual femenina de apariencia natural** en escena inicial, narrando los diez titulares en español claro, seguida de diez láminas. Debe existir y verificarse el MP4 de la presentadora y su autorización; no sustituir por una foto estática como si hablara.
- **Carrusel Instagram:** máximo **diez** láminas de noticias (límite de la plataforma). El recurso adicional `portada.png` sirve para portada de Reel, previsualización o historia, **NO como una undécima foto en el carrusel**. Así se conservan las diez noticias sin incumplir Instagram.
- Cada lámina: miniatura/favicón real del medio o fotografía licenciada, fuente visible, titular dominante y síntesis de máximo dos líneas completas (fuente tipográfica adaptable). No simular botones clicables sobre las imágenes. Fuente y detalle verdaderamente clicables desde la web; los stickers de enlace, encuesta y cuestionario son nativos de historias y pueden requerir publicación manual.

## Automatización y comprobaciones

**Copy + primer comentario:** ejecutar `scripts/build_caption.py` en cada edición. Usar `media/FECHA/instagram-publicacion.json` con campos `caption` y `firstComment`. URL exacta en línea aparte: `🌐 https://colombia-al-dia.pages.dev/`. No copiar la lista de diez titulares dentro del caption. Los enlaces en captions y comentarios de Instagram suelen no ser tocables; el enlace en la biografía y los stickers nativos sí pueden conducir a la web.

La rutina editorial conserva las franjas **08:00, 12:00 y 18:00** en `America/Bogota`. GitHub Actions prepara titulares a las 07:30/11:30/17:30 y genera recursos; las comprobaciones periodísticas y la publicación requieren una herramienta conectada que opere en ese momento.

GitHub Actions **no dispone de credenciales de publicación Metricool**. Según la documentación oficial vigente, la API directa de Metricool requiere Advanced/Custom; no activar un plan de pago sin autorización. La conexión de Metricool en ChatGPT puede crear o cambiar posts mediante acciones autorizadas; verificar **PUBLISHED y URL real**, y detectar duplicados. No prometer autonomía 100 % ni videos no creados. Si la presentadora está pendiente, continuar con noticias web y carrusel textual sin presentar Reel ficticio como realizado.

## Pipeline audiovisual

`scripts/assemble_reel.py` y `.github/workflows/reel-presentadora.yml` solo generan Reel cuando existe un `media/AAAA-MM-DD/presentadora-intro.mp4` con audio, derechos aprobados y su manifest `presentadora-intro.json`. Fallback condicional sin avatar hablado: `media/FECHA/presentadora-foto.jpg`, `presentadora-voz.wav` y `presentadora-foto.json`. Solo si existen y acreditan derechos, consentimiento, voz autorizada y lectura efectiva de los diez titulares, se crea un video con la foto de la presentadora, movimiento suave y onda sonora visible. Ese caso declara `hasRealLipSync=false`; **nunca se anuncia como labios sincronizados**. El portal sigue funcionando sin estos archivos.

Los cinco controles de autorización requeridos son `rightsVerified`, `consentVerified`, `voiceAuthorized`, `scriptChecked` y `speaksAllTenHeadlines` junto a `source` no vacío. Si no hay intro o no hay consentimiento, falla de forma segura; nunca marca como publicado un MP4 no generado.

Pruebas en CI: 10 noticias editoriales, fuentes HTTPS, no imágenes ficticias presentadas como fotografías, TTS nativo y 10 láminas para Instagram + recurso de portada.
