from __future__ import annotations

import hashlib
import html
import re
import shutil
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

DEFAULT_SITE_URL = "https://jumali-did.pages.dev"
GOOGLE_VERIFICATION_TOKEN = "icS3zruN3knQ69QHjGpy_Dpg83hsS0t90mRT2WaWouI"
BUILD_MARKER = ".jumali-build-output"
DEFAULT_DESCRIPTION = "서울 지역의 어린이·가족 대상 무료 문화행사 정보를 날짜와 지역별로 정리합니다."

BASE_CSS = """
:root { color-scheme: light; --bg:#f7fafc; --card:#ffffff; --text:#1f2937; --muted:#6b7280; --line:#e5e7eb; --accent:#2563eb; --accent-soft:#dbeafe; }
* { box-sizing: border-box; }
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:var(--bg); color:var(--text); line-height:1.65; }
a { color:var(--accent); }
header, main, footer, .topnav { width:min(960px, 100%); margin:0 auto; padding:24px; }
.topnav { display:flex; flex-wrap:wrap; gap:10px; padding-top:18px; padding-bottom:0; }
.topnav a { text-decoration:none; font-weight:700; padding:8px 11px; border:1px solid var(--line); border-radius:999px; background:#fff; color:#1f2937; }
.hero { padding-top:38px; }
.badge { display:inline-block; padding:4px 10px; border-radius:999px; background:var(--accent-soft); color:#1d4ed8; font-size:14px; font-weight:700; }
h1 { margin:12px 0 8px; font-size:36px; line-height:1.2; }
h2 { margin-top:0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:20px; margin:16px 0; box-shadow:0 8px 24px rgba(15,23,42,.05); }
.muted { color:var(--muted); }
.grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }
.pill-list { display:flex; flex-wrap:wrap; gap:8px; padding:0; list-style:none; }
.pill-list li { background:#eef2ff; color:#3730a3; border-radius:999px; padding:5px 10px; font-size:14px; }
.event-meta { margin:8px 0; }
.notice { border-left:4px solid var(--accent); padding-left:14px; }
.detail-list { display:grid; grid-template-columns:minmax(90px, 150px) 1fr; gap:8px 14px; }
.detail-list dt { font-weight:700; }
.detail-list dd { margin:0; }
footer { color:var(--muted); font-size:14px; }
@media (max-width: 560px) { h1 { font-size:30px; } .detail-list { grid-template-columns:1fr; } }
""".strip()

INDOOR_KEYWORDS = (
    "도서관",
    "박물관",
    "미술관",
    "센터",
    "교육실",
    "대강의실",
    "아트홀",
    "전시실",
    "비대면",
    "온라인",
    "강연",
    "워크숍",
)


def _site_base(site_url: str) -> str:
    return site_url.rstrip("/") + "/"


def _escape_public_url(value: str) -> str:
    """Return an ASCII-safe public URL for canonical and sitemap entries.

    Browsers can open Korean URL paths directly, but Search Console sitemap
    parsing is more reliable when <loc> values are percent-encoded URLs.
    Keep % safe so already-escaped paths are not double encoded.
    """

    parsed = urlsplit(value)
    path = quote(parsed.path or "/", safe="/%:@!$&'()*+,;=-._~")
    query = quote(parsed.query, safe="%/:?@!$&'()*+,;=-._~")
    return urlunsplit((parsed.scheme, parsed.netloc, path, query, parsed.fragment))


def _absolute_url(site_url: str, path: str) -> str:
    return _escape_public_url(urljoin(_site_base(site_url), path.lstrip("/")))


def _raw_absolute_url(site_url: str, path: str) -> str:
    return urljoin(_site_base(site_url), path.lstrip("/"))


def _slugify(value: str, fallback: str = "page", max_length: int = 70) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", str(value).strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = fallback
    return slug[:max_length].strip("-") or fallback


def _safe_external_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return ""
    if not parsed.netloc:
        return ""
    return url


def _event_slug(event: dict[str, Any]) -> str:
    readable_raw = f"{event.get('start_date', '')}-{event.get('title', '')}-{event.get('district', '')}"
    unique_raw = f"{readable_raw}-{event.get('place', '')}-{event.get('official_url', '')}"
    digest = hashlib.sha1(unique_raw.encode("utf-8")).hexdigest()[:8]
    readable = _slugify(readable_raw, fallback="event", max_length=78)
    return f"{readable}-{digest}"


