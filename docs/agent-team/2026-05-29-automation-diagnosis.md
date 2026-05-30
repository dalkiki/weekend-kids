# 주말아이 데이터 갱신·품질점검·보고 자동화 진단

진단일: 2026-05-29 19:41 KST
담당 작업: `t_5c88b2a2` — A1 자동화 진단

## 1. 현재 운영 흐름 확인

현재 주말아이는 이미 기본 자동 갱신 뼈대가 있습니다.

- 저장소: `https://github.com/dalkiki/weekend-kids`
- 운영 도메인: `https://jumalikids.com/`
- Cloudflare Pages 산출물: `public/`
- 빌드 명령: `bash scripts/build.sh`
- 데이터 수집 코드: `src/jumali/collect.py`, `src/jumali/seoul_api.py`, `src/jumali/transform.py`
- 사이트 생성 코드: `src/jumali/site.py`
- GitHub Actions: `.github/workflows/daily-refresh.yml`
- Actions 스케줄: 매일 07:10 KST 의도, cron 값은 `10 22 * * *`
- 필요한 GitHub secret: `SEOUL_OPENAPI_KEY`
- Cloudflare 변수: `SEOUL_OPENAPI_KEY`, `JUMALI_EVENT_LIMIT=200`, `JUMALI_SITE_URL=https://jumalikids.com`

검증 결과:

- 로컬 데이터: raw 200건, MVP 27건
- 라이브 `/seoul/free/`: 행사 27건
- 라이브 `/seoul/this-weekend/`: 행사 6건
- 라이브 `/seoul/indoor/`: 행사 20건
- 라이브 sitemap XML: `gsc-sitemap.xml`, `sitemap-index.xml`, `sitemap-basic.xml`, `sitemap.xml` 모두 200 응답 및 XML 파싱 성공
- 라이브 `sitemap.xml`: URL 54개, loc 모두 ASCII-safe percent-encoded
- 최근 GitHub Actions 5회: 모두 `success`
- 로컬 테스트: `python -m pytest tests -q` → 23 passed

현재 Hermes cron에는 주말아이 전용 작업이 없습니다. 등록된 작업은 경찰시험 Google Tasks 정리, 시프티 어투 자동학습 2개뿐입니다.

## 2. 자동화 후보 5개와 우선순위

### 1순위: 주말아이 운영 헬스체크·리포트 Hermes cron

목표:

- GitHub Actions, 라이브 사이트, sitemap, 행사 수를 한 번에 점검합니다.
- 실패나 급감은 바로 알리고, 정상일 때는 주 1회 요약만 보냅니다.

확인 항목:

- 최근 GitHub Actions run 상태가 `success`인지
- 최근 run이 36시간 이상 오래되지 않았는지
- `https://jumalikids.com/`, `/robots.txt`, `/gsc-sitemap.xml`, `/sitemap-index.xml`, `/sitemap.xml`이 200인지
- sitemap XML 파싱이 되는지
- 라이브 `/seoul/free/` 행사 수가 0이 아닌지
- 라이브 행사 수가 이전 기준 대비 50% 이상 급감하지 않았는지
- 홈/목록 페이지의 `최종 업데이트`가 오래되지 않았는지

장점:

- 주말아이 repo를 고치지 않고도 바로 붙일 수 있습니다.
- GitHub/Cloudflare 계정 권한 없이 public API와 라이브 URL만으로 작동합니다.
- Telegram/WebUI 보고와 잘 맞습니다.

주의:

- 실패를 막는 게 아니라 발견·알림 자동화입니다.
- 기준값 저장용 작은 상태 파일이 필요합니다. 예: `~/.hermes/state/weekend-kids-ops.json`

### 2순위: GitHub Actions 데이터 품질 게이트

목표:

- 잘못된 수집 결과가 자동 커밋·배포되기 전에 Actions에서 막습니다.

확인 항목:

- `data/seoul_cultural_events_raw.json` raw_count가 0이면 실패
- `data/seoul_cultural_events_mvp.json` mvp_count가 0이면 실패 또는 강한 경고
- 직전 커밋 대비 mvp_count가 50% 이상 급감하면 실패 또는 수동 확인 요구
- 날짜 파싱 실패, 공식 URL 스킴 오류, 중복 slug 충돌, sitemap XML 파싱 오류를 실패 처리
- sitemap loc에 한글·공백이 직접 들어가면 실패

장점:

- 배포 전 차단이 가능합니다.
- 현재 테스트 구조에 자연스럽게 붙일 수 있습니다.

주의:

- 급감 기준에는 예외가 필요합니다. 계절·월말·연휴에는 실제 행사 수가 줄 수 있습니다.
- GitHub Actions 실패 알림을 태훈님이 놓칠 수 있으므로 1순위 Hermes cron 알림과 함께 쓰는 편이 안전합니다.

### 3순위: Cloudflare 배포 후 라이브 검증 자동화

목표:

- Actions가 성공했더라도 Cloudflare Pages에 실제 반영됐는지 확인합니다.

확인 항목:

