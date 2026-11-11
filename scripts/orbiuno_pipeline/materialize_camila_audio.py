#!/usr/bin/env python3
"""Materialize actual Camila Vega audio files from HeyGen-generated HTTPS links.

Use only during secure preview/CI. A downloaded audio file is not editorial
approval; keep publication and web deployment disabled until licensed media
and approved reporting are supplied.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAX_FILE_BYTES=20_000_000

def download_https(url: str) -> bytes:
    p=urllib.parse.urlparse(url)
    if p.scheme!="https" or p.hostname!="resource2.heygen.ai":
        raise ValueError("Audio URL must be from HeyGen allowed host")
    request=urllib.request.Request(url,headers={"User-Agent":"ORBIUNO-audio-materialization/1.0"})
    with urllib.request.urlopen(request,timeout=45) as response:
        if response.status!=200:
            raise RuntimeError("HeyGen returned HTTP "+str(response.status))
        chunks=[];total=0
        while True:
            block=response.read(1024*1024)
            if not block:
                break
            total+=len(block)
            if total>MAX_FILE_BYTES:
                raise ValueError("Audio exceeds 20 MB")
            chunks.append(block)
    data=b"".join(chunks)
    if len(data)<1000 or not data.startswith(b"RIFF") or data[8:12]!=b"WAVE":
        raise ValueError("Downloaded file is not a WAV")
    return data

def probe(path: Path) -> dict:
    out=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type",
                        "-of","json",str(path)],check=True,capture_output=True,text=True).stdout
    return json.loads(out)

def materialize(refs: Path, edition_dir: Path, zip_path: Path):
    data=json.loads(refs.read_text(encoding="utf-8"))
    clips=data.get("clips",[])
    if len(clips)!=12 or len({x["file"] for x in clips})!=12:
        raise ValueError("Exactly twelve unique voice clips required")
    if data.get("voiceId")!="6ce26db0cb6f4e7881b85452619f7f19":
        raise ValueError("Wrong Camila Vega voice ID")
    audio_dir=edition_dir/"audio"
    audio_dir.mkdir(parents=True,exist_ok=True)
    evidence=[]
    for clip in clips:
        filename=clip["file"]
        if Path(filename).name!=filename or not filename.endswith(".wav"):
            raise ValueError("Unsafe filename")
        dst=audio_dir/filename
        if dst.exists():
            raise ValueError("Refusing to overwrite existing audio")
        raw=download_https(clip["url"])
        dst.write_bytes(raw)
        meta=probe(dst)
        observed=float(meta["format"]["duration"])
        if not any(x.get("codec_type")=="audio" for x in meta.get("streams",[])):
            raise ValueError("WAV has no audio track")
        if abs(observed-float(clip["durationSec"]))>1.5:
            raise ValueError("Duration mismatch: "+filename)
        evidence.append({"file":filename,"durationSec":observed,"sha256":hashlib.sha256(raw).hexdigest(),
                         "voiceId":data["voiceId"],"text":clip["text"]})
    report=edition_dir/"audio_evidence.json"
    report.write_text(json.dumps({"status":"downloaded_audio_not_editorial_approval",
                                  "recordedAtSpeed":1.0,"renderSpeed":1.25,
                                  "clips":evidence},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    zip_path.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for path in sorted(audio_dir.iterdir()):
            z.write(path,path.relative_to(ROOT))
        z.write(report,report.relative_to(ROOT))
    print("DOWNLOADED 12 real WAV files. Audio-only ZIP (not a publishable edition): "+str(zip_path))
    print("SHA256 "+hashlib.sha256(zip_path.read_bytes()).hexdigest())

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--refs",type=Path,default=ROOT/"editions/2026-11-11-0800-5news-tts.json")
    p.add_argument("--edition-dir",type=Path,default=ROOT/"editions/2026-11-11-0800-5news")
    p.add_argument("--zip",type=Path,default=ROOT/"dist/orbiuno_camila_12_audio.zip")
    a=p.parse_args()
    materialize(a.refs,a.edition_dir,a.zip)
