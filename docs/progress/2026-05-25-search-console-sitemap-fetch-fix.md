# 주말아이 Search Console sitemap 가져오기 실패 보강 - 2026-05-25

## 증상

Google Search Console의 Sitemaps 화면에서 `/sitemap.xml` 상태가 `가져올 수 없음`으로 표시되고, 발견된 페이지 수가 0으로 표시됐다.

## 확인

- 운영 URL: `https://jumali-did.pages.dev/`
- `/`: 200 응답
- `/robots.txt`: 200 응답
- `/sitemap.xml`: 200 응답
- Googlebot 계열 User-Agent로 sitemap XML 접근 가능
- Python 기본 User-Agent는 Cloudflare에서 403으로 차단되는 현상 확인
- 기존 sitemap `<loc>`에는 한글 경로가 그대로 들어가 있었다.

## 조치

- sitemap `<loc>` URL을 ASCII-safe percent-encoded URL로 생성하도록 변경
- canonical URL도 동일한 URL escape 함수를 통과하도록 보강
- `/sitemap.txt` plain-text sitemap을 추가 생성
- `robots.txt`에 XML sitemap과 TXT sitemap을 모두 노출
- 테스트에 다음 검증 추가
  - sitemap XML 파싱 가능
  - 모든 `<loc>`가 ASCII URL
  - 한글 경로가 percent-encoded 됨
  - `sitemap.txt` 생성 및 robots 노출

## 검증

- `python -m pytest tests -q`: 21 passed
- `bash scripts/build.sh`: 성공
- 생성된 `public/sitemap.xml`: 40 URL, 모든 loc ASCII
- 생성된 `public/sitemap.txt`: 존재

## Search Console 다음 조치

배포 후 Search Console이 자동 재시도할 수 있다. 수동 확인 시에는 기존 `/sitemap.xml`을 다시 제출하고, 여전히 실패하면 fallback으로 아래도 제출한다.

```text
sitemap.txt
```
