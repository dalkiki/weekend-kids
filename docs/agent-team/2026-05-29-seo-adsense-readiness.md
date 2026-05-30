# 주말아이 SEO·색인·AdSense 준비도 진단

진단 시각: 2026-05-29 19:42 KST
대상: 로컬 repo `/home/hermes/projects/weekend-kids`, 라이브 `https://jumalikids.com/`
범위: 홈, `/seoul/free/`, `/seoul/this-weekend/`, `/seoul/indoor/`, `/guides/*`, `/events/*`, sitemap/robots/canonical/lastmod, 색인 보류 리스크, AdSense 준비도

## 결론

현재 주말아이는 “기술적으로 크롤링 가능한 정보 사이트” 단계까지는 올라와 있습니다. 홈·핵심 랜딩·가이드·행사 상세·신뢰 페이지가 있고, sitemap과 canonical도 대체로 정상입니다.

다만 지금 바로 AdSense 승인/색인 확대를 기대하기에는 부족합니다. 가장 큰 리스크는 존재하지 않는 URL이 404가 아니라 홈페이지 200으로 응답하는 점입니다. 그다음은 행사 상세·구별 페이지가 얇고 반복적이며, 일부 행사 품질이 “아이랑 무료 행사” 검색 의도와 약하게 맞는 점입니다.

권장 판단: AdSense 신청 전, 404 처리와 얇은 페이지 보강을 먼저 고치는 것이 안전합니다.

## 확인한 현재 상태

- 로컬 브랜치: `main...origin/main`, 진단 전 작업트리 깨끗함
- 테스트: `python -m pytest tests -q` → 23 passed, 1 warning
- 로컬 생성 HTML: 54개
- 로컬 행사 상세 페이지: 27개
- 로컬 구별 페이지: 14개
- 라이브 `sitemap.xml`: 54 URL
  - 행사 상세: 27 URL
  - 구별 페이지: 14 URL
  - 가이드: 5 URL
- 라이브 `gsc-sitemap.xml`: 13 URL
  - 홈, 핵심 랜딩 3개, 가이드 5개, about/contact/sources/privacy
  - 행사 상세와 구별 페이지는 제외됨
- `sitemap.xml`, `gsc-sitemap.xml`, `sitemap-index.xml`, `sitemap-basic.xml`: Googlebot UA 기준 200, XML 파싱 성공
- `robots.txt`: 200, 전체 허용, 주요 sitemap 5개 명시
- `lastmod`: 모든 sitemap에서 `2026-05-29` 확인
- canonical: 점검한 라이브 페이지에서 `https://jumalikids.com/...`로 정상
- noindex: 점검한 라이브 페이지에서 발견되지 않음
- 임시/test 문구: 공개 HTML과 점검한 라이브 페이지에서 `MVP 테스트`, `테스트 사이트`, `placeholder`, `TODO`, `임시` 발견 없음

## 좋은 점

- 검색 의도에 맞는 핵심 랜딩이 이미 있습니다.
  - `/seoul/free/`
  - `/seoul/this-weekend/`
  - `/seoul/indoor/`
- 가이드 페이지 5개가 있어 단순 행사 목록보다 SEO 기반이 좋습니다.
  - `/guides/free-kids-events-seoul/`
  - `/guides/this-weekend-kids-plan/`
  - `/guides/rainy-day-indoor-kids-seoul/`
  - `/guides/age-target-check/`
  - `/guides/reservation-fee-checklist/`
- 행사 상세 페이지가 생성되어 내부 링크 구조를 만들 수 있습니다.
- about/contact/sources/privacy가 존재합니다.
- 공식 페이지 확인 안내와 데이터 출처 안내가 반복되어 공공데이터 사이트로서 기본 신뢰 요소가 있습니다.
- sitemap URL의 한글 경로가 percent-encoding되어 Search Console 파싱 리스크가 낮습니다.
- `_headers`, `_redirects`에 sitemap 관련 하드닝이 들어가 있습니다.

## 즉시 고칠 항목 5개 이내

### 1. 존재하지 않는 URL이 200 홈페이지로 응답함

증거:

