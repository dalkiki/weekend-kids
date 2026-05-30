from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

DEFAULT_SITE_URL = "https://jumalikids.com"
DEFAULT_GITHUB_REPO = "dalkiki/weekend-kids"
DEFAULT_WORKFLOW = "daily-refresh.yml"
USER_AGENT = "JumaliKidsOpsCheck/1.0 (+https://jumalikids.com/)"
GOOGLEBOT_UA = "Googlebot/2.1 (+https://www.google.com/bot.html)"
KST = ZoneInfo("Asia/Seoul")
REQUIRED_ENDPOINTS = ("/", "/robots.txt", "/gsc-sitemap.xml", "/sitemap-index.xml", "/sitemap.xml")
REQUIRED_SITEMAPS = ("/gsc-sitemap.xml", "/sitemap-index.xml", "/sitemap.xml")
COUNT_PAGES = {
    "free": "/seoul/free/",
    "this_weekend": "/seoul/this-weekend/",
    "indoor": "/seoul/indoor/",
}
CANONICAL_PAGES = ("/", "/seoul/free/", "/seoul/this-weekend/", "/seoul/indoor/")

_EVENT_COUNT_RE = re.compile(r"행사\s*수\s*[:：]\s*([0-9,]+)\s*개")
_CANONICAL_RE = re.compile(r"<link\s+rel=[\"']canonical[\"']\s+href=[\"']([^\"']+)[\"']", re.IGNORECASE)
_UPDATED_RE = re.compile(r"최종\s*업데이트\s*[:：]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})")
_PAID_PRICE_PATTERN = re.compile(r"\d[\d,]*(?:\s*원|\s*만\s*\d*\s*천?\s*원|\s*만원|\s*천원)")
_STRONG_FAMILY_TERMS = ("어린이", "아동", "유아", "초등", "가족", "키즈", "부모", "육아", "책놀이", "스토리텔링")
_ADULT_OR_BROAD_TERMS = ("성인", "19세", "청년", "시니어", "어르신", "노인", "재즈", "독창회", "예술가곡", "클래식")


@dataclass
class ActionRun:
    conclusion: str
    status: str
    started_at: str
    html_url: str = ""
    error: str = ""


@dataclass
class EndpointResult:
    path: str
    status: int
    content_type: str = ""
    error: str = ""


@dataclass
class SitemapResult:
    path: str
    status: int
    content_type: str = ""
    xml_ok: bool = False
    url_count: int = 0
    error: str = ""


@dataclass
class OpsSnapshot:
    generated_at: str
    action: ActionRun | None
    endpoints: dict[str, EndpointResult]
    sitemaps: dict[str, SitemapResult]
    missing_status: int | None
    counts: dict[str, int]
    sitemap_url_count: int | None
    canonicals: dict[str, str]
    updated_at: str | None
    local_raw_count: int | None
    local_mvp_count: int | None
    official_url_missing_ratio: float
    adult_broad_samples: list[str] = field(default_factory=list)
    free_fee_conflict_samples: list[str] = field(default_factory=list)


@dataclass
class Analysis:
    status: str
    failures: list[str]
    warnings: list[str]


@dataclass
class _FetchResult:
    status: int
    content_type: str
    body: str
    error: str = ""


def default_state_path() -> Path:
    override = os.environ.get("JUMALI_OPS_STATE")
    if override:
        return Path(override).expanduser()
    hermes_home = os.environ.get("HERMES_HOME")
    if hermes_home:
        return Path(hermes_home).expanduser() / "state" / "weekend-kids-ops.json"
    profile = os.environ.get("HERMES_PROFILE", "jumaliauto")
    return Path.home() / ".hermes" / "profiles" / profile / "state" / "weekend-kids-ops.json"


def parse_event_count(html: str) -> int | None:
    match = _EVENT_COUNT_RE.search(html)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def parse_canonical(html: str) -> str:
    match = _CANONICAL_RE.search(html)
    return match.group(1).strip() if match else ""


def parse_updated_at(html: str) -> str | None:
    match = _UPDATED_RE.search(html)
    return match.group(1) if match else None


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _format_dt_kst(value: str) -> str:
    parsed = _parse_dt(value)
    if parsed is None:
        return "확인 실패"
    return parsed.astimezone(KST).strftime("%Y-%m-%d %H:%M KST")


def _fetch_url(url: str, *, user_agent: str = USER_AGENT, timeout: int = 20) -> _FetchResult:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return _FetchResult(
                status=int(response.status),
                content_type=response.headers.get("Content-Type", ""),
                body=body,
            )
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return _FetchResult(
            status=int(exc.code),
            content_type=exc.headers.get("Content-Type", "") if exc.headers else "",
            body=body,
            error=str(exc),
        )
    except Exception as exc:  # pragma: no cover - exercised by live cron only.
        return _FetchResult(status=0, content_type="", body="", error=str(exc))


