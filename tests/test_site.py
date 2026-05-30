import xml.etree.ElementTree as ET
from pathlib import Path

from jumali.site import build_site, render_home


SAMPLE_EVENTS = [
    {
        "title": "강북 어린이 미술 체험",
        "category": "교육/체험",
        "district": "강북구",
        "place": "서울문화예술교육센터 강북 4층 대강의실",
        "date_text": "2026-05-23~2026-05-24",
        "start_date": "2026-05-23",
        "end_date": "2026-05-24",
        "target": "초등학생 가족",
        "fee": "무료",
        "official_url": "https://example.com/event-1",
        "source": "서울 열린데이터광장 서울시 문화행사 정보",
    },
    {
        "title": "송파 가족 박물관 수업",
        "category": "교육/체험",
        "district": "송파구",
        "place": "서울백제어린이박물관 교육실",
        "date_text": "2026-06-11~2026-07-30",
        "start_date": "2026-06-11",
        "end_date": "2026-07-30",
        "target": "유아 단체",
        "fee": "무료",
        "official_url": "https://example.com/event-2",
        "source": "서울 열린데이터광장 서울시 문화행사 정보",
    },
]


def test_render_home_uses_clean_information_tone_and_empty_state():
    html = render_home(events=[], updated_at="2026-05-17", site_url="https://jumalikids.com")

    assert "주말아이" in html
    assert "서울 아이랑 갈만한 무료 행사" in html
    assert "현재 조건에 맞는 행사가 없습니다" in html
    assert "최종 업데이트: 2026-05-17" in html
    assert 'name="google-site-verification"' in html
    assert "LijPvePAqz82GY0V_DW5AjF9R9e1R89j3-eOWJ_R138" in html
    assert "MVP 테스트" not in html
    assert "테스트 사이트" not in html
    assert 'rel="canonical" href="https://jumalikids.com/"' in html
    assert 'href="/seoul/free/"' in html
    assert 'href="/seoul/this-weekend/"' in html
    assert 'href="/about/"' in html
    assert 'href="/contact/"' in html


def test_render_home_prioritizes_strong_relevance_and_shows_quality_badges():
    weak_adult = dict(
        SAMPLE_EVENTS[0],
        title="주말N 인문산책",
        target="청소년 이상 성인 누구나",
        relevance_score=15,
        relevance_bucket="weak",
    )
    broad = dict(
        SAMPLE_EVENTS[0],
        title="서울 열린 거리 공연",
        target="누구나",
        relevance_score=45,
        relevance_bucket="broad",
    )
    strong = dict(
        SAMPLE_EVENTS[0],
        title="초등 가족 과학 체험",
        target="초등학생 가족",
        relevance_score=90,
        relevance_bucket="strong",
    )

    html = render_home(events=[weak_adult, broad, strong], updated_at="2026-05-17", site_url="https://jumalikids.com")

    assert html.index("초등 가족 과학 체험") < html.index("서울 열린 거리 공연") < html.index("주말N 인문산책")
    assert "아이랑 핵심" in html
    assert "가족 가능성" in html
    assert "대상 확인 필요" in html


