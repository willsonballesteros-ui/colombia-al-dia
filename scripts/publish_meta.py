#!/usr/bin/env python3
"""Publicación de una edición en Instagram con la API oficial de Meta (Reel + Story).

Documentación consultada el 2026-11-07: developers.facebook.com/documentation/instagram-platform/content-publishing
 - Flujo de dos pasos: POST /{ig-id}/media (contenedor) -> estado -> POST /{ig-id}/media_publish.
 - Reel: media_type=REELS, video_url pública, share_to_feed=true (los videos de feed se comparten como reels).
 - Story en video: media_type=STORIES (solo cuentas profesionales/business).
Credenciales SOLO por entorno: IG_USER_ID, IG_ACCESS_TOKEN (nunca se imprimen). Sin ellas: salida 2, no éxito.
Nunca se declara éxito sin id de medio devuelto por media_publish y comprobado con un GET posterior.
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbiuno_edition as oe  # noqa: E402

HOST = os.environ.get("GRAPH_HOST", "https://graph.facebook.com")
VERSION = os.environ.get("GRAPH_VERSION", "v26.0")  # vigente en la documentación consultada; verificar
TRANSIENT = {429, 500, 502, 503, 504}


class MetaError(Exception):
    pass


def redact(text, token):
    return text.replace(token, "***") if token else text


class Graph:
    def __init__(self, user_id, token, sleep=time.sleep):
        self.uid, self.token, self.sleep = user_id, token, sleep

    def call(self, method, path, params=None, retries=3):
        url = f"{HOST}/{VERSION}/{path}"
        data = None
        if method == "GET" and params:
            url += "?" + urllib.parse.urlencode(params)
        elif params:
            data = urllib.parse.urlencode(params).encode()
        for attempt in range(retries + 1):
            req = urllib.request.Request(url, data=data, method=method,
                                         headers={"Authorization": f"Bearer {self.token}"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                body = redact(e.read().decode(errors="replace"), self.token)
                if e.code in TRANSIENT and attempt < retries:
                    self.sleep(2 ** attempt * 2)
                    continue
                raise MetaError(f"HTTP {e.code} en {method} {path}: {body[:600]}")
            except (urllib.error.URLError, TimeoutError) as e:
                if attempt < retries:
                    self.sleep(2 ** attempt * 2)
                    continue
                raise MetaError(f"Red en {method} {path}: {e}")


def wait_ready(g, container_id, timeout=900, interval=10):
    t0 = time.time()
    while True:
        s = g.call("GET", container_id, {"fields": "status_code,status"})
        code = s.get("status_code")
        if code == "FINISHED":
            return s
        if code in ("ERROR", "EXPIRED"):
            raise MetaError(f"Contenedor {container_id} en estado {code}: {s.get('status')}")
        if time.time() - t0 > timeout:
            raise MetaError(f"Contenedor {container_id} sin terminar tras {timeout}s (último: {code})")
        g.sleep(interval)


def find_by_marker(g, marker):
    r = g.call("GET", f"{g.uid}/media", {"fields": "id,caption,media_product_type,permalink,timestamp", "limit": 30})
    return next((m for m in r.get("data", []) if marker in (m.get("caption") or "")), None)


def publish_reel(g, video_url, caption, marker, wait=wait_ready):
    prior = find_by_marker(g, marker)
    if prior:  # idempotencia: la edición ya está publicada
        return {"status": "already_published", "id": prior["id"], "permalink": prior.get("permalink")}
    c = g.call("POST", f"{g.uid}/media", {"media_type": "REELS", "video_url": video_url,
                                          "caption": caption, "share_to_feed": "true"})["id"]
    wait(g, c)
    try:
        mid = g.call("POST", f"{g.uid}/media_publish", {"creation_id": c}, retries=0)["id"]
    except MetaError:
        prior = find_by_marker(g, marker)  # fallo ambiguo: comprobar antes de reintentar
        if not prior:
            raise
        mid = prior["id"]
    v = g.call("GET", mid, {"fields": "id,media_product_type,permalink,timestamp"})
    if not v.get("permalink"):
        raise MetaError(f"Reel {mid} publicado pero sin permalink verificable")
    return {"status": "published", "id": mid, "container": c, "permalink": v["permalink"],
            "timestamp": v.get("timestamp"), "media_product_type": v.get("media_product_type")}


def publish_story(g, video_url, wait=wait_ready):
    c = g.call("POST", f"{g.uid}/media", {"media_type": "STORIES", "video_url": video_url})["id"]
    wait(g, c)
    mid = g.call("POST", f"{g.uid}/media_publish", {"creation_id": c}, retries=0)["id"]
    v = g.call("GET", mid, {"fields": "id,media_product_type,timestamp"})
    if v.get("id") != mid:
        raise MetaError(f"Story {mid} no verificable")
    return {"status": "published", "id": mid, "container": c, "timestamp": v.get("timestamp"),
            "media_product_type": v.get("media_product_type")}


def check_public_video(url, expect_bytes, opener=urllib.request.urlopen):
    req = urllib.request.Request(url, method="HEAD")
    with opener(req, timeout=30) as r:
        ctype, length = r.headers.get("Content-Type", ""), int(r.headers.get("Content-Length", "0"))
    if not ctype.startswith("video/"):
        raise MetaError(f"{url} responde Content-Type {ctype!r}, no video")
    if length != expect_bytes:
        raise MetaError(f"{url}: {length} bytes publicados != {expect_bytes} del manifiesto")


def http_get_text(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Cache-Control": "no-cache"}), timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _norm(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip().lower()


def check_web_first(edition_id, fetch=http_get_text, base=None):
    """Regla WEB PRIMERO: las 4 noticias deben estar ya publicadas en la web con reportaje propio y fuente.

    Devuelve la lista de problemas (vacía si todo está en línea). Descarga el noticias.json y el index.html
    PÚBLICOS: un commit exitoso no demuestra despliegue.
    """
    base = base or oe.WEB_BASE
    try:
        data = json.loads(fetch(f"{base}/noticias.json"))
        page = fetch(f"{base}/")
        page = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", "", page, flags=re.I | re.S)
        headings = {
            _norm(re.sub(r"<[^>]*>", "", title))
            for title in re.findall(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]\s*>", page, re.I | re.S)
        }
    except Exception as e:  # noqa: BLE001
        return [f"no se pudo leer la web pública: {e}"]
    try:
        _, news = oe.validate_edition(data, edition_id, require_approved=True)
    except oe.EditionError as e:
        return [f"web pública: {p}" for p in e.problems]
    problems = []
    for n in news:
        problems += oe.web_ready(n)
        if _norm(n["title"]) not in headings:
            problems.append(f"{n['id']}: el titular no aparece en la portada pública")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True)
    ap.add_argument("--media-root", default="media")
    ap.add_argument("--skip-story", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="valida todo sin llamar a Meta")
    a = ap.parse_args(argv)
    if not oe.EDITION_RE.fullmatch(a.edition):
        ap.error("identificador de edición inválido")
    folder = Path(a.media_root) / a.edition
    try:
        man = json.loads((folder / "reel-manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"No se pudo leer el manifiesto: {exc}", file=sys.stderr)
        return 2
    log = {"editionId": a.edition, "reel": None, "story": None,
           "feed": {"status": "pending", "note": "Reel con share_to_feed=true; comprobar en la cuadrícula del perfil"}}
    errors = []
    if not man.get("publishable"):
        print("Manifiesto no publicable (checks fallidos, sin aprobación humana o modo prueba).", file=sys.stderr)
        return 2
    uid, token = os.environ.get("IG_USER_ID"), os.environ.get("IG_ACCESS_TOKEN")
    if not a.dry_run and not (uid and token):
        print("Faltan IG_USER_ID / IG_ACCESS_TOKEN: NO se publicó nada (salida 2).", file=sys.stderr)
        return 2
    try:
        check_public_video(man["publicUrl"], man["bytes"])
        if not a.skip_story:
            check_public_video(man["story"]["publicUrl"], man["story"]["bytes"])
    except Exception as e:  # noqa: BLE001
        print(f"Medio no accesible públicamente: {e}", file=sys.stderr)
        return 3
    web = check_web_first(a.edition)
    if web:
        print("BLOQUEADO por la regla WEB PRIMERO:\n- " + "\n- ".join(web), file=sys.stderr)
        return 4
    if a.dry_run:
        print(json.dumps({"dry_run": True, "publicUrl": man["publicUrl"], "ok": True}))
        return 0
    g = Graph(uid, token)
    marker = f"[ORB-{a.edition}]"
    try:
        log["reel"] = publish_reel(g, man["publicUrl"], man["caption"], marker)
        log["feed"] = {"status": "reel_published_with_share_to_feed", "id": log["reel"]["id"],
                       "note": "Visibilidad en cuadrícula: confirmar visualmente"}
    except MetaError as e:
        log["reel"] = {"status": "failed", "error": redact(str(e), token)}
        errors.append("reel")
    if not a.skip_story and not errors:
        try:
            log["story"] = publish_story(g, man["story"]["publicUrl"])
        except MetaError as e:
            log["story"] = {"status": "failed", "error": redact(str(e), token)}
            errors.append("story")
    (folder / "publish-log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(log, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
