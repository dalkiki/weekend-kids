# 주말아이 수익화 에이전트팀 이관 문서

마지막 갱신: 2026-05-29

## 목적

주말아이 프로젝트를 태훈님의 조건에 맞게 수익화한다.

조건:

- 현재 서버의 Hermes Agent 사용
- Kanban 기반 다중 에이전트 운영
- 비대면 운영
- 반복 작업 자동화
- 태훈님이 기초지식을 몰라도 계속 굴러가는 구조
- 사람과 계약하거나 영업하는 모델보다 AdSense·제휴·디지털 상품·공공데이터/SEO 자산 우선
- 과장 수익 주장, 스팸성 AI 콘텐츠, 무단 복제·무단 크롤링 금지

## Kanban 보드

- board: `weekend-kids-revenue`
- name: `주말아이 수익화 에이전트팀`
- default workdir: `/home/hermes/projects/weekend-kids`
- repo: `https://github.com/dalkiki/weekend-kids`
- canonical site: `https://jumalikids.com/`

확인 명령:

```bash
hermes kanban --board weekend-kids-revenue list
```

```bash
hermes kanban --board weekend-kids-revenue stats
```

```bash
hermes kanban --board weekend-kids-revenue dispatch
```

## 팀 구성

- `jumalilead`: 수익화 총괄·오케스트레이터
  - 시장-first 원칙으로 아이디어를 선별한다.
  - Kanban 작업을 분해하고 의존성을 관리한다.
  - 직접 구현보다 검증 가능한 실험 설계를 우선한다.

- `jumaliresearch`: 시장·수익 아이디어 리서처
  - 비대면·자동화·기초지식불요 조건의 아이디어를 발굴한다.
  - 검색 의도, 경쟁, 데이터 출처, 수익 방식, 리스크를 검증한다.

- `jumaliseo`: SEO·색인·콘텐츠 담당
  - Search Console, sitemap, 내부링크, 랜딩페이지, AdSense 준비도를 본다.
  - 얇은 자동 페이지를 피하고 검색 의도 중심 페이지를 제안한다.

- `jumalibuilder`: 구현 담당
  - Python 정적 사이트 생성기, 데이터 파이프라인, public 출력물을 수정한다.
  - 새 동작은 TDD로 진행한다.
  - 테스트, 빌드, 라이브 검증 전에는 완료로 말하지 않는다.

- `jumaliauto`: 자동화·운영 담당
  - GitHub Actions, Hermes cron, 데이터 품질 점검, 운영 리포트를 설계한다.
  - 조용히 실패하지 않도록 로그·알림·검증 기준을 둔다.

- `jumalireview`: 검수 담당
  - 수익성, SEO, 개인정보, 저작권, 공공데이터 출처, 과장 표현을 검토한다.
  - 승인/수정/보류 결론과 다음 카드를 제안한다.

## 초기 작업 그래프

독립 실행:

- `t_dbf53141` — R1: 비대면·자동화 수익 아이디어 12개 발굴 — `jumaliresearch`
- `t_e71eb872` — R2: 현재 주말아이 SEO·색인·AdSense 준비도 진단 — `jumaliseo`
- `t_5c88b2a2` — A1: 데이터 갱신·품질점검·보고 자동화 기회 진단 — `jumaliauto`

부모 완료 후 실행:

- `t_01e25447` — S1: 1차 실행 후보 3개 선정 및 7일 실험 설계 — `jumalilead`
  - parents: R1, R2, A1
- `t_243038a2` — B1: 1순위 수익화 실험을 사이트/코드에 반영 — `jumalibuilder`
  - parent: S1
- `t_de86d605` — A2: 1순위 실험 운영 자동화 또는 리포트 구축 — `jumaliauto`
  - parent: S1
- `t_78ef5165` — Q1: 수익화 실험 결과 검수 및 태훈님 승인안 작성 — `jumalireview`
  - parents: B1, A2

흐름:

```text
R1 아이디어 발굴 ┐
R2 SEO/AdSense 진단 ├─> S1 후보 선정 ─┬─> B1 구현
A1 자동화 진단 ┘                       ├─> A2 자동화
                                      └─> Q1 검수/승인안
```

## 운영 원칙

1. 시장성과 유입 경로를 먼저 검증한다.
2. 사람과 계약해야 하는 서비스형 모델은 후순위다.
3. AdSense는 느리고 트래픽 의존적이다. 수익은 보수적 가정으로만 계산한다.
4. 공공데이터는 공식 링크와 출처를 유지한다.
5. 무료·어린이 친화 같은 표현은 데이터가 확실할 때만 쓴다.
6. Search Console, AdSense 승인, 계정 클릭은 태훈님이 직접 해야 하는 작업으로 분리한다.
7. 코드 변경은 테스트와 빌드 확인 후 진행한다.
8. 자동화는 실패 알림과 검증 기준을 포함한다.

## 현재 사이트 상태 요약

- 커스텀 도메인: `https://jumalikids.com/`
- 현재 색인 개선용 보강:
  - `/guides/free-kids-events-seoul/`
  - `/guides/this-weekend-kids-plan/`
  - `/guides/rainy-day-indoor-kids-seoul/`
  - `/guides/age-target-check/`
  - `/guides/reservation-fee-checklist/`
- Search Console 제출 권장 sitemap: `gsc-sitemap.xml`
- 기본 수집 데이터: 서울 열린데이터광장 `culturalEventInfo`
- 자동 갱신: GitHub Actions `Daily 주말아이 refresh`, 매일 07:10 KST

## 태훈님이 개입해야 하는 순간

- Search Console에서 URL 검사/색인 생성 요청을 눌러야 할 때
- AdSense 신청/승인/사이트 연결이 필요할 때
- 제휴 계정 가입 또는 약관 동의가 필요할 때
- 수익화 실험이 사용자에게 보이는 광고/제휴 영역을 추가할 때
- 검수 담당이 `승인/수정/보류` 결정을 요청할 때

## 다음 작업 시작 방법

수동으로 한 번 dispatcher를 돌릴 때:

```bash
hermes kanban --board weekend-kids-revenue dispatch
```

작업 상태 보기:

```bash
hermes kanban --board weekend-kids-revenue list
```

특정 작업 상세 보기:

```bash
hermes kanban --board weekend-kids-revenue show t_dbf53141
```

작업 로그 보기:

```bash
hermes kanban --board weekend-kids-revenue log t_dbf53141
```
