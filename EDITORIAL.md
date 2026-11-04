# Directriz editorial obligatoria — Colombia al Día

**Vigencia: 4 de noviembre de 2026.** Estas reglas sustituyen las instrucciones anteriores de presentadoras virtuales, avatares, lip-sync y dibujos inventados.

## 1. Identidad

Medio serio, elegante, directo y útil para la audiencia. Evitar dramatización, exageración, apodos, presunción de culpabilidad, frases clickbait y afirmaciones sin respaldo. El sitio oficial es https://colombia-al-dia.pages.dev/ y el canal operativo de Instagram es @resumen.noticias. El nombre de visualización del perfil se cambia solo cuando la plataforma lo permita y se verifique; no declarar que se cambió su usuario.

## 2. Verificación de noticias

Elegir diez noticias relevantes de Colombia y el mundo, priorizando economía, infraestructura, tecnología/IA, seguridad, políticas públicas, riesgos y hechos que afecten directamente a los ciudadanos. Para cada una conservar:

1. **Titular** claro y factual.
2. **Qué pasó:** síntesis propia de una o dos frases.
3. **Por qué importa:** impacto directo verificable.
4. **Qué sigue:** hechos previstos, actuaciones o incertidumbre; no asegurar resultados futuros.
5. **Fuente original:** nombre, fecha, enlace HTTPS directo. Agregar segunda fuente cuando sea posible.

Diferenciar planes de medidas aprobadas, declaraciones de hechos corroborados, denuncias de condenas, rumores de información oficial y ediciones históricas de las últimas noticias. Las entradas RSS `source_only` nunca son `editorial_verified` automáticamente.

## 3. Fotografías y licencias

Solo publicar fotografías de prensa permitidas o contenido institucional real, identificado con créditos y URL original. Verificar derechos de reproducción además de atribuir la fuente. **No** usar capturas de pantallas de periódicos como alternativa para eludir sus derechos. Sin permiso o imagen válida, usar texto bien compuesto, sin dibujos, pictogramas que pretendan representar el hecho, caras generadas ni imágenes sintéticas.

El formato de datos opcional requiere `imageUrl`, `imageType` (`official_photo`, `licensed_press_photo` o `official_document`), `imageSourceUrl`, `imageCredit`, `imageLicense` e `imageRightsVerified=true`. La bandera de derechos es una declaración **manual responsable**, no un valor inferido del URL.

## 4. Web

Header limpio, titulares, resumen de dos líneas, un botón que abre la fuente, un botón local de escucha del resumen y bloques de detalle contraídos. El botón de voz utiliza `speechSynthesis` del navegador y habla con la voz disponible en el dispositivo, sin reproducir el audio del periódico. No colocar textos técnicos prominentes ni banners falsamente interactivos; conservar metodologías en el pie de página. Si no hay foto autorizada, omitirla por completo (no colocar placeholder ilustrado).

## 5. Instagram y material multimedia

Crear un carrusel con **12 láminas**: portada que invite a participar, diez noticias individuales y cierre con el sitio y perfil. Cada noticia incluye titular, qué pasó, por qué importa, qué sigue, la fuente y la URL de la página que contiene las fuentes originales. Se conserva contraste alto, azul noche, blanco y detalles dorados discretos. Las láminas contienen únicamente texto o fotografías autorizadas.

**Stickers:** para Historias, sugerir un sticker de enlace hacia https://colombia-al-dia.pages.dev/, encuesta o pregunta. El editor debe agregarlo desde el editor nativo de Instagram y verificar su funcionamiento. No afirmar que un carrusel publicado por Metricool incluye stickers ni presentar un dibujo de botón como si se pudiera tocar. El enlace en el pie de una imagen tampoco es clicable.

## 6. Publicación y comprobación

Conservar las franjas 08:00, 12:00 y 18:00 de Bogotá. Preparar antes, contrastar fuentes y comprobar duplicados. Crear/progamar con Metricool solo cuando hay material válido y no se duplica el tema; exigir respuesta `PUBLISHED` y URL real antes de informar como publicado. La cuenta puede conservar contenidos históricos de otro estilo: eso no autoriza nuevas publicaciones con avatares. No gastar en APIs externas sin autorización.

## 7. Control de calidad

Mantener pruebas de que las fuentes son HTTPS, que las diez noticias son distintas, que ningún `imageUrl` de ilustración entra a producción, que las láminas son 1080×1350 y que el carrusel es de 12 piezas. Una salida fallida no puede anunciarse como publicación exitosa.
