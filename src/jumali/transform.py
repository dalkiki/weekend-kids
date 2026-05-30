from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

SOURCE_NAME = "서울 열린데이터광장 서울시 문화행사 정보"

_STRONG_CHILD_KEYWORDS = (
    "어린이",
    "아동",
    "유아",
    "초등",
    "초등학생",
    "가족",
    "부모",
    "아이",
    "키즈",
    "양육자",
    "영유아",
)
_BROAD_AUDIENCE_KEYWORDS = (
    "누구나",
    "시민 누구나",
    "전 연령",
    "전연령",
    "전체관람",
    "전체 관람",
)
_ADULT_OR_YOUTH_CENTERED_PATTERNS = (
    "청소년 이상 성인",
    "청소년이상 성인",
    "청소년 이상",
    "성인 누구나",
    "성인 대상",
    "19세 이상",
    "만 18세 이상",
    "성인 동반에 한해 가능",
    "성인동반에한해가능",
)
_AGE_FLOOR_ONLY_PATTERNS = (
    "초등학생 이상",
    "초등학생이상",
    "초등 이상",
    "초등이상",
    "초등생 이상",
    "초등생이상",
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


def _combined_text(raw: dict[str, Any], fields: tuple[str, ...]) -> str:
    return " ".join(_clean(raw.get(field)) for field in fields if _clean(raw.get(field)))


def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_fee(raw: dict[str, Any]) -> dict[str, Any]:
    is_free = _clean(raw.get("IS_FREE"))
    fee = _clean(raw.get("USE_FEE") or raw.get("fee"))
    text = f"{is_free} {fee}"
    has_free_label = "무료" in text or raw.get("is_free") is True
    has_paid_signal = bool(_PAID_PRICE_PATTERN.search(fee)) or ("유료" in fee and "무료" not in fee)

    if has_paid_signal:
        return {
            "status": "paid_or_mixed",
            "is_free": False,
            "notice": "무료 표시와 비용 문구가 함께 있어 무료로 단정하지 않습니다. 공식 페이지에서 실제 요금을 확인해 주세요.",
        }
    if has_free_label:
        return {
            "status": "free",
            "is_free": True,
            "notice": "공공데이터에는 무료로 표시되어 있습니다. 다만 재료비·보호자 비용은 공식 페이지에서 다시 확인해 주세요.",
        }
    return {
        "status": "check_needed",
        "is_free": False,
        "notice": "요금 정보가 비어 있거나 애매해 확인 필요로 분류했습니다. 무료로 단정하지 않습니다.",
    }


def assess_event_relevance(raw: dict[str, Any]) -> dict[str, Any]:
    title = _combined_text(raw, ("TITLE", "title"))
    target = _combined_text(raw, ("USE_TRGT", "target"))
    supporting = _combined_text(raw, ("PROGRAM", "ETC_DESC", "CODENAME", "category", "PLACE", "place"))
    text = f"{title} {target} {supporting}"
    compact_text = text.replace(" ", "")

    if any(pattern.replace(" ", "") in compact_text for pattern in _CHILD_NEGATIVE_PATTERNS):
        return {"score": 0, "bucket": "weak", "reasons": ["negative_child_phrase"]}

    score = 0
    reasons: list[str] = []
    if _has_keyword(title, _STRONG_CHILD_KEYWORDS):
        score += 50
        reasons.append("child_keyword_title")
    if _has_keyword(target, _STRONG_CHILD_KEYWORDS):
        score += 35
        reasons.append("child_keyword_target")
    if _has_keyword(supporting, _STRONG_CHILD_KEYWORDS):
        score += 20
        reasons.append("child_keyword_supporting")
    if _has_keyword(text, _BROAD_AUDIENCE_KEYWORDS):
        score += 35
        reasons.append("broad_audience")

    is_adult_or_youth_centered = any(
        pattern.replace(" ", "") in compact_text
        for pattern in _ADULT_OR_YOUTH_CENTERED_PATTERNS
    )
    if is_adult_or_youth_centered:
        score -= 15 if any(reason.startswith("child_keyword") for reason in reasons) else 60
        reasons.append("adult_or_youth_centered_phrase")

    compact_target = target.replace(" ", "")
    is_age_floor_only = any(
        pattern.replace(" ", "") in compact_target
        for pattern in _AGE_FLOOR_ONLY_PATTERNS
    ) and not _has_keyword(f"{title} {supporting}", _STRONG_CHILD_KEYWORDS)
    if is_age_floor_only:
        score = min(score, 34)
        reasons.append("age_floor_only_not_child_focused")

    score = max(0, min(100, score))
    has_child_signal = any(reason.startswith("child_keyword") for reason in reasons)
    if has_child_signal and score >= 35:
        bucket = "strong"
    elif score >= 35:
        bucket = "broad"
    else:
        bucket = "weak"
    return {"score": score, "bucket": bucket, "reasons": reasons}


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
    return bool(classify_fee(raw)["is_free"])


def is_child_or_family_event(raw: dict[str, Any]) -> bool:
    return str(assess_event_relevance(raw)["bucket"]) in {"strong", "broad"}


def normalize_event(raw: dict[str, Any]) -> dict[str, Any]:
    if raw.get("STRTDATE"):
        start = _parse_date(_clean(raw.get("STRTDATE")))
        end = _parse_date(_clean(raw.get("END_DATE") or raw.get("STRTDATE")))
    else:
        start, end = parse_seoul_date_range(_clean(raw.get("DATE")))

    fee = classify_fee(raw)
    relevance = assess_event_relevance(raw)

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
        "is_free": fee["is_free"],
        "fee_status": fee["status"],
        "fee_notice": fee["notice"],
        "is_child_or_family": relevance["bucket"] in {"strong", "broad"},
        "relevance_score": relevance["score"],
        "relevance_bucket": relevance["bucket"],
        "relevance_reasons": relevance["reasons"],
        "official_url": _clean(raw.get("HMPG_ADDR") or raw.get("ORG_LINK")),
        "image_url": _clean(raw.get("MAIN_IMG")),
        "source": SOURCE_NAME,
    }
