from datetime import date

from jumali.collect import filter_mvp_events


def test_filter_mvp_events_keeps_free_child_family_future_events():
    events = [
        {"title": "무료 어린이 체험", "is_free": True, "is_child_or_family": True, "end_date": "2026-05-18"},
        {"title": "유료 어린이 공연", "is_free": False, "is_child_or_family": True, "end_date": "2026-05-18"},
        {"title": "무료 성인 공연", "is_free": True, "is_child_or_family": False, "end_date": "2026-05-18"},
        {"title": "지난 무료 어린이 체험", "is_free": True, "is_child_or_family": True, "end_date": "2026-05-10"},
    ]

    filtered = filter_mvp_events(events, today=date(2026, 5, 17))

    assert [event["title"] for event in filtered] == ["무료 어린이 체험"]
