# Testing And Verification

## Test strategy

- 이 프로젝트의 기본 테스트 전략: 테스트 코드를 작성하지 않는다(2026-07-09 결정, `eodaego-server`와 동일 정책). pytest/pytest-asyncio/testcontainers 등 테스트 관련 의존성과 `tests/` 디렉터리를 두지 않는다. 애초에 testcontainers 기반으로 구현되었으나, DB 컨테이너를 임의로 띄우는 것을 원하지 않아 전면 제거되었다.
- 단위 / 통합 / E2E 우선순위: 해당 없음.
- mock 사용 기준: 해당 없음.
- 회귀 테스트 기준: 코드 변경 후 `ruff`/`mypy` 정적 검사와 Swagger UI(`/docs`)·curl을 통한 수동 확인으로 대체한다.

## Commands

- 최소 검증 명령: `uv run ruff check .`
- 구현 후 반드시 실행해야 하는 명령: `uv run ruff check .`, `uv run ruff format .`, `uv run mypy app`
- PR 전 반드시 실행해야 하는 명령: 위 세 명령 전부 + 로컬 기동(`uv run uvicorn app.main:app --reload`)으로 `GET /health` 200 응답 확인
- 일부 모듈만 대상으로 빠르게 검증하는 명령: `uv run ruff check app/domains/<domain>`, `uv run mypy app/domains/<domain>`

## Evidence

- 테스트 성공/실패를 어떻게 기록할지: 자동화 테스트가 없으므로 `ruff`/`mypy` 실행 결과(PASS/FAIL, 에러 메시지 유무)를 보고서에 기록한다.
- 스크린샷 / 로그 / 요약 결과 작성 방식: Swagger UI(`/docs`) 스크린샷 또는 curl 요청/응답(JSON)을 결과로 첨부한다. `X-Internal-Api-Key` 실값 등 민감 정보는 마스킹한다.
- UI 작업 시 필요한 검증 산출물: 해당 없음(API 전용 서버, UI 없음).

## Failure handling

- 실패 시 우선 확인할 것: `.env.{APP_ENV}` 필수 값(`INTERNAL_API_KEY`, `DATABASE_URL`) 누락 여부 — 누락 시 `pydantic-settings`가 기동 시점에 `ValidationError`로 즉시 실패한다. 그다음 `GET /health` 응답의 `db` 필드로 DB 연결 여부를 확인한다.
- flaky 판단 기준: 해당 없음(자동화 테스트가 없어 flaky 개념 자체가 적용되지 않는다).
- 실패 결과 분석 시 필요한 로그 위치: 로컬은 stdout, 배포 환경은 `docker logs eodaego-ai`(표준 `logging` 모듈, 텍스트 포맷).
