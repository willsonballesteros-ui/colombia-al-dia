#!/usr/bin/env python3
"""Importa SOLO titulares atribuidos de feeds RSS/Atom para Colombia al Día.

La importación NO es verificación periodística: ninguna noticia externa de este
script se marca como confirmada por la redacción. No requiere API, claves ni IA.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import logging
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Bogota")
RSS = [
    # Las rutas a medios son públicas. Algunas pueden dejar de funcionar o
    # modificar condiciones de uso; se omite la fuente que falle.
    ("BBC News Mundo", "Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ("Google Noticias — Colombia", "Colombia", "https://news.google.com/rss/search?q=Colombia+when%3A1d&hl=es-419&gl=CO&ceid=CO%3Aes-419"),
    ("Google Noticias — Tecnología e IA", "Tecnología e IA", "https://news.google.com/rss/search?q=inteligencia+artificial+tecnologia+when%3A1d&hl=es-419&gl=CO&ceid=CO%3Aes-419"),
    ("Google Noticias — Economía", "Economía", "https://news.google.com/rss/search?q=economia+colombiana+when%3A1d&hl=es-419&gl=CO&ceid=CO%3Aes-419"),
]
MAX_ITEMS_PER_RUN = 9
PER_CATEGORY = {"Colombia": 3, "Tecnología e IA": 2, "Economía": 2, "Mundo": 2}
MAX_AGE_HOURS = 36
USER_AGENT = "ColombiaAlDiaNoticias/1.0 (portal de enlaces y atribuciones; sin extraccion integral)"


def norm_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\W+", " ", s.lower(), flags=re.UNICODE).strip()


def text(node, tag: str, default="") -> str:
    ch = node.find(tag)
    return "" if ch is None else (ch.text or default).strip()


def normalized_url(url: str) -> str:
    p = urllib.parse.urlsplit(url.strip())
    drop = {"fbclid", "gclid", "utm_source", "utm_medium", "utm_campaign", "utm_content"}
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    q = [(k, v) for k, v in q if k.lower() not in drop]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), urllib.parse.urlencode(q), ""))


def parse_dt(raw: str):
    if not raw:
        return None
    try:
        v = parsedate_to_datetime(raw)
    except Exception:
        try:
            v = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None
    if v.tzinfo is None:
        return None
    return v.astimezone(TZ)


def parse_feed(raw: bytes, source: str, category: str):
    root = ET.fromstring(raw)
    parsed = []
    if root.tag.lower().endswith("rss") or root.find("channel") is not None:
        for item in root.findall(".//channel/item"):
            title = html.unescape(re.sub(r"<[^>]+>", "", text(item, "title"))).strip()
            link = text(item, "link")
            dt = parse_dt(text(item, "pubDate"))
            publisher = text(item, "source") or source
            if item.find("source") is not None and item.find("source").text:
                publisher = item.find("source").text.strip()
            parsed.append((title, link, dt, publisher))
    else:
        atom = "{http://www.w3.org/2005/Atom}"
        for item in root.findall(f".//{atom}entry"):
            title = html.unescape(text(item, f"{atom}title"))
            links = [x.attrib.get("href", "") for x in item.findall(f"{atom}link") if x.attrib.get("rel", "alternate") == "alternate"]
            link = links[0] if links else ""
            dt = parse_dt(text(item, f"{atom}published") or text(item, f"{atom}updated"))
            parsed.append((title, link, dt, source))
    return parsed


def safe_article(item, category: str, now: datetime, is_aggregator: bool):
    title, url, date, publisher = item
    if not title or not date or not url:
        return None
    url = normalized_url(url)
    p = urllib.parse.urlsplit(url)
    if p.scheme != "https" or not p.netloc or len(title) < 18 or len(title) > 220:
        return None
    delta = now - date
    if delta < timedelta(hours=-2) or delta > timedelta(hours=MAX_AGE_HOURS):
        return None
    # Google Noticias reúne titulares de terceros y es una ruta intermedia;
    # no afirmar que el vínculo conduce directo a la redacción original.
    if is_aggregator:
        original_publisher = publisher or "Fuente indexada"
        title = re.sub(r"\s+-\s+" + re.escape(original_publisher) + r"$", "", title, flags=re.I)
        source_label = f"{original_publisher} · vía Google Noticias"
        credit = f"Titular difundido por {original_publisher} a través de Google Noticias"
    else:
        source_label = publisher
        credit = f"Titular difundido por {publisher}"
    uid = hashlib.sha256((norm_text(title) + "|" + date.strftime("%Y-%m-%d")).encode("utf-8")).hexdigest()[:16]
    return {
        "id": "rss-" + uid,
        "date": date.strftime("%Y-%m-%d"),
        "category": category,
        "level": "Titular atribuido · Pendiente de verificación editorial",
        "title": title,
        "summary": credit + ". El contenido detallado debe consultarse en el medio enlazado.",
        "why": "Tema en seguimiento; el contexto y el impacto requieren comprobación editorial independiente.",
        "next": "Consultar el artículo enlazado y nuevas actualizaciones del medio antes de compartir datos no verificados.",
        "sources": [{"name": source_label, "url": url}],
        "verification": "source_only",
        "sourcePublishedAtBogota": date.isoformat(timespec="minutes"),
    }


def sync(db: dict, feeds: list, now: datetime, fixture=None) -> tuple[dict, dict]:
    now = now.astimezone(TZ)
    known = {x.get("id") for x in db.get("news", [])}
    seen_title = {norm_text(x.get("title", "")) for x in db.get("news", [])}
    candidates = []
    ok_sources = 0
    failures = []
    for name, category, url in feeds:
        try:
            if fixture is not None:
                raw = Path(fixture).read_bytes()
            else:
                request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml,application/atom+xml,application/xml,text/xml"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    raw = response.read(1_200_000)
            parsed = parse_feed(raw, name, category)
            if not parsed:
                raise ValueError("el feed no trae entradas utilizables")
            ok_sources += 1
            for row in parsed:
                item = safe_article(row, category, now, "news.google.com" in url)
                if item:
                    candidates.append((row[2].timestamp(), item))
        except (ValueError, OSError, ET.ParseError, UnicodeError, TimeoutError) as e:
            failures.append(f"{name}: {e}")
    if not ok_sources:
        raise RuntimeError("Ninguna fuente RSS respondió: NO cambiar la página pública. " + " | ".join(failures))
    counts = {k: 0 for k in PER_CATEGORY}
    added = []
    for _, item in sorted(candidates, key=lambda x: x[0], reverse=True):
        cat = item["category"]
        title_norm = norm_text(item["title"])
        if len(added) >= MAX_ITEMS_PER_RUN or counts.get(cat, 0) >= PER_CATEGORY.get(cat, 1):
            continue
        if item["id"] in known or title_norm in seen_title:
            continue
        seen_title.add(title_norm)
        known.add(item["id"])
        counts[cat] = counts.get(cat, 0) + 1
        added.append(item)
    db.setdefault("news", [])
    db["news"] = added + db["news"]
    # editionDate mantiene la fecha de la ÚLTIMA EDICIÓN VERIFICADA.
    db["autoSyncCheckedAtBogota"] = now.isoformat(timespec="minutes")
    if added:
        db["lastNewSourceAtBogota"] = now.isoformat(timespec="minutes")
    db["autoSyncOkSources"] = ok_sources
    db["autoSyncFailedSources"] = len(failures)
    db["siteVersion"] = "3.0"
    return db, {"added": len(added), "total": len(db["news"]), "feeds_ok": ok_sources, "feed_errors": failures}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="noticias.json")
    parser.add_argument("--fixture", help="RSS de prueba local; impide acceso a Internet")
    parser.add_argument("--now", help="Hora de prueba YYYY-MM-DDTHH:MM:SS-05:00")
    args = parser.parse_args()
    path = Path(args.data)
    db = json.loads(path.read_text(encoding="utf-8"))
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(TZ)
    feeds = [RSS[0]] if args.fixture else RSS
    try:
        db, report = sync(db, feeds, now, args.fixture)
    except Exception as e:
        print("NO PUBLICAR: " + str(e), file=sys.stderr)
        return 1
    path.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
