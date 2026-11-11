#!/usr/bin/env python3
"""Fail-closed preflight for ORBIUNO's existing meta-directo workflow."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

def check_manifest(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    stories = data.get("noticias") if isinstance(data, dict) else None
    if stories is None and isinstance(data, dict):
        stories = data.get("news")
    if not isinstance(stories, list) or not 1 <= len(stories) <= 4:
        raise ValueError("Manifest must contain 1-4 stories in noticias/news")
    for index, story in enumerate(stories, 1):
        if not isinstance(story, dict):
            raise ValueError(f"Story {index} is not an object")
        title = story.get("titulo") or story.get("title")
        source = story.get("fuente") or story.get("source")
        url = story.get("url") or story.get("sourceUrl") or story.get("source_url")
        if not source and isinstance(story.get("sources"), list) and story["sources"]:
            source = story["sources"][0].get("name")
            url = url or story["sources"][0].get("url")
        if isinstance(source, dict):
            url = url or source.get("url")
            source = source.get("name")
        if not title or not source or not url:
            raise ValueError(f"Story {index} lacks title, source or article URL")
        parsed = urlparse(str(url))
        if parsed.scheme != "https" or not parsed.hostname or parsed.path in ("", "/"):
            raise ValueError(f"Story {index} source URL is a homepage, not an article")
        if str(story.get("verification", "")).lower() != "editorial_verified":
            raise ValueError(f"Story {index} is not explicitly editorial_verified")
        if re.search(r"pendiente de verificaci[oó]n", str(story.get("level", "")), re.I):
            raise ValueError(f"Story {index} has pending editorial verification")
    return len(stories)

def check_video(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,width,height:format=duration",
         "-of", "json", path], capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not video or not audio:
        raise ValueError("MP4 must have video and audio")
    width, height = video.get("width"), video.get("height")
    if (width, height) not in ((720, 1280), (1080, 1920)):
        raise ValueError("MP4 must be approved vertical 9:16 (720x1280 or 1080x1920)")
    duration = float(info.get("format", {}).get("duration", 0))
    if not 35 <= duration <= 90:
        raise ValueError("MP4 duration outside 35-90 seconds")
    return duration


# External checks are deliberately fail-closed; automated editorial approval is not inferred.
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from datetime import datetime

def _fetch(url, fetcher=None):
    """Injectable network boundary. Returns (status, final_url, bytes, content_type)."""
    if fetcher is not None:
        return fetcher(url)
    req = Request(url, headers={"User-Agent": "ORBIUNO-Preflight/1.0", "Accept": "application/json,audio/*,*/*"})
    try:
        with urlopen(req, timeout=15) as response:
            return response.status, response.url, response.read(5_000_000), response.headers.get("Content-Type", "")
    except HTTPError as exc:
        return exc.code, exc.url, b"", ""

def _stories(obj):
    if not isinstance(obj, dict):
        raise ValueError("Website/manifest must be a JSON object")
    result = obj.get("news", obj.get("noticias"))
    if not isinstance(result, list):
        raise ValueError("Website/manifest missing news array")
    return result

def _value(item, *names):
    for name in names:
        v = item.get(name)
        if v is not None and v != "":
            return v
    return None

def _source(item):
    source = _value(item, "source", "fuente")
    if isinstance(source, dict):
        source = source.get("name")
    if not source and isinstance(item.get("sources"), list) and item["sources"]:
        source = item["sources"][0].get("name")
    return str(source or "").strip()

def _normalize(value):
    return " ".join(str(value or "").split()).casefold()

def check_release(manifest_path, site_url, fetcher=None, editorial_approvals=None):
    """G1-G4/G6: checks published site, sources, audio and photo rights.
    REVIEW requires explicit approvals keyed by story ID. Never creates editorial approvals.
    This does not certify that narration matches the audiovisual content.
    """
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    selected = _stories(data)
    check_manifest(manifest_path)
    if not site_url.startswith("https://"):
        raise ValueError("G1 BLOCKED: site must be HTTPS")
    site_root = site_url.rstrip("/") + "/"
    try:
        status, final, payload, ctype = _fetch(urljoin(site_root, "noticias.json"), fetcher)
        if status != 200 or urlparse(final).hostname != urlparse(site_root).hostname:
            raise ValueError("G1 BLOCKED: published news JSON unavailable at expected host")
        online = _stories(json.loads(payload))
    except (URLError, OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"G1 BLOCKED: cannot read published JSON: {exc}") from exc
    if not 1 <= len(selected) <= 4:
        raise ValueError("G1 BLOCKED: expected 1-4 stories")
    approvals = editorial_approvals or {}
    for story in selected:
        sid = str(_value(story, "id", "newsId") or "").strip()
        title = _value(story, "title", "titulo")
        date = _value(story, "date", "fecha")
        if not sid or not title or not date:
            raise ValueError("G1 BLOCKED: each story needs id, title and date")
        matches = [x for x in online if str(_value(x, "id", "newsId") or "") == sid]
        if len(matches) != 1:
            raise ValueError(f"G1 BLOCKED: story {sid} not uniquely published")
        live = matches[0]
        for key, a, b in (
            ("title", title, _value(live, "title", "titulo")),
            ("date", date, _value(live, "date", "fecha")),
            ("source", _source(story), _source(live)),
        ):
            if not a or _normalize(a) != _normalize(b):
                raise ValueError(f"G1 BLOCKED: {sid} {key} mismatch")
        url = _value(story, "url", "sourceUrl", "source_url")
        if not url and isinstance(story.get("sources"), list) and story["sources"]:
            url = story["sources"][0].get("url")
        if not url and isinstance(story.get("source"), dict):
            url = story["source"].get("url")
        if not url or urlparse(str(url)).scheme != "https":
            raise ValueError(f"G2 BLOCKED: invalid source for {sid}")
        try:
            src_status, src_final, _, _ = _fetch(url, fetcher)
        except (URLError, OSError, TimeoutError):
            src_status, src_final = 429, url
        if src_status in (403, 429) or src_status >= 500:
            if approvals.get(sid) != "source_reviewed":
                raise ValueError(f"G2 REVIEW REQUIRED: source {sid} returned {src_status}")
        elif not 200 <= src_status < 300:
            raise ValueError(f"G2 BLOCKED: source {sid} returned {src_status}")
        elif urlparse(src_final).hostname != urlparse(url).hostname:
            if approvals.get(sid) != "source_reviewed":
                raise ValueError(f"G2 REVIEW REQUIRED: source {sid} redirected to different host")
        audio = _value(story, "audioUrl", "audio_url", "audio")
        if isinstance(audio, dict):
            audio = audio.get("url")
        if not isinstance(audio, str) or not audio:
            raise ValueError(f"G3 BLOCKED: missing individual audio for {sid}")
        audio_url = urljoin(site_root, audio)
        if urlparse(audio_url).hostname != urlparse(site_root).hostname:
            raise ValueError(f"G3 BLOCKED: audio {sid} leaves verified host")
        try:
            audio_status, _, body, audio_type = _fetch(audio_url, fetcher)
        except (URLError, OSError, TimeoutError) as exc:
            raise ValueError(f"G3 BLOCKED: audio {sid} unavailable: {exc}") from exc
        if audio_status != 200 or not body or not (audio_type.lower().startswith("audio/") or audio_url.lower().split("?")[0].endswith((".mp3", ".wav", ".ogg", ".m4a"))):
            raise ValueError(f"G3 BLOCKED: audio {sid} missing or invalid")
        image = story.get("image")
        if not isinstance(image, dict):
            raise ValueError(f"G4 BLOCKED: image rights metadata missing for {sid}")
        if not all(_value(image, k) for k in ("url", "credit", "license", "source")):
            raise ValueError(f"G4 BLOCKED: image URL/credit/license/source missing for {sid}")
        if image.get("rightsVerified") is not True:
            raise ValueError(f"G4 BLOCKED: verified image permission missing for {sid}")
        if _normalize(image.get("kind")) in ("favicon", "placeholder", "synthetic"):
            raise ValueError(f"G4 BLOCKED: image is not an authorized factual photograph for {sid}")
    return {"status": "LISTO PARA PUBLICACION MANUAL", "story_count": len(selected),
            "note": "Checks do not verify spoken narrative or interactive browser playback; human audiovisual inspection remains mandatory."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--video")
    p.add_argument("--site-url")
    p.add_argument("--pre-render", action="store_true")
    args = p.parse_args()
    count = check_manifest(args.manifest)
    if args.pre_render and not args.site_url:
        p.error("--pre-render requires --site-url")
    if args.site_url:
        print(json.dumps(check_release(args.manifest, args.site_url), ensure_ascii=False))
    if args.video:
        duration = check_video(args.video)
        print(f"PASS: {count} source-specific stories; MP4 {duration:.1f}s, audio/video present")
    elif not args.pre_render:
        p.error("specify --video or --pre-render")
    print("NOT RELEASE-APPROVED: web deployment, playable per-story audio, source facts and image licenses still require independent checks.")

if __name__ == "__main__":
    main()
