#!/usr/bin/env python3
"""Publicador de carruseles en Instagram (API Graph de Meta). SIMULADO por defecto.

* dry_run=True (predeterminado): no llama a la red ni toca el registro; solo valida
  y devuelve el plan.
* Modo real: requiere dry_run=False, token, id de cuenta, versión de la API y
  ORBIUNO_ALLOW_LIVE=1. El workflow incluido NO activa ninguna de esas condiciones.
Flujo (según la documentación de Meta vigente al escribir esto; verificar antes de activar):
  1) un contenedor hijo por imagen (is_carousel_item=true, image_url pública, JPEG);
  2) un contenedor CAROUSEL con children y caption;
  3) esperar status_code FINISHED; 4) media_publish con creation_id.
"""
import os
import time
from pathlib import Path

from orbiuno_idempotency import DuplicateBlocked, Ledger  # noqa: F401


class PublishBlocked(Exception):
    pass


class PublishFailed(Exception):
    pass


def to_jpeg(png_path, out_path, quality=95, size=(1080, 1350)):
    from PIL import Image
    with Image.open(png_path) as im:
        if im.size != size:
            raise PublishBlocked(f"{Path(png_path).name}: tamaño {im.size}, se exige {size}")
        im.convert("RGB").save(out_path, "JPEG", quality=quality, optimize=True)
    return out_path


class MetaPublisher:
    def __init__(self, http, ledger, ig_user_id=None, token=None, graph_version=None,
                 dry_run=True, sleep=time.sleep, base="https://graph.facebook.com"):
        self.http, self.ledger, self.sleep, self.base = http, ledger, sleep, base
        self.ig_user_id, self.token, self.version = ig_user_id, token, graph_version
        self.dry_run = dry_run

    def _url(self, path):
        return f"{self.base}/{self.version}/{path}"

    def publish(self, key, image_urls, caption):
        if len(image_urls) != 6:
            raise PublishBlocked("el carrusel exige exactamente 6 imágenes")
        if not all(u.startswith("https://") for u in image_urls):
            raise PublishBlocked("todas las imágenes deben tener URL pública https")
        self.ledger.assert_can_publish(key)
        if self.dry_run:
            return {"dry_run": True, "key": key, "imagenes": len(image_urls)}
        if os.environ.get("ORBIUNO_ALLOW_LIVE") != "1":
            raise PublishBlocked("publicación real no autorizada (ORBIUNO_ALLOW_LIVE)")
        if not (self.token and self.ig_user_id and self.version):
            raise PublishBlocked("faltan credenciales o versión de la API de Meta")
        state = self.ledger.get(key) or {}
        children = []
        for i, url in enumerate(image_urls):
            cid = state.get("children", {}).get(str(i))
            if not cid:
                try:
                    cid = self.http("POST", self._url(f"{self.ig_user_id}/media"), {
                        "image_url": url, "is_carousel_item": "true",
                        "access_token": self.token})["id"]
                except Exception as exc:
                    raise PublishFailed(f"fallo al crear la imagen {i + 1}: {exc}")
                self.ledger.update(key, child=(i, cid))
            children.append(cid)
        try:
            carousel = state.get("carousel_id") or self.http(
                "POST", self._url(f"{self.ig_user_id}/media"), {
                    "media_type": "CAROUSEL", "children": ",".join(children),
                    "caption": caption, "access_token": self.token})["id"]
            self.ledger.update(key, carousel_id=carousel)
            for _ in range(20):
                st = self.http("GET", self._url(carousel),
                               {"fields": "status_code", "access_token": self.token})
                if st.get("status_code") == "FINISHED":
                    break
                if st.get("status_code") == "ERROR":
                    raise PublishFailed("Meta reportó ERROR al procesar el carrusel")
                self.sleep(3)
            else:
                raise PublishFailed("el carrusel no terminó de procesarse a tiempo")
            self.ledger.update(key, publish_attempted=True)
            media = self.http("POST", self._url(f"{self.ig_user_id}/media_publish"), {
                "creation_id": carousel, "access_token": self.token})["id"]
        except PublishFailed:
            raise
        except Exception as exc:
            raise PublishFailed(str(exc))
        self.ledger.update(key, status="published", media_id=media)
        return {"dry_run": False, "key": key, "media_id": media}