- `https://jumalikids.com/__seo_audit_missing_page__` → 200 `text/html`, 홈페이지 HTML 반환
- `https://jumalikids.com/events/not-real-event/` → 200 `text/html`, 홈페이지 HTML 반환
- `https://jumalikids.com/seoul/gu/not-real-gu/` → 200 `text/html`, 홈페이지 HTML 반환
- `https://jumalikids.com/sitemap-does-not-exist.xml` → 200 `text/html`, 홈페이지 HTML 반환

영향:

- Google이 soft 404 또는 중복 URL로 판단할 수 있습니다.
- Search Console에서 색인 보류, 크롤링 품질 저하, “발견됨/크롤링됨 - 현재 색인 생성 안 됨” 상태가 늘 수 있습니다.
- sitemap에 없는 오타 URL도 홈페이지 canonical로 묶여 불필요한 중복 신호를 만듭니다.

구현 제안:

- `src/jumali/site.py`에서 `404.html`을 생성합니다.
- `tests/test_site.py`에 `404.html` 생성과 noindex 여부 테스트를 추가합니다.
- Cloudflare Pages 배포 후 실제 없는 URL이 404로 응답하는지 확인합니다.
- 필요하면 `_redirects` 또는 Pages 설정을 함께 점검합니다.

### 2. 행사 상세 페이지가 얇고 반복적임

증거:

- 샘플 행사 상세 텍스트 길이: 약 534~666자
- 구조가 대부분 `기본 정보`와 `방문 전 3분 체크` 반복입니다.
- 행사별 고유 설명은 제목, 날짜, 장소, 대상, 비용 정도입니다.

영향:

- `/events/*`가 27개 있어도 검색엔진에는 유사·얇은 페이지 묶음으로 보일 수 있습니다.
- AdSense 관점에서도 독자적 가치가 약해 보입니다.

구현 제안:

- `src/jumali/site.py`의 `_render_event_detail`을 보강합니다.
- 행사별로 다음 섹션을 추가합니다.
  - “이 행사가 아이와 맞는지 확인할 점”
  - “예약·요금 확인 포인트”
  - “장소/날씨 체크”
  - “비슷한 행사/관련 가이드”
- 템플릿 문장만 반복하지 말고, `target`, `fee`, `place`, `category`, `district`, `date_text`에 따라 조건부 문구를 다르게 만듭니다.

### 3. 일부 행사 품질이 “아이랑 무료 행사” 의도와 약하게 맞음

증거:

- MVP 데이터 27개 중 비용란 공백: 20개
- 넓거나 약한 대상 예시:
  - `[중랑구립면목정보도서관] 6월 주말N인문산책...` → `청소년 이상 성인 누구나`
  - `세워진 기억들: 시대의 얼굴이 된 공공미술` → `성인, 청소년 어린이는 성인 동반에 한해 가능`
  - `[구산동도서관마을] SF영화 속 우주과학...` → `청소년 및 성인 (*초등학생은 성인 보호자 동석 시 참여 가능)`

영향:

- 첫 화면에 성인/청소년 중심 행사가 먼저 나오면 사이트 주제가 흐려집니다.
- “서울 아이랑 무료 행사” 검색 유입자의 만족도가 떨어질 수 있습니다.

구현 제안:

- `src/jumali/transform.py`에 relevance score를 둡니다.
- `어린이`, `유아`, `초등`, `가족`, `부모`, `양육자`는 강한 가점으로 둡니다.
- `성인`, `청소년 이상 성인`, `성인 동반에 한해 가능`은 낮은 점수 또는 별도 “동반 가능” 그룹으로 내립니다.
- 홈 첫 화면에는 strong-match 행사만 먼저 노출합니다.
- `tests/test_transform.py`에 성인/청소년 중심 문구 회귀 테스트를 추가합니다.

### 4. 구별 페이지와 일부 신뢰 페이지가 짧음

증거:

- 샘플 구별 페이지 텍스트 길이: 약 439~665자
- `/about/`: 약 405자
- `/contact/`: 약 389자
- `/sources/`: 약 623자
- `/privacy/`: 약 515자

영향:

- 구별 페이지가 1개 행사만 가진 경우 thin page로 보일 수 있습니다.
- AdSense 승인 관점에서 소개·문의·출처·개인정보 페이지가 “있기는 하지만 충분히 운영되는 사이트”라는 느낌은 아직 약합니다.

구현 제안:

- `/about/`: 서비스 기준, 업데이트 방식, 제외 기준, 주의사항을 더 설명합니다.
- `/contact/`: 실제 연락 방법이 필요합니다. 태훈님이 공개 가능한 이메일 또는 문의 채널을 정해야 합니다.
- `/sources/`: 서울 열린데이터광장 API명, 갱신 주기, 무료/대상 필터 기준, 오분류 정정 원칙을 구체화합니다.
- `/privacy/`: AdSense/Analytics 도입 시 쿠키·광고 식별자 안내를 미리 보강합니다.
- `/seoul/gu/*`: 행사 1~2개짜리 구 페이지는 가이드/근처 구/이번 주말 링크를 붙이거나, 기준 미달이면 sitemap에서 제외하는 방식을 검토합니다.

### 5. 홈이 긴 반복 리스트라 사용자가 빨리 고르기 어려움

증거:

- 라이브 홈은 행사 카드가 길게 이어집니다.
- 시각 확인 결과, 기본 완성도는 괜찮지만 텍스트 카드가 반복되어 “긴 데이터 목록”처럼 보입니다.

영향:

- 광고/검색 유입 사용자가 원하는 행사까지 스크롤을 많이 해야 합니다.
- 카드가 많아도 각 카드가 비슷해 보여 체감 품질이 낮아질 수 있습니다.

구현 제안:

- 홈 상단에 빠른 선택 버튼을 추가합니다.
  - 이번 주말
  - 무료
  - 실내
  - 영유아
  - 초등
  - 구별 보기
- 행사 카드에 날짜/지역/대상/비용을 badge 형태로 분리합니다.
- 홈 첫 노출은 8~10개로 줄이고, 나머지는 `/seoul/free/`에서 보게 합니다.
- 제목이 긴 경우 카드에서 2줄 제한을 적용합니다.

## 1주일 콘텐츠/SEO 실험안 3개

### 실험 1. Soft 404 제거 후 핵심 URL 색인 재요청

목표:

- 기술 품질 리스크를 먼저 제거합니다.

7일 실행:

- 1일차: `404.html` 생성, 없는 URL 404 확인, 테스트 추가
- 2일차: 배포 확인 후 Search Console에서 `sitemap-index.xml` 제출
- 3~4일차: 홈, `/seoul/free/`, `/seoul/this-weekend/`, 대표 행사 상세 1~2개 URL 검사
- 5~7일차: “가져올 수 있음”, “크롤링 허용”, “사용자가 선언한 canonical” 상태 기록

성공 기준:

- 없는 URL이 404로 응답
- sitemap 읽기 성공
- 핵심 URL 3개 이상 URL 검사에서 크롤링 가능 상태 확인

중단 기준:

- 404 처리 후에도 없는 URL이 200으로 남음
- sitemap이 다시 `가져올 수 없음`으로 바뀜

### 실험 2. 가이드/신뢰 페이지 깊이 보강

목표:

- AdSense와 색인 보류를 줄일 만한 독자적 설명 콘텐츠를 늘립니다.

7일 실행:

- 기존 가이드 5개를 각각 1,500~2,500자 수준으로 확장합니다.
- `/sources/`, `/about/`, `/privacy/`, `/contact/`를 운영 기준 중심으로 보강합니다.
- 내부 링크를 “무료 행사 → 예약 체크리스트 → 대상 연령 확인 → 실내 행사” 흐름으로 강화합니다.

성공 기준:

- 가이드 5개와 신뢰 페이지 4개가 모두 얇은 페이지 기준을 벗어남
- Search Console에서 가이드 URL 발견/크롤링이 확인됨

중단 기준:

- 단순 문장 늘리기로 품질이 떨어짐
- 실제 문의 채널을 공개할 수 없어 `/contact/` 신뢰 보강이 막힘

### 실험 3. 행사 품질 스코어와 상세 페이지 보강