def _enrich_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    seen: dict[str, int] = {}
    for event in events:
        copied = dict(event)
        copied["official_url"] = _safe_external_url(copied.get("official_url"))
        base_slug = _event_slug(copied)
        occurrence = seen.get(base_slug, 0) + 1
        seen[base_slug] = occurrence
        slug = base_slug if occurrence == 1 else f"{base_slug}-{occurrence}"
        copied["_slug"] = slug
        copied["_detail_path"] = f"/events/{slug}/"
        enriched.append(copied)
    return enriched


def _ensure_enriched(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _enrich_events(events)


def _reference_date(updated_at: str | None) -> date:
    if updated_at:
        try:
            return date.fromisoformat(updated_at[:10])
        except ValueError:
            pass
    return date.today()


def _parse_iso_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _overlaps(event: dict[str, Any], start: date, end: date) -> bool:
    event_start = _parse_iso_date(event.get("start_date"))
    event_end = _parse_iso_date(event.get("end_date") or event.get("start_date"))
    if event_start is None or event_end is None:
        return False
    return event_start <= end and event_end >= start


def _this_weekend_range(reference: date) -> tuple[date, date]:
    if reference.weekday() == 6:  # Sunday: keep the current weekend.
        saturday = reference - timedelta(days=1)
    else:
        saturday = reference + timedelta(days=(5 - reference.weekday()) % 7)
    return saturday, saturday + timedelta(days=1)


def _filter_this_weekend(events: list[dict[str, Any]], updated_at: str | None) -> list[dict[str, Any]]:
    start, end = _this_weekend_range(_reference_date(updated_at))
    return [event for event in events if _overlaps(event, start, end)]


def _is_indoor_event(event: dict[str, Any]) -> bool:
    text = " ".join(
        str(event.get(field, ""))
        for field in ("title", "category", "place", "target")
    )
    return any(keyword in text for keyword in INDOOR_KEYWORDS)


def _filter_indoor(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [event for event in events if _is_indoor_event(event)]


def _nav() -> str:
    return """<nav class="topnav" aria-label="주요 메뉴">
  <a href="/">홈</a>
  <a href="/seoul/free/">서울 무료 행사</a>
  <a href="/seoul/this-weekend/">이번 주말</a>
  <a href="/seoul/indoor/">실내 행사</a>
  <a href="/about/">소개</a>
  <a href="/contact/">문의</a>
</nav>"""


def _footer() -> str:
    return """<footer>
  <p><a href="/sources/">데이터 출처</a> · <a href="/privacy/">개인정보처리방침</a> · <a href="/contact/">정보 정정 문의</a></p>
  <p>주말아이는 공공데이터를 부모가 보기 쉽게 정리하는 정보 서비스입니다. 방문 전 공식 페이지에서 일정·요금·예약 가능 여부를 다시 확인해 주세요.</p>
</footer>"""


def _page(
    title: str,
    body: str,
    *,
    site_url: str = DEFAULT_SITE_URL,
    path: str = "/",
    description: str = DEFAULT_DESCRIPTION,
) -> str:
    canonical = _absolute_url(site_url, path)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description, quote=True)}">
  <link rel="canonical" href="{html.escape(canonical, quote=True)}">
  <meta name="google-site-verification" content="{GOOGLE_VERIFICATION_TOKEN}">
  <style>{BASE_CSS}</style>
</head>
<body>
{_nav()}
{body}
{_footer()}
</body>
</html>
"""


def render_home(events: list[dict[str, Any]], updated_at: str | None = None, site_url: str = DEFAULT_SITE_URL) -> str:
    updated_at = updated_at or date.today().isoformat()
    enriched_events = _ensure_enriched(events)
    if enriched_events:
        cards = "\n".join(_render_event_card(event) for event in enriched_events[:24])
    else:
        cards = """<section class="card">
  <h2>현재 조건에 맞는 행사가 없습니다</h2>
  <p class="muted">무료·어린이/가족 조건에 맞는 서울 문화행사가 확인되면 이곳에 자동으로 표시됩니다.</p>
</section>"""
    body = f"""
