#!/usr/bin/env python3
"""Preflight fail-closed. Nunca publica ni despliega; exit 1 => edición bloqueada."""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

def valid_path(root, name):
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ValueError("Ruta de recurso inválida")
    base = root.resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(base):
        raise ValueError("Ruta fuera del directorio de la edición")
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Archivo ausente o vacío: " + name)
    return path

def validate(manifest_file, web_manifest_file=None):
    errors = []
    root = manifest_file.parent
    try:
        import jsonschema
        from PIL import Image
        schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "orbiuno_carrusel.schema.json").read_text(encoding="utf-8"))
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(manifest)
    except Exception as exc:
        return ["Formato del manifiesto inválido: " + str(exc)]
    if manifest["status"] != "approved":
        errors.append("Edición no aprobada: status debe ser approved")
    ids, source_urls = set(), set()
    for i, note in enumerate(manifest["noticias"], 1):
        tag = f"Noticia {i}"
        if note["id"] in ids:
            errors.append(tag + ": ID duplicado")
        ids.add(note["id"])
        url = urlparse(note["url_fuente"])
        if url.scheme != "https" or not url.hostname or url.path in ("", "/"):
            errors.append(tag + ": URL debe apuntar a un artículo, no a una portada")
        if note["url_fuente"] in source_urls:
            errors.append(tag + ": URL de noticia duplicada")
        source_urls.add(note["url_fuente"])
        try:
            imgpath = valid_path(root, note["foto"]["archivo"])
            with Image.open(imgpath) as img:
                img.verify()
            actual = hashlib.sha256(imgpath.read_bytes()).hexdigest()
            if actual != note["foto"]["sha256"]:
                errors.append(tag + ": SHA-256 de fotografía no coincide")
        except Exception as exc:
            errors.append(tag + ": fotografía: " + str(exc))
        try:
            logo = valid_path(root, note["logo_fuente"])
            if logo.suffix.lower() not in (".png", ".svg", ".jpg", ".jpeg", ".webp"):
                raise ValueError("Logo debe ser PNG/SVG/JPG/WEBP")
        except Exception as exc:
            errors.append(tag + ": logo: " + str(exc))
        try:
            audiopath = valid_path(root, note["audio"]["archivo"])
            if audiopath.stat().st_size < 10_240:
                raise ValueError("Archivo de audio demasiado pequeño")
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=duration:stream=codec_type,codec_name,sample_rate,channels",
                 "-of", "json", str(audiopath)],
                capture_output=True, text=True, check=True, timeout=15)
            info = json.loads(probe.stdout)
            streams = [x for x in info.get("streams", []) if x.get("codec_type") == "audio"]
            if not streams:
                raise ValueError("Falta pista de audio")
            track = streams[0]
            if track.get("codec_name") not in ("mp3", "aac"):
                raise ValueError("Códec no admitido; usar MP3 o AAC")
            if int(track.get("sample_rate", 0)) not in (22050, 24000, 32000, 44100, 48000):
                raise ValueError("Frecuencia de muestreo no admitida")
            if int(track.get("channels", 0)) not in (1, 2):
                raise ValueError("Número de canales no admitido")
            dur = float(info["format"]["duration"])
            expected = float(note["audio"]["duracion_s"])
            if not math.isfinite(dur) or dur < 2 or abs(dur - expected) > max(1.0, expected * 0.03):
                raise ValueError("Duración fuera de tolerancia")
            decode = subprocess.run(
                ["ffmpeg", "-v", "error", "-i", str(audiopath), "-f", "null", "-"],
                capture_output=True, text=True, timeout=60)
            if decode.returncode != 0:
                raise ValueError("Audio no se puede decodificar")
        except Exception as exc:
            errors.append(tag + ": audio: " + str(exc))
    if web_manifest_file is None:
        errors.append("Sin manifiesto web desplegado para comparación: bloqueo")
    else:
        try:
            web = json.loads(web_manifest_file.read_text(encoding="utf-8"))
            fields = ("id", "titular", "fecha", "fuente", "url_fuente")
            a = [{**{k: n[k] for k in fields}, "foto_sha256": n["foto"]["sha256"]} for n in manifest["noticias"]]
            b = [{**{k: n[k] for k in fields}, "foto_sha256": n["foto"]["sha256"]} for n in web["noticias"]]
            if a != b or manifest["edition_id"] != web["edition_id"]:
                errors.append("Web e Instagram no coinciden en orden, datos o hash fotográfico")
        except Exception as exc:
            errors.append("No fue posible comparar la web: " + str(exc))
    return errors

def main():
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--web-manifest", type=Path, default=None,
                   help="JSON de la edición web realmente desplegada (no una copia local sin desplegar)")
    args = p.parse_args()
    errors = validate(args.manifest, args.web_manifest)
    for err in errors:
        print("BLOQUEO: " + err, file=sys.stderr)
    print("APROBADO" if not errors else f"BLOQUEADO ({len(errors)} problemas)")
    return int(bool(errors))

if __name__ == "__main__":
    sys.exit(main())
