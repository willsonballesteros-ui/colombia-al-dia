"""Instagram publication gate. Never bypass approval inside publish_reel."""
import os
from urllib.parse import urlsplit


def preconditions(state: str, env=None):
    if env is None:
        env = os.environ
    errors = []
    if state != "approved":
        errors.append(f"state {state} is not approved")
    if env.get("IG_PUBLISH_AUTHORIZED") != "yes":
        errors.append("explicit IG publishing authorization absent")
    for name in ("META_ACCESS_TOKEN", "IG_USER_ID"):
        if not env.get(name):
            errors.append(f"missing {name}")
    return errors


def publish_reel(video_url: str, caption: str, http, env=None, state="draft", retries=2):
    if env is None:
        env = os.environ
    errors = preconditions(state, env)
    if errors:
        raise PermissionError("; ".join(errors))
    uri = urlsplit(video_url)
    if uri.scheme != "https" or not uri.hostname:
        raise ValueError("Public video URL must be HTTPS")
    if retries < 0 or retries > 10:
        raise ValueError("Invalid retries")
    base = f"https://graph.facebook.com/v21.0/{env['IG_USER_ID']}"
    token = env["META_ACCESS_TOKEN"]
    created = http("POST", f"{base}/media", media_type="REELS", video_url=video_url, caption=caption, access_token=token)
    container_id = created.get("id")
    if not container_id:
        raise RuntimeError("Meta did not create a container")
    for _ in range(retries + 1):
        status = http("GET", f"https://graph.facebook.com/v21.0/{container_id}", fields="status_code", access_token=token)
        if status.get("status_code") == "FINISHED":
            break
    else:
        raise RuntimeError("Meta container did not finish")
    published = http("POST", f"{base}/media_publish", creation_id=container_id, access_token=token)
    media_id = published.get("id")
    if not media_id:
        raise RuntimeError("Meta did not confirm media ID")
    info = http("GET", f"https://graph.facebook.com/v21.0/{media_id}", fields="permalink", access_token=token)
    if not info.get("permalink"):
        raise RuntimeError("No permalink; publication not confirmed")
    return {"id": media_id, "permalink": info["permalink"]}