def _site_url(site_url: str, path: str) -> str:
    return f"{site_url.rstrip('/')}/{path.lstrip('/')}"


def _sitemap_from_fetch(path: str, fetched: _FetchResult) -> SitemapResult:
    if fetched.status != 200:
        return SitemapResult(path=path, status=fetched.status, content_type=fetched.content_type, error=fetched.error)
    try:
        root = ET.fromstring(fetched.body.encode("utf-8"))
        locs = root.findall(".//{*}loc")
        return SitemapResult(
            path=path,
            status=fetched.status,
            content_type=fetched.content_type,
            xml_ok=True,
            url_count=len(locs),
        )
    except ET.ParseError as exc:
        return SitemapResult(
            path=path,
            status=fetched.status,
            content_type=fetched.content_type,
            xml_ok=False,
            url_count=0,
            error=str(exc),
        )


def fetch_latest_action_run(github_repo: str = DEFAULT_GITHUB_REPO, workflow: str = DEFAULT_WORKFLOW) -> ActionRun:
    token = os.environ.get("GITHUB_TOKEN")
    urls = [
        f"https://api.github.com/repos/{github_repo}/actions/workflows/{workflow}/runs?event=schedule&per_page=1",
        f"https://api.github.com/repos/{github_repo}/actions/runs?event=schedule&per_page=1",
    ]
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_error = ""
    for url in urls:
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            runs = payload.get("workflow_runs") or []
            if not runs:
                return ActionRun(conclusion="unknown", status="missing", started_at="", error="scheduled run 없음")
            run = runs[0]
            return ActionRun(
                conclusion=str(run.get("conclusion") or ""),
                status=str(run.get("status") or ""),
                started_at=str(run.get("run_started_at") or run.get("created_at") or ""),
                html_url=str(run.get("html_url") or ""),
            )
        except Exception as exc:  # pragma: no cover - live API fallback path.
            last_error = str(exc)
    return ActionRun(conclusion="unknown", status="error", started_at="", error=last_error or "GitHub API 조회 실패")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _sample_label(event: dict[str, Any]) -> str:
    title = str(event.get("title") or event.get("TITLE") or "제목 없음").strip()
    target = str(event.get("target") or event.get("USE_TRGT") or "대상 확인 필요").strip()
    return f"{title} / 대상: {target}"


def _has_strong_family_signal(event: dict[str, Any]) -> bool:
    text = " ".join(str(event.get(field, "")) for field in ("title", "target", "category", "place"))
    return any(term in text for term in _STRONG_FAMILY_TERMS)


def _has_adult_or_broad_signal(event: dict[str, Any]) -> bool:
    text = " ".join(str(event.get(field, "")) for field in ("title", "target", "category", "place"))
    return any(term in text for term in _ADULT_OR_BROAD_TERMS)


def load_local_quality(repo_root: Path) -> dict[str, Any]:
    raw = _read_json(repo_root / "data" / "seoul_cultural_events_raw.json")
    mvp = _read_json(repo_root / "data" / "seoul_cultural_events_mvp.json")
    raw_rows = raw if isinstance(raw, list) else []
    mvp_events = mvp if isinstance(mvp, list) else []

    free_fee_conflicts = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        is_free = str(row.get("IS_FREE") or "")
        fee = str(row.get("USE_FEE") or "")
        if "무료" in f"{is_free} {fee}" and _PAID_PRICE_PATTERN.search(fee):
            free_fee_conflicts.append(_sample_label(row) + f" / 요금: {fee.strip()}")
        if len(free_fee_conflicts) >= 5:
            break

    adult_broad = []
    missing_official = 0
    for event in mvp_events:
        if not isinstance(event, dict):
            continue
        if not str(event.get("official_url") or "").strip():
            missing_official += 1
        if len(adult_broad) < 5 and (_has_adult_or_broad_signal(event) or not _has_strong_family_signal(event)):
            adult_broad.append(_sample_label(event))

    ratio = (missing_official / len(mvp_events)) if mvp_events else 0.0
    return {
        "local_raw_count": len(raw_rows) if raw is not None else None,
        "local_mvp_count": len(mvp_events) if mvp is not None else None,
        "official_url_missing_ratio": ratio,
        "adult_broad_samples": adult_broad,
        "free_fee_conflict_samples": free_fee_conflicts,
    }


