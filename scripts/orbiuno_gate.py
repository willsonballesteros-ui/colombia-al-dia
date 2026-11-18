#!/usr/bin/env python3
"""Compuerta final de publicación (fail-closed). Exit 1 => NO publicar.

Reúne, sin sustituir al preflight existente (scripts/preflight_carousel.py):
  1 preflight existente      2 seis PNG de 1080x1350, distintos entre sí
  3 licencias + evidencia    4 logotipos del registro de medios
  5 audio real (ffmpeg)      6 aprobación editorial externa firmada
  7 registro de duplicados
Los datos extra viven en editions/<id>/evidence.json (no se toca el esquema del PR #15).
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbiuno_approval as approval  # noqa: E402
import orbiuno_audio_check as audio  # noqa: E402
import orbiuno_media_registry as media  # noqa: E402
from orbiuno_idempotency import DuplicateBlocked, Ledger, make_key  # noqa: E402

PNG_NAMES = ["portada.png"] + [f"noticia_{i:02d}.png" for i in range(1, 6)]


def default_preflight(manifest, web_manifest):
    script = Path(__file__).resolve().parent / "preflight_carousel.py"
    cmd = [sys.executable, str(script), str(manifest)]
    if web_manifest:
        cmd += ["--web-manifest", str(web_manifest)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    return [] if p.returncode == 0 else [("preflight: " + (p.stderr.strip() or "bloqueado"))]


def check_pngs(edition):
    from PIL import Image
    errs, hashes = [], set()
    for name in PNG_NAMES:
        try:
            p = media.safe_path(edition, name)
            with Image.open(p) as im:
                if im.format != "PNG" or im.size != (1080, 1350):
                    errs.append(f"{name}: debe ser PNG de 1080x1350 (es {im.format} {im.size})")
            hashes.add(media.sha256_file(p))
        except Exception as exc:
            errs.append(f"{name}: {exc}")
    if not errs and len(hashes) != len(PNG_NAMES):
        errs.append("hay láminas idénticas entre sí")
    return errs


def evaluate(edition, web_manifest=None, ledger_path=None, approvers=(), logo_registry=None,
             key=None, generator_id=None, preflight_runner=default_preflight):
    edition = Path(edition)
    manifest_file = edition / "manifest.json"
    errs = []
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        evidence = json.loads((edition / "evidence.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return ["manifiesto o evidencia ilegible: " + str(exc)]
    errs += preflight_runner(manifest_file, web_manifest)
    errs += check_pngs(edition)
    try:
        reg_root, fuentes = media.load_registry(logo_registry)
    except Exception as exc:
        reg_root, fuentes = None, {}
        errs.append("registro de medios ilegible: " + str(exc))
    for i, n in enumerate(manifest["noticias"], 1):
        tag = f"Noticia {i}"
        ev = evidence.get("noticias", {}).get(n["id"])
        if not ev:
            errs.append(f"{tag}: sin entrada en evidence.json")
            continue
        errs += [f"{tag}: {e}" for e in media.check_photo_evidence(edition, n["foto"], ev.get("foto"))]
        try:
            logo = media.safe_path(edition, n["logo_fuente"])
            errs += [f"{tag}: {e}" for e in media.check_logo(
                reg_root, fuentes, ev.get("fuente_id"), n["url_fuente"], logo)]
        except Exception as exc:
            errs.append(f"{tag}: logotipo: {exc}")
        try:
            ap = media.safe_path(edition, n["audio"]["archivo"])
            errs += [f"{tag}: {e}" for e in audio.check_audio(ap, ev.get("guion", ""))]
        except Exception as exc:
            errs.append(f"{tag}: audio: {exc}")
    errs += approval.verify(edition / "approval.json", manifest_file, key, set(approvers), generator_id)
    if ledger_path is None:
        errs.append("sin registro de publicaciones: bloqueo")
    else:
        try:
            Ledger(ledger_path).assert_can_publish(
                make_key(manifest["edition_id"], approval.manifest_digest(manifest_file)))
        except DuplicateBlocked as exc:
            errs.append(str(exc))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edition", type=Path)
    ap.add_argument("--web-manifest", type=Path)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--approvers", type=Path, required=True, help="JSON: lista de aprobadores")
    ap.add_argument("--logo-registry", type=Path, required=True)
    ap.add_argument("--generator-id", default=os.environ.get("ORBIUNO_GENERATOR_ID"))
    a = ap.parse_args()
    errs = evaluate(a.edition, a.web_manifest, a.ledger,
                    json.loads(a.approvers.read_text(encoding="utf-8")), a.logo_registry,
                    os.environ.get("ORBIUNO_APPROVAL_KEY"), a.generator_id)
    for e in errs:
        print("BLOQUEO:", e, file=sys.stderr)
    print("COMPUERTA ABIERTA" if not errs else f"COMPUERTA CERRADA ({len(errs)} problemas)")
    return int(bool(errs))


if __name__ == "__main__":
    sys.exit(main())
