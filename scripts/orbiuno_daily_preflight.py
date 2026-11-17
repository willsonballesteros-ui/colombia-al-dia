#!/usr/bin/env python3
"""Verify that Cloudflare serves exactly the six reviewed news items and audio.

No social publication in this script. Fail closed when there is a mismatch.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.request import Request, urlopen

WEB = "https://colombia-al-dia.pages.dev/"
REPO = "willsonballesteros-ui/colombia-al-dia"


def get(url: str, limit: int = 12_000_000) -> bytes:
    request = Request(url, headers={"User-Agent": "ORBIUNO-Daily-Preflight/1.0",
                                    "Cache-Control": "no-cache"})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError("HTTP inesperado en " + url)
        return response.read(limit)


def check(manifest: dict, root: Path) -> dict:
    day, slot = manifest["edition"], manifest["slot"]
    ids = manifest["newsIds"]
    if len(ids) != 6 or len(set(ids)) != 6 or manifest["newsCount"] != 6:
        raise ValueError("Manifiesto sin seis IDs únicos")
    path = root / manifest["video"]
    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("MP4 ausente o diferente a SHA-256")
    if not (50 <= float(manifest.get("duration", 0)) <= 60):
        raise ValueError("Duración del MP4 inválida")
    home = get(WEB).decode("utf-8")
    matched = re.search(r'<script[^>]*id="initial-news"[^>]*>(.*?)</script>', home, re.S)
    if not matched:
        raise RuntimeError("Web pública carece del JSON incrustado")
    data = json.loads(matched.group(1))
    actual = sorted(
        [n for n in data["news"] if n.get("date") == day
         and n.get("editionSlot") == slot and n.get("verification") == "editorial_verified"],
        key=lambda n: n.get("priority", 999),
    )
    if data.get("editionDate") != day or [n["id"] for n in actual] != ids:
        raise RuntimeError("Fecha o seis noticias de la web no coinciden con el MP4")
    for manifest_news, n in zip(manifest["news"], actual):
        if manifest_news["id"] != n["id"] or manifest_news["title"] != n["title"]:
            raise RuntimeError("Titular o ID del manifiesto difiere de la web")
        source = n["sources"][0]["url"]
        if manifest_news["sourceUrl"] != source:
            raise RuntimeError("Fuente del Reel y web no coinciden")
        if 'id="noticia-' + n["id"] + '"' not in home:
            raise RuntimeError("Falta la lámina desarrollada en la web: " + n["id"])
    if "audio-fix.js" not in home:
        raise RuntimeError("Sin reproductor de audio en el sitio")
    voices = json.loads(get(WEB + "media/web-voice/manifest.json").decode("utf-8"))
    for n in actual:
        item = voices.get("items", {}).get(n["id"])
        if not item or not item.get("text") or not item.get("url"):
            raise RuntimeError("Falta audio completo para " + n["id"])
        if not get(WEB + item["url"].removeprefix("./"), limit=512):
            raise RuntimeError("MP3 sin datos: " + n["id"])
    video_url = ("https://raw.githubusercontent.com/" + REPO + "/main/media/" +
                 day + "/" + manifest["video"])
    if not get(video_url, limit=512):
        raise RuntimeError("MP4 no accesible desde Internet")
    return {"state": "PREFLIGHT_PASS", "date": day, "slot": slot,
            "newsIds": ids, "videoUrl": video_url,
            "sha256": manifest["sha256"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--tries", type=int, default=16)
    parser.add_argument("--sleep", type=float, default=20.0)
    args = parser.parse_args()
    if args.tries < 1 or args.tries > 20:
        raise SystemExit("Número de intentos inválido")
    p = Path(args.manifest)
    m = json.loads(p.read_text(encoding="utf-8"))
    result = None
    for i in range(args.tries):
        try:
            result = check(m, p.parent)
            break
        except (ValueError, OSError, RuntimeError, KeyError) as exc:
            print("PREFLIGHT_RETRY", i + 1, str(exc)[:250], flush=True)
            if i + 1 == args.tries:
                raise
            time.sleep(args.sleep)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
