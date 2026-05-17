from __future__ import annotations

import json
import urllib.request
from typing import Any

BASE_URL = "http://openapi.seoul.go.kr:8088"
SERVICE_NAME = "culturalEventInfo"


def build_cultural_event_url(api_key: str, start: int = 1, end: int = 100) -> str:
    if start < 1 or end < start:
        raise ValueError("start/end range is invalid")
    return f"{BASE_URL}/{api_key}/json/{SERVICE_NAME}/{start}/{end}/"


def fetch_cultural_events(api_key: str = "sample", start: int = 1, end: int = 100) -> dict[str, Any]:
    url = build_cultural_event_url(api_key=api_key, start=start, end=end)
    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    root = payload.get(SERVICE_NAME, {})
    rows = root.get("row", [])
    return rows if isinstance(rows, list) else []
