"""Edition keys and fail-closed persistent state for Bogotá editions."""
import json
import os
import tempfile
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")
SLOTS = (8, 18)
FLOW = ["draft", "verified", "rendered", "validated", "web_synced", "approved", "published"]
TERMINAL_BAD = ("blocked", "failed")


def edition_key(now_utc: datetime) -> str:
    if now_utc.tzinfo is None:
        raise ValueError("Timezone-aware datetime required")
    now = now_utc.astimezone(BOGOTA)
    for days_back in (0, 1):
        d = (now - timedelta(days=days_back)).date()
        for hour in reversed(SLOTS):
            if datetime(d.year, d.month, d.day, hour, tzinfo=BOGOTA) <= now:
                return f"{d.isoformat()}-{hour:02d}00"
    raise RuntimeError("No eligible edition slot")


def can_transition(current: str, next_state: str) -> bool:
    if next_state in TERMINAL_BAD:
        return current in FLOW and current != "published"
    return current in FLOW and next_state in FLOW and FLOW.index(next_state) == FLOW.index(current) + 1


class EditionState:
    def __init__(self, path: str, key: str):
        self.path = path
        self.key = key
        self.data = {"key": key, "state": "draft", "history": []}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as handle:
                self.data = json.load(handle)
            if self.data.get("key") != key:
                raise ValueError("State belongs to a different edition")

    @property
    def state(self):
        return self.data["state"]

    def move(self, next_state: str, detail: str = ""):
        if not can_transition(self.state, next_state):
            raise ValueError(f"Invalid state transition: {self.state} -> {next_state}")
        self.data["history"].append({"from": self.state, "to": next_state, "detail": detail})
        self.data["state"] = next_state
        self.save()

    def fail(self, stage: str, cause: str, action: str, status: str = "failed"):
        if status not in TERMINAL_BAD or not can_transition(self.state, status):
            raise ValueError("Cannot fail published or invalid state")
        self.data["history"].append({"from": self.state, "to": status, "stage": stage, "cause": cause, "action": action})
        self.data["state"] = status
        self.save()

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".orbiuno-", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self.data, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