목표:

- “아이랑 무료 행사” 의도와 맞는 행사만 상단에 노출하고, `/events/*`의 독자적 가치를 높입니다.

7일 실행:

- relevance score를 추가합니다.
- strong-match, broad-match, weak-match로 행사 노출 우선순위를 나눕니다.
- 홈 첫 10개는 strong-match 위주로 제한합니다.
- 대표 행사 상세 10개를 필드 기반 안내문이 풍부하게 나오도록 템플릿을 보강합니다.

성공 기준:

- 홈 첫 화면에 성인 중심 행사가 나오지 않음
- 대표 상세 페이지 텍스트가 행사별로 차별화됨
- 테스트에 성인/청소년 중심 오분류 회귀 케이스가 추가됨

중단 기준:

- strong-match 행사가 너무 적어 홈이 비어 보임
- 공공데이터 필드만으로 품질 판단이 불안정함

## Search Console 작업 분리

태훈님이 직접 해야 하는 작업:

- Search Console 속성이 정확히 `https://jumalikids.com/` URL-prefix인지 확인합니다.
- 기존 `pages.dev` 속성이나 다른 도메인 속성과 헷갈리지 않게 현재 보고 있는 속성명을 확인합니다.
- sitemap 제출은 URL-prefix 속성에서 상대 경로로 넣습니다.
  - 우선: `sitemap-index.xml`
  - 보조: `gsc-sitemap.xml`
  - 필요 시: `sitemap.xml`
- URL 검사에서 아래 URL을 직접 확인합니다.
  - `https://jumalikids.com/`
  - `https://jumalikids.com/seoul/free/`
  - `https://jumalikids.com/seoul/this-weekend/`
  - 대표 행사 상세 1~2개
- `/contact/`에 공개할 이메일 또는 문의 채널을 정합니다.
- AdSense 신청은 404와 thin-page 보강 후 진행합니다.

에이전트가 할 작업:

- `404.html` 생성과 없는 URL 404 응답 검증
- `src/jumali/site.py`의 가이드·신뢰 페이지·행사 상세 템플릿 보강
- `src/jumali/transform.py`의 행사 relevance score와 성인/청소년 중심 행사 하향 처리
- `tests/test_site.py`, `tests/test_transform.py` 회귀 테스트 추가
- sitemap/robots/canonical/lastmod 재검증
- 배포 후 Googlebot UA로 `/`, sitemap, 없는 URL, 대표 상세 페이지를 재확인

## 다음 구현 카드에 넘길 파일/페이지 제안

파일:

- `src/jumali/site.py`
  - `404.html` 생성
  - `_render_event_detail` 보강
  - `_render_about`, `_render_contact`, `_render_sources`, `_render_privacy` 보강
  - 홈 빠른 선택/카드 badge/첫 노출 개수 조정
  - 구별 페이지 보강 또는 sitemap 포함 조건 조정
- `src/jumali/transform.py`
  - relevance score 추가
  - 성인/청소년 중심 broad-match 하향
  - strong-match 우선 정렬 기준 추가
- `tests/test_site.py`
  - 404 생성 테스트
  - 신뢰 페이지 최소 내용 테스트
  - 행사 상세 차별화 테스트
  - sitemap 포함/제외 기준 테스트
- `tests/test_transform.py`
  - `청소년 이상 성인`, `성인 동반에 한해 가능`, `누구나` 케이스 테스트
- `public/_headers`, `public/_redirects`, `public/robots.txt`, `public/sitemap*.xml`
  - site build 후 재생성·검증 대상

페이지:

- `/404.html`
- `/about/`
- `/contact/`
- `/sources/`
- `/privacy/`
- `/events/*`
- `/seoul/gu/*`
- `/guides/*`

## 최종 판정

- 기술 SEO 기본기: 보통 이상
- sitemap/canonical/robots: 대체로 정상
- 색인 확대 준비도: 아직 보강 필요
- AdSense 준비도: 아직 이른 편
- 가장 먼저 할 일: soft 404 제거
- 그다음 할 일: 행사 상세·구별·신뢰 페이지의 얇은 콘텐츠 보강