<header class="hero">
  <span class="badge">서울 어린이·가족 무료 문화행사</span>
  <h1>주말아이</h1>
  <p>서울 아이랑 갈만한 무료 행사 정보를 공공데이터 기반으로 정리합니다.</p>
  <p class="muted">최종 업데이트: {html.escape(updated_at)}</p>
</header>
<main>
  <section class="card">
    <h2>이번 주말, 아이와 어디 갈지 찾기 쉽게</h2>
    <p>주말아이는 서울 열린데이터광장 등 공식 출처의 행사 정보를 바탕으로 날짜, 장소, 대상, 비용 확인 포인트를 한곳에 모아 보여줍니다.</p>
    <ul class="pill-list">
      <li>무료 행사 우선</li>
      <li>어린이·가족 대상</li>
      <li>공식 링크 확인</li>
      <li>지역별 탐색</li>
    </ul>
    <p class="muted notice">방문 전에는 반드시 공식 페이지에서 일정·요금·예약 가능 여부를 다시 확인해 주세요.</p>
  </section>
  <section class="grid" aria-label="주요 페이지">
    <article class="card"><h2><a href="/seoul/free/">서울 아이랑 무료 행사</a></h2><p>현재 확인되는 서울 무료 어린이·가족 행사를 모았습니다.</p></article>
    <article class="card"><h2><a href="/seoul/this-weekend/">이번 주말 행사</a></h2><p>이번 토요일·일요일에 겹치는 행사를 빠르게 볼 수 있습니다.</p></article>
    <article class="card"><h2><a href="/seoul/indoor/">비오는 날 실내 행사</a></h2><p>도서관, 박물관, 센터 등 실내 가능성이 높은 행사를 따로 모았습니다.</p></article>
  </section>
  <section>
    <h2>서울 아이랑 갈만한 무료 행사</h2>
    {cards}
  </section>
</main>
"""
    return _page("주말아이 - 서울 아이랑 갈만한 무료 행사", body, site_url=site_url, path="/")


def _render_event_card(event: dict[str, Any]) -> str:
    title = html.escape(str(event.get("title", "제목 없음")))
    district = html.escape(str(event.get("district", "")))
    place = html.escape(str(event.get("place", "")))
    date_text = html.escape(str(event.get("date_text") or event.get("start_date", "")))
    target = html.escape(str(event.get("target", "")))
    fee = html.escape(str(event.get("fee") or "공식 페이지 확인 필요"))
    detail_path = html.escape(str(event.get("_detail_path", "")), quote=True)
    official_url = html.escape(str(event.get("official_url", "")), quote=True)
    title_html = f'<a href="{detail_path}">{title}</a>' if detail_path else title
    official_html = f' · <a href="{official_url}" rel="nofollow noopener">공식 페이지</a>' if official_url else ""
    return f"""<article class="card">
  <h3>{title_html}</h3>
  <p class="event-meta">{district} · {place}</p>
  <p class="muted">{date_text} · 비용: {fee}</p>
  {f'<p class="muted">대상: {target}</p>' if target else ''}
  <p><a href="{detail_path}">상세 정보 보기</a>{official_html}</p>
</article>"""


def _render_empty_state(title: str) -> str:
    return f"""<section class="card">
  <h2>{html.escape(title)}</h2>
  <p class="muted">현재 조건에 맞는 행사가 없습니다. 새 데이터가 수집되면 자동으로 갱신됩니다.</p>
</section>"""


def _render_event_list_page(
    *,
    title: str,
    heading: str,
    intro: str,
    events: list[dict[str, Any]],
    updated_at: str,
    site_url: str,
    path: str,
) -> str:
    cards = "\n".join(_render_event_card(event) for event in events) if events else _render_empty_state("조건에 맞는 행사 없음")
    body = f"""
<header class="hero">
  <span class="badge">서울 행사 모음</span>
  <h1>{html.escape(heading)}</h1>
  <p>{html.escape(intro)}</p>
  <p class="muted">최종 업데이트: {html.escape(updated_at)} · 행사 수: {len(events)}개</p>
</header>
<main>
  <section class="card notice">
    <p>공공데이터의 요금·예약 정보는 실제 현장 상황과 다를 수 있습니다. 방문 전 공식 페이지에서 반드시 최신 정보를 확인해 주세요.</p>
  </section>
  <section>
    {cards}
  </section>
