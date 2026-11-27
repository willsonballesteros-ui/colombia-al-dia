#!/usr/bin/env python3
"""Permanent ORBIUNO publisher: verify, reconcile, reserve, send, record."""
from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from scripts import verify_public_edition, orbiuno_daily_preflight, orbiuno_publish_6

ROOT = Path(__file__).resolve().parents[1]
ZONE = ZoneInfo("America/Bogota")
SLOTS = ("0800", "1800")

def due(now):
    return [s for s in SLOTS if now.hour * 100 + now.minute >= int(s)]

def read(path):
    return json.loads(path.read_text(encoding="utf-8"))

def confirmed(row):
    u = urlsplit(row.get("url") or "")
    return (str(row.get("id", "")).isdigit() and u.scheme == "https"
            and u.netloc in ("instagram.com", "www.instagram.com")
            and u.path.startswith(("/reel/", "/p/")) and not u.query and not u.fragment)

def stage(root, day, slot):
    ledger = root / "editions/publication-ledger" / f"{day}-{slot}.json"
    row = read(ledger).get("orbiuno", {}) if ledger.exists() else {}
    if row.get("state") == "published":
        if not confirmed(row):
            raise RuntimeError("Registro publicado sin evidencia; conciliar")
        return "published"
    folder = root / "media" / day / f"edicion-{slot}-orbiuno"
    flat = root / "media" / day / f"orbiuno_{slot}_6_noticias_manifest.json"
    if (folder / "orbiuno_manifest.json").is_file() or flat.is_file():
        return "reconcile" if row else "ready"
    if row:
        raise RuntimeError("Existe intento previo sin manifiesto; conciliar")
    if (root / "editions/daily" / f"{day}-{slot}.json").is_file():
        return "editorial_ready"
    return "editorial_missing"

def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)

def ledger_write(day, slot, state, **fields):
    git("fetch", "origin", "main")
    git("merge", "--ff-only", "origin/main")
    path = ROOT / "editions/publication-ledger" / f"{day}-{slot}.json"
    data = read(path) if path.exists() else {"edition": f"{day}-{slot}"}
    old = data.get("orbiuno", {})
    if old.get("state") == "published":
        if not confirmed(old) or state == "published" and old["id"] != fields["id"]:
            raise RuntimeError("Conflicto de publicación")
        return
    if state == "publishing" and old:
        raise RuntimeError("Ya existe una reserva")
    data["orbiuno"] = {**old, **fields, "state": state,
                       "updated_at": datetime.now(ZONE).isoformat()}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    git("add", str(path.relative_to(ROOT)))
    git("commit", "-m", f"ORBIUNO: {state} {day}-{slot}")
    git("push", "origin", "HEAD:main")

def approved(day, slot):
    folder = ROOT / "media" / day / f"edicion-{slot}-orbiuno"
    flat = ROOT / "media" / day / f"orbiuno_{slot}_6_noticias_manifest.json"
    if (folder / "orbiuno_manifest.json").exists():
        report = verify_public_edition.verify(day, slot)
        caption = (folder / "orbiuno_caption.txt").read_text(encoding="utf-8")
        marker = f"[ORBIUNO-{day}-{slot}]"
        return report["video_url"], "\n".join(x for x in caption.splitlines() if x.strip() != marker).strip(), report["sha256"]
    manifest = read(flat)
    if manifest.get("edition") != day or manifest.get("slot") != slot[:2]+":"+slot[2:]:
        raise ValueError("Manifiesto no corresponde a la franja")
    report = orbiuno_daily_preflight.check(manifest, flat.parent)
    return report["videoUrl"], orbiuno_publish_6.caption_for(manifest), report["sha256"]

def meta(day, slot, url, caption, live=False):
    args = [sys.executable, str(ROOT/"scripts/publish_meta_direct.py"),
            "--video-url", url, "--caption", caption,
            "--edition-key", f"ORBIUNO-{day}-{slot}"]
    if live:
        args.append("--publish")
    result = subprocess.run(args, cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE, timeout=1000 if live else 240)
    return json.loads(result.stdout.strip().splitlines()[-1])

def process(day, slot, live):
    status = stage(ROOT, day, slot)
    print(f"{day} {slot}: {status}", flush=True)
    if status == "published":
        return True
    if status in ("editorial_missing", "editorial_ready"):
        return False
    url, caption, digest = approved(day, slot)
    result = meta(day, slot, url, caption)
    if result.get("state") == "ALREADY_PUBLISHED":
        if not confirmed(result):
            raise RuntimeError("Respuesta Meta sin enlace")
        if live:
            ledger_write(day, slot, "published", id=result["id"], url=result["url"], sha256=digest)
        return True
    if result.get("state") != "DRY_RUN_OK":
        raise RuntimeError("Preflight Meta no confirmado")
    if status == "reconcile":
        raise RuntimeError("Intento anterior incierto; no repetir POST")
    if not live:
        print("DRY_RUN_OK", flush=True)
        return True
    ledger_write(day, slot, "publishing", sha256=digest, provider="Meta")
    result = meta(day, slot, url, caption, live=True)
    if result.get("state") not in ("PUBLISHED", "ALREADY_PUBLISHED") or not confirmed(result):
        raise RuntimeError("Envío no confirmado: conservar reserva")
    ledger_write(day, slot, "published", id=result["id"], url=result["url"], sha256=digest)
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--slot", choices=SLOTS)
    p.add_argument("--publish", action="store_true")
    p.add_argument("--status-only", action="store_true")
    args = p.parse_args()
    now = datetime.now(ZONE)
    day = now.date().isoformat()
    slots = due(now)
    if args.slot:
        if args.slot not in slots:
            raise SystemExit("Franja futura")
        slots = [args.slot]
    ok = True
    for slot in slots:
        try:
            if args.status_only:
                print(json.dumps({"day": day, "slot": slot, "state": stage(ROOT, day, slot)}))
            else:
                ok = process(day, slot, args.publish) and ok
        except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as e:
            print(f"NOT_CONFIRMED {day}-{slot}: {type(e).__name__}", file=sys.stderr)
            ok = False
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
