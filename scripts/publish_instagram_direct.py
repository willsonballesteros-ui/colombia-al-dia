#!/usr/bin/env python3
"""ORBIUNO publisher for Instagram Login (Meta official API).

Requires: IG_USER_ID, IG_ACCESS_TOKEN. Media must be public HTTPS and licensed.
No Metricool dependency. Manual execution only; never publish on import.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.getenv("IG_GRAPH_BASE", "https://graph.instagram.com").rstrip("/")
VERSION = os.getenv("IG_GRAPH_VERSION", "v24.0")


def request(method, path, token, params=None):
    url = f"{API}/{VERSION}/{path.lstrip('/')}"
    payload = urllib.parse.urlencode(params or {}).encode()
    req = urllib.request.Request(
        url + (("?" + urllib.parse.urlencode(params)) if method == "GET" and params else ""),
        data=payload if method == "POST" else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/x-www-form-urlencoded"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=40) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Instagram HTTP {exc.code}: {raw[:500]}") from None


def publish(image_url, caption, *, confirmed=False):
    if not confirmed:
        raise ValueError("Must pass --confirm-publish to authorize publication.")
    url = urllib.parse.urlsplit(image_url)
    if url.scheme != "https" or not url.netloc or url.username or url.password:
        raise ValueError("Image must use a public HTTPS URL.")
    user_id = os.getenv("IG_USER_ID", "").strip()
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    if not user_id or not token:
        raise RuntimeError("Missing IG_USER_ID and/or IG_ACCESS_TOKEN secrets.")
    if not caption.strip() or len(caption) > 2200:
        raise ValueError("Caption must be 1–2200 characters.")
    # Check media is publicly reachable before creating a container.
    probe = urllib.request.Request(image_url, headers={"User-Agent": "ORBIUNO-Publisher/1.0"})
    with urllib.request.urlopen(probe, timeout=30) as response:
        if not response.headers.get("Content-Type", "").lower().startswith("image/"):
            raise ValueError("Media URL did not return an image MIME type.")
    created = request("POST", f"{user_id}/media", token, {"image_url": image_url, "caption": caption})
    creation_id = str(created["id"])
    for _ in range(18):
        status = request("GET", creation_id, token, {"fields": "status_code"})
        code = status.get("status_code")
        if code == "FINISHED":
            result = request("POST", f"{user_id}/media_publish", token, {"creation_id": creation_id})
            media_id = str(result["id"])
            details = request("GET", media_id, token, {"fields": "id,permalink"})
            return {"status": "published", "media_id": media_id, "permalink": details.get("permalink")}
        if code in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram media processing failed: {code}")
        time.sleep(5)
    raise RuntimeError(f"Container {creation_id} processing timed out; check before retrying to avoid duplicates.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image-url", required=True)
    p.add_argument("--caption-file", required=True)
    p.add_argument("--rights-confirmed", action="store_true", help="Confirm you have rights to use the image")
    p.add_argument("--confirm-publish", action="store_true")
    args = p.parse_args()
    if not args.rights_confirmed:
        p.error("Image usage rights must be confirmed with --rights-confirmed.")
    with open(args.caption_file, encoding="utf-8") as f:
        caption = f.read()
    try:
        print(json.dumps(publish(args.image_url, caption, confirmed=args.confirm_publish), ensure_ascii=False))
    except Exception as exc:
        print(f"Publication NOT confirmed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
