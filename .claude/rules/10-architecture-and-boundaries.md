# Architecture And Boundaries

## High-level architecture

- 현재 시스템의 상위 구조: FE(Flutter) → BE(Spring Boot, `eodaego-server`) → AI(FastAPI, 이 레포) → 개인 LLM 서버(1순위) / Google Vertex AI(fallback, 순차 호출). 관리자 브라우저는 BE 내부 SSR 관리자 페이지(프롬프트·크롤링 스케줄 설정)만 접근하고, BE 서버 코드가 내부적으로 AI CRUD API를 호출한다. AI는 FE·관리자 브라우저 어디에도 직접 노출되지 않는다.
- 주요 계층: `router`(HTTP 요청/응답 + 인증 dependency) → `service`(비즈니스 로직, DB 조작) → `model`(SQLAlchemy ORM) / `schema`(Pydantic DTO). `core/`는 도메인 무관 공통 기반(설정/인증/로깅/에러), `db/`는 엔진·세션 팩토리, `scheduler/`는 앱 기동 시 스케줄 재구성.
- 외부 시스템 연동: 개인 LLM 서버(1순위) → Vertex AI(fallback) — `recommendation` 도메인 구현 예정, 아직 코드 없음. BE 관리자 API(도감 크롤링 결과 반영) — 아직 미구현.

## Module boundaries

- 각 주요 모듈의 책임: `app/domains/{crawling,prompt}`는 각자 자신의 router/service/schema/model만 소유한다. `app/core`는 여러 도메인이 공유하는 횡단 관심사(설정/인증/로깅/에러)만 담고 도메인 로직을 갖지 않는다. `app/db`는 SQLAlchemy `Base`와 엔진/세션 팩토리만 제공한다. `app/scheduler`는 도메인의 실제 job 함수를 `JOB_REGISTRY`로 참조만 하고 크롤링 로직 자체는 갖지 않는다(각 도메인이 소유).
- 모듈 간 허용 의존 방향: `domains → core, db` (단방향). `core`/`db`는 `domains`를 알지 못한다. `scheduler`는 `crawling` 도메인의 `ScheduleConfig` 모델만 참조하고, 실제 job 함수는 각 도메인이 `JOB_REGISTRY`에 등록하는 방식으로 역할을 분리한다(현재 `JOB_REGISTRY`는 비어있음 — `congestion_job`/`catalog_job` 미구현).
- 금지 의존 관계: `core`/`db` → `domains` 의존 금지. 도메인 간 model/service 직접 import는 **단방향**(A가 B를 import하되 B는 A를 import하지 않는 방향)이면 허용한다(2026-07-11 결정: 도메인 간 의존을 100% 차단하는 것이 비현실적이라 판단 — 예: 향후 `recommendation` 도메인이 `weather`/`crawling`(혼잡도) 도메인의 조회 함수를 직접 import). **순환 의존은 금지** — B가 다시 A를 import하는 관계가 생기면 공용 로직을 `core`로 승격해 순환을 끊는다.

## Data flow

- 요청/응답 흐름: BE → `X-Internal-Api-Key` 헤더 포함 요청 → router(인증 dependency 통과) → service → db(동기 session) → 응답은 Pydantic response schema로 직렬화. 예외는 `core/errors.py`가 `{success, data, error:{code, message}}` 공통 포맷으로 변환.
- 비동기 처리 흐름: HTTP 요청 자체는 FastAPI가 sync 함수를 스레드풀에서 처리한다(진짜 async 코드 없음). 크롤링/스케줄 작업은 APScheduler `BackgroundScheduler`가 별도 스레드에서 실행해 요청 처리(이벤트 루프)를 막지 않는다.
- 캐시/큐/스토리지 사용 방식: AI 자체에는 캐시/큐가 없다(Redis는 BE가 날씨 캐싱 용도로만 보유, AI와 무관). 스케줄 "설정값"만 Postgres(`schedule_config` 테이블)에 영속화하고, 실제 job 등록 상태는 메모리(`MemoryJobStore`)로만 유지한다 — 재시작 시 `bootstrap_scheduler()`가 DB에서 재구성한다.

## File / folder conventions

- 폴더 구조 규칙: 계층 기반이 아닌 도메인 기반. 새 기능은 `app/domains/<domain>/`에 `router.py`/`service.py`/`schema.py`/`model.py` 세트로 추가한다(도메인 수가 적고 각 도메인 책임이 명확해 계층 기반보다 파일당 책임이 뚜렷함).
- 새 파일 생성 시 위치 기준: 특정 도메인에서만 쓰이면 해당 `domains/<domain>/`에, 여러 도메인이 공유하면 `core/`로 승격한다.
- 공통 유틸 / 도메인 로직 / API 계층 분리 기준: `router`는 HTTP 계층(요청 파싱, 인증 dependency, 응답 모델 지정)만 담당하고 비즈니스 로직을 갖지 않는다. `service`는 순수 비즈니스 로직 + DB 조작을 담당한다(별도 repository 계층 없음). `model`은 SQLAlchemy ORM 매핑만, `schema`는 Pydantic 요청/응답 DTO만 담당한다.

## Extension points

- 기능 추가 시 먼저 참고해야 하는 패턴: `app/domains/prompt/`(가장 단순한 CRUD 도메인) 또는 `app/domains/crawling/`(CRUD + 스케줄러 연동)을 템플릿으로 삼는다.
- 기존 구현 재사용 포인트: 인증은 `core/security.py`의 `verify_internal_api_key`를 라우터 `dependencies`에 추가, DB 세션은 `db/session.py`의 `get_db` Depends, 에러는 `HTTPException`을 던지면 `core/errors.py`가 공통 포맷으로 자동 변환한다.
- 대표적으로 따라야 하는 파일 경로 예시: `app/domains/prompt/router.py`, `app/domains/prompt/service.py`, `app/domains/prompt/schema.py`, `app/domains/prompt/model.py`