def test_build_site_writes_planned_landing_detail_trust_pages_and_sitemap(tmp_path: Path):
    build_site(events=SAMPLE_EVENTS, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    expected_files = [
        "index.html",
        "seoul/free/index.html",
        "seoul/this-weekend/index.html",
        "seoul/indoor/index.html",
        "seoul/gu/강북구/index.html",
        "seoul/gu/송파구/index.html",
        "about/index.html",
        "contact/index.html",
        "sources/index.html",
        "privacy/index.html",
        "404.html",
        "robots.txt",
        "_headers",
        "_redirects",
        "gsc-sitemap.xml",
        "sitemap-index.xml",
        "sitemap-basic.xml",
        "sitemap.xml",
        "sitemap.txt",
    ]
    for rel_path in expected_files:
        assert (tmp_path / rel_path).exists(), rel_path

    event_pages = sorted((tmp_path / "events").glob("*/index.html"))
    assert len(event_pages) == 2
    first_event_html = event_pages[0].read_text(encoding="utf-8")
    assert "공식 페이지" in first_event_html
    assert "방문 전" in first_event_html
    assert "예약 방식" in first_event_html
    assert "요금 확인" in first_event_html
    assert "대상 연령" in first_event_html
    assert 'rel="canonical"' in first_event_html

    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://jumalikids.com/seoul/free/" in sitemap
    assert "https://jumalikids.com/seoul/this-weekend/" in sitemap
    assert "https://jumalikids.com/about/" in sitemap
    assert "https://jumalikids.com/contact/" in sitemap
    assert "https://jumalikids.com/events/" in sitemap
    assert "<lastmod>2026-05-22</lastmod>" in sitemap
    assert "404.html" not in sitemap

    not_found = (tmp_path / "404.html").read_text(encoding="utf-8")
    assert "페이지를 찾을 수 없습니다" in not_found
    assert 'name="robots" content="noindex"' in not_found
    assert 'href="/seoul/free/"' in not_found

    sitemap_root = ET.fromstring(sitemap)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locs = [node.text or "" for node in sitemap_root.findall(".//sm:loc", namespace)]
    assert locs
    assert all(loc.isascii() for loc in locs)
    assert all(" " not in loc for loc in locs)
    assert any("%EA%B0%95%EB%B6%81%EA%B5%AC" in loc for loc in locs)
    assert "강북구" not in sitemap

    sitemap_txt = (tmp_path / "sitemap.txt").read_text(encoding="utf-8")
    assert "https://jumalikids.com/seoul/free/" in sitemap_txt
    assert "%EA%B0%95%EB%B6%81%EA%B5%AC" in sitemap_txt
    assert "강북구" not in sitemap_txt

    robots = (tmp_path / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap: https://jumalikids.com/gsc-sitemap.xml" in robots
    assert "Sitemap: https://jumalikids.com/sitemap-index.xml" in robots
    assert "Sitemap: https://jumalikids.com/sitemap.xml" in robots
    assert "Sitemap: https://jumalikids.com/sitemap-basic.xml" in robots
    assert "Sitemap: https://jumalikids.com/sitemap.txt" in robots

    sitemap_index = (tmp_path / "sitemap-index.xml").read_text(encoding="utf-8")
    index_root = ET.fromstring(sitemap_index)
    index_locs = [node.text or "" for node in index_root.findall(".//sm:loc", namespace)]
    assert index_locs == [
        "https://jumalikids.com/gsc-sitemap.xml",
        "https://jumalikids.com/sitemap-basic.xml",
        "https://jumalikids.com/sitemap.xml",
    ]

    gsc_sitemap = (tmp_path / "gsc-sitemap.xml").read_text(encoding="utf-8")
    gsc_root = ET.fromstring(gsc_sitemap)
    gsc_locs = [node.text or "" for node in gsc_root.findall(".//sm:loc", namespace)]
    assert "https://jumalikids.com/" in gsc_locs
    assert "https://jumalikids.com/seoul/free/" in gsc_locs
    assert all("events/" not in loc for loc in gsc_locs)

    sitemap_basic = (tmp_path / "sitemap-basic.xml").read_text(encoding="utf-8")
    assert "https://jumalikids.com/seoul/free/" in sitemap_basic
    assert "https://jumalikids.com/events/" not in sitemap_basic

    redirects = (tmp_path / "_redirects").read_text(encoding="utf-8")
    assert "/https:/*/gsc-sitemap.xml /gsc-sitemap.xml 301" in redirects
    assert "/https:/*/sitemap.xml /sitemap.xml 301" in redirects
    assert "/https:/*/sitemap-index.xml /sitemap-index.xml 301" in redirects
    assert "/https:/*/sitemap-basic.xml /sitemap-basic.xml 301" in redirects
    assert "/https:/*/sitemap.txt /sitemap.txt 301" in redirects
    assert "/sitemap.xml/ /sitemap.xml 301" in redirects
    assert "/sitemap /sitemap.xml 301" in redirects

    headers = (tmp_path / "_headers").read_text(encoding="utf-8")
    assert "/gsc-sitemap.xml" in headers
    assert "/sitemap.xml" in headers
    assert "Content-Type: application/xml; charset=utf-8" in headers


def test_trust_pages_are_substantial_and_not_test_placeholders(tmp_path: Path):
    build_site(events=SAMPLE_EVENTS, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    sources = (tmp_path / "sources" / "index.html").read_text(encoding="utf-8")
    privacy = (tmp_path / "privacy" / "index.html").read_text(encoding="utf-8")
    contact = (tmp_path / "contact" / "index.html").read_text(encoding="utf-8")

    assert "업데이트 주기" in sources
    assert "필터링 기준" in sources
    assert "오분류 정정 원칙" in sources
    assert len(sources) > 900
    assert "개인정보를 직접 수집하지 않습니다" in privacy
    assert "광고" in privacy
    assert len(privacy) > 700
    assert "정보 정정" in contact
    assert "공개 문의 채널" in contact
    assert "mailto:thk8544@gmail.com" in contact
    assert "MVP 테스트" not in sources + privacy + contact


def test_event_detail_uses_conservative_fee_age_and_reservation_cautions(tmp_path: Path):
    mixed_fee_event = dict(
        SAMPLE_EVENTS[0],
        title="청소년 이상 성인 인문산책",
        target="청소년 이상 성인 누구나",
        fee="입장 무료, 체험 재료비 5,000원",
        fee_status="paid_or_mixed",
        fee_notice="무료 표시와 비용 문구가 함께 있어 무료로 단정하지 않습니다.",
        relevance_bucket="weak",
        relevance_score=15,
    )

    build_site(events=[mixed_fee_event], out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    detail = next((tmp_path / "events").glob("*/index.html")).read_text(encoding="utf-8")
    assert "무료로 단정하지 않습니다" in detail
    assert "예약 방식" in detail
    assert "공식 페이지에서 접수" in detail
    assert "대상 연령" in detail
    assert "어린이·가족 대상인지 확인 필요" in detail


def test_build_site_writes_substantial_parent_guide_pages_and_links_them(tmp_path: Path):
    build_site(events=SAMPLE_EVENTS, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    expected_guides = {
        "guides/free-kids-events-seoul/index.html": "서울 아이랑 무료 행사 찾는 법",
        "guides/this-weekend-kids-plan/index.html": "이번 주말 아이랑 갈 곳 고르는 법",
        "guides/rainy-day-indoor-kids-seoul/index.html": "비 오는 날 서울 실내 행사 고르는 법",
        "guides/age-target-check/index.html": "유아·초등 대상 연령 확인법",
        "guides/reservation-fee-checklist/index.html": "무료 행사 예약·요금 체크리스트",
    }
    all_guide_html = []
    for rel_path, heading in expected_guides.items():
        guide = (tmp_path / rel_path).read_text(encoding="utf-8")
        all_guide_html.append(guide)
        assert heading in guide
        assert "방문 전 체크리스트" in guide
        assert "공식 페이지" in guide
        assert 'rel="canonical" href="https://jumalikids.com/' in guide
        assert len(guide) > 1600
        assert "MVP 테스트" not in guide
        assert "테스트 사이트" not in guide

    home = (tmp_path / "index.html").read_text(encoding="utf-8")
    free = (tmp_path / "seoul" / "free" / "index.html").read_text(encoding="utf-8")
    weekend = (tmp_path / "seoul" / "this-weekend" / "index.html").read_text(encoding="utf-8")
    indoor = (tmp_path / "seoul" / "indoor" / "index.html").read_text(encoding="utf-8")
    detail = next((tmp_path / "events").glob("*/index.html")).read_text(encoding="utf-8")

    assert "부모용 행사 선택 가이드" in home
    assert 'href="/guides/free-kids-events-seoul/"' in home
    assert 'href="/guides/this-weekend-kids-plan/"' in weekend
    assert 'href="/guides/rainy-day-indoor-kids-seoul/"' in indoor
    assert 'href="/guides/reservation-fee-checklist/"' in free
    assert "방문 전 3분 체크" in detail
    assert 'href="/guides/age-target-check/"' in detail
    assert 'href="/guides/reservation-fee-checklist/"' in detail

    gsc_sitemap = (tmp_path / "gsc-sitemap.xml").read_text(encoding="utf-8")
    sitemap = (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://jumalikids.com/guides/free-kids-events-seoul/" in gsc_sitemap
    assert "https://jumalikids.com/guides/reservation-fee-checklist/" in sitemap
    assert "서울 아이랑 무료 행사" in "\n".join(all_guide_html)


def test_generated_html_does_not_contain_whitespace_only_lines(tmp_path: Path):
    build_site(events=SAMPLE_EVENTS, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    offenders = []
    for html_file in tmp_path.rglob("*.html"):
        for line_no, line in enumerate(html_file.read_text(encoding="utf-8").splitlines(), start=1):
            if line and not line.strip():
                offenders.append(f"{html_file.relative_to(tmp_path)}:{line_no}")

    assert offenders == []


def test_build_site_removes_stale_output_pages(tmp_path: Path):
    (tmp_path / ".jumali-build-output").write_text("generated\n", encoding="utf-8")
    stale = tmp_path / "events" / "old-event" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    build_site(events=SAMPLE_EVENTS[:1], out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    assert not stale.exists()
    assert (tmp_path / ".jumali-build-output").exists()


def test_event_urls_are_unique_when_title_date_and_district_match(tmp_path: Path):
    duplicated = [dict(SAMPLE_EVENTS[0], place="1층 강의실"), dict(SAMPLE_EVENTS[0], place="2층 강의실")]

    build_site(events=duplicated, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    event_pages = sorted((tmp_path / "events").glob("*/index.html"))
    assert len(event_pages) == 2
    assert len({page.parent.name for page in event_pages}) == 2


def test_unsafe_official_url_schemes_are_not_rendered(tmp_path: Path):
    unsafe = [dict(SAMPLE_EVENTS[0], official_url="javascript:alert(1)")]

    build_site(events=unsafe, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")

    all_html = "\n".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("*.html"))
    assert "javascript:alert" not in all_html


def test_build_site_refuses_to_clear_project_root(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='unsafe'\n", encoding="utf-8")

    try:
        build_site(events=SAMPLE_EVENTS, out_dir=tmp_path, updated_at="2026-05-22", site_url="https://jumalikids.com")
    except ValueError as exc:
        assert "Unsafe output directory" in str(exc)
    else:
        raise AssertionError("build_site should reject deleting a project root")


def test_build_site_refuses_to_delete_unmarked_existing_directory(tmp_path: Path):
    existing = tmp_path / "photos"
    existing.mkdir()
    keep = existing / "important.txt"
    keep.write_text("do not delete", encoding="utf-8")

    try:
        build_site(events=SAMPLE_EVENTS, out_dir=existing, updated_at="2026-05-22", site_url="https://jumalikids.com")
    except ValueError as exc:
        assert "Unsafe output directory" in str(exc)
    else:
        raise AssertionError("build_site should reject deleting unmarked directories")

    assert keep.read_text(encoding="utf-8") == "do not delete"


def test_build_site_allows_marked_existing_output_directory(tmp_path: Path):
    out_dir = tmp_path / "site-output"
    out_dir.mkdir()
    (out_dir / ".jumali-build-output").write_text("generated\n", encoding="utf-8")
    stale = out_dir / "events" / "old-event" / "index.html"
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")

    build_site(events=SAMPLE_EVENTS[:1], out_dir=out_dir, updated_at="2026-05-22", site_url="https://jumalikids.com")

    assert not stale.exists()
    assert (out_dir / ".jumali-build-output").exists()


def test_input_detail_path_cannot_escape_output_directory(tmp_path: Path):
    out_dir = tmp_path / "site"
    escaped = tmp_path / "escaped" / "index.html"
    malicious = [dict(SAMPLE_EVENTS[0], _detail_path="/../escaped/")]

    build_site(events=malicious, out_dir=out_dir, updated_at="2026-05-22", site_url="https://jumalikids.com")

    assert not escaped.exists()
    assert len(list((out_dir / "events").glob("*/index.html"))) == 1


def _detail_slug_by_title(out_dir: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for page in (out_dir / "events").glob("*/index.html"):
        text = page.read_text(encoding="utf-8")
        for event in SAMPLE_EVENTS:
            if event["title"] in text:
                mapping[event["title"]] = page.parent.name
    return mapping


def test_event_slugs_stay_stable_when_input_order_changes(tmp_path: Path):
    extra = dict(SAMPLE_EVENTS[0], title="새로 추가된 행사", place="다른 장소", official_url="https://example.com/extra")
    first_out = tmp_path / "first"
    second_out = tmp_path / "second"

    build_site(events=SAMPLE_EVENTS, out_dir=first_out, updated_at="2026-05-22", site_url="https://jumalikids.com")
    build_site(events=[extra, *SAMPLE_EVENTS], out_dir=second_out, updated_at="2026-05-22", site_url="https://jumalikids.com")

    assert _detail_slug_by_title(first_out) == _detail_slug_by_title(second_out)
