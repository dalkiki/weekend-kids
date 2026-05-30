# A2: 주말아이 1순위 실험 운영 자동화

작성 시각: 2026-05-29 20:05 KST
작업 ID: `t_de86d605`
대상: `https://jumalikids.com/`

## 결론

주말아이 1순위 실험용 운영 헬스체크와 주간 리포트를 붙였습니다.

- daily silent check: 이상이 있을 때만 알림을 냅니다.
- weekly report: 정상이어도 월요일 아침에 1회 요약합니다.
- 상태 파일: 이전 정상 카운트와 마지막 성공 시각을 저장합니다.
- Search Console, AdSense, 공개 연락 채널 결정은 태훈님 직접 작업으로 분리했습니다.

## 생성한 파일

repo 안 파일:

- `src/jumali/ops_check.py`
  - GitHub Actions, 라이브 URL, sitemap XML, 404, 행사 수, canonical, 최종 업데이트, 품질 샘플을 점검합니다.
- `scripts/weekend_kids_daily_check.py`
  - repo 실행용 daily wrapper입니다.
- `scripts/weekend_kids_weekly_report.py`
  - repo 실행용 weekly wrapper입니다.
- `tests/test_ops_check.py`
  - event count, canonical, state path, 실패 판정, daily silence, weekly report, state baseline 회귀 테스트입니다.
- `docs/agent-team/2026-05-29-ops-automation-a2.md`
  - 이 운영 문서입니다.

Hermes profile script wrapper:

- `/home/hermes/.hermes/profiles/jumaliauto/scripts/weekend_kids_daily_check.sh`
- `/home/hermes/.hermes/profiles/jumaliauto/scripts/weekend_kids_weekly_report.sh`
- `/home/hermes/.hermes/profiles/jumaliauto/scripts/weekend_kids_daily_check.py`
- `/home/hermes/.hermes/profiles/jumaliauto/scripts/weekend_kids_weekly_report.py`

cron script는 Hermes 제약상 profile scripts 디렉터리 아래 상대 경로만 받을 수 있어서, profile wrapper가 repo의 `src/jumali/ops_check.py`를 호출하게 했습니다. 실제 cron에는 `.sh` wrapper를 연결했습니다. 이 wrapper는 Python 시작 시 환경에서 찍히는 `Hermes: openai SDK...` 배너를 제거해 daily silent check가 정상일 때 빈 stdout을 유지하게 합니다.

## 생성한 Hermes cron

- daily: `a5315f6325cb`
  - 이름: `주말아이 운영 daily silent check`
  - schedule: `30 8 * * *`
  - next run: `2026-05-30T08:30:00+09:00`
  - script: `weekend_kids_daily_check.sh`
  - mode: `no_agent=True`
  - deliver: `all`
  - 동작: 정상일 때 stdout이 비어 있으면 조용히 지나갑니다. 실패 또는 주의가 있으면 한국어 알림을 출력합니다.

- weekly: `9ddfa84a252a`
  - 이름: `주말아이 주간 운영 리포트`
  - schedule: `40 8 * * 1`
  - next run: `2026-06-01T08:40:00+09:00`
  - script: `weekend_kids_weekly_report.sh`
  - mode: `no_agent=True`
  - deliver: `all`
  - 동작: 정상이어도 주 1회 한국어 요약을 출력합니다.

## 상태 파일

기본 경로:

```text
$HERMES_HOME/state/weekend-kids-ops.json
```

`HERMES_HOME`이 없으면 아래 profile 경로를 사용합니다.

```text
/home/hermes/.hermes/profiles/jumaliauto/state/weekend-kids-ops.json
```

저장 항목:

- `last_run`: 마지막 점검 시각, 상태, 실패/주의 항목
- `last_success`: 마지막 실패 없는 점검의 live 행사 수, MVP 행사 수, sitemap URL 수, 최종 업데이트
- `last_clean`: 실패와 주의가 모두 없었던 마지막 점검

## 점검 항목

필수 점검:

- GitHub Actions 최근 scheduled run 상태와 시각
- `/`, `/robots.txt`, `/gsc-sitemap.xml`, `/sitemap-index.xml`, `/sitemap.xml` HTTP 상태
- sitemap XML 파싱 성공 여부와 loc 수
- 없는 URL이 404로 응답하는지
- live `/seoul/free/`, `/seoul/this-weekend/`, `/seoul/indoor/` 행사 수
- sitemap URL 수가 이전 정상 기준 대비 급감했는지
- 핵심 canonical이 `https://jumalikids.com/` 계열인지
- strong-match 부족 또는 adult/broad-match 의심 샘플
- 무료/요금 충돌 의심 샘플
- `최종 업데이트`가 3일 이상 오래됐는지

