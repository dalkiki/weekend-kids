from pathlib import Path

from jumali.site import build_site, render_home


def test_render_home_uses_clean_information_tone_and_empty_state():
    html = render_home(events=[], updated_at="2026-05-17")

    assert "주말아이" in html
    assert "서울 아이랑 갈만한 무료 행사" in html
    assert "현재 조건에 맞는 행사가 없습니다" in html
    assert "최종 업데이트: 2026-05-17" in html
    assert 'name="google-site-verification"' in html
    assert "icS3zruN3knQ69QHjGpy_Dpg83hsS0t90mRT2WaWouI" in html


def test_build_site_writes_index_sources_privacy_robots_and_sitemap(tmp_path: Path):
    build_site(events=[], out_dir=tmp_path, updated_at="2026-05-17", site_url="https://jumali.pages.dev")

    assert (tmp_path / "index.html").exists()
    assert (tmp_path / "sources" / "index.html").exists()
    assert (tmp_path / "privacy" / "index.html").exists()
    assert (tmp_path / "robots.txt").exists()
    assert (tmp_path / "sitemap.xml").exists()
    assert "https://jumali.pages.dev/sources/" in (tmp_path / "sitemap.xml").read_text(encoding="utf-8")
