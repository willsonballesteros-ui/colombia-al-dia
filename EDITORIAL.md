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

## Audio interno y promoción en redes (vigente)

El lector escucha sin salir de ORBIUNO. Cada tarjeta tiene botones **▶ Escuchar completo** cuando exista texto de artículo completo apto para su reproducción, o **▶ Escuchar resumen** en casos de limitación; **Fuente ↗** siempre abre por separado el medio original.

**Artículo completo** puede referirse a: (a) un reportaje **original completo de Redacción ORBIUNO**, con `originalArticleTextEs`, `originalArticleByline`, `originalArticleReviewed=true` y URLs de fuentes coincidentes y contrastadas; o (b) la transcripción íntegra del medio cuando existan permisos documentados de reproducción y, si se trata de un artículo extranjero traducido, traducción. No copiar artículos de Reuters, EFE, Financial Times y otros sin una licencia de ese tipo. Una narración extensa de resumen NO es un artículo completo y no se presenta como tal.

**Preferencia de voz:** `speechSynthesis.getVoices()` ofrece exclusivamente voces habilitadas por el sistema del usuario. Dar preferencia a voces femeninas y claras en español si las hay, sin prometer disponibilidad específica ni voces reales de niñas. El usuario puede seleccionar voz y el timbre **Dulce (recomendado, pitch 1,10)**, **Juvenil (pitch 1,18)** o **Natural (pitch 1,0)**. El timbre es un ajuste de voz sintética, no un modelo de voz nueva; en algunos navegadores puede ignorarse. Opciones de velocidad **1x, 1,25x, 1,5x, 2x** más pausa, reanudación y parada. Se recuerda elección de voz/timbre cuando el navegador permite almacenamiento local. El texto se narra en español; las fuentes en inglés solo se reproducen traducidas íntegramente cuando existe autorización específica.

**Instagram:** todas las nuevas entregas informan que las noticias pueden escucharse en la web. El copy y primer comentario se generan con `scripts/build_caption.py`; cada uno incluye «🎧 Las noticias también se escuchan en nuestra web» y la URL independiente `🌐 https://colombia-al-dia.pages.dev/`. Las láminas del carrusel incluyen CTA visual discreta de audio. Los enlaces pegados en captions no siempre son tocables: el enlace de perfil/bio o sticker de Historia es el acceso interactivo. Nunca publicar el CTA en posts anteriores como si se hubieran editado: los carruseles ya publicados no se cambian regenerando PNG. El Reel requiere su archivo hablado real y aprobado; la publicidad de audio en web **no significa** que el Reel incluya a una presentadora.

## Imágenes reales y marcas

Para noticias, priorizar fotografía real con derechos de reproducción confirmados. Campos: `imageUrl`, `imageType` (`official_photo`, `licensed_press_photo`, `official_document`), `imageCredit`, `imageLicense`, `imageRightsVerified=true`, `imageSourceUrl`. Sin esos datos, se puede consultar el **favicon real del dominio de la fuente** y mostrar su nombre en una tarjeta. El favicon identifica al medio, NO representa una foto del hecho, y no se inventan marcas ni logotipos. La presentadora virtual solicitada debe identificarse y tener derechos de uso y autorización de voz verificables; nunca afirmar que una foto inventada documenta un hecho.

## Dos formatos sociales diferentes

- **Reel vertical:** once escenas de video: **presentadora virtual femenina de apariencia natural** en escena inicial, narrando los diez titulares en español claro, seguida de diez láminas. Debe existir y verificarse el MP4 de la presentadora y su autorización; no sustituir por una foto estática como si hablara.
- **Carrusel Instagram:** **diez** láminas de noticias para el flujo conectado con Metricool. El recurso adicional `portada.png` sirve para portada de Reel, previsualización o historia, **NO como una undécima foto en el carrusel**. Así se conservan las diez noticias sin incumplir Instagram.
- Cada lámina: miniatura/favicón real del medio o fotografía licenciada, fuente visible, titular dominante y síntesis de máximo dos líneas completas (fuente tipográfica adaptable). No simular botones clicables sobre las imágenes. Fuente y detalle verdaderamente clicables desde la web; los stickers de enlace, encuesta y cuestionario son nativos de historias y pueden requerir publicación manual.

## Automatización y comprobaciones

**Copy + primer comentario:** ejecutar `scripts/build_caption.py` en cada edición. Usar `media/FECHA/instagram-publicacion.json` con campos `caption` y `firstComment`. URL exacta en línea aparte: `🌐 https://colombia-al-dia.pages.dev/`. No copiar la lista de diez titulares dentro del caption. Los enlaces en captions y comentarios de Instagram suelen no ser tocables; el enlace en la biografía y los stickers nativos sí pueden conducir a la web.

La rutina editorial conserva las franjas **08:00, 12:00 y 18:00** en `America/Bogota`. GitHub Actions prepara titulares a las 07:30/11:30/17:30 y genera recursos; las comprobaciones periodísticas y la publicación requieren una herramienta conectada que opere en ese momento.

GitHub Actions **no dispone de credenciales de publicación Metricool**. Según la documentación oficial vigente, la API directa de Metricool requiere Advanced/Custom; no activar un plan de pago sin autorización. La conexión de Metricool en ChatGPT puede crear o cambiar posts mediante acciones autorizadas; verificar **PUBLISHED y URL real**, y detectar duplicados. No prometer autonomía 100 % ni videos no creados. Si la presentadora está pendiente, continuar con noticias web y carrusel textual sin presentar Reel ficticio como realizado.

## Pipeline audiovisual

`scripts/assemble_reel.py` y `.github/workflows/reel-presentadora.yml` solo generan Reel cuando existe un `media/AAAA-MM-DD/presentadora-intro.mp4` con audio, derechos aprobados y su manifest `presentadora-intro.json`. Fallback condicional sin avatar hablado: `media/FECHA/presentadora-foto.jpg`, `presentadora-voz.wav` y `presentadora-foto.json`. Solo si existen y acreditan derechos, consentimiento, voz autorizada y lectura efectiva de los diez titulares, se crea un video con la foto de la presentadora, movimiento suave y onda sonora visible. Ese caso declara `hasRealLipSync=false`; **nunca se anuncia como labios sincronizados**. El portal sigue funcionando sin estos archivos.

Los cinco controles de autorización requeridos son `rightsVerified`, `consentVerified`, `voiceAuthorized`, `scriptChecked` y `speaksAllTenHeadlines` junto a `source` no vacío. Si no hay intro o no hay consentimiento, falla de forma segura; nunca marca como publicado un MP4 no generado.

Pruebas en CI: 10 noticias editoriales, fuentes HTTPS, no imágenes ficticias presentadas como fotografías, TTS nativo y 10 láminas para Instagram + recurso de portada.
