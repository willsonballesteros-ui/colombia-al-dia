#!/usr/bin/env python3
"""ORBIUNO: publicación binaria reanudable adaptada del publicador verificado de MyCar.

Consume exclusivamente un MP4 aprobado de un artefacto de GitHub Actions.
Nunca utiliza credenciales de MyCar ni publica sin --publish.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

GRAPH = "https://graph.facebook.com/v27.0"
ACCOUNT = "resumen.noticias"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for b in iter(lambda: fp.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def request(method, url, token, fields=None):
    if method == "GET" and fields:
        url += "?" + urllib.parse.urlencode(fields)
    data = urllib.parse.urlencode(fields or {}).encode() if method == "POST" else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=55) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError("Meta " + method + ": HTTP " + str(e.code)) from None
    except (urllib.error.URLError, ValueError, TimeoutError) as e:
        raise RuntimeError("Meta: respuesta no valida (" + type(e).__name__ + ")") from None


def permalink_ok(media):
    u = urllib.parse.urlsplit(media.get("permalink", ""))
    return (str(media.get("id", "")).isdigit()
            and media.get("media_product_type") == "REELS"
            and u.scheme == "https"
            and u.hostname in ("instagram.com", "www.instagram.com")
            and u.path.startswith(("/reel/", "/p/")))


def validate_manifest(p, key, digest):
    if not isinstance(p, dict):
        raise RuntimeError("Manifiesto invalido")
    if p.get("edition_key") != key or p.get("sha256") != digest:
        raise RuntimeError("Edicion o huella no coinciden")
    if p.get("approved_for_production") is not True:
        raise RuntimeError("Edicion sin aprobacion de produccion")
    if not all(p.get(k) is True for k in (
        "editorial_approved", "rights_verified", "audio_verified",
        "web_sync_verified", "final_review_approved")):
        raise RuntimeError("Falta una aprobacion obligatoria")
    news = p.get("news")
    if not isinstance(news, list) or len(news) != 4:
        raise RuntimeError("El Reel debe contener cuatro noticias")
    if len({str(n.get("id", "")) for n in news}) != 4:
        raise RuntimeError("IDs faltantes o duplicados")
    if not all(str(n.get("source_url", "")).startswith("https://")
               and str(n.get("web_url", "")).startswith("https://colombia-al-dia.pages.dev/")
               for n in news):
        raise RuntimeError("Fuentes o fichas web incompletas")
    caption = p.get("caption", "").strip()
    if not caption or len(caption) > 2100:
        raise RuntimeError("Caption vacio o demasiado largo")
    return caption


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--edition-key", required=True)
    ap.add_argument("--expected-sha", required=True)
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    if not re.fullmatch(r"ORBIUNO-20\d{2}-\d{2}-\d{2}-(0800|1200|1800)", args.edition_key):
        raise RuntimeError("Identificador invalido")
    target_date = args.edition_key[8:18]
    if target_date != datetime.now(ZoneInfo("America/Bogota")).date().isoformat():
        raise RuntimeError("No publicar ediciones de otra fecha")
    if not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha):
        raise RuntimeError("SHA256 incorrecto")
    directory = Path(args.dir).resolve()
    path = directory / "reel.mp4"
    if not path.is_file() or path.stat().st_size < 100000:
        raise RuntimeError("MP4 ausente o incompleto")
    digest = sha256(path)
    if digest != args.expected_sha:
        raise RuntimeError("SHA256 del MP4 no coincide con el aprobado")
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=30, check=True)
    technical = json.loads(probe.stdout)
    streams = technical.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    seconds = float(technical.get("format", {}).get("duration") or 0)
    if (video.get("codec_name") != "h264" or audio.get("codec_name") != "aac"
            or video.get("width") != 1080 or video.get("height") != 1920
            or not 30 <= seconds <= 90):
        raise RuntimeError("MP4 no cumple H.264/AAC 1080x1920 y 30-90 segundos")
    p = json.loads((directory / "publish_ready.json").read_text(encoding="utf-8"))
    caption = validate_manifest(p, args.edition_key, digest)
    token = os.environ.get("ORBIUNO_IG_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("ORBIUNO_IG_USER_ID", "").strip()
    if not token or not user_id or not user_id.isdigit():
        raise RuntimeError("Faltan secretos propios de ORBIUNO (token y user ID)")
    def graph(method, endpoint, fields=None):
        return request(method, GRAPH + "/" + endpoint, token, fields)
    profile = graph("GET", user_id, {"fields": "id,username"})
    if str(profile.get("id")) != user_id or profile.get("username", "").lower() != ACCOUNT:
        raise RuntimeError("Token no autorizado para @resumen.noticias")
    marker = "[" + args.edition_key + "]"
    caption = caption + "\n\n" + marker
    media = graph("GET", user_id + "/media",
                  {"fields": "id,caption,permalink,media_product_type", "limit": "100"})
    for item in media.get("data", []):
        if marker in (item.get("caption") or ""):
            if not permalink_ok(item):
                item = graph("GET", str(item["id"]),
                             {"fields": "id,caption,permalink,media_product_type"})
            if not permalink_ok(item):
                raise RuntimeError("Publicacion previa sin permalink verificable")
            print(json.dumps({"state": "ALREADY_PUBLISHED", "id": item["id"],
                              "permalink": item["permalink"]}))
            return
    if not args.publish:
        print(json.dumps({"state": "DRY_RUN_OK", "account": ACCOUNT,
                          "sha256": digest, "edition": args.edition_key}))
        return
    container = graph("POST", user_id + "/media",
                      {"media_type": "REELS", "upload_type": "resumable",
                       "share_to_feed": "true", "caption": caption})
    cid = str(container.get("id", ""))
    url = urllib.parse.urlsplit(container.get("uri", ""))
    if not (cid.isdigit() and url.scheme == "https" and url.hostname == "rupload.facebook.com"
            and url.path == "/ig-api-upload/v27.0/" + cid and not url.query):
        raise RuntimeError("URI de carga no autorizada")
    cfg = 'header = "Authorization: OAuth ' + token + '"\n'
    cp = subprocess.run(
        ["curl", "--silent", "--show-error", "--max-time", "120",
         "--config", "-", "--request", "POST",
         "--header", "offset: 0",
         "--header", "file_size: " + str(path.stat().st_size),
         "--header", "Content-Type: application/octet-stream",
         "--data-binary", "@" + str(path),
         "--write-out", "\n%{http_code}", url.geturl()],
        input=cfg, text=True, capture_output=True, timeout=140)
    body, _, status = cp.stdout.rpartition("\n")
    try:
        transfer = json.loads(body)
    except ValueError:
        transfer = {}
    if cp.returncode or not status.startswith("2") or transfer.get("success") is not True:
        raise RuntimeError("Subida binaria rechazada, HTTP " + status[-3:])
    for _ in range(30):
        s = graph("GET", cid, {"fields": "status_code"}).get("status_code")
        if s == "FINISHED":
            break
        if s != "IN_PROGRESS":
            raise RuntimeError("Meta no termino el procesamiento: " + str(s))
        time.sleep(10)
    else:
        raise RuntimeError("Meta no finalizo el procesamiento")
    published = graph("POST", user_id + "/media_publish", {"creation_id": cid})
    mid = str(published.get("id", ""))
    if not mid.isdigit():
        raise RuntimeError("Resultado ambiguo de Meta; NO reintentar sin reconciliacion")
    item = graph("GET", mid, {"fields": "id,permalink,media_product_type"})
    if str(item.get("id")) != mid or not permalink_ok(item):
        raise RuntimeError("ID publicado pero permalink aun no confirmado: " + mid)
    report = {"state": "PUBLISHED", "media_id": mid, "permalink": item["permalink"],
              "edition_key": args.edition_key, "sha256": digest}
    (directory / "publish_result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("REEL PUBLICADO Y VERIFICADO:", item["permalink"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print("PUBLICACION DETENIDA:", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
