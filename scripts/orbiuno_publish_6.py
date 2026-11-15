#!/usr/bin/env python3
"""Una sola orden: conciliar web/voz/video, dry-run Meta y publicar sin duplicados.

No se reintenta media_publish cuando el resultado es ambiguo. Requiere seis
noticias del día, MP4 final, web sincronizada, secret de Instagram y autorización.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SITE="https://colombia-al-dia.pages.dev/"
REPO="willsonballesteros-ui/colombia-al-dia"
SLOT={"08:00":"0800","12:00":"1200","18:00":"1800"}
BOGOTA=ZoneInfo("America/Bogota")


def get(url,limit=4_000_000):
    req=Request(url,headers={"User-Agent":"ORBIUNO-Verify/1.0",
                             "Cache-Control":"no-cache"})
    with urlopen(req,timeout=25) as resp:
        if resp.status!=200:
            raise RuntimeError(f"HTTP {resp.status} en sitio público")
        return resp.read(limit)


def site_ready(expected_ids):
    homepage=get(SITE).decode("utf-8")
    match=re.search(r'<script[^>]*id="initial-news"[^>]*>(.*?)</script>',
                    homepage,re.S)
    if not match:
        raise RuntimeError("La web pública no tiene datos de noticias embebidos")
    db=json.loads(match.group(1))
    day=datetime.now(BOGOTA).date().isoformat()
    if db.get("editionDate")!=day:
        raise RuntimeError("La web pública todavía muestra otra fecha")
    rows=sorted((n for n in db.get("news",[])
                 if n.get("date")==day and n.get("editionSlot")=="08:00" and
                 n.get("verification")=="editorial_verified"),
                key=lambda n:n.get("priority",999))
    ids=[n["id"] for n in rows]
    if ids!=expected_ids:
        raise RuntimeError("IDs/orden de las noticias no coinciden con el MP4")
    for n in rows:
        if ('id="noticia-'+n["id"]+'"') not in homepage:
            raise RuntimeError("Una noticia falta en la web pública: "+n["id"])
        url=(n.get("sources") or [{}])[0].get("url","")
        if url not in homepage:
            # El JSON embebido puede codificar caracteres; comprobar estructura.
            if not url.startswith("https://"):
                raise RuntimeError("Fuente sin enlace HTTPS")
    voice=json.loads(get(SITE+"media/web-voice/manifest.json").decode("utf-8"))
    for n in rows:
        item=voice.get("items",{}).get(n["id"])
        if not item or not item.get("text") or not item.get("url"):
            raise RuntimeError("Audio pregrabado no disponible en web: "+n["id"])
        # Descarga un fragmento para comprobar que existe, sin leer su voz.
        audio_url=SITE+item["url"].removeprefix("./")
        if not get(audio_url,limit=1024):
            raise RuntimeError("MP3 sin contenido público: "+n["id"])
    if "audio-fix.js" not in homepage:
        raise RuntimeError("Web sin reproductor de audio")
    return {"site":SITE,"newsIds":ids,"voiceItems":len(rows)}


def caption_for(manifest):
    pieces=["ORBIUNO | "+manifest["edition"]+" | Seis noticias verificadas",
            "Colombia y el mundo. Escucha las noticias completas en nuestra web:",
            SITE]
    for idx,n in enumerate(manifest["news"],1):
        pieces.append(f"{idx}. {n['title']}\nFuente: {n['sourceUrl']}")
    pieces.append("Síguenos en @resumen.noticias. #ORBIUNO #NoticiasColombia")
    text="\n\n".join(pieces)
    if len(text)>2000:
        raise RuntimeError("Pie de foto excede el límite seguro")
    return text


def publish(manifest_path, *, dry_only=False):
    p=Path(manifest_path)
    manifest=json.loads(p.read_text(encoding="utf-8"))
    day=datetime.now(BOGOTA).date().isoformat()
    if manifest.get("edition")!=day or manifest.get("newsCount")!=6:
        raise RuntimeError("Edición caducada o sin seis noticias")
    slot=manifest.get("slot")
    if slot not in SLOT:
        raise RuntimeError("Horario no autorizado")
    folder=p.parent
    file=folder/manifest["video"]
    if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=manifest["sha256"]:
        raise RuntimeError("MP4 ausente o hash diferente")
    if not (50<=float(manifest.get("duration",0))<=60):
        raise RuntimeError("Duración del video fuera de 50 a 60 segundos")
    expected=manifest["newsIds"]
    if len(expected)!=6 or len(set(expected))!=6:
        raise RuntimeError("IDs duplicados en Reel")
    report={"edition":day,"slot":slot,"newsIds":expected,"state":"PRECHECK",
            "timestampBogota":datetime.now(BOGOTA).isoformat()}
    outcome=folder/"publication_report.json"
    def save():
        outcome.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    save()
    try:
        # Cloudflare puede tardar tras push. No se elude la comprobación.
        for attempt in range(10):
            try:
                report["web"]=site_ready(expected)
                break
            except (OSError,ValueError,RuntimeError) as exc:
                if attempt==9: raise
                time.sleep(18)
        url=(f"https://raw.githubusercontent.com/{REPO}/main/media/"
             f"{day}/{file.name}")
        # Debe estar públicamente disponible en un hosting HTTPS.
        if not get(url,limit=1024):
            raise RuntimeError("MP4 aún no accesible por Meta")
        if not os.getenv("ORBIUNO_IG_ACCESS_TOKEN") or not os.getenv("ORBIUNO_IG_USER_ID"):
            raise RuntimeError("Faltan GitHub Secrets de Instagram")
        edition_key=f"ORBIUNO-{day}-{SLOT[slot]}"
        caption=caption_for(manifest)
        args=[sys.executable,str(ROOT/"scripts/publish_meta_direct.py"),
              "--video-url",url,"--caption",caption,"--edition-key",edition_key]
        dry=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,check=False,timeout=120)
        if dry.returncode:
            raise RuntimeError("Dry-run Meta falló: "+dry.stderr[-500:])
        data=json.loads(dry.stdout.strip().splitlines()[-1])
        report["dryRun"]=data
        if data.get("state")=="ALREADY_PUBLISHED":
            report.update(state="ALREADY_PUBLISHED",media_id=data.get("id"),permalink=data.get("url"))
            save();return report
        if data.get("state")!="DRY_RUN_OK":
            raise RuntimeError("Meta no confirmó dry-run")
        if dry_only:
            report["state"]="DRY_RUN_OK"
            save();return report
        # Una sola llamada final. No repetir ante resultado ambiguo.
        report["state"]="PUBLISH_ATTEMPT_STARTED";save()
        live=subprocess.run(args+["--publish"],cwd=ROOT,capture_output=True,text=True,
                            check=False,timeout=850)
        if live.returncode:
            report.update(state="PUBLISH_UNKNOWN",error="Meta rechazó o no confirmó el envío; conciliar antes de repetir",detail=live.stderr[-350:])
            save();raise RuntimeError(report["error"])
        published=json.loads(live.stdout.strip().splitlines()[-1])
        if published.get("state") not in ("PUBLISHED","ALREADY_PUBLISHED") or not published.get("id") or not published.get("url"):
            report.update(state="PUBLISH_UNKNOWN",error="Meta no devolvió ID y permalink")
            save();raise RuntimeError(report["error"])
        report.update(state="PUBLISHED_VERIFIED",media_id=published["id"],permalink=published["url"])
        save();return report
    except Exception as exc:
        if report["state"]!="PUBLISH_UNKNOWN" and report["state"]!="PUBLISH_ATTEMPT_STARTED":
            report["state"]="BLOCKED"
            report["error"]=str(exc)[:700]
        save()
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",required=True)
    parser.add_argument("--dry-only",action="store_true")
    a=parser.parse_args()
    result=publish(a.manifest,dry_only=a.dry_only)
    print(json.dumps({k:result.get(k) for k in ("state","media_id","permalink")},ensure_ascii=False))


if __name__=="__main__":
    main()
