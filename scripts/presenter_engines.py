#!/usr/bin/env python3
"""Orquestador de presentadora: API primaria -> reserva -> animación local.

APIs remotas son opcionales y DESACTIVADAS por defecto: ningún cargo sin
habilitar explícitamente ORBIUNO_REMOTE_AVATAR_ENABLED=1 y configurar endpoint.
Protocolo para endpoints propios: POST JSON audio_base64 + image_base64;
respuesta audio/video MP4 binaria o JSON {"video_base64":"..."}.
No se afirma compatibilidad directa con las APIs comerciales de terceros.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from presenter_motion import make_presenter_clip

MAX_RESPONSE_BYTES = 80 * 1024 * 1024


def valid_clip(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 15_000:
        return False
    try:
        result = subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
            text=True, timeout=15,
        ).strip()
        return result == "720,1280"
    except (subprocess.SubprocessError, OSError):
        return False


def request_remote(endpoint: str, token: str, portrait: Path, audio: Path,
                   output: Path, timeout: int = 90):
    url = urllib.parse.urlparse(endpoint)
    if url.scheme != "https" or not url.netloc:
        raise ValueError("El endpoint de video debe utilizar HTTPS")
    if not portrait.is_file():
        raise FileNotFoundError("Imagen de la presentadora no disponible")
    if portrait.stat().st_size > 5_000_000 or audio.stat().st_size > 15_000_000:
        raise ValueError("Archivo de entrada demasiado grande")
    payload = json.dumps({
        "image_base64": base64.b64encode(portrait.read_bytes()).decode("ascii"),
        "audio_base64": base64.b64encode(audio.read_bytes()).decode("ascii"),
        "format": "mp4", "width": 720, "height": 1280, "language": "es",
    }).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "video/mp4, application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(endpoint, payload, headers, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("La respuesta del motor supera el tamaño permitido")
    if content_type.startswith("video/mp4"):
        output.write_bytes(data)
    elif "application/json" in content_type:
        message = json.loads(data)
        encoded = message.get("video_base64")
        if not isinstance(encoded, str):
            raise ValueError("El adaptador no devolvió 'video_base64'")
        output.write_bytes(base64.b64decode(encoded, validate=True))
    else:
        raise ValueError("Formato de salida de la API no reconocido")
    if not valid_clip(output):
        output.unlink(missing_ok=True)
        raise ValueError("El video remoto no cumple la validación 720x1280")
    return {"engine": "remote_endpoint", "realLipSync": False, "talkingPresenter": True,
            "presenterType": "remote_unverified", "durationSec": None}


def render_presenter(audio: Path, target: Path, label: str = "BOLETÍN DEL DÍA"):
    portrait = Path(os.environ.get("ORBIUNO_PRESENTER_IMAGE", "branding/presentadora.png"))
    remote_enabled = os.environ.get("ORBIUNO_REMOTE_AVATAR_ENABLED") == "1"
    # Ninguna ruta comercial se prueba automáticamente si no está autorizada.
    if remote_enabled and portrait.exists():
        for role in ("PRIMARY", "BACKUP"):
            endpoint = os.environ.get("ORBIUNO_LIPSYNC_" + role + "_URL", "").strip()
            token = os.environ.get("ORBIUNO_LIPSYNC_" + role + "_TOKEN", "").strip()
            if not endpoint:
                continue
            try:
                outcome = request_remote(endpoint, token, portrait, audio, target)
                # Sólo la verificación específica del proveedor puede acreditar
                # sincronización fonética auténtica: no inferirlo del MP4.
                outcome["engine"] = "external_" + role.lower()
                return outcome
            except Exception as error:
                target.unlink(missing_ok=True)
                print("Motor", role, "falló, pasando al siguiente:", type(error).__name__, flush=True)

    # Fallback C: funciona sin claves ni consumo de APIs externas.
    return make_presenter_clip(audio, target, label)


if __name__ == "__main__":
    raise SystemExit("Usar render_presenter() desde render_narrated.py")
