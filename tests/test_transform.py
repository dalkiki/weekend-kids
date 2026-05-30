from datetime import date

from jumali.transform import assess_event_relevance, classify_fee, is_child_or_family_event, is_free_event, normalize_event, parse_seoul_date_range


def test_parse_seoul_date_range_handles_tilde_range():
    start, end = parse_seoul_date_range("2026-05-16~2026-05-18")

    assert start == date(2026, 5, 16)
    assert end == date(2026, 5, 18)


def test_free_event_uses_free_field_and_fee_text_without_paid_conflict():
    assert is_free_event({"IS_FREE": "무료", "USE_FEE": "무료"}) is True
    assert is_free_event({"IS_FREE": "유료", "USE_FEE": "무료"}) is True
    assert is_free_event({"IS_FREE": "무료", "USE_FEE": "R석 30,000원, S석 20,000원"}) is False
    assert is_free_event({"IS_FREE": "무료", "USE_FEE": "R석 2만원 S석 1만5천원"}) is False
    assert is_free_event({"IS_FREE": "유료", "USE_FEE": "20,000원"}) is False


def test_child_or_family_event_detects_target_and_title_keywords():
    assert is_child_or_family_event({"TITLE": "어린이 뮤지컬", "USE_TRGT": "누구나"}) is True
    assert is_child_or_family_event({"TITLE": "전시", "USE_TRGT": "가족 및 초등학생"}) is True
    assert is_child_or_family_event({"TITLE": "성인 재즈 공연", "USE_TRGT": "19세 이상"}) is False


def test_child_or_family_event_does_not_treat_no_preschoolers_as_child_friendly():
    raw = {"TITLE": "피아노 리사이틀", "USE_TRGT": "8세이상 관람가능(미취학아동입장불가)"}

    assert is_child_or_family_event(raw) is False


def test_relevance_score_separates_strong_broad_and_weak_family_fit():
    strong = assess_event_relevance({"TITLE": "유아 가족 과학 체험", "USE_TRGT": "초등학생 가족"})
    broad = assess_event_relevance({"TITLE": "서울 거리 공연", "USE_TRGT": "누구나"})
    weak = assess_event_relevance({"TITLE": "주말N 인문산책", "USE_TRGT": "청소년 이상 성인 누구나"})

    assert strong["bucket"] == "strong"
    assert broad["bucket"] == "broad"
    assert weak["bucket"] == "weak"
    assert strong["score"] > broad["score"] > weak["score"]


def test_adult_companion_phrase_is_not_treated_as_child_friendly():
    raw = {"TITLE": "재즈 공연", "USE_TRGT": "성인 동반에 한해 가능"}

    assert assess_event_relevance(raw)["bucket"] == "weak"
    assert is_child_or_family_event(raw) is False


def test_target_only_child_signal_is_a_strong_match():
    raw = {"TITLE": "몸으로 예술놀이", "USE_TRGT": "초등 2~4학년"}

    assert assess_event_relevance(raw)["bucket"] == "strong"


def test_age_floor_only_is_not_promoted_to_strong_child_focus():
    raw = {"TITLE": "소프라노 독창회", "USE_TRGT": "초등학생 이상 관람 가능", "CODENAME": "클래식"}

    result = assess_event_relevance(raw)

    assert result["bucket"] == "weak"
    assert "age_floor_only_not_child_focused" in result["reasons"]


def test_age_floor_with_explicit_child_title_stays_strong():
    raw = {"TITLE": "어린이 가족 클래식 체험", "USE_TRGT": "초등학생 이상 관람 가능", "CODENAME": "클래식"}

    assert assess_event_relevance(raw)["bucket"] == "strong"


def test_fee_classification_marks_free_and_paid_conflicts_as_check_needed():
    raw = {"IS_FREE": "무료", "USE_FEE": "입장 무료, 체험 재료비 5,000원"}

    fee = classify_fee(raw)

    assert fee["status"] == "paid_or_mixed"
    assert fee["is_free"] is False
    assert "무료로 단정하지 않습니다" in fee["notice"]


def test_normalize_event_keeps_core_fields_and_tags():
    raw = {
        "TITLE": "어린이 무료 체험",
        "DATE": "2026-05-16~2026-05-18",
        "GUNAME": "마포구",
        "PLACE": "마포아트센터",
        "USE_TRGT": "어린이 및 가족",
        "USE_FEE": "무료",
        "IS_FREE": "무료",
        "HMPG_ADDR": "https://example.com/event",
        "CODENAME": "체험",
        "MAIN_IMG": "https://example.com/image.jpg",
        "STRTDATE": "2026-05-16 00:00:00.0",
        "END_DATE": "2026-05-18 00:00:00.0",
    }

    event = normalize_event(raw)

    assert event["title"] == "어린이 무료 체험"
    assert event["district"] == "마포구"
    assert event["start_date"] == "2026-05-16"
    assert event["end_date"] == "2026-05-18"
    assert event["is_free"] is True
    assert event["is_child_or_family"] is True
    assert event["fee_status"] == "free"
    assert event["relevance_bucket"] == "strong"
    assert event["relevance_score"] > 0
    assert event["source"] == "서울 열린데이터광장 서울시 문화행사 정보"
