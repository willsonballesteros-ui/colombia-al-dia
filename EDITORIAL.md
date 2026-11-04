# ORBIUNO · Colombia al Día — Directiva editorial y técnica vigente

**4 de noviembre de 2026. Sustituye la directriz anterior de textos largos y prohibición absoluta de presentadoras digitales.**

## Identidad y noticias

Noticiero de Colombia y el mundo: información seria, sobria, comprensible y breve. Cada una de las diez noticias debe llevar **titular**, **resumen ejecutivo de hasta dos líneas visibles** y **fuente original con enlace HTTPS**. El campo `executiveSummary` almacena esa síntesis (idealmente 100 a 145 caracteres). No publicar en la interfaz ni en las láminas las etiquetas «Qué pasó», «Por qué importa» o «Qué sigue». El archivo histórico puede conservar observaciones internas, pero no se muestran al público.

Priorizar economía, tecnología/IA, infraestructura, seguridad y panorama global, con hechos contrastados e incertidumbre atribuida. No elevar RSS `source_only` a noticia `editorial_verified` sin comprobación.

## Sitio web

- Encabezado mínimo «ORBIUNO | Colombia al Día» y texto corto, sin cajas de fecha ni avisos llamativos.
- Tarjetas de lectura rápida, con máximo dos líneas visibles de `executiveSummary`, fuente original clicable y audio gratuito del navegador.
- TTS de `window.speechSynthesis` mediante clic expreso del lector; ▶️ Escuchar resumen / Pausar / Reanudar / Detener. No se afirma una voz natural idéntica en todos los dispositivos.
- Las advertencias de atribución y metodología se mantienen en el pie, no sobre los titulares.

## Imágenes reales y marcas

Para noticias, priorizar fotografía real con derechos de reproducción confirmados. Campos: `imageUrl`, `imageType` (`official_photo`, `licensed_press_photo`, `official_document`), `imageCredit`, `imageLicense`, `imageRightsVerified=true`, `imageSourceUrl`. Sin esos datos, usar bloque tipográfico con **nombre de la fuente**, no simular una foto ni inventar el logotipo de Reuters, EFE, etc. La presentadora virtual solicitada debe identificarse y tener derechos de uso y autorización de voz verificables; nunca afirmar que una foto inventada documenta un hecho.

## Dos formatos sociales diferentes

- **Reel vertical:** once escenas de video: **presentadora virtual femenina de apariencia natural** en escena inicial, narrando los diez titulares en español claro, seguida de diez láminas. Debe existir y verificarse el MP4 de la presentadora y su autorización; no sustituir por una foto estática como si hablara.
- **Carrusel Instagram:** máximo **diez** láminas de noticias (límite de la plataforma). El recurso adicional `portada.png` sirve para portada de Reel, previsualización o historia, **NO como una undécima foto en el carrusel**. Así se conservan las diez noticias sin incumplir Instagram.
- Cada lámina: fuente visible, titular dominante y síntesis de dos o tres líneas en móvil. No simular botones clicables sobre las imágenes. Fuente y detalle verdaderamente clicables desde la web; los stickers de enlace, encuesta y cuestionario son nativos de historias y pueden requerir publicación manual.

## Automatización y comprobaciones

La rutina editorial conserva las franjas **08:00, 12:00 y 18:00** en `America/Bogota`. GitHub Actions prepara titulares a las 07:30/11:30/17:30 y genera recursos; las comprobaciones periodísticas y la publicación requieren una herramienta conectada que opere en ese momento.

GitHub Actions **no dispone de credenciales de publicación Metricool**. Según la documentación oficial vigente, la API directa de Metricool requiere Advanced/Custom; no activar un plan de pago sin autorización. La conexión de Metricool en ChatGPT puede crear o cambiar posts mediante acciones autorizadas; verificar **PUBLISHED y URL real**, y detectar duplicados. No prometer autonomía 100 % ni videos no creados. Si la presentadora está pendiente, continuar con noticias web y carrusel textual sin presentar Reel ficticio como realizado.

## Pipeline audiovisual

`scripts/assemble_reel.py` y `.github/workflows/reel-presentadora.yml` solo generan Reel cuando existe un `media/AAAA-MM-DD/presentadora-intro.mp4` con audio, derechos aprobados y su manifest `presentadora-intro.json`. Los cinco controles de autorización requeridos son `rightsVerified`, `consentVerified`, `voiceAuthorized`, `scriptChecked` y `speaksAllTenHeadlines` junto a `source` no vacío. Si no hay intro o no hay consentimiento, falla de forma segura; nunca marca como publicado un MP4 no generado.

Pruebas en CI: 10 noticias editoriales, fuentes HTTPS, no imágenes ficticias presentadas como fotografías, TTS nativo y 10 láminas para Instagram + recurso de portada.
