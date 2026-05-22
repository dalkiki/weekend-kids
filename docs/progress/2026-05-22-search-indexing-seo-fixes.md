# 주말아이 색인/SEO 구조 보강 - 2026-05-22

저장 시각: 2026-05-22 20:44:22 KST

## 목적

Google Search Console에서 `크롤링됨 - 현재 색인이 생성되지 않음` 상태가 확인되어, 계획서 기준의 최소 색인 가능 사이트 구조까지 보강했다.

## 확인한 문제

- 기술 차단 문제는 아니었다.
  - `/` 응답 200
  - `/robots.txt` 허용
  - `/sitemap.xml` 접근 가능
  - `noindex` 없음
- 계획서 대비 실제 페이지 수가 부족했다.
  - 기존 공개 페이지: `/`, `/sources/`, `/privacy/`
  - 계획서 핵심 페이지: `/seoul/this-weekend/`, `/seoul/free/`, `/seoul/indoor/`, `/seoul/gu/{구}/`, `/events/{event-id}/`, `/about/`, `/contact/` 등
- 본문에 `MVP 테스트`, `테스트 사이트` 문구가 남아 있었다.
- `sources`, `privacy` 페이지가 너무 얇았다.
- sitemap에 3개 URL만 포함되어 있었다.
- canonical과 sitemap lastmod가 없었다.

## 적용한 변경

- 홈 문구에서 테스트성 표현 제거
- 전역 내비게이션 추가
- 핵심 랜딩 페이지 생성
  - `/seoul/free/`
  - `/seoul/this-weekend/`
  - `/seoul/indoor/`
- 구별 페이지 자동 생성
  - 현재 데이터 기준 11개 구 페이지 생성
- 행사 상세 페이지 자동 생성
  - 현재 데이터 기준 21개 상세 페이지 생성
- 신뢰 페이지 추가/보강
  - `/about/`
  - `/contact/`
  - `/sources/`
  - `/privacy/`
- 모든 HTML 페이지에 canonical 추가
- sitemap에 모든 생성 페이지와 `<lastmod>` 추가
- 빌드 시 `public/`을 먼저 정리해 지난 행사/오래된 출력물이 남지 않게 변경
- `public/` 외 기존 디렉터리는 생성기 마커가 있을 때만 삭제하도록 가드 추가
- 행사 상세 URL은 입력 순서가 바뀌어도 안정적으로 유지되도록 수정
- 외부 공식 링크는 `http/https`만 렌더링하도록 제한
- 실제 운영 URL 기본값을 `https://jumali-did.pages.dev`로 정정

## 검증 결과

- 테스트: `21 passed`
- 빌드: `bash scripts/build.sh` 성공
- 생성 파일 수: 43개
- sitemap URL 수: 40개
- 행사 상세 페이지: 21개
- 구별 페이지: 11개
- 주요 페이지에서 `MVP 테스트` / `테스트 사이트` 문구 제거 확인
- 주요 페이지 canonical 포함 확인

## 다음 Search Console 조치

1. Cloudflare Pages 배포 완료 후 `/sitemap.xml` 재제출
2. URL 검사 대상
   - `https://jumali-did.pages.dev/`
   - `https://jumali-did.pages.dev/seoul/free/`
   - `https://jumali-did.pages.dev/seoul/this-weekend/`
   - 행사 상세 페이지 1~2개
3. 실제 URL 테스트 후 색인 생성 요청

## 남은 개선 후보

- Google Doc 계획서와 로컬 진행 상태 동기화
- 매일 자동 수집/배포 워크플로우 추가
- 데이터 출처 B: 서울시 문화행사 공공서비스예약 정보 연동
- 행사 상세 페이지에 지도 링크/예약 여부 표시 강화
