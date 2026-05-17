# 주말아이 MVP

공공데이터 기반으로 서울 아이랑 갈만한 무료 행사 정보를 정리하는 정적 사이트 MVP입니다.

## 현재 확정 방향

- 사이트명: 주말아이
- 도메인: 무료 주소로 MVP 테스트 후 유료 도메인 검토
- 톤: 깔끔한 정보형
- 1차 데이터: 서울 열린데이터광장 `culturalEventInfo`
- 기본 무료 배포 후보: `https://jumali.pages.dev`

## 로컬 실행

샘플 키는 서울 열린데이터광장 정책상 최대 5건만 조회됩니다.
실서비스 수집에는 `SEOUL_OPENAPI_KEY` 환경변수에 발급받은 인증키를 넣습니다.

```bash
cp .env.example .env
```

```bash
set -a; . ./.env; set +a; bash scripts/build.sh
```

```bash
python -m http.server 8765 --directory public
```

## 테스트

```bash
python -m pytest tests -q
```

## Cloudflare Pages 설정

Cloudflare Pages에서 GitHub 저장소를 연결한 뒤 아래처럼 설정합니다.

- Project name: `jumali`
- Production branch: `main`
- Build command: `bash scripts/build.sh`
- Build output directory: `public`
- Environment variables:
  - `SEOUL_OPENAPI_KEY`: 서울 열린데이터광장 인증키
  - `JUMALI_EVENT_LIMIT`: `200`
  - `JUMALI_SITE_URL`: `https://jumali.pages.dev`

## 생성물

- `data/seoul_cultural_events_raw.json`: 서울 문화행사 원본 샘플
- `data/seoul_cultural_events_mvp.json`: 무료·어린이/가족 조건으로 정제한 MVP 후보
- `public/`: 정적 사이트 출력물

## 주의

- `.env`는 GitHub에 올리지 않습니다.
- 샘플 키에서는 후보 행사가 0건일 수 있습니다.
- `IS_FREE`가 무료여도 요금란에 금액이 있으면 무료 행사로 보지 않도록 보수적으로 필터링합니다.
- “미취학아동 입장불가” 같은 문구는 어린이 친화 행사로 오인하지 않도록 제외합니다.
