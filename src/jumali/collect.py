from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .seoul_api import extract_rows, fetch_cultural_events
from .transform import normalize_event


def _date_from_iso(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def filter_mvp_events(events: list[dict[str, Any]], today: date | None = None) -> list[dict[str, Any]]:
    today = today or date.today()
    filtered = []
    for event in events:
        try:
            end_date = _date_from_iso(str(event.get("end_date", "")))
        except ValueError:
            continue
        if not event.get("is_free"):
            continue
        if not event.get("is_child_or_family"):
            continue
        if end_date < today:
            continue
        filtered.append(event)
    return filtered


def effective_limit(api_key: str, requested: int) -> int:
    if api_key == "sample":
        return min(requested, 5)
    return requested


def collect_sample(api_key: str = "sample", limit: int = 100) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    limit = effective_limit(api_key=api_key, requested=limit)
    payload = fetch_cultural_events(api_key=api_key, start=1, end=limit)
    rows = extract_rows(payload)
    normalized = [normalize_event(row) for row in rows]
    return rows, filter_mvp_events(normalized)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Collect Seoul cultural events for 주말아이 MVP")
    parser.add_argument("--api-key", default=os.environ.get("SEOUL_OPENAPI_KEY", "sample"))
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--out-dir", default="data")
    args = parser.parse_args(argv)

    rows, events = collect_sample(api_key=args.api_key, limit=args.limit)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "seoul_cultural_events_raw.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_dir / "seoul_cultural_events_mvp.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"raw_count": len(rows), "mvp_count": len(events), "out_dir": str(out_dir)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
