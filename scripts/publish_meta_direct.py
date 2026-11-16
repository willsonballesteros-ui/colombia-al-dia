#!/usr/bin/env python3
"""ORBIUNO: publicador directo de un Reel mediante Instagram Login (Meta).

Credenciales únicamente desde GitHub Actions Secrets. Nunca imprime tokens.
La edición se identifica con edition_key para prevenir publicaciones repetidas.
"""
import argparse
import json
from pathlib import Path
import os
import re
import sys
import time
from datetime import datetime, date
from zoneinfo import ZoneInfo
import urllib.error
import urllib.parse
import urllib.request

HOST = "https://graph.instagram.com/v26.0"

def api(method, path, token, values=None):
    url = HOST + path
    payload = None
    if method == "GET":
        if values:
            url += "?" + urllib.parse.urlencode(values)
    else:
        payload = urllib.parse.urlencode(values or {}).encode()
    request = urllib.request.Request(
        url, data=payload, method=method,
        headers={"Authorization": "Bearer " + token}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        # Meta error details may help diagnosis, but must never expose credentials.
        details = {}
        try:
            details = json.loads(err.read(8192).decode("utf-8")).get("error", {})
        except (ValueError, UnicodeDecodeError, AttributeError):
            pass
        code = details.get("code")
        subcode = details.get("error_subcode")
        message = str(details.get("message", ""))[:400]
        # Redact access tokens and credential-like query strings from Meta messages.
        message = message.replace(token, "[REDACTED]")
        message = re.sub(r"(?i)(access_token|client_secret|appsecret_proof)\s*[=:]\s*[^\s&,]+", r"\1=[REDACTED]", message)
        message = re.sub(r"https?://\S+", "[URL_REDACTED]", message)
        summary = "Meta HTTP " + str(err.code) + " on " + path
        if code is not None:
            summary += " code=" + str(code)
        if subcode is not None:
            summary += " subcode=" + str(subcode)
        if message:
            summary += " message=" + message
        raise RuntimeError(summary) from None

def existing_media(user_id, token, marker):
    url = "/" + user_id + "/media"
    query = {"fields": "id,caption,permalink", "limit": "100"}
    for _ in range(5):
        result = api("GET", url, token, query)
        for item in result.get("data", []):
            if marker in (item.get("caption") or ""):
                return item
        nxt = result.get("paging", {}).get("next")
        if not nxt:
            break
        # Follow paging cursor only through the authorized Instagram host.
        parsed = urllib.parse.urlparse(nxt)
        if parsed.hostname != "graph.instagram.com":
            raise RuntimeError("Host de paginacion no permitido")
        url, query = parsed.path.replace("/v26.0", "", 1), dict(urllib.parse.parse_qsl(parsed.query))
        query.pop("access_token", None)
    return None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--edition-key", required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--allow-archive", action="store_true", help="Autorizar expresamente una edicion de hasta 7 dias de antiguedad")
    args = parser.parse_args()
    parsed = urllib.parse.urlparse(args.video_url)
    if parsed.scheme != "https" or not parsed.hostname:
        sys.exit("Se requiere video_url HTTPS publico")
    match = re.fullmatch(r"ORBIUNO-(\d{4}-\d{2}-\d{2})-(0800|1200|1800|1900|2100|2200)", args.edition_key)
    if not match:
        sys.exit("edition_key invalida: ORBIUNO-AAAA-MM-DD-HHMM")
    today = datetime.now(ZoneInfo("America/Bogota")).date()
    edition_day = date.fromisoformat(match.group(1))
    age = (today - edition_day).days
    if age < 0:
        sys.exit("Se bloquea una edicion futura")
    if age > 0 and (not args.allow_archive or age > 7):
        sys.exit("Edicion anterior: requiere --allow-archive y antiguedad maxima de 7 dias")
    # Fail closed: a generated video with source-only news is not editorially approved.
    if match.group(1) == "2026-11-15" and match.group(2) == "1900":
        manifest_path = Path(__file__).resolve().parents[1] / "media/2026-11-15/orbiuno_1900_dora_regenerado_manifest.json"
        if not manifest_path.is_file():
            sys.exit("Falta manifiesto verificable de la edicion")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("sourceOnly") is not False or manifest.get("newsCount") != 6:
            sys.exit("BLOQUEADO: noticias source_only; requieren verificacion editorial y web antes de Meta")
    if not args.caption.strip():
        sys.exit("La descripcion editorial no puede estar vacia")
    if len(args.caption) + 2 + len("[" + args.edition_key + "]") > 2200:
        sys.exit("El pie de foto, incluida la marca de edicion, supera 2200 caracteres")
    if len(re.findall(r"(?<!\w)#[\w]+", args.caption)) > 30:
        sys.exit("El pie de foto supera 30 hashtags")
    token = os.getenv("ORBIUNO_IG_ACCESS_TOKEN")
    user_id = os.getenv("ORBIUNO_IG_USER_ID")
    if not token or not user_id:
        sys.exit("Faltan GitHub Secrets ORBIUNO_IG_ACCESS_TOKEN / ORBIUNO_IG_USER_ID")
    profile = api("GET", "/me", token, {"fields": "id,user_id,username"})
    if profile.get("username", "").lower().lstrip("@") != "resumen.noticias":
        sys.exit("Cuenta equivocada: se detiene antes de publicar")
    if str(profile.get("user_id") or profile.get("id")) != user_id:
        sys.exit("ID de cuenta no coincide con el secret: se detiene")
    marker = "[" + args.edition_key + "]"
    caption = args.caption.rstrip() + "\n\n" + marker
    old = existing_media(user_id, token, marker)
    if old:
        print(json.dumps({"state": "ALREADY_PUBLISHED", "id": old.get("id"), "url": old.get("permalink")}))
        return
    if not args.publish:
        print(json.dumps({"state": "DRY_RUN_OK", "account": profile.get("username"), "edition": args.edition_key}))
        return
    container = api("POST", "/" + user_id + "/media", token, {
        "media_type": "REELS", "video_url": args.video_url,
        "caption": caption, "share_to_feed": "true"
    })["id"]
    for _ in range(40):
        time.sleep(15)
        state = api("GET", "/" + container, token, {"fields": "status_code"})
        if state.get("status_code") == "FINISHED":
            break
        if state.get("status_code") in ("ERROR", "EXPIRED"):
            raise RuntimeError("Contenedor Meta " + state["status_code"])
    else:
        raise RuntimeError("Meta no termino de procesar; revisar contenedor " + container + " ANTES de reintentar")
    created = api("POST", "/" + user_id + "/media_publish", token, {"creation_id": container})
    item = api("GET", "/" + created["id"], token, {"fields": "id,permalink"})
    print(json.dumps({"state": "PUBLISHED", "id": item.get("id"), "url": item.get("permalink")}))

if __name__ == "__main__":
    main()
