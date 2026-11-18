#!/usr/bin/env python3
"""Registro de publicaciones para impedir duplicados.

Clave = sha256(edition_id + manifest_sha256). Estados: pending / published.
Si se intentó media_publish y no hay confirmación, el estado es INCIERTO y se
exige revisión manual antes de reintentar (la respuesta pudo perderse).
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path


class DuplicateBlocked(Exception):
    pass


def make_key(edition_id, manifest_sha256):
    return hashlib.sha256((edition_id + "|" + manifest_sha256).encode()).hexdigest()


class Ledger:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, sort_keys=True)
        os.replace(tmp, self.path)

    def get(self, key):
        return self._load().get(key)

    def assert_can_publish(self, key):
        st = self.get(key)
        if st and st.get("status") == "published":
            raise DuplicateBlocked("edición ya publicada: " + str(st.get("media_id")))
        if st and st.get("publish_attempted"):
            raise DuplicateBlocked("estado incierto: se intentó publicar sin confirmación; "
                                   "verificar en Instagram antes de reintentar")

    def update(self, key, **fields):
        data = self._load()
        st = data.setdefault(key, {"status": "pending", "children": {}})
        for k, v in fields.items():
            if k == "child":
                st["children"][str(v[0])] = v[1]
            else:
                st[k] = v
        self._save(data)
        return st
