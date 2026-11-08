#!/usr/bin/env python3
"""Inserta de forma idempotente una edición (noticias + entrada en 'editions') en noticias.json.

Uso: python scripts/merge_edition.py editions/2026-11-07-0800.json [--data noticias.json]
No sobrescribe noticias existentes con distinto contenido: aborta. Conserva el resto del archivo.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orbiuno_edition as oe  # noqa: E402


def merge(data, frag):
    ed = frag["edition"]
    ids = {n["id"] for n in data.setdefault("news", [])}
    for n in frag["news"]:
        old = next((x for x in data["news"] if x["id"] == n["id"]), None)
        if old is None:
            data["news"].append(n)
        elif old != n:
            raise SystemExit(f"Conflicto: {n['id']} ya existe con contenido distinto")
    eds = data.setdefault("editions", [])
    prior = next((e for e in eds if e["editionId"] == ed["editionId"]), None)
    if prior is None:
        eds.append(ed)
    elif prior != ed:
        eds[eds.index(prior)] = ed
    oe.validate_edition(data, ed["editionId"], require_approved=False)
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("fragment")
    ap.add_argument("--data", default="noticias.json")
    a = ap.parse_args()
    p = Path(a.data)
    out = merge(json.loads(p.read_text(encoding="utf-8")), json.loads(Path(a.fragment).read_text(encoding="utf-8")))
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Edición integrada y validada (sin exigir aprobación todavía).")