</main>
"""
    return _page(title, body, site_url=site_url, path=path, description=intro)


def _render_event_detail(event: dict[str, Any], *, updated_at: str, site_url: str) -> str:
    title = str(event.get("title", "행사 상세"))
    path = str(event.get("_detail_path", "/events/"))
    official_url = str(event.get("official_url", ""))
    official_link = f'<p><a href="{html.escape(official_url, quote=True)}" rel="nofollow noopener">공식 페이지에서 최신 정보 확인하기</a></p>' if official_url else ""
    details = [
        ("행사명", title),
        ("날짜", str(event.get("date_text") or event.get("start_date", ""))),
        ("장소", str(event.get("place", ""))),
        ("자치구", str(event.get("district", ""))),
        ("분류", str(event.get("category", ""))),
        ("비용", str(event.get("fee") or "공식 페이지 확인 필요")),
        ("대상", str(event.get("target", ""))),
        ("출처", str(event.get("source", "서울 열린데이터광장 서울시 문화행사 정보"))),
    ]
    detail_html = "\n".join(
        f"<dt>{html.escape(label)}</dt><dd>{html.escape(value) if value else '확인 필요'}</dd>"
        for label, value in details
    )
    body = f"""
<header class="hero">
  <span class="badge">행사 상세</span>
  <h1>{html.escape(title)}</h1>
  <p class="muted">최종 업데이트: {html.escape(updated_at)}</p>
</header>
<main>
  <section class="card">
    <h2>기본 정보</h2>
    <dl class="detail-list">{detail_html}</dl>
    {official_link}
  </section>
  <section class="card notice">
    <h2>방문 전 체크</h2>
    <p>일정, 비용, 예약 가능 여부, 대상 연령은 변경될 수 있습니다. 아이와 방문하기 전 공식 페이지 또는 운영기관 안내를 다시 확인해 주세요.</p>
  </section>
</main>
"""
    description = f"{title}의 날짜, 장소, 대상, 비용과 공식 확인 링크를 정리했습니다."
    return _page(f"{title} - 주말아이", body, site_url=site_url, path=path, description=description)


def _render_about(site_url: str) -> str:
    body = """
<header class="hero"><span class="badge">서비스 소개</span><h1>주말아이 소개</h1></header>
<main>
  <section class="card">
    <p>주말아이는 부모가 “이번 주말 아이랑 어디 가지?”를 빠르게 판단할 수 있도록 서울의 어린이·가족 대상 문화행사 정보를 정리하는 사이트입니다.</p>
    <p>공공데이터에서 확인되는 행사 중 무료 또는 무료 가능성이 높은 정보를 우선 보여주며, 행사명·날짜·장소·대상·공식 링크를 함께 제공합니다.</p>
    <p>자동 수집 정보는 오류나 변경 가능성이 있으므로, 실제 방문 전에는 공식 페이지를 다시 확인하는 것을 원칙으로 안내합니다.</p>
  </section>
</main>
"""
    return _page("주말아이 소개", body, site_url=site_url, path="/about/", description="주말아이가 어떤 기준으로 서울 어린이·가족 무료 행사를 정리하는지 안내합니다.")


def _render_contact(site_url: str) -> str:
    body = """
<header class="hero"><span class="badge">문의</span><h1>문의와 정보 정정</h1></header>
<main>
  <section class="card">
    <p>행사 정보가 공식 페이지와 다르거나 종료된 행사가 노출되는 경우, 정보 정정이 필요합니다.</p>
    <p>현재 주말아이는 초기 운영 단계라 별도 회원 기능을 제공하지 않습니다. 정보 정정, 제휴가 아닌 일반 문의, 데이터 출처 관련 요청은 사이트 운영자가 확인해 반영합니다.</p>
    <p class="muted">문의 시 행사명, 공식 페이지 주소, 수정이 필요한 내용을 함께 남기면 더 빠르게 확인할 수 있습니다.</p>
  </section>
</main>
"""
    return _page("문의와 정보 정정 - 주말아이", body, site_url=site_url, path="/contact/", description="주말아이 행사 정보 정정과 사이트 문의 안내입니다.")


def _render_sources(site_url: str) -> str:
    body = """
