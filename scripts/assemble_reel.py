#!/usr/bin/env python3
"""Reel ORBIUNO: presentadora AUTORIZADA hablando + diez láminas breves.

NO inventa ni sintetiza un rostro. Requiere intro.mp4 real, audio verdadero
y manifest de autorización editorial. Sin intro válido NO crea un "Reel hablado".
La distribución en Metricool es un proceso separado y verificable.
"""
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
W,H=720,1280


def run(*args):
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)


def probe(path):
    try:
        x=run("ffprobe","-v","error","-show_entries",
              "format=duration:stream=codec_type","-of","json",str(path))
        return json.loads(x.stdout)
    except (OSError,subprocess.CalledProcessError,ValueError):
        raise RuntimeError("No se pudo comprobar la integridad multimedia de "+str(path))


def has_audio_video(data):
    kinds={x.get("codec_type") for x in data.get("streams",[])}
    return "audio" in kinds and "video" in kinds


def make_slides(daydir):
    slides=[daydir/f"top10-{i:02d}.png" for i in range(1,11)]
    if not all(x.is_file() for x in slides):
        raise RuntimeError("No están las diez láminas de esta edición")
    return slides


def make_part(input_path,out_path,seconds=None,still=False):
    args=["ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y"]
    if still:
        args+=["-loop","1","-framerate","24","-i",str(input_path),
               "-f","lavfi","-i","anullsrc=channel_layout=stereo:sample_rate=48000"]
    else:
        args+=["-i",str(input_path)]
    if seconds is not None:
        args+=["-t",str(seconds)]
    args+=["-vf","scale=720:1280:force_original_aspect_ratio=decrease,"
           "pad=720:1280:(ow-iw)/2:(oh-ih)/2:color=0x081d49,setsar=1,fps=24",
           "-ar","48000","-ac","2","-c:a","aac","-b:a","96k",
           "-c:v","libx264","-pix_fmt","yuv420p","-preset","fast","-crf","27",
           "-movflags","+faststart",str(out_path)]
    run(*args)


def make_photo_intro(photo, narration, out_path):
    """Fallback honesto: foto autorizada + voz + onda animada, NO lip-sync."""
    run(
        "ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
        "-loop","1","-framerate","24","-i",str(photo),
        "-i",str(narration),
        "-filter_complex",
        "[0:v]scale=900:1600:force_original_aspect_ratio=increase,"
        "crop=720:1280,zoompan=z='min(zoom+0.0006,1.07)':d=1:"
        "s=720x1280:fps=24,format=yuv420p[portrait];"
        "[1:a]asplit=2[voice][waveaudio];"
        "[waveaudio]showwaves=s=560x70:mode=line:rate=24:colors=white,"
        "format=rgba[wave];"
        "[portrait][wave]overlay=(W-w)/2:H-h-105:shortest=1[v]",
        "-map","[v]","-map","[voice]","-shortest",
        "-c:v","libx264","-preset","fast","-crf","25",
        "-c:a","aac","-b:a","128k","-pix_fmt","yuv420p",
        "-movflags","+faststart",str(out_path)
    )



