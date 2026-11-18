#!/usr/bin/env python3
"""Genera el sitio estático de una edición DESDE el manifiesto (misma fuente que el carrusel).

out/index.html, out/noticia/<id>/index.html, out/web-manifest.json (copia byte a byte del
manifiesto), out/player.js y los recursos con las mismas rutas relativas que el manifiesto.
El audio solo inicia con un toque del usuario (requisito de Safari/iOS).
"""
import argparse
import html
import json
import shutil
import sys
from pathlib import Path

SPEEDS = [1, 1.25, 1.5, 2]
DEFAULT_SPEED = 1.25

PLAYER_JS = r"""
(function () {
  var SPEEDS = [1, 1.25, 1.5, 2], current = null;
  function rate(a, r) { a.playbackRate = r; try { a.preservesPitch = true; } catch (e) {} }
  document.querySelectorAll('[data-story]').forEach(function (box) {
    var btn = box.querySelector('.listen'), a = box.querySelector('audio'),
        msg = box.querySelector('.audio-msg'), speed = parseFloat(box.dataset.speed || '1.25');
    if (!btn || !a) return;
    a.preload = 'none';
    ['loadedmetadata', 'play'].forEach(function (ev) { a.addEventListener(ev, function () { rate(a, speed); }); });
    a.addEventListener('error', function () { msg.textContent = 'No se pudo cargar el audio.'; btn.setAttribute('aria-pressed', 'false'); });
    a.addEventListener('ended', function () { btn.textContent = 'Escuchar noticia'; btn.setAttribute('aria-pressed', 'false'); });
    btn.addEventListener('click', function () {
      msg.textContent = '';
      if (a.paused) {
        if (current && current !== a) current.pause();
        current = a; rate(a, speed);
        var p = a.play();
        if (p && p.catch) p.catch(function () { msg.textContent = 'No se pudo reproducir el audio.'; });
        btn.textContent = 'Pausar'; btn.setAttribute('aria-pressed', 'true');
      } else {
        a.pause(); btn.textContent = 'Reanudar'; btn.setAttribute('aria-pressed', 'false');
      }
    });
    box.querySelectorAll('.speed').forEach(function (b) {
      b.addEventListener('click', function () {
        speed = parseFloat(b.dataset.rate); rate(a, speed);
        box.querySelectorAll('.speed').forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      });
    });
  });
})();
"""

CSS = """
:root{--navy:#091b47;--orange:#ff6f0f;--ink:#0b1b3f;--bg:#f4f6fb}
*{box-sizing:border-box}body{margin:0;font:17px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--ink)}
header{background:var(--navy);color:#fff;padding:18px 16px}header b{font-size:26px;letter-spacing:.5px}
header span{display:block;color:#ffc9a3;font-size:14px}
main{max-width:720px;margin:0 auto;padding:12px}
article{background:#fff;border-radius:14px;overflow:hidden;margin:16px 0;box-shadow:0 2px 8px #0b1b3f22}
article img.foto{display:block;width:100%;height:auto}
.pad{padding:14px 16px 18px}.logo{height:38px;width:auto;max-width:60%}
h2{font-size:22px;line-height:1.25;margin:.4em 0}h1{font-size:26px;line-height:1.2}
.credit{font-size:13px;color:#51608a}.row{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px;align-items:center}
button,a.btn{min-height:44px;padding:0 16px;border-radius:22px;border:2px solid var(--navy);background:#fff;color:var(--navy);font:600 16px system-ui;text-decoration:none;display:inline-flex;align-items:center}
button.listen{background:var(--orange);border-color:var(--orange);color:#fff}
button[aria-pressed=true].speed{background:var(--navy);color:#fff}
.audio-msg{color:#b00020;font-size:14px;min-height:1em}
@media (prefers-color-scheme:dark){:root{--bg:#0b1226;--ink:#e8edf8}article{background:#121c3a}button,a.btn{background:#121c3a;color:#fff;border-color:#5a79c8}}
"""


def _fecha(iso):
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
             "septiembre", "octubre", "noviembre", "diciembre"]
    y, m, d = iso.split("-")
    return f"{int(d)} de {meses[int(m) - 1]} de {y}"


def _hora(h):
    hh, mm = map(int, h.split(":"))
    return f"{hh % 12 or 12}:{mm:02d} {'a. m.' if hh < 12 else 'p. m.'}"


def _story(n, base, full):
    e = html.escape
    sp = "".join(f'<button class="speed" data-rate="{r}" aria-pressed="{str(r == DEFAULT_SPEED).lower()}">{str(r).replace(".", ",")}×</button>' for r in SPEEDS)
    head = f'<h1>{e(n["titular"])}</h1>' if full else f'<h2><a href="{base}noticia/{e(n["id"])}/">{e(n["titular"])}</a></h2>'
    more = "" if full else f'<a class="btn" href="{base}noticia/{e(n["id"])}/">Abrir noticia</a>'
    return f'''<article data-story="{e(n["id"])}" data-speed="{DEFAULT_SPEED}">
<img class="foto" src="{base}{e(n["foto"]["archivo"])}" alt="Fotografía de la noticia: {e(n["titular"])}" loading="lazy">
<div class="pad"><img class="logo" src="{base}{e(n["logo_fuente"])}" alt="Logotipo de {e(n["fuente"])}">
{head}<p>{e(n["resumen"])}</p>
<p class="credit">Fuente: {e(n["fuente"])} · {e(n["fecha"])} · Foto: {e(n["foto"]["credito"])}</p>
<div class="row"><button class="listen" aria-pressed="false">Escuchar noticia</button>{sp}</div>
<audio src="{base}{e(n["audio"]["archivo"])}" preload="none"></audio><div class="audio-msg" role="status"></div>
<div class="row">{more}<a class="btn" href="{e(n["url_fuente"])}" rel="noopener noreferrer" target="_blank">Leer en {e(n["fuente"])}</a></div></div></article>'''


def _page(title, body, base, manifest):
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<header><b>ORBIUNO</b><span>Colombia y el mundo al día · {_fecha(manifest["fecha"])} · {_hora(manifest["hora"])}</span></header>
<main>{body}</main><script src="{base}player.js"></script></body></html>'''


def build_site(edition, out):
    edition, out = Path(edition), Path(out)
    mf = edition / "manifest.json"
    manifest = json.loads(mf.read_text(encoding="utf-8"))
    if len(manifest["noticias"]) != 5:
        raise ValueError("la web exige cinco noticias")
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for n in manifest["noticias"]:
        for rel in (n["foto"]["archivo"], n["logo_fuente"], n["audio"]["archivo"]):
            src = (edition / rel).resolve()
            if not src.is_relative_to(edition.resolve()) or not src.is_file():
                raise ValueError("recurso inválido: " + rel)
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, out / rel)
    shutil.copy2(mf, out / "web-manifest.json")
    (out / "player.js").write_text(PLAYER_JS, encoding="utf-8")
    body = "".join(_story(n, "", False) for n in manifest["noticias"])
    (out / "index.html").write_text(_page("ORBIUNO · Cinco noticias", body, "", manifest), encoding="utf-8")
    for n in manifest["noticias"]:
        d = out / "noticia" / n["id"]
        d.mkdir(parents=True)
        body = _story(n, "../../", True) + '<p><a class="btn" href="../../">← Volver a las cinco noticias</a></p>'
        (d / "index.html").write_text(_page(n["titular"], body, "../../", manifest), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", type=Path)
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    try:
        print("OK", build_site(a.edition, a.out))
    except Exception as exc:
        print("BLOQUEO:", exc, file=sys.stderr)
        sys.exit(1)
