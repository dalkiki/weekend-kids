# 주말아이 Cloudflare Pages 다음 작업 계획

> **목적:** 내일 태훈님이 다시 물어보면 어디서부터 진행해야 하는지 바로 안내하기 위한 체크리스트.

## 현재 상태

- GitHub 저장소 생성 완료: https://github.com/dalkiki/weekend-kids
- 코드 업로드 완료
- 서울 열린데이터광장 인증키는 GitHub에 올리지 않음
- 로컬 빌드 성공
- 로컬 테스트 성공: `21 passed`
- 실제 데이터 수집 성공: 원본 200건, MVP 후보 22건

## 내일 태훈님이 할 첫 작업

Cloudflare Pages에서 GitHub 저장소를 연결한다.

1. Cloudflare 접속
   - https://dash.cloudflare.com/

2. 메뉴 이동
   - `Workers & Pages` 또는 `Pages`

3. 새 프로젝트 생성
   - `Create application` 또는 `Create a project`
   - `Connect to Git` 선택

4. GitHub 저장소 선택
   - `dalkiki/weekend-kids`

5. 빌드 설정 입력
   - Project name: `jumali`
   - Production branch: `main`
   - Build command: `bash scripts/build.sh`
   - Build output directory: `public`

6. 환경변수 추가
   - `SEOUL_OPENAPI_KEY`: 서울 열린데이터광장 인증키
   - `JUMALI_EVENT_LIMIT`: `200`
   - `JUMALI_SITE_URL`: `https://jumalikids.com`

7. 배포 실행
   - `Save and Deploy` 또는 `Deploy`

## 배포 후 시프티가 할 일

태훈님이 Cloudflare 배포 주소를 알려주면 아래를 확인한다.

1. 실제 사이트 접속 확인
2. 모바일 화면 확인
3. `/robots.txt` 확인
4. `/sitemap.xml` 확인
5. 행사 카드 링크 동작 확인
6. 서울 열린데이터광장 사용 URL에 넣을 최종 주소/문구 안내
7. Google Search Console 등록 절차 안내

## 태훈님에게 다시 안내할 한 줄

“내일은 Cloudflare에서 `dalkiki/weekend-kids` 저장소를 Pages 프로젝트로 연결하는 것부터 시작하시면 돼요.”
