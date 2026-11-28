# Distribución de TikTok y selección orgánica

Requisitos: Node 24, FFmpeg (ffprobe y ffmpeg), conexión HTTPS y
un directorio privado con almacenamiento persistente local. Ejecutar desde
la raíz del repositorio. El MP4 procede de Pages y conserva los bytes originales.
El módulo limita el archivo a 25 MiB, conforme al límite de Pages.

```sh
node --test integrations/tiktok/*.test.mjs
node integrations/tiktok/distribution.mjs validate /ruta/persistente/distribution.sqlite manifiesto.json ID_DE_CUENTA_VERIFICADO
node integrations/tiktok/distribution.mjs get /ruta/persistente/distribution.sqlite MARCA-AAAA-MM-DD-HHMM
node integrations/tiktok/distribution.mjs advance /ruta/persistente/distribution.sqlite MARCA-AAAA-MM-DD-HHMM VERSION ESTADO evidencia.json
node integrations/tiktok/distribution.mjs rank reels.json
node integrations/tiktok/distribution.mjs promotion historial.json
```

El manifiesto operativo requiere brand, editionId, localTime (ISO 8601, UTC−5),
videoUrl, size, duration en segundos, mediaSha256, caption, sources, credits,
accountId, approved, approvedAt, rightsConfirmed y rights
(status cleared, platform tiktok, evidence). Las fuentes y créditos son
listas de texto. La cuenta debe provenir de la lectura OAuth autorizada
de vidIQ. La evidencia JSON de cada transición incluye reference y los IDs
que correspondan. Los JSON verified-* son evidencia histórica de descarga y
plataformas. No son solicitudes de publicación.

Los operadores deben usar el mismo archivo SQLite en el mismo equipo.
No copiarlo a ejecuciones paralelas o a almacenamiento efímero. Mantener sus
archivos WAL en el mismo volumen y utilizar la API de respaldo de SQLite.
Si falta el volumen, detener los envíos y reconciliar antes de restaurar.

Antes de importar comprobar historial vidIQ y permisos de fotos, logos,
música y locución para TikTok. Usar vidIQ OAuth y aprobar la revisión exacta.
Para approved, guardar ownerApproved. Para submitted, guardar accountId,
canPublish e historyChecked. Solo el proceso cuyo cambio approved → submitted
tiene éxito puede hacer la llamada externa. Si se interrumpe, consultar el
postId y la publicationId ya registrados. En caso incierto, registrar
reconciliation_required y consultar la plataforma. El estado completed
documenta entrega. Registrar aparte la comprobación de visibilidad pública.
Este módulo no llama al publicador ni simula aprobaciones.

Para rank, entregar una lista con publishedAt, relevant, alreadyPromoted y
las métricas opcionales reach, views, shares, saves e interactions. Comparar
piezas de la misma marca y plataforma. Para promotion, entregar complete
y promotions con id, publishedAt y verified. Un historial incompleto impide
autorizar una promoción.

Activación reversible: usar un único operador con acceso al volumen y vidIQ.
No programar nuevos cron ni agregar secretos. Para detenerlo, dejar de ejecutar
el módulo y conservar la base con las evidencias. Si el código llega a main,
se puede revertir el commit de distribución sin tocar publicaciones o archivos
editoriales. La automatización de ChatGPT debe comprobar que puede operar sobre
el mismo registro antes de habilitar envíos.
