"""Inspect a rendered MP4, not its metadata claims."""
import json
import subprocess


def check_ffprobe(info: dict, min_s: float = 50, max_s: float = 60):
    errors = []
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        errors.append("sin video")
    else:
        if video.get("codec_name") != "h264":
            errors.append("codec video no es h264")
        width, height = video.get("width", 0), video.get("height", 0)
        if not width or not height or abs(width / height - 9 / 16) > 0.01:
            errors.append(f"relación {width}x{height} no es 9:16")
    if audio is None:
        errors.append("sin audio")
    elif audio.get("codec_name") != "aac":
        errors.append("codec audio no es aac")
    try:
        duration = float(info.get("format", {}).get("duration"))
        if not min_s <= duration <= max_s:
            errors.append(f"duración {duration:.2f}s fuera de {min_s}-{max_s}")
    except (TypeError, ValueError):
        errors.append("duración ausente")
    return errors


def run_ffprobe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