<header class="hero"><span class="badge">데이터 출처</span><h1>데이터 출처와 필터링 기준</h1></header>
<main>
  <section class="card">
    <h2>1차 데이터 출처</h2>
    <p>주말아이는 서울 열린데이터광장의 “서울시 문화행사 정보”를 1차 데이터 소스로 사용합니다. 행사명, 자치구, 장소, 날짜, 대상, 요금, 공식 링크 등 공개된 항목을 바탕으로 페이지를 생성합니다.</p>
    <h2>필터링 기준</h2>
    <p>어린이, 아동, 유아, 초등, 가족 등 아이와 함께 방문할 가능성이 높은 키워드가 있는 행사를 우선 선별합니다. 요금란에 금액이 명확히 표시된 행사는 무료 행사로 단정하지 않습니다.</p>
    <h2>업데이트 주기</h2>
    <p>사이트는 자동 수집과 정적 페이지 생성을 전제로 운영됩니다. 데이터가 갱신되면 지난 행사는 제외하고, 새 행사와 변경된 공식 링크를 반영합니다.</p>
    <h2>주의 사항</h2>
    <p>공공데이터의 무료 여부, 예약 가능 여부, 대상 연령은 실제 운영기관 공지와 다를 수 있습니다. 주말아이는 탐색을 돕는 정보 사이트이며, 최종 방문 결정 전에는 공식 페이지 확인이 필요합니다.</p>
  </section>
</main>
"""
    return _page("데이터 출처 - 주말아이", body, site_url=site_url, path="/sources/", description="주말아이가 사용하는 서울 문화행사 데이터 출처와 필터링 기준을 안내합니다.")


def _render_privacy(site_url: str) -> str:
    body = """
<header class="hero"><span class="badge">개인정보처리방침</span><h1>개인정보처리방침</h1></header>
<main>
  <section class="card">
    <p>주말아이는 현재 회원가입, 댓글, 결제 기능을 제공하지 않으며 이름, 연락처, 주민등록번호 같은 개인정보를 직접 수집하지 않습니다.</p>
    <p>사이트 운영 과정에서 일반적인 웹 서버 접속 기록이 호스팅 사업자에 의해 처리될 수 있습니다. 이는 보안, 장애 확인, 트래픽 통계 같은 기본 운영 목적에 한정됩니다.</p>
    <p>향후 Google AdSense, 방문 통계, 문의 양식 등 광고 또는 분석 도구를 사용하는 경우 수집 항목, 이용 목적, 보관 기간을 이 페이지에 추가로 고지합니다.</p>
    <p>주말아이는 어린이와 가족 대상 행사 정보를 다루지만, 어린이의 개인정보를 직접 입력받는 기능은 제공하지 않습니다.</p>
  </section>
</main>
"""
    return _page("개인정보처리방침 - 주말아이", body, site_url=site_url, path="/privacy/", description="주말아이의 개인정보 수집 여부와 광고·분석 도구 사용 가능성을 안내합니다.")


def _write_page(out_path: Path, path: str, content: str) -> None:
    clean_path = path.strip("/")
    target_dir = out_path if not clean_path else out_path / clean_path
    resolved_out = out_path.resolve()
    resolved_target = target_dir.resolve()
    if resolved_target != resolved_out and not resolved_target.is_relative_to(resolved_out):
        raise ValueError(f"Unsafe output path: {path}")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "index.html").write_text(content, encoding="utf-8")


def _render_sitemap(site_url: str, paths: list[str], lastmod: str) -> str:
    urls = "\n".join(
        "  <url>"
        f"<loc>{html.escape(_absolute_url(site_url, path))}</loc>"
        f"<lastmod>{html.escape(lastmod)}</lastmod>"
        "</url>"
        for path in paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""


def _render_sitemap_txt(site_url: str, paths: list[str]) -> str:
    return "\n".join(_absolute_url(site_url, path) for path in paths) + "\n"


def _render_sitemap_index(site_url: str, sitemap_paths: list[str], lastmod: str) -> str:
    sitemaps = "\n".join(
        "  <sitemap>"
        f"<loc>{html.escape(_absolute_url(site_url, path))}</loc>"
        f"<lastmod>{html.escape(lastmod)}</lastmod>"
        "</sitemap>"
        for path in sitemap_paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemaps}
</sitemapindex>
"""


