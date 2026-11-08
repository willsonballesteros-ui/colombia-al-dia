import json
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
from edicion import rows, edition_news, media, root

FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
BG, GREEN, INK, WHITE = "#09271d", "#b4fa65", "#0a2118", "#f2faee"
domains = ("larepublica.co", "larepublica.co", "dnp.gov.co", "elespectador.com")
news = edition_news()
intro = "ORBIUNO. Edición especial del sábado siete de noviembre. Metro de Bogotá, acuerdo con Emiratos, finanzas municipales y TikTok en Europa."
outro = "Escucha cada noticia completa en nuestra web. Enlace en el perfil."
voice = [intro] + [n["reelNarrationEs"] for n in news] + [outro]

def font(size, bold=True):
    return ImageFont.truetype(str(FONT_DIR / ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf")), size)

def wrapped(draw, text, x, y, size, width, max_lines, color=WHITE):
    while size >= 24:
        f = font(size)
        lines = [""]
        for word in text.split():
            candidate = (lines[-1] + " " + word).strip()
            if lines[-1] and draw.textlength(candidate, font=f) > width:
                lines.append(word)
            else:
                lines[-1] = candidate
        if len(lines) <= max_lines and all(draw.textlength(line, font=f) <= width for line in lines):
            break
        size -= 2
    assert len(lines) <= max_lines
    for line in lines:
        draw.text((x, y), line, font=f, fill=color)
        y += round(size * 1.14)
    return y

def base(height):
    im = Image.new("RGB", (1080, height), BG)
    d = ImageDraw.Draw(im)
    top = 268 if height == 1920 else 64
    d.rectangle((0, 0, 23, height), fill=GREEN)
    d.text((93, top), "ORBIUNO", font=font(92), fill=WHITE)
    d.text((100, top + 116), "ESPECIAL  ·  7 NOV 2026  ·  8:00 P. M.", font=font(29), fill=GREEN)
    d.line((100, top + 180, 980, top + 180), fill=GREEN, width=3)
    return im, d, top

def panel(height, index):
    im, d, y = base(height)
    if index == 0:
        d.text((100, y + 227), "CUATRO NOTICIAS", font=font(54), fill=WHITE)
        for i, n in enumerate(news, 1):
            line = y + 345 + 130 * (i - 1)
            d.rounded_rectangle((101, line + 2, 157, line + 54), radius=13, fill=GREEN)
            d.text((119, line + 6), str(i), font=font(30), fill=INK)
            wrapped(d, n["reelShort"], 185, line, 40, 765, 2)
        d.text((103, y + 917), "@resumen.noticias  ·  Escucha en la web", font=font(31), fill=GREEN)
    elif index == 5:
        wrapped(d, "Escucha cada noticia completa", 100, y + 277, 97, 830, 4)
        d.text((103, y + 675), "↓  ENLACE EN EL PERFIL", font=font(46), fill=GREEN)
        d.text((103, y + 781), "colombia-al-dia.pages.dev", font=font(45), fill=WHITE)
    else:
        n, row = news[index - 1], rows[index - 1]
        photo = ImageOps.exif_transpose(Image.open(root / "assets" / row[7])).convert("RGB")
        photo.thumbnail((1000, 720))
        photo.save(media / f"foto-{row[0]}.jpg", quality=83, optimize=True)
        fit = ImageOps.contain(photo, (880, 390))
        d.rectangle((100, y + 239, 980, y + 629), fill=INK)
        im.paste(fit, (100 + (880-fit.width)//2, y + 239 + (390-fit.height)//2))
        d.text((101, y + 644), n["imageCaption"], font=font(24), fill=WHITE)
        d.text((101, y + 678), f'{n["imageCredit"]} / Wikimedia Commons · {n["imageLicense"]}', font=font(22, False), fill=WHITE)
        d.text((101, y + 735), f'0{index}   /   {n["category"].upper()}', font=font(28), fill=GREEN)
        bottom = wrapped(d, n["title"], 100, y + 785, 56, 870, 3)
        icon = Image.open(root / "assets" / (domains[index - 1] + ".png")).convert("RGBA")
        icon.thumbnail((44, 44))
        pos = max(bottom + 25, y + 975)
        d.rounded_rectangle((100, pos, 148, pos + 48), radius=7, fill=WHITE)
        im.paste(icon, (102, pos + 2), icon)
        d.text((167, pos + 6), n["sources"][0]["name"], font=font(28), fill=GREEN)
    return im

def ff(*args):
    return subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", *map(str, args)], check=True)

def render():
    import tempfile
    import soundfile as sf
    import onnxruntime as ort
    from kokoro_onnx import Kokoro

    opts = ort.SessionOptions()
    opts.intra_op_num_threads, opts.inter_op_num_threads = 2, 1
    opts.enable_cpu_mem_arena = opts.enable_mem_pattern = False
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session = ort.InferenceSession(os.environ["ORBIUNO_VOICE_MODEL"], sess_options=opts, providers=["CPUExecutionProvider"])
    model = Kokoro.from_session(session, os.environ["ORBIUNO_VOICE_BANK"])

    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        segments = []
        durations = []
        for i, phrase in enumerate(voice):
            png, wav, clip = [work / f"{i}.{ext}" for ext in ("png", "wav", "mp4")]
            panel(1920, i).save(png)
            if i < 5:
                panel(1350, i).save(media / f"lamina-{i}.jpg", quality=87, optimize=True)
            audio, rate = model.create(phrase, "ef_dora", speed=1.25, lang="es")
            sf.write(wav, audio, rate)
            duration = len(audio) / rate + 0.23
            durations.append(round(duration, 3))
            ff("-loop", "1", "-framerate", 30, "-i", png, "-i", wav, "-af", "apad", "-t", round(duration, 3),
               "-threads", 3, "-c:v", "libx264", "-preset", "fast", "-crf", 24, "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "96k", "-ar", 48000, "-ac", 2, clip)
            segments.append(clip)
        for name, selection in (("reel", segments), ("historia", [segments[0], segments[-1]])):
            listing = work / f"{name}.txt"
            listing.write_text("".join(f"file '{clip}'\n" for clip in selection))
            ff("-f", "concat", "-safe", 0, "-i", listing, "-c:v", "copy", "-af",
               "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", 48000, "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", media / f"{name}.mp4")
        assert 30 <= sum(durations) <= 40, durations
        (media / "narracion.json").write_text(json.dumps(dict(voice="ef_dora", speed=1.25, texts=voice, seconds=durations),
                                                             ensure_ascii=False, indent=2) + "\n")
        print(durations, flush=True)

if __name__ == "__main__":
    render()
