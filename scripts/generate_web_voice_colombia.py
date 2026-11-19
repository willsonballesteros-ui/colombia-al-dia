#!/usr/bin/env python3
"""Genera audios INTEGROS de los artículos propios con voz es-CO-SalomeNeural.
No reusa audios Kokoro o de proveedor desconocido. Conserva histórico.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from scripts.prepare_site import original_article_ready
from scripts.narration_body import narration_for
from scripts.generate_voice import VOICE, TEMPO, synthesize, duration_sec

ROOT = Path(__file__).resolve().parents[1]


def generate(*, day: str, slot: str, db_path: Path, out: Path):
    doc = json.loads(db_path.read_text(encoding="utf-8"))
    news = sorted((n for n in doc["news"] if n.get("date") == day and
                   n.get("editionSlot") == slot and n.get("verification") == "editorial_verified"),
                  key=lambda n: n.get("priority", 999))
    if len(news) != 6 or len({n["id"] for n in news}) != 6:
        raise ValueError("La franja requiere exactamente seis noticias verificadas")
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    old = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    manifest = {"voice": VOICE, "language": "es-CO", "baseRate": TEMPO,
                "items": old.get("items", {})}
    for n in news:
        body = narration_for(n, original_article_ready)
        if not body or not original_article_ready(n) or len(body) < 600:
            raise ValueError("Falta redacción íntegra revisada: " + n["id"])
        digest = hashlib.sha256((body + "|" + VOICE + "|" + str(TEMPO)).encode()).hexdigest()
        filename = digest[:28] + ".mp3"
        target = out / filename
        if not target.is_file() or duration_sec(target) < 10:
            result = synthesize(digest[:24], body, out)
            (out / result["file"]).replace(target)
        if duration_sec(target) < 10:
            raise RuntimeError("Audio íntegro vacío o truncado: " + n["id"])
        manifest["items"][n["id"]] = {"url": "./media/web-voice/" + filename,
            "text": body, "sha256": hashlib.sha256(body.encode()).hexdigest(),
            "voice": VOICE, "language": "es-CO", "speed": TEMPO}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--day", required=True)
    p.add_argument("--slot", required=True)
    p.add_argument("--news", default=str(ROOT / "noticias.json"))
    p.add_argument("--out", default=str(ROOT / "media/web-voice"))
    a = p.parse_args()
    result = generate(day=a.day, slot=a.slot, db_path=Path(a.news), out=Path(a.out))
    print("WEB_AUDIO_ES_CO_COMPLETE", len([x for x in result["items"] if x.startswith("orbiuno-")]))


if __name__ == "__main__":
    main()