- `https://jumalikids.com/`의 `최종 업데이트`가 최신인지
- canonical이 `https://jumalikids.com/` 계열인지
- `_headers` 적용으로 sitemap content-type이 `application/xml`인지
- `robots.txt`에 `gsc-sitemap.xml`, `sitemap-index.xml`, `sitemap.xml`, `sitemap-basic.xml`, `sitemap.txt`가 모두 노출되는지
- Cloudflare가 Python 기본 UA를 막더라도 Googlebot UA에서는 sitemap이 접근되는지

장점:

- "빌드는 성공했는데 라이브는 옛날 버전" 문제를 잡습니다.

주의:

- Cloudflare Pages 배포 완료까지 지연이 있을 수 있어 3~5분 재시도가 필요합니다.

### 4순위: 데이터 품질 샘플 감사 자동화

목표:

- 무료·어린이 친화 필터의 오탐을 줄입니다.

확인 항목:

- `IS_FREE=무료`이지만 `USE_FEE`에 `원`, `만원`, `천원`, `1만5천원` 같은 금액 패턴이 있는 항목
- `미취학아동입장불가`처럼 어린이 키워드가 있지만 제외 의미인 항목
- 공식 URL 누락 비율
- 종료일이 지난 항목 포함 여부
- 같은 제목·장소·일자의 중복 항목

장점:

- AdSense/SEO 관점에서 신뢰도를 지킵니다.
- 코드의 기존 보수적 필터와 방향이 맞습니다.

주의:

- 완전 자동 판정보다 "의심 항목 5개 샘플"을 운영 리포트에 싣는 방식이 안전합니다.

### 5순위: Search Console·AdSense 사용자 작업 추적 자동화

목표:

- 태훈님이 직접 눌러야 하는 계정 작업을 놓치지 않게 합니다.

자동화 가능:

- sitemap 라이브 검증 결과 정리
- Search Console에서 제출할 권장 경로 안내: `gsc-sitemap.xml`, 필요 시 `sitemap-index.xml`, `sitemap-basic.xml`
- AdSense 신청 전 About/Contact/Privacy/출처/콘텐츠 두께 점검 체크리스트 생성
- Kanban 카드나 Telegram 메시지로 "사용자 클릭 필요" 알림

사용자 직접 작업:

- Search Console 소유권 확인, URL 검사, 색인 생성 요청 클릭
- AdSense 계정 신청, 사이트 연결, 정책 동의
- 제휴 계정 가입·약관 동의
- 광고/제휴 영역 노출 승인

장점:

- 계정 권한이 필요한 일을 무리하게 자동화하지 않습니다.

주의:

- Search Console API를 붙이려면 Google OAuth 범위와 프로젝트 설정이 필요합니다. MVP에서는 수동 확인 + 리포트 안내가 낫습니다.

## 3. 구현 가능한 최소 자동화 1개 추천

추천: `주말아이 운영 헬스체크·주간 리포트 Hermes cron`

이유:

- 지금 바로 만들 수 있습니다.
- 추가 외부 계정 권한이 없어도 됩니다.
- GitHub Actions 성공 여부, Cloudflare 라이브 상태, sitemap 오류, 행사 수 급감을 모두 감시할 수 있습니다.
- 실패 시 조용히 지나가지 않고 Telegram/WebUI로 알릴 수 있습니다.
- 이후 A2 작업에서 품질 게이트나 Search Console 추적까지 확장하기 쉽습니다.

권장 동작:

- 매일 08:30 KST: 조용한 헬스체크 실행
- 실패 또는 위험 조건이 있으면 즉시 알림
- 매주 월요일 08:40 KST: 정상/주의/실패를 요약한 운영 리포트 전송

필요 파일 후보:

- `~/.hermes/scripts/weekend_kids_ops_check.py`
- 상태 파일: `~/.hermes/state/weekend-kids-ops.json`
- Hermes cron job: `no_agent=True` 또는 LLM 요약형 cron

## 4. 실패 시 알림 조건

즉시 알림 조건:

- GitHub Actions 최근 run 결론이 `success`가 아님
- 최근 scheduled run이 36시간 이상 없음
- 라이브 `/` 또는 `/robots.txt`가 200이 아님
- `gsc-sitemap.xml`, `sitemap-index.xml`, `sitemap.xml` 중 하나가 200이 아니거나 XML 파싱 실패
- sitemap content-type이 XML이 아님
- `/seoul/free/` 행사 수가 0
- 행사 수가 이전 정상 기준 대비 50% 이상 급감
- 라이브 페이지의 `최종 업데이트`가 3일 이상 오래됨
- canonical 또는 robots sitemap URL이 `jumalikids.com`이 아닌 옛 Pages URL로 되돌아감

주의 알림 조건:

- GitHub scheduled run이 2회 연속 30분 이상 지연
- 공식 URL 누락 비율이 30% 이상
- sitemap URL 수가 이전 대비 30% 이상 감소
- `this-weekend` 행사 수가 0이지만 전체 free 행사는 남아 있음
- Cloudflare 캐시가 너무 오래된 ETag를 유지하는 듯 보임

