#!/usr/bin/env python3
"""Bloquea un Reel si falta alguna foto real, logo, pista Salomé o web íntegra.
Verifica archivos y manifiestos; nunca autoriza publicación por su cuenta.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.narration_body import story_body

VOICE = "es-CO-SalomeNeural"


def validate(manifest: dict, *, folder: Path, assets: Path, news: dict, webvoice: dict) -> list[str]:
    errors = []
    day, slot = manifest.get("edition"), manifest.get("slot")
    ordered = sorted((n for n in news.get("news", []) if n.get("date") == day and
                      n.get("editionSlot") == slot and n.get("verification") == "editorial_verified"),
                     key=lambda n: n.get("priority", 999))
    ids = [n["id"] for n in ordered]
    if len(ids) != 6 or len(set(ids)) != 6 or ids != manifest.get("newsIds"):
        errors.append("six_story_ids_not_matching")
    if manifest.get("voice") != VOICE or manifest.get("voiceSpeed") != 1.25 or manifest.get("language") != "es-CO":
        errors.append("wrong_voice_or_speed")
    if manifest.get("visualMode") != "verified_real_photos" or manifest.get("imagesCount") != 6 or manifest.get("logosCount") != 6:
        errors.append("real_photos_or_logos_missing")
    if manifest.get("sourceOnly") is not False or manifest.get("publicationAuthorized") is not False:
        errors.append("source_only_or_false_approval")
    credits = manifest.get("photoCredits", [])
    if len(credits) != 6 or len(manifest.get("news", [])) != 6:
        errors.append("credits_incomplete")
    for i, n in enumerate(ordered, 1):
        for file in (assets / f"photo-{i:02}.jpg",
                     folder / "frames" / f"noticia-{i:02}.jpg"):
            if not file.is_file() or file.stat().st_size < 1000:
                errors.append("missing_visual_asset_" + str(i))
        icon = assets / f"logo-{i:02}.png"
        if not icon.is_file() or icon.stat().st_size < 150:
            errors.append("missing_source_icon_" + str(i))
            errors.append("missing_visual_asset_" + str(i))  # backwards-compatible fail-closed gate
        else:
            from PIL import Image, UnidentifiedImageError
            try:
                with Image.open(icon) as im:
                    im.load()
                    if im.format != "PNG" or min(im.size) < 32:
                        errors.append("source_icon_unreadable_" + str(i))
            except (UnidentifiedImageError, OSError):
                errors.append("source_icon_corrupt_" + str(i))
        if n.get("imageRightsVerified") is not True or not n.get("imageLicense") or not n.get("imageCredit"):
            errors.append("image_license_missing_" + str(i))
        if i <= len(credits) and (credits[i-1].get("author") != n.get("imageCredit") or
                                  credits[i-1].get("license") != n.get("imageLicense")):
            errors.append("image_credit_mismatch_" + str(i))
        origin = str(n.get("imageSourceUrl", ""))
        commons_ok = origin.startswith("https://commons.wikimedia.org/wiki/File:")
        unsplash_ok = (origin.startswith("https://unsplash.com/photos/")
                       and n.get("imageLicense") == "Unsplash License"
                       and n.get("imageCaption", "").lower().find("archivo") >= 0)
        if not str(n.get("imageUrl", "")).startswith("./media/") or not (commons_ok or unsplash_ok):
            errors.append("image_origin_unverified_" + str(i))
        v = webvoice.get("items", {}).get(n["id"], {})
        if v.get("voice") != VOICE or v.get("speed") != 1.25 or v.get("text") != story_body(n.get("originalArticleTextEs")):
            errors.append("web_full_audio_mismatch_" + str(i))
        if i <= len(manifest.get("news", [])) and manifest["news"][i-1].get("sourceUrl") != n["sources"][0]["url"]:
            errors.append("source_url_mismatch_" + str(i))
    video = folder / str(manifest.get("video", ""))
    if not video.is_file() or video.stat().st_size < 300_000:
        errors.append("mp4_missing_or_too_small")
    elif hashlib.sha256(video.read_bytes()).hexdigest() != manifest.get("sha256"):
        errors.append("mp4_sha_mismatch")
    if not isinstance(manifest.get("duration"), (int, float)) or manifest.get("duration", 0) < 10:
        errors.append("invalid_duration")
    return errors


def check_media_decodes(path: Path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(path),
                        "-f", "null", "-"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("El MP4 no decodifica completamente")
    streams = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                                       "stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels", "-of", "json", str(path)])
    data = json.loads(streams)["streams"]
    if not any(s.get("codec_type") == "video" and s.get("codec_name") == "h264" and
               s.get("width") == 1080 and s.get("height") == 1920 for s in data):
        raise RuntimeError("H264 vertical ausente")
    if not any(s.get("codec_type") == "audio" and s.get("codec_name") == "aac"
               and s.get("sample_rate") == "48000" and s.get("channels") == 2 for s in data):
        raise RuntimeError("AAC estéreo 48kHz ausente")
    video = next((s for s in data if s.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError("Video stream ausente")
    rate = str(video.get("avg_frame_rate", "0/1")).split("/")
    fps = float(rate[0]) / float(rate[1]) if len(rate) == 2 and float(rate[1]) else 0
    if not 29.5 <= fps <= 30.5:
        raise RuntimeError("FPS fuera del formato 30fps: " + str(fps))


def main():
    ap = argparse.ArgumentParser()
    for arg in ("manifest", "assets", "news", "webvoice"):
        ap.add_argument("--" + arg, required=True)
    a = ap.parse_args()
    path = Path(a.manifest)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    news = json.loads(Path(a.news).read_text(encoding="utf-8"))
    web = json.loads(Path(a.webvoice).read_text(encoding="utf-8"))
    errors = validate(manifest, folder=path.parent, assets=Path(a.assets), news=news, webvoice=web)
    if errors:
        raise SystemExit("BLOCKED_QA: " + ",".join(errors))
    for item in manifest["news"]:
        voice_item = web["items"][item["id"]]
        audio_file = Path(a.webvoice).parent / Path(voice_item["url"]).name
        if not audio_file.is_file() or audio_file.stat().st_size < 3000:
            raise SystemExit("BLOCKED_QA: missing_web_audio_" + item["id"])
        if hashlib.sha256(voice_item["text"].encode()).hexdigest() != voice_item.get("sha256"):
            raise SystemExit("BLOCKED_QA: web_audio_transcript_hash_mismatch_" + item["id"])
        decoded = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error",
                                  "-i", str(audio_file), "-f", "null", "-"],
                                 capture_output=True, text=True)
        if decoded.returncode:
            raise SystemExit("BLOCKED_QA: corrupt_web_audio_" + item["id"])
    check_media_decodes(path.parent / manifest["video"])
    print("ORBIUNO_QA_PASS: seis fotos, seis logos, audios íntegros Salome, SHA y decodificación completa; PUBLICATION_AUTHORIZED=false")


if __name__ == "__main__":
    main()
