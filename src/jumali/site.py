from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

BASE_CSS = """
:root { color-scheme: light; --bg:#f7fafc; --card:#ffffff; --text:#1f2937; --muted:#6b7280; --line:#e5e7eb; --accent:#2563eb; }
* { box-sizing: border-box; }
body { margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:var(--bg); color:var(--text); line-height:1.65; }
header, main, footer { width:min(960px, 100%); margin:0 auto; padding:24px; }
.hero { padding-top:48px; }
.badge { display:inline-block; padding:4px 10px; border-radius:999px; background:#dbeafe; color:#1d4ed8; font-size:14px; }
h1 { margin:12px 0 8px; font-size:36px; line-height:1.2; }
.card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:20px; margin:16px 0; box-shadow:0 8px 24px rgba(15,23,42,.05); }
.muted { color:var(--muted); }
a { color:var(--accent); }
.grid { display:grid; gap:16px; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); }
""".strip()


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="서울 지역의 어린이·가족 대상 무료 문화행사 정보를 날짜와 지역별로 정리합니다.">
  <style>{BASE_CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def render_home(events: list[dict[str, Any]], updated_at: str | None = None) -> str:
    updated_at = updated_at or date.today().isoformat()
    if events:
        cards = "\n".join(_render_event_card(event) for event in events)
    else:
        cards = """<section class="card">
  <h2>현재 조건에 맞는 행사가 없습니다</h2>
  <p class="muted">무료·어린이/가족 조건에 맞는 서울 문화행사가 확인되면 이곳에 자동으로 표시됩니다.</p>
</section>"""
    body = f"""
<header class="hero">
  <span class="badge">서울 MVP 테스트</span>
  <h1>주말아이</h1>
  <p>서울 아이랑 갈만한 무료 행사 정보를 공공데이터 기반으로 정리합니다.</p>
  <p class="muted">최종 업데이트: {html.escape(updated_at)}</p>
</header>
<main>
  <section class="card">
    <h2>이번 주말, 아이와 어디 갈지 찾기 쉽게</h2>
    <p>주말아이는 서울 열린데이터광장 등 공식 출처의 행사 정보를 바탕으로 무료 여부, 대상, 장소, 날짜를 보기 쉽게 정리하는 테스트 사이트입니다.</p>
    <p class="muted">방문 전에는 반드시 공식 페이지에서 일정·요금·예약 가능 여부를 다시 확인해 주세요.</p>
  </section>
  <section>
    <h2>서울 아이랑 갈만한 무료 행사</h2>
    {cards}
  </section>
</main>
<footer>
  <p><a href="/sources/">데이터 출처</a> · <a href="/privacy/">개인정보처리방침</a></p>
</footer>
"""
    return _page("주말아이 - 서울 아이랑 갈만한 무료 행사", body)


def _render_event_card(event: dict[str, Any]) -> str:
    title = html.escape(str(event.get("title", "제목 없음")))
    district = html.escape(str(event.get("district", "")))
    place = html.escape(str(event.get("place", "")))
    date_text = html.escape(str(event.get("date_text") or event.get("start_date", "")))
    url = html.escape(str(event.get("official_url", "")), quote=True)
    return f"""<article class="card">
  <h3>{title}</h3>
  <p>{district} · {place}</p>
  <p class="muted">{date_text} · 무료 여부는 공식 페이지 확인 필요</p>
  {f'<p><a href="{url}" rel="nofollow noopener">공식 페이지 보기</a></p>' if url else ''}
</article>"""


def _render_sitemap(site_url: str, paths: list[str]) -> str:
    base = site_url.rstrip("/") + "/"
    urls = "\n".join(
        f"  <url><loc>{html.escape(urljoin(base, path.lstrip('/')))}</loc></url>"
        for path in paths
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""


def build_site(events: list[dict[str, Any]], out_dir: str | Path = "public", updated_at: str | None = None, site_url: str = "https://jumali.pages.dev") -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    (out_path / "index.html").write_text(render_home(events, updated_at=updated_at), encoding="utf-8")

    sources_dir = out_path / "sources"
    sources_dir.mkdir(exist_ok=True)
    (sources_dir / "index.html").write_text(_page("데이터 출처 - 주말아이", """
<header><h1>데이터 출처</h1></header>
<main class="card"><p>주말아이는 서울 열린데이터광장 “서울시 문화행사 정보”를 1차 데이터 소스로 사용합니다.</p><p>각 행사 정보는 공식 링크를 기준으로 확인해 주세요.</p></main>
"""), encoding="utf-8")

    privacy_dir = out_path / "privacy"
    privacy_dir.mkdir(exist_ok=True)
    (privacy_dir / "index.html").write_text(_page("개인정보처리방침 - 주말아이", """
<header><h1>개인정보처리방침</h1></header>
<main class="card"><p>주말아이는 MVP 테스트 단계에서 회원가입, 댓글, 결제 기능을 제공하지 않으며 별도의 개인정보를 직접 수집하지 않습니다.</p><p>향후 광고 또는 분석 도구를 사용하는 경우 관련 내용을 이 페이지에 고지합니다.</p></main>
"""), encoding="utf-8")

    (out_path / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {site_url.rstrip('/')}/sitemap.xml\n", encoding="utf-8")
    (out_path / "sitemap.xml").write_text(_render_sitemap(site_url, ["/", "/sources/", "/privacy/"]), encoding="utf-8")


def main() -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build 주말아이 static MVP site")
    parser.add_argument("--events", default="data/seoul_cultural_events_mvp.json")
    parser.add_argument("--out-dir", default="public")
    parser.add_argument("--site-url", default="https://jumali.pages.dev")
    args = parser.parse_args()

    events_path = Path(args.events)
    events = json.loads(events_path.read_text(encoding="utf-8")) if events_path.exists() else []
    build_site(events=events, out_dir=args.out_dir, site_url=args.site_url)
    print(f"built {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
