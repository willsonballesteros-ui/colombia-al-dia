#!/usr/bin/env python3
"""Select only reviewed replacements; never promote discovery-only items."""
from __future__ import annotations
import argparse
import copy
import json
import tempfile
import time
from urllib.parse import urlsplit
from functools import lru_cache
from pathlib import Path
from scripts.orbiuno_import_daily import ROOT, import_edition, validated
from scripts.orbiuno_media_assets import stage, fetch

COUNT = 6
MAX_RESERVES = 12

def select(doc, probe):
    if doc.get("sourceOnly") is not False:
        raise ValueError("Edición sin revisión editorial")
    primary = doc.get("news")
    reserve = doc.get("reserveNews", [])
    if not isinstance(primary, list) or len(primary) != COUNT or not isinstance(reserve, list):
        raise ValueError("Se requieren seis titulares y una lista de reservas")
    if len(reserve) > MAX_RESERVES:
        raise ValueError("Demasiadas reservas")
    selected, failures, ids, urls = [], [], set(), set()
    # O(n), n <= 18. Each candidate is tried at most once.
    for candidate in primary + reserve:
        if len(selected) == COUNT:
            break
        if not isinstance(candidate, dict):
            failures.append({"id": None, "reason": "Formato inválido"})
            continue
        item = copy.deepcopy(candidate)
        try:
            ident = item["id"]
            source = item["sources"][0]["url"]
            if ident in ids or source in urls:
                raise ValueError("Duplicado")
            item["priority"] = 1
            single = {**doc, "news": [item]}
            validated(single, today=doc["editionDate"], expected_count=1)
            probe(single, item)
            item["priority"] = len(selected) + 1
            selected.append(item)
            ids.add(ident)
            urls.add(source)
        except (ValueError, OSError, RuntimeError, KeyError, TypeError, IndexError) as exc:
            failures.append({"id": item.get("id"), "reason": str(exc)[:250]})
            print("CANDIDATE_REJECTED", item.get("id"), type(exc).__name__, str(exc)[:160], flush=True)
    if len(selected) != COUNT:
        raise RuntimeError(f"Solo {len(selected)} de {COUNT} candidatos aprobados; faltan reservas verificadas")
    result = {**doc, "news": selected}
    validated(result)
    return result, failures

def recover(edition, news, output):
    doc = json.loads(edition.read_text(encoding="utf-8"))
    base = json.loads(news.read_text(encoding="utf-8"))
    # Never replace any news already present in the historical published slot.
    if any(n.get("date")==doc["editionDate"] and n.get("editionSlot")==doc["editionSlot"] and
           n.get("verification")=="editorial_verified" for n in base["news"]):
        raise ValueError("Franja ya registrada; recuperar publicación sin sustituir")
    @lru_cache(maxsize=40)
    def cached(url):
        # The original getter pauses Commons metadata calls; retain this limit.
        if urlsplit(url).hostname == 'commons.wikimedia.org':
            time.sleep(1.4)
        return fetch(url)
    with tempfile.TemporaryDirectory(prefix=".orbiuno-preflight-", dir=ROOT) as folder:
        tmp = Path(folder)
        ep, np = tmp/"edition.json", tmp/"news.json"
        def probe(single, item):
            ep.write_text(json.dumps(single,ensure_ascii=False),encoding="utf-8")
            np.write_text(json.dumps({"news":[item]},ensure_ascii=False),encoding="utf-8")
            stage(ep,np,tmp/"assets",getter=cached,expected_count=1)
        chosen, failures = select(doc, probe)
        ep.write_text(json.dumps(chosen,ensure_ascii=False),encoding="utf-8")
        from datetime import datetime
        from zoneinfo import ZoneInfo
        combined = import_edition(base,chosen,today=datetime.now(ZoneInfo("America/Bogota")).date().isoformat())
        np.write_text(json.dumps(combined,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        stage(ep,np,output,getter=cached)
        # Atomically replace the working news file only after all six pass.
        pending = news.with_suffix(".pending")
        pending.write_bytes(np.read_bytes())
        pending.replace(news)
    (output/"selection.json").write_text(json.dumps({"selected":[n["id"] for n in chosen["news"]],"rejected":failures},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("SIX_WITH_VERIFIED_RESERVES",len(failures),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--edition",type=Path,required=True)
    p.add_argument("--news",type=Path,default=ROOT/"noticias.json")
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    recover(args.edition.resolve(),args.news.resolve(),args.out.resolve())

if __name__=="__main__":
    main()