def _assert_safe_output_dir(out_path: Path) -> None:
    resolved = out_path.resolve()
    cwd = Path.cwd().resolve()
    unsafe_roots = {Path("/").resolve(), Path.home().resolve(), cwd, cwd.parent}
    if resolved in unsafe_roots:
        raise ValueError(f"Unsafe output directory: {resolved}")
    if not resolved.exists():
        return

    dangerous_markers = (".git", "pyproject.toml", "src", "tests", "scripts")
    if any((resolved / marker).exists() for marker in dangerous_markers):
        raise ValueError(f"Unsafe output directory: {resolved}")

    has_contents = any(resolved.iterdir())
    if not has_contents:
        return

    is_default_public = resolved.name == "public"
    has_build_marker = (resolved / BUILD_MARKER).exists()
    if not is_default_public and not has_build_marker:
        raise ValueError(f"Unsafe output directory: {resolved}")


def build_site(events: list[dict[str, Any]], out_dir: str | Path = "public", updated_at: str | None = None, site_url: str = DEFAULT_SITE_URL) -> None:
    out_path = Path(out_dir)
    _assert_safe_output_dir(out_path)
    if out_path.exists():
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / BUILD_MARKER).write_text("generated by jumali site builder\n", encoding="utf-8")
    updated_at = updated_at or date.today().isoformat()
    enriched_events = _ensure_enriched(events)
    generated_paths: list[str] = []

    _write_page(out_path, "/", render_home(enriched_events, updated_at=updated_at, site_url=site_url))
    generated_paths.append("/")

    free_path = "/seoul/free/"
    _write_page(
        out_path,
        free_path,
        _render_event_list_page(
            title="서울 아이랑 무료 행사 모음 - 주말아이",
            heading="서울 아이랑 무료 행사 모음",
            intro="서울에서 아이와 함께 가볼 만한 무료 어린이·가족 문화행사를 정리했습니다.",
            events=enriched_events,
            updated_at=updated_at,
            site_url=site_url,
            path=free_path,
        ),
    )
    generated_paths.append(free_path)

    weekend_path = "/seoul/this-weekend/"
    weekend_events = _filter_this_weekend(enriched_events, updated_at)
    _write_page(
        out_path,
        weekend_path,
        _render_event_list_page(
            title="서울 이번 주말 아이랑 무료 행사 - 주말아이",
            heading="서울 이번 주말 아이랑 무료 행사",
            intro="이번 토요일·일요일에 일정이 겹치는 서울 어린이·가족 무료 행사를 모았습니다.",
            events=weekend_events,
            updated_at=updated_at,
            site_url=site_url,
            path=weekend_path,
        ),
    )
    generated_paths.append(weekend_path)

    indoor_path = "/seoul/indoor/"
    indoor_events = _filter_indoor(enriched_events)
    _write_page(
        out_path,
        indoor_path,
        _render_event_list_page(
            title="서울 비오는 날 아이랑 실내 무료 행사 - 주말아이",
            heading="서울 비오는 날 아이랑 실내 무료 행사",
            intro="도서관, 박물관, 문화센터 등 실내 방문 가능성이 높은 서울 어린이·가족 행사를 정리했습니다.",
            events=indoor_events,
            updated_at=updated_at,
            site_url=site_url,
            path=indoor_path,
        ),
    )
    generated_paths.append(indoor_path)

    districts = sorted({str(event.get("district", "")).strip() for event in enriched_events if str(event.get("district", "")).strip()})
    for district in districts:
        district_events = [event for event in enriched_events if str(event.get("district", "")).strip() == district]
        district_slug = _slugify(district, fallback="district")
        district_path = f"/seoul/gu/{district_slug}/"
        _write_page(
            out_path,
            district_path,
            _render_event_list_page(
                title=f"{district} 아이랑 무료 행사 - 주말아이",
                heading=f"{district} 아이랑 무료 행사",
                intro=f"서울 {district}에서 확인되는 어린이·가족 대상 무료 문화행사를 모았습니다.",
                events=district_events,
                updated_at=updated_at,
                site_url=site_url,
                path=district_path,
            ),
        )
        generated_paths.append(district_path)

    for event in enriched_events:
        event_path = str(event["_detail_path"])
        _write_page(out_path, event_path, _render_event_detail(event, updated_at=updated_at, site_url=site_url))
        generated_paths.append(event_path)

    trust_pages = {
        "/about/": _render_about(site_url),
        "/contact/": _render_contact(site_url),
        "/sources/": _render_sources(site_url),
        "/privacy/": _render_privacy(site_url),
    }
    for path, content in trust_pages.items():
        _write_page(out_path, path, content)
        generated_paths.append(path)

    basic_sitemap_paths = [
        "/",
        free_path,
        weekend_path,
        indoor_path,
        "/about/",
        "/contact/",
        "/sources/",
        "/privacy/",
    ]

    (out_path / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {_raw_absolute_url(site_url, '/sitemap-index.xml')}\n"
        f"Sitemap: {_raw_absolute_url(site_url, '/sitemap.xml')}\n"
        f"Sitemap: {_raw_absolute_url(site_url, '/sitemap-basic.xml')}\n"
        f"Sitemap: {_raw_absolute_url(site_url, '/sitemap.txt')}\n",
        encoding="utf-8",
    )
    (out_path / "_headers").write_text(
        "/sitemap.xml\n"
        "  Content-Type: application/xml; charset=utf-8\n"
        "  X-Robots-Tag: all\n"
        "/sitemap-index.xml\n"
        "  Content-Type: application/xml; charset=utf-8\n"
        "  X-Robots-Tag: all\n"
        "/sitemap-basic.xml\n"
        "  Content-Type: application/xml; charset=utf-8\n"
        "  X-Robots-Tag: all\n"
        "/sitemap.txt\n"
        "  Content-Type: text/plain; charset=utf-8\n"
        "  X-Robots-Tag: all\n"
        "/robots.txt\n"
        "  Content-Type: text/plain; charset=utf-8\n"
        "  X-Robots-Tag: all\n",
        encoding="utf-8",
    )
    (out_path / "_redirects").write_text(
        # Search Console URL-prefix properties sometimes receive a full URL pasted
        # into the sitemap field. That turns into a malformed path such as
        # /https://example.pages.dev/sitemap.xml. Serve a real sitemap there too
        # instead of letting the static HTML fallback return 200 text/html.
        "/https://:site/sitemap-index.xml /sitemap-index.xml 301\n"
        "/http://:site/sitemap-index.xml /sitemap-index.xml 301\n"
        "/https://:site/sitemap-basic.xml /sitemap-basic.xml 301\n"
        "/http://:site/sitemap-basic.xml /sitemap-basic.xml 301\n"
        "/https://:site/sitemap.xml /sitemap.xml 301\n"
        "/http://:site/sitemap.xml /sitemap.xml 301\n"
        "/https://:site/sitemap.txt /sitemap.txt 301\n"
        "/http://:site/sitemap.txt /sitemap.txt 301\n"
        "/sitemap.xml/ /sitemap.xml 301\n"
        "/sitemap /sitemap.xml 301\n"
        "/sitemap.XML /sitemap.xml 301\n"
        "/SITEMAP.XML /sitemap.xml 301\n"
        "/robots.txt/ /robots.txt 301\n",
        encoding="utf-8",
    )
    (out_path / "sitemap-index.xml").write_text(
        _render_sitemap_index(site_url, ["/sitemap-basic.xml", "/sitemap.xml"], updated_at),
        encoding="utf-8",
    )
    (out_path / "sitemap-basic.xml").write_text(_render_sitemap(site_url, basic_sitemap_paths, updated_at), encoding="utf-8")
    (out_path / "sitemap.xml").write_text(_render_sitemap(site_url, generated_paths, updated_at), encoding="utf-8")
    (out_path / "sitemap.txt").write_text(_render_sitemap_txt(site_url, generated_paths), encoding="utf-8")


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build 주말아이 static MVP site")
    parser.add_argument("--events", default="data/seoul_cultural_events_mvp.json")
    parser.add_argument("--out-dir", default="public")
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    args = parser.parse_args()

    events_path = Path(args.events)
    events = json.loads(events_path.read_text(encoding="utf-8")) if events_path.exists() else []
    build_site(events=events, out_dir=args.out_dir, site_url=args.site_url)
    print(f"built {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