실패 기준:

- 최근 Actions run이 success가 아님
- 최근 scheduled run이 36시간 이상 없음
- 핵심 URL이나 sitemap이 200이 아님
- sitemap XML 파싱 실패
- 없는 URL이 404가 아님
- `/seoul/free/` 행사 수가 0
- live 행사 수, MVP 행사 수, sitemap URL 수가 이전 정상 대비 50% 이상 감소
- canonical이 `https://jumalikids.com/` 계열이 아님

주의 기준:

- 이번 주말 행사 수가 0이지만 전체 무료 행사는 남아 있음
- 공식 URL 누락 비율이 30% 이상
- 행사 수 또는 sitemap URL 수가 이전 정상 대비 30% 이상 감소
- adult/broad-match 의심 샘플이 있음
- 무료/요금 충돌 의심 샘플이 있음
- 최종 업데이트가 3일 이상 오래됨

## 검증 결과

repo 모듈 dry-run:

```bash
PYTHONPATH=src python -m jumali.ops_check --mode daily --force-output --no-state-write --repo-root .
```

결과 요약:

- exit_code: 0
- GitHub Actions 최근 scheduled run: success / completed
- 최근 run 시각: 2026-05-29 08:41 KST
- `/gsc-sitemap.xml`: HTTP 200, XML OK, loc 13개
- `/sitemap-index.xml`: HTTP 200, XML OK, loc 3개
- `/sitemap.xml`: HTTP 200, XML OK, loc 54개
- live free: 27건
- live this-weekend: 6건
- live indoor: 20건
- live 최종 업데이트: 2026-05-29
- 현재 실패: 없는 URL이 HTTP 200으로 응답합니다. B1의 soft 404 수정 전까지 daily check가 이 문제를 알립니다.
- 현재 주의: adult/broad-match 의심 샘플과 무료/요금 충돌 의심 샘플이 있습니다.

profile wrapper 검증:

```bash
/home/hermes/.hermes/profiles/jumaliauto/scripts/weekend_kids_daily_check.sh
```

결과:

- exit_code: 0
- alert stdout 출력 확인
- `Hermes: openai SDK...` 배너 제거 확인
- state file 생성 확인: `/home/hermes/.hermes/profiles/jumaliauto/state/weekend-kids-ops.json`
- 현재 라이브가 soft 404 실패 상태라 `last_success` baseline은 아직 갱신하지 않습니다. B1 수정 후 첫 실패 없는 점검에서 이전 정상 카운트가 저장됩니다.

강제 실패 시뮬레이션:

```bash
PYTHONPATH=src python -m jumali.ops_check --mode daily --force-output --no-state-write --repo-root . --simulate-soft-404
```

이 옵션은 없는 URL 상태를 HTTP 200으로 강제해 alert 포맷을 확인할 때 사용합니다. 현재 라이브도 실제로 HTTP 200이라 같은 실패가 잡힙니다.

테스트와 빌드:

```bash
python -m pytest tests/test_ops_check.py -q
```

결과:

```text
6 passed
```

```bash
python -m pytest tests -q
```

결과:

```text
35 passed
```

```bash
bash scripts/build.sh
```

결과:

```text
built public
```

```bash
git diff --check
```

결과:

```text
passed
```

## 태훈님 직접 작업

계정 클릭과 승인 작업은 자동화하지 않았습니다.

태훈님이 직접 확인할 일:

- Search Console URL-prefix 속성이 `https://jumalikids.com/`인지 확인 — 태훈님 완료 보고
- Search Console에서 `gsc-sitemap.xml`, `sitemap-index.xml` 제출 상태 확인
- URL 검사와 색인 요청 클릭 — 태훈님 완료 보고
  - `https://jumalikids.com/`
  - `https://jumalikids.com/seoul/free/`
  - `https://jumalikids.com/seoul/this-weekend/`
  - 대표 행사 상세 1~2개
- AdSense 신청, 사이트 연결, 정책 동의
- `/contact/` 공개 문의 채널 결정 — `thk8544@gmail.com`로 승인됨

## 다음 리뷰 포인트

- B1이 soft 404를 고치면 daily check가 정상 또는 주의 상태로 내려가는지 확인합니다.
- adult/broad-match 의심 항목은 B1 relevance score 개선 또는 Q1 검수에서 실제 노출 우선순위를 확인해야 합니다.
- 무료/요금 충돌 샘플은 raw 데이터 기준 의심 항목입니다. transform 필터가 이미 제외하더라도 주간 리포트에 샘플로 남겨 품질 회귀를 봅니다.
