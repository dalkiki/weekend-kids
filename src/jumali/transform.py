from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

SOURCE_NAME = "서울 열린데이터광장 서울시 문화행사 정보"

_CHILD_KEYWORDS = (
    "어린이",
    "아동",
    "유아",
    "초등",
    "초등학생",
    "가족",
    "부모",
    "아이",
    "키즈",
    "청소년",
)
_PAID_PRICE_PATTERN = re.compile(r"\d[\d,]*(?:\s*원|\s*만\s*\d*\s*천?\s*원|\s*만원|\s*천원)")
_CHILD_NEGATIVE_PATTERNS = (
    "미취학아동입장불가",
    "미취학 아동 입장 불가",
    "미취학아동 입장불가",
    "미취학 아동입장불가",
)


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _parse_date(value: str) -> date:
    value = _clean(value)
    if not value:
        raise ValueError("date value is empty")
    # Seoul API may return either YYYY-MM-DD or YYYY-MM-DD HH:MM:SS.0.
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def parse_seoul_date_range(date_range: str) -> tuple[date, date]:
    parts = [_clean(part) for part in _clean(date_range).split("~") if _clean(part)]
    if not parts:
        raise ValueError("date range is empty")
    start = _parse_date(parts[0])
    end = _parse_date(parts[1]) if len(parts) > 1 else start
    return start, end


def is_free_event(raw: dict[str, Any]) -> bool:
    is_free = _clean(raw.get("IS_FREE"))
    fee = _clean(raw.get("USE_FEE"))
    if _PAID_PRICE_PATTERN.search(fee):
        return False
    text = f"{is_free} {fee}"
    if "무료" in text:
        return True
    return False


def is_child_or_family_event(raw: dict[str, Any]) -> bool:
    text = " ".join(
        _clean(raw.get(field))
        for field in ("TITLE", "USE_TRGT", "PROGRAM", "ETC_DESC", "CODENAME")
    )
    compact_text = text.replace(" ", "")
    if any(pattern.replace(" ", "") in compact_text for pattern in _CHILD_NEGATIVE_PATTERNS):
        return False
    return any(keyword in text for keyword in _CHILD_KEYWORDS)


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("STRTDATE"):
        start = _parse_date(_clean(raw.get("STRTDATE")))
        end = _parse_date(_clean(raw.get("END_DATE") or raw.get("STRTDATE")))
    else:
        start, end = parse_seoul_date_range(_clean(raw.get("DATE")))

    return {
        "title": _clean(raw.get("TITLE")),
        "category": _clean(raw.get("CODENAME")),
        "district": _clean(raw.get("GUNAME")),
        "place": _clean(raw.get("PLACE")),
        "date_text": _clean(raw.get("DATE")),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "target": _clean(raw.get("USE_TRGT")),
        "fee": _clean(raw.get("USE_FEE")),
        "is_free": is_free_event(raw),
        "is_child_or_family": is_child_or_family_event(raw),
        "official_url": _clean(raw.get("HMPG_ADDR") or raw.get("ORG_LINK")),
        "image_url": _clean(raw.get("MAIN_IMG")),
        "source": SOURCE_NAME,
    }
