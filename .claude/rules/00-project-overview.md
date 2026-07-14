# Project Overview

## Purpose

- 이 프로젝트의 목적: 서울어린이대공원 방문객 대상 AI 코스 추천·도감 수집 모바일 서비스 "어대GO"의 AI 서버. `eodaego-server`(Spring Boot, BE)가 내부망을 통해서만 호출하는 내부 전용 API 서버로, LLM 기반 코스 추천·공식 데이터 크롤링·프롬프트/스케줄 관리 API를 담당한다.
- 해결하려는 문제: BE(Java) 스택에서 다루기 번거로운 영역(LLM SDK 호출·프롬프트 조립, 웹 크롤링, xlsx/csv 데이터 정규화)을 Python 생태계로 분리해 처리한다.
- 주요 사용자 또는 시스템 소비자: FE(Flutter)나 관리자 브라우저에서 직접 호출되지 않는다. 오직 `eodaego-server`(BE)만 커스텀 브리지 네트워크(`eodaego-internal`)를 통해 컨테이너 이름(`eodaego-ai`)으로 호출한다. 관리자 화면(프롬프트·크롤링 스케줄 설정)은 BE 내부 SSR 관리자 페이지가 담당하며, BE 서버 코드가 내부적으로 이 서비스의 CRUD API를 호출한다.

## Primary Stack

- Language: Python 3.12
- Framework: FastAPI (동기(`def`) 라우터 기반 — async 미사용)
- Runtime: uvicorn, uv로 의존성 관리(`pyproject.toml` + `uv.lock`)
- Database / storage: PostgreSQL (`eodaego_ai` 전용 인스턴스, BE의 `eodaego` DB와 완전 분리) + SQLAlchemy 2.0 동기 ORM + Alembic 마이그레이션
- Infra / deployment: Docker 단일 컨테이너(`eodaego-ai`, 내부 포트 8000, 호스트 포트 미바인딩), 커스텀 브리지 네트워크 `eodaego-internal`로 BE와만 통신. GitHub Actions(`.github/workflows/python-server-cicd.yml`)가 DockerHub에 푸시 후 SSH로 NAS에 배포

## Important directories

- app/domains/: 도메인별 API 계층(router/service/schema/model.py). 현재 `ai`(개인 LLM 서버 챗 프록시), `catalog`(동식물 도감 크롤링·CRUD, 위치 동기화 포함), `crawling`(스케줄 설정 CRUD + 혼잡도 크롤링), `facility`(놀이기구·운영시간 등 시설 정보), `prompt`(프롬프트 템플릿 CRUD), `weather`(날씨 스냅샷 크롤링)가 구현되어 있다. `recommendation`(AI 코스 추천, 서비스의 핵심 기능)은 `docs/superpowers/specs/2026-07-06-ai-service-separation-design.md`에 설계만 되어 있고 아직 코드가 없다 — 향후 이 컨벤션을 그대로 따라 추가될 예정.
- app/core/: 도메인 무관 공통 기반 — 설정(`config.py`), 내부 인증(`security.py`), 로깅(`logging.py`), 공통 에러 응답(`errors.py`)
- app/db/: SQLAlchemy `Base` 선언 및 동기 엔진/세션 팩토리
- app/scheduler/: 앱 기동 시 `schedule_config` 테이블을 조회해 APScheduler job을 재등록하는 registry
- alembic/: DB 마이그레이션 스크립트 (`env.py`가 `app.db.base.Base.metadata`를 target으로 사용)
- docs/superpowers/: 아키텍처·스캐폴딩 설계 의사결정 문서(배경/근거 확인용, 코드 아님)
- .issue/: 작업 대상 GitHub 이슈 본문 로컬 사본
- test/ or tests/: 해당 없음 — 테스트 코드를 작성하지 않는 정책(아래 제약 참고)
- scripts/: 해당 없음(현재 없음)

## Main commands

- install: `uv sync`
- lint: `uv run ruff check .`
- typecheck: `uv run mypy app`
- build: `docker build -t eodaego-ai .`
- unit-test / integration-test / e2e-test: 해당 없음 — 테스트 코드를 작성하지 않는 정책 (`30-testing-and-verification.md` 참고)
- run-dev: `APP_ENV=local uv run uvicorn app.main:app --reload --port 8000` (`.env.local` 필요)
- run-prod-like: `docker run --name eodaego-ai --network eodaego-internal --env-file .env.production eodaego-ai` (호스트 포트 `-p` 옵션 사용 금지)
- 참고(포맷): `uv run ruff format .`
- 참고(마이그레이션): `uv run alembic revision --autogenerate -m "설명"` → 리비전 파일 검토 → `uv run alembic upgrade head`

## Project-specific constraints

