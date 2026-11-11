#!/usr/bin/env python3
"""ORBIUNO: deterministic editorial candidate-to-manifest adapter.

Reads researched candidate records from JSON and emits the EXISTING
PLANTILLA_NO_APROBADA schema. This is NOT an automated factual fact-checker:
evidence and approval require separate verification. No publication gates
are promoted by this script.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import re
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

TEMPLATE = Path(__file__).resolve().parents[1] / "editions/PLANTILLA_NO_APROBADA.json"
SLOTS = {"08:00", "16:00", "18:00", "20:00"}
VOICE_ID = "6ce26db0cb6f4e7881b85452619f7f19"

def canonical_url(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError("Source URL must be a string")
    p = urlsplit(raw.strip())
    if p.scheme != "https" or not p.hostname or p.hostname in {"example.org", "google.com", "news.google.com"}:
        raise ValueError("A direct, specific HTTPS source is required")
    if p.path in ("", "/"):
        raise ValueError("Source must point to an actual article")
    return urlunsplit(("https", p.netloc.lower(), p.path.rstrip("/"), "", ""))

def normalized_title(raw: str) -> str:
    return re.sub(r"[^\w]+", " ", raw.casefold(), flags=re.UNICODE).strip()

def choose(candidates: list, edition_date: str) -> list:
    if not isinstance(candidates, list):
        raise ValueError("Candidate feed must be an array")
    found, seen_urls, seen_titles = [], set(), set()
    for item in candidates:
        try:
            url = canonical_url(item["source"]["url"])
            title = item["title"].strip()
            text = normalized_title(title)
            if not title or len(title) < 12 or len(item["narration"].strip()) < 15:
                continue
            published = datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00"))
            if published.date() > date.fromisoformat(edition_date):
                continue
            if url in seen_urls or text in seen_titles:
                continue
            if item.get("editorialEvidence") != "verified" or not item.get("source", {}).get("name"):
                continue
            # A declared review is input evidence, never independently proven by this adapter.
            seen_urls.add(url); seen_titles.add(text)
            found.append(item)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    regular = [x for x in found if x.get("tone") not in ("positive", "curious")]
    closing = [x for x in found if x.get("tone") in ("positive", "curious")]
    if len(regular) < 3 or not closing:
        raise ValueError("BLOCKED: need 3 sourced news items plus a positive/curious closer")
    return regular[:3] + [closing[0]]

def build(candidates: list, edition_date: str, slot: str, template_path: Path = TEMPLATE) -> dict:
    date.fromisoformat(edition_date)
    if slot not in SLOTS:
        raise ValueError("Unknown edition slot")
    data = copy.deepcopy(json.loads(template_path.read_text(encoding="utf-8")))
    if data["brand"] != "ORBIUNO" or data["voice"]["id"] != VOICE_ID:
        raise ValueError("Unexpected template or voice")
    chosen = choose(candidates, edition_date)
    data["editionDate"], data["slot"] = edition_date, slot
    data["voice"]["speed"], data["voice"]["recordedAtSpeed"] = 1.25, 1.0
    data["intro"]["audioFile"] = "audio/intro.wav"
    data["outro"]["audioFile"] = "audio/outro.wav"
    data["news"] = []
    for i, item in enumerate(chosen, 1):
        url = canonical_url(item["source"]["url"])
        stable_id = hashlib.sha256(url.encode()).hexdigest()[:12]
        media = item.get("image") or {}
        # IMPORTANT: do not assert license rights from text supplied by an untrusted feed.
        entry = {
            "id": stable_id, "date": edition_date,
            "category": item.get("category", "Mundo"),
            "verification": "pending",
            "title": item["title"].strip(), "narration": item["narration"].strip(),
            "audioFile": f"audio/{i:02d}.wav",
            "source": {"name": item["source"]["name"], "url": url},
            "image": {
                "file": f"images/{i:02d}.jpg",
                "sourceUrl": media.get("sourceUrl", ""),
                "credit": media.get("credit", ""),
                "license": media.get("license", ""),
                "rightsVerified": False,
            },
        }
        data["news"].append(entry)
    for gate in data["approval"]:
        data["approval"][gate] = False
    data["music"]["rightsVerified"] = False
    return data

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--date", required=True)
    parser.add_argument("--slot", default="08:00")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    manifest = build(candidates, args.date, args.slot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit("BLOCKED: edition manifest exists; will not overwrite")
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Created draft manifest: {args.output}; editorial and media approvals remain blocked")

if __name__ == "__main__":
    main()