def collect_snapshot(
    *,
    site_url: str = DEFAULT_SITE_URL,
    repo_root: Path | None = None,
    github_repo: str = DEFAULT_GITHUB_REPO,
    workflow: str = DEFAULT_WORKFLOW,
    simulate_soft_404: bool = False,
) -> OpsSnapshot:
    repo_root = repo_root or Path.cwd()
    now = datetime.now(KST).isoformat(timespec="seconds")
    action = fetch_latest_action_run(github_repo=github_repo, workflow=workflow)

    endpoints: dict[str, EndpointResult] = {}
    bodies: dict[str, str] = {}
    for path in REQUIRED_ENDPOINTS:
        fetched = _fetch_url(_site_url(site_url, path), user_agent=GOOGLEBOT_UA if path.endswith(".xml") else USER_AGENT)
        endpoints[path] = EndpointResult(path=path, status=fetched.status, content_type=fetched.content_type, error=fetched.error)
        bodies[path] = fetched.body

    sitemaps = {}
    for path in REQUIRED_SITEMAPS:
        sitemaps[path] = _sitemap_from_fetch(path, _fetch_url(_site_url(site_url, path), user_agent=GOOGLEBOT_UA))

    counts: dict[str, int] = {}
    canonicals: dict[str, str] = {}
    updated_at = parse_updated_at(bodies.get("/", ""))
    page_bodies = {"/": bodies.get("/", "")}
    for key, path in COUNT_PAGES.items():
        fetched = _fetch_url(_site_url(site_url, path))
        page_bodies[path] = fetched.body
        count = parse_event_count(fetched.body)
        if count is not None:
            counts[key] = count
        if updated_at is None:
            updated_at = parse_updated_at(fetched.body)

    for path in CANONICAL_PAGES:
        body = page_bodies.get(path)
        if body is None:
            body = _fetch_url(_site_url(site_url, path)).body
        canonicals[path] = parse_canonical(body)

    missing = _fetch_url(_site_url(site_url, "/__jumali_ops_missing_check__/"))
    missing_status = 200 if simulate_soft_404 else missing.status

    quality = load_local_quality(repo_root)
    sitemap_url_count = sitemaps.get("/sitemap.xml", SitemapResult("/sitemap.xml", 0)).url_count or None
    return OpsSnapshot(
        generated_at=now,
        action=action,
        endpoints=endpoints,
        sitemaps=sitemaps,
        missing_status=missing_status,
        counts=counts,
        sitemap_url_count=sitemap_url_count,
        canonicals=canonicals,
        updated_at=updated_at,
        local_raw_count=quality["local_raw_count"],
        local_mvp_count=quality["local_mvp_count"],
        official_url_missing_ratio=quality["official_url_missing_ratio"],
        adult_broad_samples=quality["adult_broad_samples"],
        free_fee_conflict_samples=quality["free_fee_conflict_samples"],
    )


def _compare_drop(label: str, current: int | None, previous: int | None, failures: list[str], warnings: list[str]) -> None:
    if current is None or previous in (None, 0):
        return
    if current < previous * 0.5:
        failures.append(f"{label}가 이전 정상 {previous}건에서 {current}건으로 50% 이상 감소")
    elif current < previous * 0.7:
        warnings.append(f"{label}가 이전 정상 {previous}건에서 {current}건으로 30% 이상 감소")