def main():
    db=json.loads((ROOT/"noticias.json").read_text(encoding="utf-8"))
    day=db["editionDate"]
    local_today=datetime.now(ZoneInfo("America/Bogota")).date().isoformat()
    if day != local_today:
        raise RuntimeError(f"Reel prohibido para edición anterior: {day} != {local_today}")
    notes=sorted((n for n in db["news"] if n.get("date")==day
                  and n.get("verification")=="editorial_verified"),
                 key=lambda x:x.get("priority",999))
    if len(notes)!=10 or len({n["id"] for n in notes})!=10:
        raise RuntimeError("Reel requiere diez noticias editoriales distintas")
    daydir=ROOT/"media"/day
    intro=daydir/"presentadora-intro.mp4"
    rights=daydir/"presentadora-intro.json"
    fallback_photo=daydir/"presentadora-foto.jpg"
    fallback_audio=daydir/"presentadora-voz.wav"
    fallback_rights=daydir/"presentadora-foto.json"
    photo_mode=not intro.is_file()
    if photo_mode:
        if not all(x.is_file() for x in (fallback_photo,fallback_audio,fallback_rights)):
            raise RuntimeError("Falta video o foto y audio autorizados. No simular presentadora.")
        rights=fallback_rights
    elif not rights.is_file():
        raise RuntimeError("Falta manifiesto de derechos para el video de apertura")
    meta=json.loads(rights.read_text(encoding="utf-8"))
    required=["rightsVerified","consentVerified","voiceAuthorized",
              "scriptChecked","speaksAllTenHeadlines"]
    if photo_mode:
        required.append("imageRightsVerified")
    if not all(meta.get(k) is True for k in required):
        raise RuntimeError("Presentadora o locución sin derechos, consentimiento o guion verificados")
    if not str(meta.get("source","")).strip():
        raise RuntimeError("No se identificó proveedor o autor de la presentadora")
    if not photo_mode:
        info=probe(intro)
        if not has_audio_video(info) or float(info.get("format",{}).get("duration",0))<8:
            raise RuntimeError("El video de la presentadora requiere audio real y duración mínima")
    else:
        audio_info=probe(fallback_audio)
        if ("audio" not in {s.get("codec_type") for s in audio_info.get("streams",[])}) or float(audio_info.get("format",{}).get("duration",0))<8:
            raise RuntimeError("El audio del fallback debe incluir los titulares completos")
    slides=make_slides(daydir)
    media_fingerprint=(fallback_photo.read_bytes()+fallback_audio.read_bytes()) if photo_mode else intro.read_bytes()
    checksum=hashlib.sha256(
        media_fingerprint+rights.read_bytes()+
        "\n".join(str(n.get("executiveSummary") or "") for n in notes).encode("utf-8")
    ).hexdigest()
    out=daydir/"reel-presentadora.mp4"
    manifest=daydir/"reel-presentadora.json"
    if out.is_file() and manifest.is_file():
        old=json.loads(manifest.read_text(encoding="utf-8"))
        if old.get("fingerprint")==checksum:
            print("Reel de esta edición ya generado, sin duplicar")
            return
    with tempfile.TemporaryDirectory(prefix="orbiuno-reel-") as folder:
        tmp=Path(folder)
        parts=[]
        p=tmp/"000.mp4"
        if photo_mode:
            make_photo_intro(fallback_photo,fallback_audio,p)
        else:
            make_part(intro,p)
        parts.append(p)
        for i,slide in enumerate(slides,1):
            p=tmp/f"{i:03d}.mp4"
            make_part(slide,p,seconds=3,still=True)
            parts.append(p)
        filelist=tmp/"concat.txt"
        filelist.write_text("".join("file '"+str(x).replace("'","'\\''")+"'\n" for x in parts),encoding="utf-8")
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
            "-f","concat","-safe","0","-i",str(filelist),
            "-c:v","libx264","-c:a","aac","-pix_fmt","yuv420p",
            "-preset","fast","-crf","28","-movflags","+faststart",str(out))
    result=probe(out)
    if not has_audio_video(result):
        raise RuntimeError("El video exportado no contiene audio y video")
    manifest.write_text(json.dumps({
        "editionDate":day,
        "presenterProvider":meta["source"],
        "presenterRightsChecked":True,
        "speaksAllTenHeadlines":True,
        "scenes":11,
        "visualFormat":"photo_narrated_waveform_then_10_news" if photo_mode else "talking_presenter_then_10_news",
        "hasRealLipSync":False if photo_mode else bool(meta.get("realLipSync",False)),
        "presenterIntroType":"photo_with_voice_and_waveform" if photo_mode else "video_talking_presenter",
        "fingerprint":checksum,
        "video":"reel-presentadora.mp4",
        "durationSec":round(float(result["format"]["duration"]),2)
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Reel válido:",out.relative_to(ROOT),"11 escenas")


if __name__=="__main__":
    main()
