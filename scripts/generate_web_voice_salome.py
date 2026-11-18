#!/usr/bin/env python3
"""ORBIUNO: voz Salomé de artículos propios ÍNTEGROS, no los extractos del Reel.

En etapa de prueba no modifica la web pública. El workflow de aprobación
podrá usar este archivo solo tras VOICE_SAMPLE_APPROVED=true.
"""
from __future__ import annotations
import hashlib,json,os,shutil,sys
from pathlib import Path
from generate_voice import VOICE,TEMPO,synthesize,concat_full
from voice_render_guard import approved_audio
from prepare_site import original_article_ready
from narration_body import narration_for

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"media"/"web-voice"

def main():
    if os.environ.get("VOICE_SAMPLE_APPROVED")!="true":
        raise RuntimeError("NO GENERAR WEB: falta aprobación auditiva Salomé")
    approved_audio(ROOT/"build"/"audio",
                   expected_ids=["saludo"]+[f"n{i:02d}" for i in range(1,7)]+["despedida"])
    data=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    today=data["editionDate"]
    notes=[n for n in data["news"] if n.get("date")==today and n.get("verification")=="editorial_verified"]
    if len(notes)<6:
        raise RuntimeError("Faltan noticias completas verificadas para web")
    OUT.mkdir(parents=True,exist_ok=True)
    source=ROOT/"build"/"web_audio"
    source.mkdir(parents=True,exist_ok=True)
    manifest_file=OUT/"manifest.json"
    manifest=json.loads(manifest_file.read_text(encoding="utf-8")) if manifest_file.exists() else {"items":{}}
    manifest.update({"voice":VOICE,"language":"es-CO","baseRate":TEMPO})
    manifest.setdefault("items",{})
    results=[]
    for n in notes:
        text=narration_for(n,original_article_ready)
        if not text or len(text)<640:
            raise RuntimeError("Texto original completo no disponible: "+n["id"])
        key=hashlib.sha256((VOICE+text).encode("utf-8")).hexdigest()
        name=key[:20]+".mp3"
        destination=OUT/name
        if not destination.exists():
            info=synthesize(n["id"],text,source)
            shutil.copy2(source/info["file"],destination)
        else:
            info={"id":n["id"],"engine":"cached","seconds":0}
        manifest["items"][n["id"]]={"url":"./media/web-voice/"+name,"text":text,"sha256":hashlib.sha256(text.encode("utf-8")).hexdigest()}
        results.append(info)
    (source/"web_audio_report.json").write_text(json.dumps({"status":"ok","voice":VOICE,"segments":results},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    manifest_file.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("WEB_SALOME_OK",len(results))

if __name__=="__main__":
    try:main()
    except Exception as e:
        sys.exit("BLOCKED_WEB_SALOME: "+str(e))
