#!/usr/bin/env python3
"""Publica una sola edición ORBIUNO validada en Instagram y Facebook.

Uso:
  python scripts/orbiuno_daily_preflight.py --manifest media/2026-11-21/orbiuno_0800_6_noticias_manifest.json
  python scripts/publish_orbiuno_video.py --manifest media/2026-11-21/orbiuno_0800_6_noticias_manifest.json --publish

No realiza cambios en el contenido de las noticias ni genera fotografías.
Complejidad de deduplicación: O(n) para hasta 50 publicaciones por cuenta.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

API = "https://graph.facebook.com/v27.0"
REPO = "willsonballesteros-ui/colombia-al-dia"
EXPECTED_IG = "resumen.noticias"
EXPECTED_IG_ID = "17841438062554418"
EXPECTED_PAGE_ID = "1516359454884058"


class PublishError(RuntimeError):
    pass


def https_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise PublishError("La URL debe ser HTTPS sin credenciales")
    if parsed.fragment:
        raise PublishError("URL con fragmento no autorizada")
    return value


def graph(token: str, endpoint: str, *, fields: dict | None = None,
          form: dict | None = None, timeout: float = 45) -> dict:
    if not token:
        raise PublishError("Falta el secreto de Meta")
    if not re.fullmatch(r"[A-Za-z0-9_/,?=&.+-]+", endpoint):
        raise PublishError("Endpoint Meta inválido")
    url = f"{API}/{endpoint.lstrip('/')}"
    if fields:
        url += "?" + urlencode(fields)
    data = urlencode(form).encode("utf-8") if form is not None else None
    req = Request(url, data=data, headers={
        "Authorization": "Bearer " + token,
        "User-Agent": "ORBIUNO-Newsroom/1.0",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read(1_000_000))
            if not isinstance(payload, dict):
                raise PublishError("La API Meta devolvió un formato incorrecto")
            return payload
    except HTTPError as exc:
        # No emitir body: algunos errores incluyen datos sensibles.
        raise PublishError(f"Meta rechazó la operación: HTTP {exc.code}") from None
    except (URLError, TimeoutError, ValueError) as exc:
        raise PublishError("Error al conectar con Meta o interpretar su respuesta") from exc


def load_manifest(path: Path) -> tuple[dict, str, str]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    day, slot = manifest.get("edition"), manifest.get("slot")
    if not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", str(day)):
        raise PublishError("Fecha editorial inválida")
    if slot not in ("08:00", "09:30", "12:00", "17:00", "18:00", "19:00"):
        raise PublishError("Franja editorial inválida")
    ids = manifest.get("newsIds", [])
    news = manifest.get("news", [])
    if (len(ids) != 6 or len(set(ids)) != 6 or len(news) != 6 or
            manifest.get("newsCount") != 6 or
            [item.get("id") for item in news] != ids):
        raise PublishError("La edición no contiene seis noticias únicas")
    if (manifest.get("voice") != "es-CO-SalomeNeural" or
            manifest.get("voiceSpeed") != 1.25 or
            manifest.get("imagesCount") != 6 or manifest.get("logosCount") != 6 or
            manifest.get("visualMode") != "verified_real_photos"):
        raise PublishError("Control editorial de voz/fotos/logos no conforme")
    credits = manifest.get("photoCredits", [])
    if (len(credits) != 6 or
            not all(c.get("author") and c.get("license") and
                    https_url(c.get("page", "")) for c in credits)):
        raise PublishError("Créditos fotográficos incompletos")
    stamp = slot.replace(":", "")
    prefix = f"ORBIUNO | {day} | {slot} CO"
    video = "https://raw.githubusercontent.com/" + REPO + "/main/media/" + day + "/" + str(manifest.get("video", ""))
    if not re.fullmatch(r"ORBIUNO_20\d{2}-\d{2}-\d{2}_\d{4}_6_NOTICIAS\.mp4", str(manifest.get("video", ""))):
        raise PublishError("Nombre de MP4 no corresponde a la edición")
    if stamp not in video:
        raise PublishError("Hora del MP4 no corresponde a la edición")
    https_url(video)
    return manifest, prefix, video


def build_caption(m: dict, prefix: str) -> str:
    lines = [prefix, "", "Seis noticias verificadas de Colombia y el mundo:"]
    for index, item in enumerate(m["news"], 1):
        title = str(item.get("title", "")).strip()
        src = https_url(str(item.get("sourceUrl", "")))
        if not title:
            raise PublishError("Falta un titular")
        lines.append(f"{index}. {title}")
        lines.append(src)
    lines.extend(["", "Fotografías reales de archivo; autor, licencia y detalles en cada noticia de la web.",
                  "https://colombia-al-dia.pages.dev/", "#ORBIUNO #ResumenNoticias #Colombia"])
    text = "\n".join(lines)
    if len(text) > 2200:
        raise PublishError(f"El texto supera el máximo de Instagram: {len(text)}")
    return text


def check_identity(token: str, ig_id: str) -> None:
    data = graph(token, ig_id, fields={"fields": "id,username"})
    if str(data.get("id")) != ig_id or data.get("username") != EXPECTED_IG:
        raise PublishError("La cuenta de Instagram no coincide con ORBIUNO")


def find_duplicate(token: str, endpoint: str, prefix: str, text_field: str) -> dict | None:
    fields = "id,permalink,caption,media_product_type" if text_field == "caption" else "id,description,permalink_url"
    data = graph(token, endpoint, fields={"fields": fields, "limit": 50})
    for item in data.get("data", []):
        first_line = str(item.get(text_field) or "").split("\n", 1)[0].strip()
        if first_line == prefix:
            return item
    return None


def publish_ig(token: str, account: str, prefix: str, video: str, caption: str) -> dict:
    check_identity(token, account)
    existing = find_duplicate(token, account + "/media", prefix, "caption")
    if existing:
        return {"duplicate": True, "id": existing.get("id"), "permalink": existing.get("permalink")}
    creation = graph(token, account + "/media", form={
        "media_type": "REELS", "video_url": video, "share_to_feed": "true", "caption": caption
    })
    creation_id = str(creation.get("id", ""))
    if not creation_id.isdigit():
        raise PublishError("Meta no devolvió ID del contenedor")
    for attempt in range(40):
        status = graph(token, creation_id, fields={"fields": "status_code"}).get("status_code")
        if status == "FINISHED":
            break
        if status not in ("IN_PROGRESS", "PUBLISHED"):
            raise PublishError(f"Contenedor Instagram no procesable: {status}")
        if attempt == 39:
            raise PublishError("Tiempo de espera del procesamiento agotado")
        time.sleep(10)
    result = graph(token, account + "/media_publish", form={"creation_id": creation_id})
    media_id = str(result.get("id", ""))
    if not media_id.isdigit():
        raise PublishError("Publicación incierta; NO reintentar sin consultar Meta")
    media = graph(token, media_id, fields={"fields": "id,permalink,media_product_type"})
    permalink = str(media.get("permalink") or "")
    if media.get("id") != media_id or not permalink.startswith("https://www.instagram.com/"):
        raise PublishError(f"Instagram devolvió ID {media_id}, sin enlace verificado")
    return {"duplicate": False, "id": media_id, "permalink": permalink}


def publish_facebook(token: str, page_id: str, prefix: str, video: str, caption: str) -> dict:
    page = graph(token, page_id, fields={"fields": "id"})
    if str(page.get("id")) != page_id:
        raise PublishError("La página Facebook no coincide con ORBIUNO")
    existing = find_duplicate(token, page_id + "/videos", prefix, "description")
    if existing:
        return {"duplicate": True, "id": existing.get("id"),
                "permalink": existing.get("permalink_url")}
    result = graph(token, page_id + "/videos", form={
        "file_url": video, "title": prefix,
        "description": caption,
        "published": "true",
    }, timeout=120)
    media_id = str(result.get("id", ""))
    if not media_id.isdigit():
        raise PublishError("Facebook no devolvió ID; publicación incierta")
    return {"duplicate": False, "id": media_id,
            "permalink": f"https://www.facebook.com/{page_id}/videos/{media_id}/"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("orbiuno_meta_result.json"))
    args = parser.parse_args()
    m, prefix, video = load_manifest(args.manifest)
    caption = build_caption(m, prefix)
    print("EDICION_CONTROLADA", prefix, "NOTICIAS", len(m["news"]))
    if not args.publish:
        print("MODO_PREVISUALIZACION", video)
        return 0
    ig_token = os.environ.get("ORBIUNO_IG_ACCESS_TOKEN", "")
    fb_token = os.environ.get("ORBIUNO_FB_PAGE_ACCESS_TOKEN", "")
    ig_id = os.environ.get("ORBIUNO_IG_USER_ID", "")
    fb_id = os.environ.get("ORBIUNO_FB_PAGE_ID", "")
    if ig_id != EXPECTED_IG_ID or fb_id != EXPECTED_PAGE_ID or not ig_token or not fb_token:
        raise PublishError("Las cuentas oficiales o credenciales no están configuradas")
    # El guardado tras Instagram permite reconciliar errores de Facebook sin repetir el Reel.
    output = {"edition": prefix, "instagram": None, "facebook": None}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output["instagram"] = publish_ig(ig_token, ig_id, prefix, video, caption)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    output["facebook"] = publish_facebook(fb_token, fb_id, prefix, video, caption)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("PUBLICADO_META", json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (PublishError, OSError, KeyError, json.JSONDecodeError) as exc:
        print("PUBLICACION_DETENIDA:", str(exc), file=sys.stderr)
        sys.exit(1)
