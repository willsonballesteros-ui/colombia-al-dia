#!/usr/bin/env python3
"""Reel + Story ORBIUNO de una edición: 2 noticias principales + 2 breves, 1080x1920, voz femenina.

Sin avatares ni presentadora: tarjetas tipográficas, una escena por segmento de voz con la
duración medida del audio real. La Story es un clip complementario corto (portada + cierre).
Música opcional (--music) con ducking real (sidechaincompress, voz como detector) y -14 LUFS / -1 dBTP.
Uso:  python scripts/render_orbiuno_edition.py --edition 2026-11-07-0800 [--music assets/audio/orbiuno-pulse.m4a]
Salida: media/<editionId>/reel.mp4, story.mp4 y reel-manifest.json (con 'publishable').
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import orbiuno_edition as oe  # noqa: E402
import verify_voice as vv  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS, TAIL = 1080, 1920, 30, 0.35
X0, XR, SAFE_TOP, SAFE_BOTTOM = 100, 940, 260, 1530  # zona segura del manual vigente
BAR_Y = 1505
TEAL, TEAL2 = (6, 52, 60), (0, 96, 104)
AMBER, CORAL, MINT, WHITE = (255, 196, 0), (255, 94, 91), (64, 224, 176), (255, 255, 255)
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]


def run(*a, **k):
    return subprocess.run(a, check=True, capture_output=True, **k)


def font(size):
    for f in FONTS:
        if Path(f).is_file():
            return ImageFont.truetype(f, size)
    raise RuntimeError("No hay fuente TrueType (instale fonts-dejavu-core)")


def wrap(draw, text, fnt, width):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def background():
    img = Image.new("RGB", (W, H), TEAL)
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(TEAL[i] + (TEAL2[i] - TEAL[i]) * t) for i in range(3)))
    px.rectangle([0, 0, 24, H], fill=AMBER)
    return img


def chip(d, xy, text, fill, ink, size=40):
    f = font(size)
    w = d.textlength(text, font=f) + 56
    d.rounded_rectangle([xy[0], xy[1], xy[0] + w, xy[1] + size + 40], 40, fill=fill)
    d.text((xy[0] + 28, xy[1] + 16), text, font=f, fill=ink)
    return w


def card_overview(ed, news, active=None):
    img = background()
    d = ImageDraw.Draw(img)
    d.text((X0, SAFE_TOP), "ORBIUNO", font=font(140), fill=WHITE)
    d.text((X0 + 4, SAFE_TOP + 165), "Colombia al Día", font=font(52), fill=MINT)
    slot = ed["editionId"][-4:]
    d.text((X0 + 4, SAFE_TOP + 280), oe.long_date(ed["date"]).capitalize(), font=font(54), fill=WHITE)
    chip(d, (X0 + 4, SAFE_TOP + 370), f"EDICIÓN {oe.SLOT_LABEL[slot]}", AMBER, TEAL)
    y = SAFE_TOP + 550
    for i, n in enumerate(news, 1):
        accent = AMBER if i <= 2 else CORAL
        highlighted = i == active
        fill = accent if highlighted else (11, 72, 81)
        ink = TEAL if highlighted else WHITE if active is None else (176, 212, 214)
        d.rounded_rectangle([X0, y - 12, XR, y + 124], radius=22, fill=fill)
        d.ellipse([X0 + 14, y + 12, X0 + 70, y + 68], fill=TEAL if highlighted else accent)
        d.text((X0 + 30, y + 17), str(i), font=font(36), fill=accent if highlighted else TEAL)
        width = XR - (X0 + 92) - 16
        size = 44
        lines = wrap(d, n["reelShort"], font(size), width)
        while size > 30 and (len(lines) > 2 or any(d.textlength(line, font=font(size)) > width for line in lines)):
            size -= 2
            lines = wrap(d, n["reelShort"], font(size), width)
        for j, line in enumerate(lines[:2]):
            if (j == 1 and len(lines) > 2) or d.textlength(line, font=font(size)) > width:
                while d.textlength(line + "…", font=font(size)) > width:
                    line = line[:-1]
                line += "…"
            d.text((X0 + 92, y + 2 + j * 48), line, font=font(size), fill=ink)
        if highlighted:
            source = n["sources"][0]["name"]
            while d.textlength(source, font=font(24)) > width:
                source = source[:-2] + "…"
            d.text((X0 + 92, y + 98), source, font=font(24), fill=TEAL)
        y += 150
    return img


def card_outro(ed):
    img = background()
    d = ImageDraw.Draw(img)
    cx = X0 + 70
    d.polygon([(cx - 70, SAFE_TOP + 40), (cx + 70, SAFE_TOP + 40), (cx, SAFE_TOP + 170)], fill=AMBER)
    d.text((X0, SAFE_TOP + 250), "ESCUCHA CADA", font=font(84), fill=WHITE)
    d.text((X0, SAFE_TOP + 350), "NOTICIA EN", font=font(84), fill=AMBER)
    d.text((X0, SAFE_TOP + 450), "LA WEB", font=font(84), fill=WHITE)
    chip(d, (X0, SAFE_TOP + 640), "ENLACE DEL PERFIL", MINT, TEAL, 46)
    d.text((X0, SAFE_TOP + 820), "ORBIUNO", font=font(110), fill=WHITE)
    return img


def synth_kokoro(texts, outdir):
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    o = ort.SessionOptions()
    o.intra_op_num_threads, o.inter_op_num_threads = 2, 1
    o.enable_cpu_mem_arena = o.enable_mem_pattern = False
    o.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    sess = ort.InferenceSession(os.environ.get("ORBIUNO_VOICE_MODEL", "/tmp/kokoro-v1.0.onnx"),
                                sess_options=o, providers=["CPUExecutionProvider"])
    k = Kokoro.from_session(sess, os.environ.get("ORBIUNO_VOICE_BANK", "/tmp/voices-v1.0.bin"))
    speed = float(os.environ.get("ORBIUNO_VOICE_SPEED", "1.25"))  # velocidad NATIVA; no acelerar después
    out = []
    for i, t in enumerate(texts):
        audio, sr = k.create(t, "ef_dora", speed=speed, lang="es")
        p = outdir / f"seg{i}.wav"
        run("ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", "pipe:0",
            "-c:a", "pcm_s16le", str(p), input=np.asarray(audio, dtype=np.float32).tobytes())
        out.append(p)
    return out


def scene_clip(png, wav, dur, out):
    vf = (f"[0:v]fade=t=in:st=0:d=0.25,fade=t=out:st={dur - 0.25:.3f}:d=0.25[v0];"
          f"color=c=0xFFC400:s={W}x14:r={FPS}:d={dur:.3f}[bar];"
          f"[v0][bar]overlay=x='-w+w*t/{dur:.3f}':y={BAR_Y},format=yuv420p[v]")
    run("ffmpeg", "-y", "-v", "error", "-nostdin", "-loop", "1", "-framerate", str(FPS), "-i", str(png),
        "-i", str(wav), "-filter_complex", vf, "-map", "[v]", "-map", "1:a",
        "-af", f"apad=pad_dur={TAIL}", "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "20", "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", str(out))


def concat(clips, listfile, out_raw):
    listfile.write_text("".join(f"file '{c}'\n" for c in clips), encoding="utf-8")
    run("ffmpeg", "-y", "-v", "error", "-nostdin", "-f", "concat", "-safe", "0", "-i", str(listfile),
        "-c", "copy", str(out_raw))


LOUDNORM = "loudnorm=I=-14:TP=-1:LRA=11"
LIMIT = "alimiter=limit=0.85:level=disabled"  # margen para el redondeo del AAC


def measure_loudnorm(wav):
    err = subprocess.run(["ffmpeg", "-nostats", "-nostdin", "-i", str(wav), "-af",
                          LOUDNORM + ":print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return json.loads(err[err.rindex("{"):err.rindex("}") + 1])


def finalize_audio(raw, out, music=None):
    """Mezcla (voz + música con sidechaincompress, voz = detector), loudnorm en dos pasos a -14 LUFS / -1 dBTP,
    y limitador final. Sin música: solo normalización de la voz."""
    with tempfile.TemporaryDirectory(prefix="orbiuno-aud-") as t:
        pre = Path(t) / "pre.wav"
        if music:
            g = ("[0:a]asplit=2[v1][v2];[1:a]volume=0.55[m];"
                 "[m][v1]sidechaincompress=threshold=0.04:ratio=10:attack=15:release=450[duck];"
                 "[v2][duck]amix=inputs=2:duration=first:normalize=0[a]")
            run("ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(raw), "-stream_loop", "-1", "-i", str(music),
                "-filter_complex", g, "-map", "[a]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_f32le", str(pre))
        else:
            run("ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(raw), "-vn", "-ar", "48000", "-ac", "2",
                "-c:a", "pcm_f32le", str(pre))
        m = measure_loudnorm(pre)
        ln = (f"{LOUDNORM}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
              f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,{LIMIT}")
        run("ffmpeg", "-y", "-v", "error", "-nostdin", "-i", str(raw), "-i", str(pre), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-af", ln, "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-shortest", "-movflags", "+faststart", str(out))


def loudness(mp4):
    err = subprocess.run(["ffmpeg", "-nostats", "-nostdin", "-i", str(mp4), "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    i = re.findall(r"\n\s*I:\s+(-?\d+\.?\d*) LUFS", err)
    p = re.findall(r"\n\s*Peak:\s+(-?\d+\.?\d*) dBFS", err)
    return (float(i[-1]) if i else None), (float(p[-1]) if p else None)


def frame_signature(mp4, t):
    raw = run("ffmpeg", "-v", "error", "-nostdin", "-ss", f"{t:.3f}", "-i", str(mp4), "-frames:v", "1",
              "-vf", "scale=64:112,format=gray", "-f", "rawvideo", "pipe:1").stdout
    return np.frombuffer(raw, dtype=np.uint8).astype(float)


def validate_mp4(mp4, scenes, narration_text, test_mode, limits=(20, 90), target=(45, 60), voice_src=None):
    r = {"errors": [], "warnings": []}
    info = json.loads(run("ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,codec_name,width,height:format=duration",
                          "-of", "json", str(mp4)).stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})
    dur = float(info["format"]["duration"])
    r.update(width=v.get("width"), height=v.get("height"), video_codec=v.get("codec_name"),
             audio_codec=a.get("codec_name"), duration_s=round(dur, 2))
    if (v.get("width"), v.get("height")) != (W, H):
        r["errors"].append(f"resolución {v.get('width')}x{v.get('height')} != {W}x{H}")
    if v.get("codec_name") != "h264" or a.get("codec_name") != "aac":
        r["errors"].append("códecs deben ser h264 + aac")
    if abs(dur - scenes[-1]["end"]) > 0.8:
        r["errors"].append(f"duración {dur:.1f}s no coincide con la línea de tiempo {scenes[-1]['end']:.1f}s")
    if not limits[0] <= dur <= limits[1]:
        r["errors"].append(f"duración fuera de {limits[0]}-{limits[1]} s: {dur:.1f}")
    elif not target[0] <= dur <= target[1]:
        r["warnings"].append(f"duración {dur:.1f}s fuera del objetivo {target[0]}-{target[1]} s")
    vsrc = voice_src or mp4  # la voz se valida SIN música (la música no debe disparar ni ocultar alertas)
    voice = vv.analyze(vv.decode(vsrc), vv.probe_duration(vsrc), narration_text)
    r["voice"] = {k: voice[k] for k in voice if k != "errors"}
    r["errors"] += [f"audio: {e}" for e in voice["errors"]]
    lufs, tp = loudness(mp4)
    r.update(lufs_integrated=lufs, true_peak_dbfs=tp)
    if tp is not None and tp > -0.5:
        r["errors"].append(f"pico verdadero {tp} dBTP supera el margen")
    if lufs is not None and not -16.5 <= lufs <= -11.5:
        r["warnings"].append(f"sonoridad {lufs} LUFS lejos de -14")
    sigs = [frame_signature(mp4, (s["start"] + s["end"]) / 2) for s in scenes]
    diffs = [float(np.abs(sigs[i] - sigs[i + 1]).mean()) for i in range(len(sigs) - 1)]
    r["scene_frame_diffs"] = [round(x, 2) for x in diffs]
    if diffs and min(diffs) < 1.5:
        r["errors"].append("hay escenas consecutivas casi idénticas: el resaltado no se distingue")
    r["ok"] = not r["errors"]
    r["test_mode"] = test_mode
    return r


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--edition", required=True)
    ap.add_argument("--data", default=str(ROOT / "noticias.json"))
    ap.add_argument("--out-root", default=str(ROOT / "media"))
    ap.add_argument("--music", help="pista aprobada (ORBIUNO PULSE) con licencia confirmada; mezcla con ducking")
    ap.add_argument("--preview", action="store_true", help="permite edición sin aprobar; publishable=false")
    ap.add_argument("--test-audio-dir", help="SOLO PRUEBAS: seg0.wav..seg5.wav en lugar de Kokoro; publishable=false")
    a = ap.parse_args(argv)
    ed, news = oe.validate_edition(oe.load(a.data), a.edition, require_approved=not a.preview)
    music = Path(a.music) if a.music and Path(a.music).is_file() else None
    if a.music and not music:
        print(f"AVISO: pista {a.music} no existe; se genera sin música.", file=sys.stderr)
    texts = oe.narration_segments(ed, news)
    out = Path(a.out_root) / a.edition
    out.mkdir(parents=True, exist_ok=True)
    cards = [card_overview(ed, news)] + [card_overview(ed, news, i) for i in range(1, 5)] + [card_outro(ed)]
    with tempfile.TemporaryDirectory(prefix="orbiuno-reel-") as tmpd:
        tmp = Path(tmpd)
        wavs = ([Path(a.test_audio_dir) / f"seg{i}.wav" for i in range(len(texts))] if a.test_audio_dir
                else synth_kokoro(texts, tmp))
        clips, scenes, t = [], [], 0.0
        names = ["intro"] + [n["id"] for n in news] + ["cierre"]
        for i, (card, wav) in enumerate(zip(cards, wavs)):
            png = tmp / f"s{i}.png"
            card.save(png)
            dur = vv.probe_duration(wav) + TAIL
            clip = tmp / f"s{i}.mp4"
            scene_clip(png, wav, dur, clip)
            clips.append(clip)
            scenes.append({"scene": names[i], "start": round(t, 3), "end": round(t + dur, 3), "text": texts[i]})
            t += dur
        concat(clips, tmp / "reel.txt", tmp / "reel_raw.mp4")
        finalize_audio(tmp / "reel_raw.mp4", out / "reel.mp4", music)
        # Story complementaria: portada + cierre (clip corto, separado del Reel)
        concat([clips[0], clips[-1]], tmp / "story.txt", tmp / "story_raw.mp4")
        finalize_audio(tmp / "story_raw.mp4", out / "story.mp4", music)
        d0 = scenes[0]["end"] - scenes[0]["start"]
        story_scenes = [{"scene": "intro", "start": 0.0, "end": round(d0, 3)},
                        {"scene": "cierre", "start": round(d0, 3),
                         "end": round(d0 + scenes[-1]["end"] - scenes[-1]["start"], 3)}]
        test_mode = bool(a.test_audio_dir)
        check = validate_mp4(out / "reel.mp4", scenes, " ".join(texts), test_mode, voice_src=tmp / "reel_raw.mp4")
        scheck = validate_mp4(out / "story.mp4", story_scenes, texts[0] + " " + texts[-1], test_mode,
                              limits=(8, 60), target=(10, 30), voice_src=tmp / "story_raw.mp4")
    approved = (ed.get("review") or {}).get("status") == "approved"
    ok = check["ok"] and scheck["ok"]
    manifest = {
        "editionId": ed["editionId"], "video": "reel.mp4", "sha256": sha(out / "reel.mp4"),
        "bytes": (out / "reel.mp4").stat().st_size,
        "publicUrl": f"{oe.WEB_BASE}/media/{ed['editionId']}/reel.mp4",
        "story": {"video": "story.mp4", "sha256": sha(out / "story.mp4"), "bytes": (out / "story.mp4").stat().st_size,
                  "publicUrl": f"{oe.WEB_BASE}/media/{ed['editionId']}/story.mp4", "checks": scheck},
        "music": {"file": music.name, "sha256": sha(music)} if music else None,
        "voice": "TEST-FIXTURE" if test_mode else "kokoro:ef_dora@1.25",
        "scenes": scenes, "caption": oe.build_caption(ed, news),
        "sources": [{"id": n["id"], "name": n["sources"][0]["name"], "url": n["sources"][0]["url"]} for n in news],
        "checks": check,
        "publishable": bool(ok and approved and not a.preview and not test_mode),
    }
    (out / "reel-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"editionId": manifest["editionId"], "voice": manifest["voice"], "music": manifest["music"],
                      "publishable": manifest["publishable"], "reel": check, "story": scheck},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except oe.EditionError as e:
        print("EDICIÓN NO PUBLICABLE:\n- " + "\n- ".join(e.problems), file=sys.stderr)
        sys.exit(2)
