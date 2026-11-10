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

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--video", required=True)
    args = p.parse_args()
    count = check_manifest(args.manifest)
    duration = check_video(args.video)
    print(f"PASS: {count} source-specific stories; MP4 {duration:.1f}s, audio/video present")
    print("NOT RELEASE-APPROVED: web deployment, playable per-story audio, source facts and image licenses still require independent checks.")

if __name__ == "__main__":
    main()
