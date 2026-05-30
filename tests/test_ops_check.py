from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jumali.ops_check import (
    ActionRun,
    EndpointResult,
    OpsSnapshot,
    SitemapResult,
    default_state_path,
    evaluate_snapshot,
    format_report,
    next_state,
    parse_canonical,
    parse_event_count,
)


def _healthy_snapshot() -> OpsSnapshot:
    return OpsSnapshot(
        generated_at="2026-05-29T09:00:00+09:00",
        action=ActionRun(
            conclusion="success",
            status="completed",
            started_at="2026-05-28T22:10:00Z",
            html_url="https://github.com/dalkiki/weekend-kids/actions/runs/1",
        ),
        endpoints={
            "/": EndpointResult(path="/", status=200, content_type="text/html"),
            "/robots.txt": EndpointResult(path="/robots.txt", status=200, content_type="text/plain"),
            "/gsc-sitemap.xml": EndpointResult(path="/gsc-sitemap.xml", status=200, content_type="application/xml"),
            "/sitemap-index.xml": EndpointResult(path="/sitemap-index.xml", status=200, content_type="application/xml"),
            "/sitemap.xml": EndpointResult(path="/sitemap.xml", status=200, content_type="application/xml"),
        },
        sitemaps={
            "/gsc-sitemap.xml": SitemapResult(path="/gsc-sitemap.xml", status=200, content_type="application/xml", xml_ok=True, url_count=13),
            "/sitemap-index.xml": SitemapResult(path="/sitemap-index.xml", status=200, content_type="application/xml", xml_ok=True, url_count=3),
            "/sitemap.xml": SitemapResult(path="/sitemap.xml", status=200, content_type="application/xml", xml_ok=True, url_count=54),
        },
        missing_status=404,
        counts={"free": 27, "this_weekend": 6, "indoor": 20},
        sitemap_url_count=54,
        canonicals={
            "/": "https://jumalikids.com/",
            "/seoul/free/": "https://jumalikids.com/seoul/free/",
            "/seoul/this-weekend/": "https://jumalikids.com/seoul/this-weekend/",
            "/seoul/indoor/": "https://jumalikids.com/seoul/indoor/",
        },
        updated_at="2026-05-29",
        local_raw_count=200,
        local_mvp_count=27,
        official_url_missing_ratio=0.0,
        adult_broad_samples=[],
        free_fee_conflict_samples=[],
    )


def test_parse_event_count_and_canonical_from_generated_html():
    html = '<link rel="canonical" href="https://jumalikids.com/seoul/free/">\n<p>최종 업데이트: 2026-05-29 · 행사 수: 27개</p>'

    assert parse_event_count(html) == 27
    assert parse_canonical(html) == "https://jumalikids.com/seoul/free/"


def test_default_state_path_uses_active_hermes_home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "profile-home"))

    assert default_state_path() == tmp_path / "profile-home" / "state" / "weekend-kids-ops.json"


def test_evaluate_snapshot_flags_soft_404_and_bad_canonical():
    snapshot = _healthy_snapshot()
    snapshot.missing_status = 200
    snapshot.canonicals["/"] = "https://jumali-did.pages.dev/"

    analysis = evaluate_snapshot(snapshot, previous_state={}, now=datetime.fromisoformat("2026-05-29T09:00:00+09:00"))

    assert analysis.status == "실패"
    assert any("없는 URL" in item for item in analysis.failures)
    assert any("canonical" in item for item in analysis.failures)


def test_evaluate_snapshot_flags_count_drop_against_previous_state():
    snapshot = _healthy_snapshot()
    snapshot.counts["free"] = 9
    snapshot.local_mvp_count = 9
    snapshot.sitemap_url_count = 24
    snapshot.sitemaps["/sitemap.xml"].url_count = 24
    previous_state = {
        "last_success": {
            "counts": {"free": 27, "this_weekend": 6, "indoor": 20},
            "local_mvp_count": 27,
            "sitemap_url_count": 54,
        }
    }

    analysis = evaluate_snapshot(snapshot, previous_state=previous_state, now=datetime.fromisoformat("2026-05-29T09:00:00+09:00"))

    assert analysis.status == "실패"
    assert any("무료 행사 수" in item for item in analysis.failures)
    assert any("sitemap URL 수" in item for item in analysis.failures)


def test_daily_report_is_silent_when_healthy_but_weekly_summarizes():
    snapshot = _healthy_snapshot()
    analysis = evaluate_snapshot(snapshot, previous_state={}, now=datetime.fromisoformat("2026-05-29T09:00:00+09:00"))

    assert format_report(snapshot, analysis, mode="daily", force_output=False) == ""
    weekly = format_report(snapshot, analysis, mode="weekly", force_output=False)

    assert "주말아이 주간 운영 리포트" in weekly
    assert "상태: 정상" in weekly
    assert "태훈님 직접 작업" in weekly


def test_next_state_updates_success_baseline_only_without_failures():
    snapshot = _healthy_snapshot()
    analysis = evaluate_snapshot(snapshot, previous_state={}, now=datetime.fromisoformat("2026-05-29T09:00:00+09:00"))

    state = next_state({}, snapshot, analysis)

    assert state["last_success"]["counts"] == {"free": 27, "this_weekend": 6, "indoor": 20}
    assert state["last_success"]["sitemap_url_count"] == 54

    failed_snapshot = _healthy_snapshot()
    failed_snapshot.missing_status = 200
    failed_analysis = evaluate_snapshot(failed_snapshot, previous_state=state, now=datetime.fromisoformat("2026-05-29T09:00:00+09:00"))
    unchanged = next_state(state, failed_snapshot, failed_analysis)

    assert unchanged["last_success"]["sitemap_url_count"] == 54
