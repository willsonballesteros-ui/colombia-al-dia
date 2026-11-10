#!/usr/bin/env python3
"""Publish a previously validated, publicly hosted ORBIUNO Reel via Meta Graph API.

Never renders, selects news, or changes site files. Set EDITION_KEY uniquely.
A durable receipt must be stored by CI; absence of receipt is NOT proof of nonpublication.
"""
import json
import os
import sys
import time
from urllib.parse import urlparse
import requests

API_VERSION = os.getenv("META_GRAPH_VERSION", "v24.0")
API = f"https://graph.facebook.com/{API_VERSION}"
IG_ID = os.getenv("INSTAGRAM_USER_ID", "").strip()
TOKEN = os.getenv("META_USER_ACCESS_TOKEN", "").strip()
VIDEO_URL = os.getenv("REEL_VIDEO_URL", "").strip()
CAPTION = os.getenv("REEL_CAPTION", "").strip()
EDITION_KEY = os.getenv("EDITION_KEY", "").strip()
RECEIPT = os.getenv("PUBLISH_RECEIPT", "orbiuno_publish_receipt.json")

def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def call(method, path, **kwargs):
    response = requests.request(method, f"{API}/{path}", timeout=35, **kwargs)
    try:
        result = response.json()
    except ValueError:
        raise RuntimeError(f"Meta returned non-JSON HTTP {response.status_code}")
    if not response.ok or "error" in result:
        error = result.get("error", {})
        raise RuntimeError(f"Meta API error: code={error.get('code', response.status_code)} type={error.get('type', 'unknown')}")
    return result

def main():
    require(all((IG_ID, TOKEN, VIDEO_URL, CAPTION, EDITION_KEY)), "Missing required publishing configuration")
    parsed = urlparse(VIDEO_URL)
    require(parsed.scheme == "https" and bool(parsed.netloc), "REEL_VIDEO_URL must be public HTTPS")
    require(len(CAPTION) <= 2200, "Caption exceeds Instagram limit")
    require(os.path.isfile(os.getenv("VALIDATED_VIDEO", "output_reel.mp4")), "Validated local MP4 missing")
    require(os.getenv("EDITORIAL_VERIFIED") == "true", "Editorial verification not confirmed")
    require(os.getenv("MEDIA_VALIDATED") == "true", "Media validation not confirmed")
    if os.path.exists(RECEIPT):
        with open(RECEIPT, encoding="utf-8") as handle:
            old = json.load(handle)
        if old.get("edition_key") == EDITION_KEY:
            raise RuntimeError("Edition already has a publication receipt; refusing duplicate")
    head = requests.head(VIDEO_URL, allow_redirects=True, timeout=30)
    require(head.ok and "video" in head.headers.get("content-type", "").lower(), "Public MP4 URL not reachable as video")
    creation = call("POST", f"{IG_ID}/media", data={
        "media_type": "REELS", "video_url": VIDEO_URL,
        "caption": CAPTION, "access_token": TOKEN
    })
    creation_id = creation["id"]
    print(f"Meta container created: {creation_id}", flush=True)
    for _ in range(36):
        time.sleep(10)
        state = call("GET", creation_id, params={"fields": "status_code", "access_token": TOKEN}).get("status_code")
        if state == "FINISHED":
            break
        if state in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Meta container processing failed: {state}")
    else:
        raise RuntimeError(f"Container {creation_id} not ready. Check it before any retry.")
    # If the request times out, publication may still have happened. Never retry blindly.
    published = call("POST", f"{IG_ID}/media_publish", data={"creation_id": creation_id, "access_token": TOKEN})
    media_id = published.get("id")
    require(media_id, "Publish response lacked media ID; inspect Meta before retry")
    details = call("GET", media_id, params={"fields": "permalink", "access_token": TOKEN})
    receipt = {"edition_key": EDITION_KEY, "container_id": creation_id,
               "media_id": media_id, "permalink": details.get("permalink")}
    with open(RECEIPT, "w", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2)
    print(json.dumps(receipt), flush=True)

if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, requests.RequestException, KeyError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        sys.exit(1)
