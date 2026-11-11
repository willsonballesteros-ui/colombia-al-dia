#!/usr/bin/env python3
"""ORBIUNO 4 noticias: MP4 real 9:16 con locución Camila Vega proporcionada.

Uso:
  python scripts/render_orbiuno_4.py editions/2026-11-10-2000.json --output dist/orbiuno.mp4
  python scripts/render_orbiuno_4.py editions/2026-11-10-2000.json --output dist/orbiuno.mp4 --release

No sintetiza voz ni inventa imágenes; consume archivos aprobados y falla cerrado.
Solo --release exige la compuerta editorial completa.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shutil, subprocess, tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont, ImageOps

W, H, FPS = 720, 1280, 24
NAVY = (7, 25, 57)
CYAN = (59, 226, 207)
WHITE = (248, 251, 255)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
ALLOWED_IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_AUDIO = {".wav", ".mp3", ".m4a"}
VOICE_ID = "6ce26db0cb6f4e7881b85452619f7f19"
RELEASE_GATES = ["editorialApproved", "imagesApproved", "voiceApproved", "pronunciationApproved", "webSyncApproved", "finalReviewApproved"]


def run(*args):
    return subprocess.run(args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def local_asset(base: Path, rel: str, extensions: set[str]) -> Path:
    if not isinstance(rel, str) or not rel or rel.startswith(("/", "~")):
        raise ValueError("Archivo local inválido")
    root = base.resolve()
    dest = (root / rel).resolve()
    if not dest.is_relative_to(root) or dest.suffix.lower() not in extensions or not dest.is_file():
        raise ValueError("Archivo ausente o ruta no autorizada: " + repr(rel))
    if dest.stat().st_size < 1000:
        raise ValueError("Archivo demasiado pequeño: " + str(dest))
    return dest


def url_ok(value: str) -> bool:
    if not isinstance(value, str):
        return False
    p = urlsplit(value)
    return p.scheme == "https" and bool(p.hostname) and p.hostname not in {"news.google.com", "google.com"} and p.path not in ("", "/")


def validate(data: dict, base: Path, release: bool = False):
    if data.get("brand") != "ORBIUNO" or data.get("voice", {}).get("name") != "Camila Vega":
        raise ValueError("Marca o voz distinta de la aprobada")
    if data["voice"].get("id") != VOICE_ID:
        raise ValueError("Identificador Camila Vega incorrecto")
    if float(data["voice"].get("speed", 0)) != 1.25:
        raise ValueError("Velocidad aprobada: 1.25x")
    if float(data["voice"].get("recordedAtSpeed", 0)) not in (1.0, 1.25):
        raise ValueError("Indicar velocidad original 1.0 o 1.25")
    day = data["editionDate"]
    date.fromisoformat(day)
    if data.get("slot") not in ("08:00", "16:00", "18:00", "20:00"):
        raise ValueError("Franja editorial desconocida")
    items = data.get("news", [])
    if len(items) != 4 or len({x.get("id") for x in items}) != 4:
        raise ValueError("Cada Reel debe contener exactamente cuatro noticias distintas")
    intro = data.get("intro", {})
    outro = data.get("outro", {})
    if not intro.get("narration", "").strip().lower().startswith("orbiuno"):
        raise ValueError("Inicio debe pronunciar 'Orbiuno' como palabra, no deletreado")
    if re.search(r"\bo[\s.,-]+r[\s.,-]+b[\s.,-]+i[\s.,-]+u[\s.,-]+n[\s.,-]+o\b", intro["narration"], re.I):
        raise ValueError("No deletrear ORBIUNO")
    end = outro.get("narration", "").lower()
    if not all(term in end for term in ("síguenos", "escuchar", "colombia-al-dia", "pages", "dev")):
        raise ValueError("Cierre sin invitación a seguir y escuchar en la web exacta")
    sources = []
    for i, x in enumerate(items, 1):
        if x.get("date") != day or x.get("verification") != "editorial_verified":
            raise ValueError(f"Noticia {i}: fecha o verificación no coinciden")
        if not x.get("title") or not x.get("narration"):
            raise ValueError(f"Noticia {i}: titular y locución obligatorios")
        s = x.get("source", {})
        if not s.get("name") or not url_ok(s.get("url")):
            raise ValueError(f"Noticia {i}: fuente directa y específica obligatoria")
        sources.append(s["url"])
        img = x.get("image", {})
        if img.get("rightsVerified") is not True or not img.get("credit") or not img.get("license") or not url_ok(img.get("sourceUrl")):
            raise ValueError(f"Noticia {i}: falta licencia, autoría y procedencia de imagen")
        local_asset(base, img.get("file"), ALLOWED_IMAGES)
        local_asset(base, x.get("audioFile"), ALLOWED_AUDIO)
    if len(set(sources)) != 4:
        raise ValueError("Fuente duplicada o cuatro noticias sin fuentes independientes")
    for x in (intro, outro):
        local_asset(base, x.get("audioFile"), ALLOWED_AUDIO)
    music = data.get("music")
    if music:
        if not music.get("rightsVerified") or not music.get("credit") or not music.get("license") or not url_ok(music.get("sourceUrl")):
            raise ValueError("Música sin procedencia o derechos verificables")
        local_asset(base, music.get("file"), ALLOWED_AUDIO)
    if release:
        if not music:
            raise ValueError("PUBLICACIÓN BLOQUEADA: falta música autorizada con mezcla de volumen bajo")
        missing = [g for g in RELEASE_GATES if data.get("approval", {}).get(g) is not True]
        if missing:
            raise ValueError("PUBLICACIÓN BLOQUEADA: faltan controles: " + ", ".join(missing))
    return True


def font(size, bold=False):
    return ImageFont.truetype(BOLD if bold else FONT, size)


def wrap(d, text, size, maxwidth, maxlines):
    face = font(size, True)
    lines, line = [], ""
    for word in text.split():
        candidate = (line + " " + word).strip()
        if d.textbbox((0, 0), candidate, font=face)[2] < maxwidth:
            line = candidate
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    if len(lines) > maxlines:
        lines = lines[:maxlines]
        while d.textbbox((0, 0), lines[-1] + "…", font=face)[2] > maxwidth:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "…"
    return lines, face


def write_lines(d, text, xy, maxwidth=640, maxlines=3, size=46, gap=18, fill=WHITE):
    x, y = xy
    for line, face in [wrap(d, text, size, maxwidth, maxlines)]:
        for part in line:
            d.text((x, y), part, font=face, fill=fill)
            y += size + gap
    return y


def card_base():
    im = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 12), fill=CYAN)
    d.text((42, 45), "ORBIUNO", font=font(55, True), fill=WHITE)
    d.text((47, 116), "COLOMBIA Y EL MUNDO", font=font(21, True), fill=CYAN)
    return im


def make_card(entry, day, i, out):
    im = card_base()
    with Image.open(entry["imagePath"]) as original:
        photo = ImageOps.fit(original.convert("RGB"), (720, 680), Image.Resampling.LANCZOS)
    im.paste(photo, (0, 188))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 188, W, 225), fill=NAVY)
    d.text((45, 192), f"{i:02d}/04 · {entry['category'].upper()[:24]}", font=font(20, True), fill=WHITE)
    d.rectangle((0, 845, W, H), fill=NAVY)
    write_lines(d, entry["title"], (42, 880), maxwidth=640, maxlines=3, size=42, gap=8)
    d.text((43, 1092), "FUENTE: " + entry["source"]["name"][:42], font=font(18, True), fill=CYAN)
    d.text((43, 1130), "IMAGEN: " + entry["image"]["credit"][:47], font=font(17), fill=WHITE)
    d.text((43, 1170), day + " · @resumen.noticias", font=font(17), fill=WHITE)
    d.rectangle((40, 1220, 680, 1228), fill=(41, 66, 83))
    d.rectangle((40, 1220, 40 + i * 160, 1228), fill=CYAN)
    im.save(out)


def make_cover(text, day, out, closing=False):
    im = card_base(); d=ImageDraw.Draw(im)
    title = "SÍGUENOS Y ESCUCHA" if closing else "LAS NOTICIAS DE HOY"
    d.text((47, 335), title, font=font(41, True), fill=WHITE)
    d.text((47, 450), "4 NOTICIAS REALES", font=font(33, True), fill=CYAN)
    if closing:
        write_lines(d, "@resumen.noticias", (47, 590), size=34, maxlines=2)
        write_lines(d, "colombia-al-dia.pages.dev", (47, 680), size=25, maxlines=2, fill=CYAN)
        write_lines(d, "Lee y escucha las noticias en voz alta", (47, 795), size=27, maxlines=3)
    d.text((47, 1150), day + " · COLOMBIA", font=font(24, True), fill=WHITE)
    im.save(out)


def duration(path):
    p = run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path))
    return float(p.stdout.strip())


def render(manifest: Path, output: Path, release: bool=False):
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        raise RuntimeError("ffmpeg y ffprobe son necesarios")
    manifest=manifest.resolve(); base=manifest.parent
    data=json.loads(manifest.read_text(encoding="utf-8"))
    validate(data,base,release)
    output=output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    # Cada archivo de Camila fue sintetizado a 1.0x o ya a 1.25x, nunca usar otra voz.
    source_speed=float(data["voice"]["recordedAtSpeed"])
    multiplier=1.25 / source_speed
    stages = [data["intro"]] + data["news"] + [data["outro"]]
    total = sum(duration(local_asset(base, x["audioFile"], ALLOWED_AUDIO))/multiplier for x in stages)
    # No estirar imágenes ni narración artificialmente para fingir 50-60 s.
    if not 50 <= total <= 60:
        raise ValueError(f"Audio real a 1.25x dura {total:.1f}s; debe quedar entre 50 y 60. Ajustar guion y regenerar los seis audios.")
    with tempfile.TemporaryDirectory(prefix="orbiuno4-") as temp:
        t=Path(temp); parts=[]
        for idx, scene in enumerate(stages):
            png=t/f"scene{idx}.png"
            if idx in (0, 5):make_cover(scene["narration"],data["editionDate"],png,idx==5)
            else:
                item=dict(scene)
                item["imagePath"]=local_asset(base,scene["image"]["file"],ALLOWED_IMAGES)
                make_card(item,data["editionDate"],idx,png)
            audio=local_asset(base,scene["audioFile"],ALLOWED_AUDIO)
            part=t/f"p{idx}.mp4"
            # Audio a 1.25x SIN modificar timbre con pitch; clips independientes por noticia.
            run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-loop","1","-framerate",str(FPS),"-i",str(png),"-i",str(audio),
                "-filter_complex",f"[1:a]atempo={multiplier:.5f},aresample=48000[a]",
                "-map","0:v","-map","[a]","-c:v","libx264","-preset","veryfast","-crf","25",
                "-pix_fmt","yuv420p","-r",str(FPS),"-c:a","aac","-b:a","128k",
                "-ar","48000","-ac","2","-shortest","-movflags","+faststart",str(part))
            parts.append(part)
        concat=t/"concat.txt"
        concat.write_text("".join("file '"+str(p).replace("'","'\\''")+"'\n" for p in parts), encoding="utf-8")
        clean = t/"no-music.mp4"
        run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y", "-f","concat","-safe","0","-i",str(concat),
            "-c:v","libx264","-preset","veryfast","-crf","25","-pix_fmt","yuv420p",
            "-c:a","aac","-b:a","128k","-movflags","+faststart",str(clean))
        if data.get("music"):
            bed=local_asset(base,data["music"]["file"],ALLOWED_AUDIO)
            # Bed autorizado a -24 dB aprox. bajo la narración: nunca tapa la voz.
            run("ffmpeg","-hide_banner","-loglevel","error","-nostdin","-y",
                "-i",str(clean),"-stream_loop","-1","-i",str(bed),
                "-filter_complex","[0:a]aresample=48000[voice];[1:a]volume=0.06,aresample=48000[bed];[voice][bed]amix=inputs=2:duration=first:dropout_transition=0[a]",
                "-map","0:v","-map","[a]","-c:v","copy","-c:a","aac","-b:a","128k","-movflags","+faststart",str(output))
        else:
            shutil.copyfile(clean,output)
    probe = json.loads(run("ffprobe","-v","error","-show_entries","format=duration:stream=codec_name,codec_type,width,height", "-of","json",str(output)).stdout)
    types={x.get("codec_type") for x in probe.get("streams",[])}
    video=next((x for x in probe.get("streams",[]) if x.get("codec_type")=="video"),{})
    final_duration=float(probe.get("format",{}).get("duration",0))
    if types!={"audio","video"} or video.get("width")!=W or video.get("height")!=H or not 50<=final_duration<=61:
        output.unlink(missing_ok=True)
        raise RuntimeError("El MP4 no pasó la inspección de medios")
    checksum=hashlib.sha256(output.read_bytes()).hexdigest()
    report={"editionDate":data["editionDate"],"slot":data["slot"],"newsIds":[x["id"] for x in data["news"]],
            "voice":"Camila Vega","speechSpeed":1.25,"durationSec":round(final_duration,2),"width":W,"height":H,
            "sha256":checksum,"status":"APPROVED_FOR_MANUAL_PUBLICATION" if release else "PREVIEW_ONLY_NOT_APPROVED",
            "approvalGates":data.get("approval",{})}
    output.with_suffix(".report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n", encoding="utf-8")
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument("manifest",type=Path);parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--release",action="store_true");args=parser.parse_args()
    try:print(json.dumps(render(args.manifest,args.output,args.release),ensure_ascii=False,indent=2))
    except (ValueError,RuntimeError,subprocess.CalledProcessError,OSError,KeyError) as exc:
        parser.exit(2,"PRODUCCIÓN BLOQUEADA: "+str(exc)+"\n")

if __name__=="__main__":main()
