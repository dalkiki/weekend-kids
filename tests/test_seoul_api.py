from jumali.collect import effective_limit
from jumali.seoul_api import build_cultural_event_url, extract_rows


def test_build_cultural_event_url_uses_json_endpoint_and_range():
    url = build_cultural_event_url(api_key="sample", start=1, end=100)

    assert url == "http://openapi.seoul.go.kr:8088/sample/json/culturalEventInfo/1/100/"


def test_effective_limit_caps_sample_key_to_openapi_sample_limit():
    assert effective_limit(api_key="sample", requested=100) == 5
    assert effective_limit(api_key="real-key", requested=100) == 100


def test_extract_rows_returns_empty_list_when_no_rows():
    payload = {"culturalEventInfo": {"RESULT": {"CODE": "INFO-000"}}}

    assert extract_rows(payload) == []


def test_extract_rows_reads_cultural_event_rows():
    payload = {"culturalEventInfo": {"row": [{"TITLE": "행사"}]}}

    assert extract_rows(payload) == [{"TITLE": "행사"}]
