/* ORBIUNO — fotografía en pantalla, sin redirecciones al repositorio ni a Drive.
   La fuente periodística es un enlace independiente. */
(() => {
  'use strict';
  let lastTrigger = null;
  let overlay = null;
  const css = `
    .orbiuno-photo-viewer {
      position: fixed; inset: 0; z-index: 2147483600;
      display: flex; align-items: center; justify-content: center;
      padding: max(16px, env(safe-area-inset-top)) 16px max(16px, env(safe-area-inset-bottom));
      background: rgba(0, 0, 0, .93); color: white;
      overscroll-behavior: contain;
    }
    .orbiuno-photo-viewer[hidden] { display: none !important; }
    .orbiuno-photo-viewer__content {
      position: relative; max-width: min(95vw, 1100px); max-height: 94vh;
      display: flex; flex-direction: column; align-items: center; gap: 12px;
    }
    .orbiuno-photo-viewer__image {
      display: block; object-fit: contain; max-width: 100%;
      max-height: min(80vh, 850px); height: auto; width: auto;
      border-radius: 6px;
    }
    .orbiuno-photo-viewer__close {
      position: absolute; top: 4px; right: 4px; z-index: 1;
      border: 0; border-radius: 999px; padding: 9px 14px;
      background: #fff; color: #111; font-size: 22px; cursor: pointer;
    }
    .orbiuno-photo-viewer__caption {
      margin: 0; font: 14px/1.4 system-ui, sans-serif;
      text-align: center; max-width: 80ch; color: #eee;
    }
    .orbiuno-photo-viewer__source {
      color: #cde9ff; font: 14px system-ui, sans-serif;
    }
  `;
  const makeViewer = () => {
    if (overlay) return overlay;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    overlay = document.createElement('section');
    overlay.className = 'orbiuno-photo-viewer';
    overlay.hidden = true;
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', 'Fotografía de la noticia');
    overlay.innerHTML =
      '<div class="orbiuno-photo-viewer__content">' +
      '<button type="button" class="orbiuno-photo-viewer__close" aria-label="Cerrar fotografía">×</button>' +
      '<img class="orbiuno-photo-viewer__image" alt="">' +
      '<p class="orbiuno-photo-viewer__caption"></p>' +
      '<a class="orbiuno-photo-viewer__source" target="_blank" rel="noopener noreferrer" hidden>Ver fuente original</a>' +
      '</div>';
    document.body.appendChild(overlay);
    overlay.querySelector('.orbiuno-photo-viewer__close').addEventListener('click', close);
    overlay.addEventListener('click', ev => {
      if (ev.target === overlay) close();
    });
    return overlay;
  };
  const originalSource = card => {
    const a = card?.querySelector('.source-thumbnail a.source');
    if (!a) return null;
    try {
      const parsed = new URL(a.href, document.location.href);
      const host = parsed.hostname.toLowerCase();
      if (parsed.protocol !== 'https:' || host === 'drive.google.com' ||
          host === 'docs.google.com' || host.endsWith('.drive.google.com')) {
        return null;
      }
      return parsed.href;
    } catch { return null; }
  };
  function close() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    overlay.querySelector('img').removeAttribute('src');
    document.body.style.overflow = overlay.dataset.oldOverflow || '';
    if (lastTrigger?.isConnected) lastTrigger.focus({preventScroll:true});
    lastTrigger = null;
  }
  function open(trigger) {
    const photo = trigger.querySelector('img');
    if (!photo) return;
    const src = photo.currentSrc || photo.getAttribute('src');
    if (!src) return;
    const box = makeViewer();
    lastTrigger = trigger;
    box.querySelector('img').src = src;
    box.querySelector('img').alt = photo.alt || 'Fotografía de la noticia';
    const caption = trigger.closest('figure')?.querySelector('figcaption');
    box.querySelector('.orbiuno-photo-viewer__caption').textContent =
      caption?.textContent?.trim() || photo.alt || '';
    const url = originalSource(trigger.closest('article'));
    const source = box.querySelector('.orbiuno-photo-viewer__source');
    source.hidden = !url;
    if (url) source.href = url; else source.removeAttribute('href');
    box.dataset.oldOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    box.hidden = false;
    box.querySelector('.orbiuno-photo-viewer__close').focus({preventScroll:true});
  }
  // Capturar antes de manejadores antiguos para impedir cualquier desvío.
  document.addEventListener('click', ev => {
    const button = ev.target.closest?.('button.photo-open');
    if (button) {
      ev.preventDefault();
      ev.stopImmediatePropagation();
      open(button);
    }
  }, true);
  document.addEventListener('keydown', ev => {
    if (ev.key === 'Escape' && overlay && !overlay.hidden) {
      ev.preventDefault(); close();
    }
  });
})();