- 반드시 지켜야 하는 제약:
  - **모듈 임포트/컨테이너 기동 시점에 외부에서 모델·가중치를 동기 다운로드하는 라이브러리 도입 금지(원칙)**: 이 AI 서버는 호스트 포트 미바인딩 + `eodaego-internal` 내부망 전용으로 배포된다(인바운드만 차단, 아웃바운드는 개인 LLM 서버/Vertex AI 호출을 위해 열려 있어야 함). 다른 사내 내부망 전용 AI 서버에서 실제로 발생한 사례: TrustMark류 라이브러리가 `import` 시점에 인터넷에서 모델을 다운로드하는데, 다운로드가 실패하면 앱 자체가 기동되지 않아 `/health`조차 응답하지 못함. 향후 `recommendation` 도메인 등에 로컬 임베딩/토크나이저 모델을 쓰는 라이브러리를 추가할 경우, (1) 다운로드를 첫 실제 요청 시점으로 지연 로딩하거나 (2) 이미지 빌드 타임에 모델 가중치를 이미지 안에 미리 포함시켜 런타임 다운로드를 없앨 것. 임포트 시점 동기 다운로드 방식은 채택하지 않는다.
  - Docker 컨테이너 실행 시 `-p`(호스트 포트 퍼블리시) 옵션 사용 금지. AI는 `eodaego-internal` 네트워크에만 join하며, BE만 컨테이너 이름(`eodaego-ai`) + 내부 포트(8000)로 접근한다. uvicorn은 반드시 `--host 0.0.0.0`으로 바인딩한다(`127.0.0.1` 바인딩 시 같은 네트워크의 다른 컨테이너에서도 접근 불가).
  - `/health`를 제외한 모든 엔드포인트는 `X-Internal-Api-Key` 헤더 검증(`core/security.py`의 dependency)을 거쳐야 한다. 새 라우터를 추가할 때 `dependencies=[Depends(verify_internal_api_key)]`를 빠뜨리지 않는다.
  - 테스트 코드를 작성하지 않는다(pytest, testcontainers, `tests/` 디렉터리 등 전부 미사용) — 2026-07-09 결정, `eodaego-server`와 동일 정책. 신규 기능 검증은 Swagger UI(`/docs`)·curl 등 수동 확인 또는 `ruff`/`mypy` 정적 검사로 대체한다.
  - SQLAlchemy는 동기(sync) 엔진만 사용한다(`psycopg` sync 드라이버). 라우터는 `async def`가 아닌 `def`로 작성해 FastAPI가 스레드풀에서 실행하도록 둔다. APScheduler 크롤링 job도 동일한 동기 세션 패턴을 재사용한다.
  - CORS 미들웨어를 추가하지 않는다. AI는 브라우저(FE/관리자)에서 직접 호출되지 않고 BE만 호출한다.
  - AI는 크롤링한 동식물 도감 데이터(`catalog` 도메인의 `Animal`/`Plant` 테이블, 위치 동기화 포함)를 자체 DB에 저장한다(추천 로직 등 AI 내부용). 사용자에게 노출되는 도감 화면·수집 진행도는 여전히 BE 소유이며, AI → BE로 크롤링 결과를 반영하는 연동은 아직 미구현이다.
  - APScheduler jobstore는 `SQLAlchemyJobStore`가 아닌 기본 `MemoryJobStore`를 사용한다. 스케줄 "설정값"만 `schedule_config` 테이블에 저장하고, 앱 기동 시 `bootstrap_scheduler()`가 이를 읽어 `scheduler.add_job()`으로 재등록한다.
- 사용 금지 기술 / 패턴: Django/Flask(FastAPI로 확정), BE·AI를 하나의 docker-compose로 통합하는 방식(독립 배포 파이프라인 유지), OAuth2/JWT 기반 BE-AI 인증(사용자 인증이 아닌 내부 신뢰 채널이므로 정적 공유 키로 충분하다고 판단해 기각), APScheduler `SQLAlchemyJobStore`(job 함수 pickle 직렬화로 인한 재시작 시 역직렬화 실패 위험 때문에 기각)
- 현재 프로젝트에서 중요하게 보는 품질 기준: `ruff`(E, F, I, UP, B) 0 errors, `mypy --strict` 통과, 도메인 기반 폴더 구조 유지(파일당 200~400라인, router는 HTTP 계층만·비즈니스 로직은 service), 모든 예외를 `core/errors.py`의 공통 에러 응답 포맷으로 통일

## Change policy

- 어떤 변경은 허용되고 어떤 변경은 금지되는지: `app/domains/` 하위 신규 도메인(예: `recommendation`) 추가·기존 도메인 확장, `alembic` 리비전 추가, `core`/`db`/`scheduler`의 공통 로직 수정은 허용. 위 "Project-specific constraints"를 위반하는 변경(호스트 포트 바인딩 추가, 인증 dependency 제거, async 세션 도입, 테스트 코드 추가 등)은 금지.
- 지금 레포에서 수정해도 되는 범위: 이 레포(`eodaego-ai`) 전체 — AI 서버 담당자 1인이 전담.
- 절대 건드리면 안 되는 영역: `eodaego-server`(BE, Spring Boot), `eodaego-FE`(Flutter) — 별도 레포·별도 담당자이며, 이 레포 세션에서는 참고(read-only)만 한다. `docs/superpowers/`, `.issue/`, `.report/`는 의사결정·이력 기록용이므로 기존 문서를 임의로 재작성하지 않는다(새 문서 추가는 가능).