## 5. 검증 방법

로컬 검증:

```bash
python -m pytest tests -q
```

```bash
bash scripts/build.sh
```

데이터 카운트 검증:

```bash
python - <<'PY'
import json, pathlib
root = pathlib.Path('.')
raw = json.loads((root / 'data/seoul_cultural_events_raw.json').read_text(encoding='utf-8'))
mvp = json.loads((root / 'data/seoul_cultural_events_mvp.json').read_text(encoding='utf-8'))
print({'raw_count': len(raw), 'mvp_count': len(mvp)})
PY
```

라이브 sitemap 검증:

```bash
for url in \
  https://jumalikids.com/gsc-sitemap.xml \
  https://jumalikids.com/sitemap-index.xml \
  https://jumalikids.com/sitemap-basic.xml \
  https://jumalikids.com/sitemap.xml \
  https://jumalikids.com/robots.txt; do
  echo "===== $url ====="
  curl -sSIL --max-time 20 -A 'Googlebot/2.1 (+https://www.google.com/bot.html)' "$url" | sed -n '1,16p'
done
```

XML 파싱 검증:

```bash
python - <<'PY'
import urllib.request, xml.etree.ElementTree as ET
urls = [
  'https://jumalikids.com/gsc-sitemap.xml',
  'https://jumalikids.com/sitemap-index.xml',
  'https://jumalikids.com/sitemap-basic.xml',
  'https://jumalikids.com/sitemap.xml',
]
for url in urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Googlebot/2.1 (+https://www.google.com/bot.html)'})
    raw = urllib.request.urlopen(req, timeout=20).read()
    root = ET.fromstring(raw)
    print(url, root.tag, len(raw))
PY
```

## 6. 주간 운영 리포트 설계

Telegram/WebUI 메시지는 짧고 판단 중심으로 보냅니다.

권장 형식:

```text
주말아이 주간 운영 리포트
기간: YYYY-MM-DD ~ YYYY-MM-DD
상태: 정상 / 주의 / 실패

데이터
- raw: 200건
- 무료·어린이 후보: 27건
- 이번 주말: 6건
- 실내: 20건
- 전주 대비: +N / -N

갱신
- GitHub Actions 최근 run: success
- 최근 run 시각: YYYY-MM-DD HH:mm KST
- 라이브 최종 업데이트: YYYY-MM-DD

사이트맵
- gsc-sitemap.xml: 200, XML OK, 13 URL
- sitemap.xml: 200, XML OK, 54 URL
- robots.txt: OK

주의 항목
- 없음

태훈님 직접 작업
- Search Console에서 gsc-sitemap.xml 상태 확인
- AdSense 신청 전 Privacy/About/Contact 유지 확인

다음 추천
- 데이터 급감 게이트를 GitHub Actions에 추가
```

실패 알림은 더 짧게 보냅니다.

```text
주말아이 운영 알림: 실패
원인: sitemap.xml XML 파싱 실패
확인 URL: https://jumalikids.com/sitemap.xml
조치: 최근 Actions run과 public/sitemap.xml 생성 결과 확인 필요
```

## 7. 필요한 권한/API/사용자 작업

에이전트가 자동화 가능한 작업:

- GitHub public API로 최근 Actions run 확인
- GitHub Actions workflow 수정 및 품질 게이트 추가
- repo 내부 테스트·빌드 실행
- 라이브 URL, robots, sitemap HTTP 검증
- Hermes cron 생성 및 Telegram/WebUI 리포트 발송
- Kanban에 구현/검수 작업 연결

추가 권한이 있으면 자동화 가능한 작업:

- GitHub token 또는 `gh` CLI: 비공개 run 로그, workflow dispatch, issue 생성
- Cloudflare API token: Pages 배포 상태 확인, redeploy, 환경변수 존재 여부 확인
- Google Search Console API OAuth: sitemap 제출 상태, URL inspection 일부 자동 조회
- Google AdSense API/OAuth: 승인 상태 일부 조회. 단, 신청·정책 동의는 사용자 직접 작업

태훈님이 직접 해야 하는 작업:

- Search Console 소유권 확인, URL 검사, 색인 생성 요청
- AdSense 계정 신청, 사이트 연결, 광고 정책 동의
- Cloudflare/GitHub/Google 계정 권한 승인
- 광고·제휴 링크처럼 사용자에게 보이는 수익화 요소 승인

## 8. 결론

현재 기본 자동 갱신은 정상입니다. 다만 실패 알림과 운영 리포트가 아직 비어 있어, GitHub Actions나 Cloudflare가 조용히 실패하면 태훈님이 늦게 알 가능성이 있습니다.

1차로는 Hermes cron 기반 운영 헬스체크·주간 리포트를 붙이는 것이 가장 작고 안전합니다. 그다음 GitHub Actions 품질 게이트를 추가하면 "발견"에서 "배포 전 차단"으로 자동화 수준을 올릴 수 있습니다.
