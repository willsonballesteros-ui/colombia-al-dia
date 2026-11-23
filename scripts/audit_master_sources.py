#!/usr/bin/env python3
"""Auditoría de accesibilidad, no verificación editorial ni publicación."""
import argparse
import json
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
AGENT = "ORBIUNO-Newsroom/1.0 (public source accessibility audit)"
MAX_BYTES = 65536

def read_sources(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))["sources"]
    if len(rows) != 80 or {r["number"] for r in rows} != set(range(1, 81)):
        raise ValueError("Se requieren exactamente las 80 fuentes numeradas")
    urls = [r["url"] for r in rows]
    if len(set(urls)) != 80:
        raise ValueError("URLs repetidas")
    for url in urls:
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname or p.username or p.password or p.port not in (None, 443):
            raise ValueError("URL inválida: " + url)
    return rows

def check(row, opener=urlopen):
    result = {**row, "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "http_status": None, "status": "network_error", "editorial_verified": False}
    try:
        req = Request(row["url"], headers={"User-Agent": AGENT, "Accept": "text/html,application/xhtml+xml,application/xml"})
        with opener(req, timeout=12) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            raw = response.read(MAX_BYTES)
            result.update(http_status=status, final_url=response.geturl(),
                          content_type=content_type, sampled_bytes=len(raw))
            sample = raw.decode("utf-8", errors="replace").lower()
            challenge = bool(re.search(r"just a moment|verify you are human|checking your browser|captcha", sample[:12000]))
            if status == 200 and raw and not challenge and any(x in content_type.lower() for x in ("html", "xml", "text")):
                result["status"] = "content_response"
            elif challenge:
                result["status"] = "access_challenge"
            else:
                result["status"] = "other_response"
    except HTTPError as exc:
        result.update(http_status=exc.code, status="rate_limited" if exc.code == 429 else "http_error",
                      retry_after=exc.headers.get("Retry-After") if exc.headers else None)
        exc.close()
    except (OSError, URLError, ValueError) as exc:
        result["error_type"] = type(exc).__name__
    return result

def audit(rows, workers=6, checker=check):
    # O(n) requests; bounded concurrency, no retries of blocked sources.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        records = list(pool.map(checker, rows))
    counts = {}
    for item in records:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    return {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": "bounded GET; accessibility only, not article verification",
            "total": len(records), "counts": counts, "sources": records}

class AuditTests(unittest.TestCase):
    def test_catalog(self):
        self.assertEqual(len(read_sources(ROOT / "editorial/fuentes-maestras.json")), 80)
    def test_counts(self):
        rows = read_sources(ROOT / "editorial/fuentes-maestras.json")
        report = audit(rows, checker=lambda r: {**r, "status": "content_response" if r["number"] % 2 else "http_error"})
        self.assertEqual(report["counts"], {"content_response": 40, "http_error": 40})
        self.assertEqual([x["number"] for x in report["sources"]], list(range(1,81)))
    def test_http_block(self):
        def blocked(*args, **kwargs):
            raise HTTPError("https://example.org", 429, "limited", {"Retry-After":"120"}, None)
        record = check({"url":"https://example.org"}, blocked)
        self.assertEqual(record["status"], "rate_limited")
        self.assertEqual(record["retry_after"], "120")
        self.assertFalse(record["editorial_verified"])
    def test_duplicate_rejected(self):
        rows = read_sources(ROOT / "editorial/fuentes-maestras.json")
        rows[1]["url"] = rows[0]["url"]
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "sources.json"
            p.write_text(json.dumps({"sources":rows}), encoding="utf-8")
            with self.assertRaises(ValueError):
                read_sources(p)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", default=str(ROOT / "editorial/fuentes-maestras.json"))
    parser.add_argument("--out", default="dist/source-audit.json")
    parser.add_argument("--test", action="store_true")
    args = parser.parse_args()
    if args.test:
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuditTests)
        return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1
    report = audit(read_sources(args.sources))
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    temp.replace(output)
    print(json.dumps({"total": report["total"], "counts": report["counts"]}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
