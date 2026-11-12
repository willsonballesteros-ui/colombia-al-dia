#!/usr/bin/env python3
"""Aprobación editorial externa, ligada al contenido.

approval.json = {edition_id, manifest_sha256, approved_by, approved_at, signature}
La firma es HMAC-SHA256 con una clave que SOLO existe en el entorno protegido de
aprobación (o en ORBIUNO Studio). El proceso que genera contenido no la tiene,
y cualquier cambio del manifiesto invalida la aprobación.
Limitación: HMAC implica clave compartida; migrar a firma asimétrica (Ed25519) cuando exista Studio.
"""
import hashlib
import hmac
import json
from pathlib import Path


def manifest_digest(manifest_path):
    return hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()


def _msg(edition_id, digest, approved_by, approved_at):
    return "|".join([edition_id, digest, approved_by, approved_at]).encode()


def sign(key, edition_id, digest, approved_by, approved_at):
    return hmac.new(key.encode(), _msg(edition_id, digest, approved_by, approved_at),
                    hashlib.sha256).hexdigest()


def verify(approval_file, manifest_path, key, approvers, generator_id=None):
    if not key:
        return ["clave de aprobación no disponible: bloqueo"]
    try:
        ap = json.loads(Path(approval_file).read_text(encoding="utf-8"))
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except Exception as exc:
        return ["aprobación editorial ausente o ilegible: " + str(exc)]
    errs = []
    digest = manifest_digest(manifest_path)
    for campo in ("edition_id", "manifest_sha256", "approved_by", "approved_at", "signature"):
        if not ap.get(campo):
            errs.append(f"aprobación: falta {campo}")
    if errs:
        return errs
    if ap["edition_id"] != manifest.get("edition_id"):
        errs.append("la aprobación es de otra edición")
    if ap["manifest_sha256"] != digest:
        errs.append("el manifiesto cambió después de la aprobación")
    if ap["approved_by"] not in approvers:
        errs.append("el aprobador no está autorizado")
    if generator_id and ap["approved_by"] == generator_id:
        errs.append("quien genera la edición no puede aprobarla")
    good = sign(key, ap["edition_id"], ap["manifest_sha256"], ap["approved_by"], ap["approved_at"])
    if not hmac.compare_digest(good, ap["signature"]):
        errs.append("firma de aprobación inválida")
    return errs
