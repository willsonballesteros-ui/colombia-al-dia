#!/usr/bin/env python3
"""Media Manager: busca candidatas en Wikimedia Commons y prepara evidencia de licencia.

Solo PROPONE. Nunca aprueba: cada candidata queda con requiere_revision_humana=True
(que la foto corresponda a la noticia y que los derechos sean válidos lo decide una persona).
Se bloquean licencias fuera de la lista cerrada y las obras sin autor/licencia legibles.
La respuesta cruda de la API se guarda como documento de evidencia (con su SHA-256).
Red: se inyecta `http_get(url, params) -> dict|bytes`; las pruebas usan respuestas simuladas.
"""
import hashlib
import json
import re
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
# nombre corto de licencia en Commons -> código de la lista cerrada de orbiuno_media_registry
LICENSE_MAP = {
    "cc0": "CC0-1.0", "public domain": "PUBLIC-DOMAIN", "pd": "PUBLIC-DOMAIN",
    "cc by 3.0": "CC-BY-3.0", "cc by 4.0": "CC-BY-4.0",
    "cc by-sa 3.0": "CC-BY-SA-3.0", "cc by-sa 4.0": "CC-BY-SA-4.0",
}
LICENSE_URL = {
    "CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
    "PUBLIC-DOMAIN": "https://commons.wikimedia.org/wiki/Commons:Licensing",
    "CC-BY-3.0": "https://creativecommons.org/licenses/by/3.0/",
    "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/",
    "CC-BY-SA-3.0": "https://creativecommons.org/licenses/by-sa/3.0/",
    "CC-BY-SA-4.0": "https://creativecommons.org/licenses/by-sa/4.0/",
}


def _text(v):
    return re.sub(r"<[^>]+>", "", (v or {}).get("value", "") if isinstance(v, dict) else (v or "")).strip()


def search(http_get, query, limit=8):
    data = http_get(API, {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": 6,
        "gsrsearch": query, "gsrlimit": limit, "prop": "imageinfo",
        "iiprop": "url|size|mime|sha1|extmetadata", "iiurlwidth": 1600})
    return data, parse_candidates(data)


def parse_candidates(data):
    out = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        lic_short = _text(meta.get("LicenseShortName")).lower().replace("-", " ").replace("  ", " ")
        lic_short = lic_short.replace("cc by sa", "cc by-sa")
        code = LICENSE_MAP.get(lic_short)
        autor = _text(meta.get("Artist"))
        reasons = []
        if info.get("mime") not in ("image/jpeg", "image/png"):
            reasons.append("formato no admitido")
        if not code:
            reasons.append(f"licencia no permitida o ilegible: {lic_short!r}")
        if not autor:
            reasons.append("autor no identificado")
        if info.get("width", 0) < 1080:
            reasons.append("resolución insuficiente")
        out.append({
            "titulo": page.get("title"), "url_pagina": info.get("descriptionurl"),
            "url_archivo": info.get("url"), "autor": autor, "licencia_codigo": code,
            "licencia_url": LICENSE_URL.get(code), "credito": f"{autor} / {_text(meta.get('LicenseShortName'))}".strip(" /"),
            "atribucion_obligatoria": _text(meta.get("AttributionRequired")).lower() == "true",
            "ancho": info.get("width"), "alto": info.get("height"),
            "bloqueada": bool(reasons), "motivos": reasons, "requiere_revision_humana": True})
    return out


def download_and_document(http_get, candidate, raw_api_response, dest_dir, stem):
    """Descarga una candidata NO bloqueada y escribe foto + documento de evidencia."""
    if candidate["bloqueada"]:
        raise ValueError("candidata bloqueada: " + "; ".join(candidate["motivos"]))
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    blob = http_get(candidate["url_archivo"], {})
    if not isinstance(blob, (bytes, bytearray)) or not blob:
        raise ValueError("descarga vacía")
    ext = ".png" if blob[:4] == b"\x89PNG" else ".jpg"
    photo = dest / f"{stem}{ext}"
    photo.write_bytes(blob)
    evid = dest / f"{stem}-licencia.json"
    evid.write_text(json.dumps({"consulta": "Wikimedia Commons API", "pagina": candidate["url_pagina"],
                                "respuesta_api": raw_api_response}, ensure_ascii=False, indent=1), encoding="utf-8")
    sha = hashlib.sha256(photo.read_bytes()).hexdigest()
    return {
        "foto_manifest": {"archivo": photo.name, "sha256": sha, "url_origen": candidate["url_pagina"],
                          "autor": candidate["autor"], "licencia": candidate["licencia_codigo"],
                          "credito": candidate["credito"], "revision_humana": False},
        "foto_evidence": {"licencia_codigo": candidate["licencia_codigo"], "licencia_url": candidate["licencia_url"],
                          "sha256_foto": sha, "evidencia": {"archivo": evid.name,
                                                            "sha256": hashlib.sha256(evid.read_bytes()).hexdigest()}},
        "nota": "revision_humana=False: una persona debe confirmar que la foto corresponde a la noticia "
                "y que los derechos son válidos antes de poner True y aprobar la edición."}