def evaluate_snapshot(snapshot: OpsSnapshot, previous_state: dict[str, Any], now: datetime | None = None) -> Analysis:
    now = now or datetime.now(KST)
    failures: list[str] = []
    warnings: list[str] = []

    action = snapshot.action
    if action is None:
        failures.append("GitHub Actions 최근 scheduled run 조회 실패")
    elif action.error:
        failures.append(f"GitHub Actions 조회 실패: {action.error}")
    else:
        if action.status != "completed" or action.conclusion != "success":
            failures.append(f"GitHub Actions 최근 scheduled run이 success가 아님: status={action.status}, conclusion={action.conclusion or 'none'}")
        started = _parse_dt(action.started_at)
        if started is None:
            failures.append("GitHub Actions 최근 scheduled run 시각 확인 실패")
        else:
            hours_old = (now - started.astimezone(now.tzinfo)).total_seconds() / 3600
            if hours_old > 36:
                failures.append(f"GitHub Actions 최근 scheduled run이 {hours_old:.1f}시간 전으로 36시간 초과")

    for path in REQUIRED_ENDPOINTS:
        result = snapshot.endpoints.get(path)
        if result is None:
            failures.append(f"{path} HTTP 확인 결과 없음")
        elif result.status != 200:
            failures.append(f"{path} HTTP {result.status} 응답")

    for path in REQUIRED_SITEMAPS:
        result = snapshot.sitemaps.get(path)
        if result is None:
            failures.append(f"{path} sitemap 확인 결과 없음")
            continue
        if result.status != 200:
            failures.append(f"{path} HTTP {result.status} 응답")
        elif not result.xml_ok:
            failures.append(f"{path} XML 파싱 실패: {result.error or 'unknown'}")
        if path.endswith(".xml") and result.content_type and "xml" not in result.content_type.lower():
            warnings.append(f"{path} Content-Type이 XML 계열이 아님: {result.content_type}")

    if snapshot.missing_status != 404:
        failures.append(f"없는 URL이 404가 아니라 HTTP {snapshot.missing_status}로 응답")

    free_count = snapshot.counts.get("free")
    if free_count is None:
        failures.append("/seoul/free/ 행사 수 파싱 실패")
    elif free_count == 0:
        failures.append("/seoul/free/ 행사 수가 0")

    weekend_count = snapshot.counts.get("this_weekend")
    if weekend_count == 0 and free_count and free_count > 0:
        warnings.append("이번 주말 행사 수가 0이지만 전체 무료 행사는 남아 있음")

    indoor_count = snapshot.counts.get("indoor")
    if indoor_count is None:
        warnings.append("/seoul/indoor/ 행사 수 파싱 실패")

    if snapshot.updated_at:
        try:
            updated_date = datetime.fromisoformat(snapshot.updated_at).date()
            days_old = (now.astimezone(KST).date() - updated_date).days
            if days_old >= 3:
                warnings.append(f"최종 업데이트가 {snapshot.updated_at}로 {days_old}일 지남")
        except ValueError:
            warnings.append(f"최종 업데이트 날짜 파싱 실패: {snapshot.updated_at}")
    else:
        warnings.append("최종 업데이트 문구를 찾지 못함")

    for path, canonical in sorted(snapshot.canonicals.items()):
        if not canonical:
            failures.append(f"{path} canonical 없음")
        elif not canonical.startswith(DEFAULT_SITE_URL.rstrip("/") + "/"):
            failures.append(f"{path} canonical이 jumalikids.com 계열이 아님: {canonical}")

    last_success = previous_state.get("last_success") or {}
    previous_counts = last_success.get("counts") if isinstance(last_success.get("counts"), dict) else {}
    _compare_drop("무료 행사 수", snapshot.counts.get("free"), previous_counts.get("free"), failures, warnings)
    _compare_drop("이번 주말 행사 수", snapshot.counts.get("this_weekend"), previous_counts.get("this_weekend"), failures, warnings)
    _compare_drop("실내 행사 수", snapshot.counts.get("indoor"), previous_counts.get("indoor"), failures, warnings)
    _compare_drop("sitemap URL 수", snapshot.sitemap_url_count, last_success.get("sitemap_url_count"), failures, warnings)
    _compare_drop("MVP 행사 수", snapshot.local_mvp_count, last_success.get("local_mvp_count"), failures, warnings)

    if snapshot.official_url_missing_ratio >= 0.3:
        warnings.append(f"공식 URL 누락 비율이 {snapshot.official_url_missing_ratio:.0%}로 30% 이상")
    if snapshot.adult_broad_samples:
        warnings.append("strong-match 부족 또는 adult/broad-match 의심 샘플 있음")
    if snapshot.free_fee_conflict_samples:
        warnings.append("무료/요금 충돌 의심 샘플 있음")

    status = "실패" if failures else "주의" if warnings else "정상"
    return Analysis(status=status, failures=failures, warnings=warnings)


def _format_samples(title: str, samples: list[str]) -> list[str]:
    if not samples:
        return [f"- {title}: 없음"]
    lines = [f"- {title}:"]
    lines.extend(f"  - {sample}" for sample in samples[:5])
    return lines


