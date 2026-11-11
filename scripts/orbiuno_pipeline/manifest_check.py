"""Validate the REAL ORBIUNO manifest shape; never grant editorial approval."""
from urllib.parse import urlsplit


def validate(manifest: dict, template: dict, expected_items: int = 4, items_key: str = "news"):
    errors = []
    if not isinstance(manifest, dict) or not isinstance(template, dict):
        return ["manifest and template must be objects"]
    def required_shape(expected, actual, path=""):
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                errors.append(f"{path}: expected object")
                return
            for key, value in expected.items():
                if key not in actual:
                    errors.append(f"{path}/{key}: missing")
                else:
                    required_shape(value, actual[key], f"{path}/{key}")
        elif isinstance(expected, list):
            if not isinstance(actual, list):
                errors.append(f"{path}: expected array")
            elif expected and isinstance(expected[0], dict):
                for i, entry in enumerate(actual):
                    required_shape(expected[0], entry, f"{path}[{i}]")
    required_shape(template, manifest)
    items = manifest.get(items_key)
    if not isinstance(items, list):
        return errors + [f"{items_key}: missing news array"]
    if len(items) != expected_items:
        errors.append(f"{items_key}: need {expected_items} news items, received {len(items)}")
    ids = [entry.get("id") for entry in items if isinstance(entry, dict)]
    if len(ids) != len(items) or any(not x for x in ids) or len(set(ids)) != len(ids):
        errors.append("missing or duplicate IDs")
    if manifest.get("brand") != "ORBIUNO":
        errors.append("wrong brand")
    if manifest.get("voice", {}).get("id") != "6ce26db0cb6f4e7881b85452619f7f19":
        errors.append("unapproved voice")
    if manifest.get("slot") not in {"08:00", "16:00", "18:00", "20:00"}:
        errors.append("invalid slot")
    for entry in items:
        if not isinstance(entry, dict):
            continue
        source = entry.get("source", {})
        u = source.get("url", "") if isinstance(source, dict) else ""
        parts = urlsplit(u)
        if parts.scheme != "https" or not parts.netloc or parts.path in ("", "/"):
            errors.append(f"{entry.get('id')}: source must be direct HTTPS article")
        if entry.get("date") != manifest.get("editionDate"):
            errors.append(f"{entry.get('id')}: date mismatch")
    return errors
