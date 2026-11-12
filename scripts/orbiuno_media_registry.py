#!/usr/bin/env python3
"""Registro de medios y evidencia de fotografías (ORBIUNO).

Valida, sin red, que:
  * el logotipo de cada fuente sea el archivo registrado (hash) y el dominio de la
    noticia pertenezca a esa fuente;
  * cada fotografía tenga licencia permitida y un documento de evidencia cuyo hash
    coincida (la licencia escrita en el manifiesto no basta).
No decide autenticidad ni derechos: eso lo hace una persona (ver orbiuno_approval).
"""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_LICENSES = {
    "CC0-1.0", "PUBLIC-DOMAIN", "CC-BY-3.0", "CC-BY-4.0",
    "CC-BY-SA-3.0", "CC-BY-SA-4.0", "WRITTEN-PERMISSION",
}
OPEN_LICENSE_HOSTS = {"creativecommons.org", "commons.wikimedia.org"}
MIN_LOGO_WIDTH = 400
MIN_PHOTO_WIDTH = 1080


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_path(root, name):
    root = Path(root).resolve()
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("ruta inválida")
    p = (root / name).resolve()
    if not p.is_relative_to(root):
        raise ValueError("ruta fuera del directorio permitido")
    if not p.is_file() or p.stat().st_size == 0:
        raise ValueError("archivo ausente o vacío: " + name)
    return p


def host_matches(url, domains):
    host = (urlparse(url).hostname or "").lower()
    return any(host == d.lower() or host.endswith("." + d.lower()) for d in domains)


def _image_width(path):
    from PIL import Image
    with Image.open(path) as im:
        im.verify()
    with Image.open(path) as im:
        return im.size[0]


def load_registry(registry_file):
    registry_file = Path(registry_file)
    data = json.loads(registry_file.read_text(encoding="utf-8"))
    return registry_file.parent, data.get("fuentes", {})


def check_logo(registry_root, fuentes, fuente_id, url_fuente, logo_file):
    """Devuelve lista de errores para el logotipo de una noticia."""
    errs = []
    entry = fuentes.get(fuente_id)
    if not entry:
        return [f"fuente '{fuente_id}' no está en el registro de medios"]
    for campo in ("nombre_oficial", "dominios", "archivo", "url_origen", "sha256", "condiciones_uso"):
        if not entry.get(campo):
            errs.append(f"registro de '{fuente_id}': falta {campo}")
    if errs:
        return errs
    if not host_matches(url_fuente, entry["dominios"]):
        errs.append(f"el dominio de url_fuente no pertenece a '{fuente_id}'")
    try:
        reg_logo = safe_path(registry_root, entry["archivo"])
        if sha256_file(reg_logo) != entry["sha256"]:
            errs.append(f"el logotipo registrado de '{fuente_id}' no coincide con su hash")
        if sha256_file(logo_file) != sha256_file(reg_logo):
            errs.append("el logotipo usado en la edición no es el registrado")
        if reg_logo.suffix.lower() != ".svg" and _image_width(reg_logo) < MIN_LOGO_WIDTH:
            errs.append(f"logotipo de '{fuente_id}' demasiado pequeño (< {MIN_LOGO_WIDTH}px)")
    except Exception as exc:  # fail closed
        errs.append("logotipo: " + str(exc))
    return errs


def check_photo_evidence(edition_root, foto_manifest, foto_evidence):
    """Errores de licencia/evidencia de una fotografía."""
    errs = []
    ev = foto_evidence or {}
    code = ev.get("licencia_codigo")
    if code not in ALLOWED_LICENSES:
        errs.append(f"licencia no permitida o ausente: {code!r}")
    url = ev.get("licencia_url", "")
    if not url.startswith("https://"):
        errs.append("falta licencia_url https")
    elif code not in (None, "WRITTEN-PERMISSION") and not host_matches(url, OPEN_LICENSE_HOSTS):
        errs.append("licencia_url no apunta a una fuente de licencia reconocida")
    if ev.get("sha256_foto") != foto_manifest.get("sha256"):
        errs.append("la evidencia no está vinculada al hash de esta fotografía")
    doc = ev.get("evidencia") or {}
    try:
        p = safe_path(edition_root, doc.get("archivo"))
        if sha256_file(p) != doc.get("sha256"):
            errs.append("el documento de evidencia no coincide con su hash")
    except Exception as exc:
        errs.append("evidencia: " + str(exc))
    try:
        photo = safe_path(edition_root, foto_manifest.get("archivo"))
        if sha256_file(photo) != foto_manifest.get("sha256"):
            errs.append("el archivo de la fotografía no coincide con el hash del manifiesto")
        if _image_width(photo) < MIN_PHOTO_WIDTH:
            errs.append(f"fotografía demasiado pequeña (< {MIN_PHOTO_WIDTH}px de ancho)")
    except Exception as exc:
        errs.append("fotografía: " + str(exc))
    return errs