def format_report(snapshot: OpsSnapshot, analysis: Analysis, *, mode: str, force_output: bool = False) -> str:
    if mode == "daily" and analysis.status == "정상" and not force_output:
        return ""

    if mode == "weekly":
        title = "주말아이 주간 운영 리포트"
    elif force_output and analysis.status == "정상":
        title = "주말아이 운영 헬스체크"
    else:
        title = f"주말아이 운영 알림: {analysis.status}"

    action = snapshot.action
    action_line = "조회 실패"
    action_time = "확인 실패"
    if action:
        action_line = f"{action.conclusion or 'none'} / {action.status or 'unknown'}"
        action_time = _format_dt_kst(action.started_at)

    lines = [title, f"상태: {analysis.status}", f"점검 시각: {snapshot.generated_at}", ""]
    lines.extend(
        [
            "데이터",
            f"- raw: {snapshot.local_raw_count if snapshot.local_raw_count is not None else '확인 실패'}건",
            f"- MVP 후보: {snapshot.local_mvp_count if snapshot.local_mvp_count is not None else '확인 실패'}건",
            f"- live free: {snapshot.counts.get('free', '확인 실패')}건",
            f"- live this-weekend: {snapshot.counts.get('this_weekend', '확인 실패')}건",
            f"- live indoor: {snapshot.counts.get('indoor', '확인 실패')}건",
            f"- live sitemap.xml URL: {snapshot.sitemap_url_count if snapshot.sitemap_url_count is not None else '확인 실패'}개",
            "",
            "갱신",
            f"- GitHub Actions 최근 scheduled run: {action_line}",
            f"- 최근 run 시각: {action_time}",
            f"- 라이브 최종 업데이트: {snapshot.updated_at or '확인 실패'}",
            "",
            "사이트맵",
        ]
    )
    for path in REQUIRED_SITEMAPS:
        sitemap = snapshot.sitemaps.get(path)
        if sitemap is None:
            lines.append(f"- {path}: 확인 실패")
        else:
            xml_status = "XML OK" if sitemap.xml_ok else f"XML 실패({sitemap.error or 'unknown'})"
            lines.append(f"- {path}: HTTP {sitemap.status}, {xml_status}, loc {sitemap.url_count}개")

    lines.extend(["", "실패 항목"])
    lines.extend(f"- {item}" for item in analysis.failures) if analysis.failures else lines.append("- 없음")
    lines.extend(["", "주의 항목"])
    lines.extend(f"- {item}" for item in analysis.warnings) if analysis.warnings else lines.append("- 없음")
    lines.extend(["", "샘플 점검"])
    lines.extend(_format_samples("strong-match/adult-broad-match 의심", snapshot.adult_broad_samples))
    lines.extend(_format_samples("무료/요금 충돌 의심", snapshot.free_fee_conflict_samples))
    lines.extend(
        [
            "",
            "태훈님 직접 작업",
            "- Search Console URL-prefix 속성이 https://jumalikids.com/ 인지 확인",
            "- Search Console에서 gsc-sitemap.xml, sitemap-index.xml 제출 상태 확인",
            "- 홈, /seoul/free/, /seoul/this-weekend/, 대표 행사 상세 URL 검사",
            "- AdSense 신청, 사이트 연결, 정책 동의는 검수 후 직접 진행",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def next_state(previous_state: dict[str, Any], snapshot: OpsSnapshot, analysis: Analysis) -> dict[str, Any]:
    state = dict(previous_state)
    state["last_run"] = {
        "checked_at": snapshot.generated_at,
        "status": analysis.status,
        "failures": analysis.failures,
        "warnings": analysis.warnings,
    }
    if not analysis.failures:
        state["last_success"] = {
            "checked_at": snapshot.generated_at,
            "counts": dict(snapshot.counts),
            "local_mvp_count": snapshot.local_mvp_count,
            "sitemap_url_count": snapshot.sitemap_url_count,
            "updated_at": snapshot.updated_at,
        }
    if not analysis.failures and not analysis.warnings:
        state["last_clean"] = dict(state["last_success"])
    return state


def load_state(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="주말아이 운영 헬스체크와 주간 리포트")
    parser.add_argument("--mode", choices=("daily", "weekly"), default="daily")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    parser.add_argument("--github-repo", default=DEFAULT_GITHUB_REPO)
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--state-path", default=str(default_state_path()))
    parser.add_argument("--force-output", action="store_true")
    parser.add_argument("--no-state-write", action="store_true")
    parser.add_argument("--simulate-soft-404", action="store_true")
    args = parser.parse_args(argv)

    state_path = Path(args.state_path).expanduser()
    previous_state = load_state(state_path)
    snapshot = collect_snapshot(
        site_url=args.site_url,
        repo_root=Path(args.repo_root),
        github_repo=args.github_repo,
        workflow=args.workflow,
        simulate_soft_404=args.simulate_soft_404,
    )
    analysis = evaluate_snapshot(snapshot, previous_state=previous_state)
    report = format_report(snapshot, analysis, mode=args.mode, force_output=args.force_output)
    if not args.no_state_write:
        save_state(state_path, next_state(previous_state, snapshot, analysis))
    if report:
        sys.stdout.write(report)
    # Detected site failures are the payload, not a broken watchdog. Keep exit 0
    # so no_agent cron delivers the Korean alert text instead of a generic
    # scheduler error. Unhandled exceptions still produce non-zero process exits.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
