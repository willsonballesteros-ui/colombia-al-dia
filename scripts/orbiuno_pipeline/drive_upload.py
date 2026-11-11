"""Upload approved artifacts to a shared Drive folder; no credentials in git."""
import hashlib
import json
import os


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def upload(paths, folder_id, env=None):
    if env is None:
        env = os.environ
    if not folder_id or not paths:
        raise ValueError("Drive folder and artifact paths required")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    credentials_json = env["GDRIVE_SERVICE_ACCOUNT_JSON"]
    credentials = service_account.Credentials.from_service_account_info(json.loads(credentials_json), scopes=["https://www.googleapis.com/auth/drive.file"])
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    results = []
    for path in paths:
        digest = sha256(path)
        item = service.files().create(body={"name": os.path.basename(path), "parents": [folder_id]}, media_body=MediaFileUpload(path), fields="id,webViewLink", supportsAllDrives=True).execute()
        results.append({"file": path, "sha256": digest, **item})
    return results
